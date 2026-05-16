"""Tests for backend/services/dosage_service.py"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock

from backend.services.dosage_service import _crop_stage_bucket, lookup, _generate_narrative
from backend.schemas.dosage import DosageAdvice


# ---------------------------------------------------------------------------
# 1. _crop_stage_bucket
# ---------------------------------------------------------------------------

def test_stage_bucket_seedling():
    assert _crop_stage_bucket(0) == "seedling"

def test_stage_bucket_vegetative():
    assert _crop_stage_bucket(45) == "vegetative"

def test_stage_bucket_flowering():
    assert _crop_stage_bucket(75) == "flowering"

def test_stage_bucket_harvest():
    assert _crop_stage_bucket(120) == "harvest"

# Boundary tests
def test_stage_bucket_boundary_day30_seedling():
    assert _crop_stage_bucket(30) == "seedling"

def test_stage_bucket_boundary_day31_vegetative():
    assert _crop_stage_bucket(31) == "vegetative"

def test_stage_bucket_boundary_day60_vegetative():
    assert _crop_stage_bucket(60) == "vegetative"

def test_stage_bucket_boundary_day61_flowering():
    assert _crop_stage_bucket(61) == "flowering"

def test_stage_bucket_boundary_day90_flowering():
    assert _crop_stage_bucket(90) == "flowering"

def test_stage_bucket_boundary_day91_harvest():
    assert _crop_stage_bucket(91) == "harvest"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(coro):
    return asyncio.run(coro)


def _make_mock_anthropic(text: str):
    """Build a mock AsyncAnthropic client that returns `text` as a message."""
    mock_content = MagicMock()
    mock_content.text = text

    mock_message = MagicMock()
    mock_message.content = [mock_content]

    mock_messages = MagicMock()
    mock_messages.create = AsyncMock(return_value=mock_message)

    mock_client = MagicMock()
    mock_client.messages = mock_messages

    return mock_client


# ---------------------------------------------------------------------------
# 2. Basic lookup — source == db, positive quantities/cost
# ---------------------------------------------------------------------------

def test_lookup_armyworm_maize_returns_db():
    # Patch market to avoid HTTP calls and Haiku to avoid API calls
    mock_client = _make_mock_anthropic("Spray the pesticide early morning. Apply before sunrise for best results.")
    with patch("backend.services.dosage_service.market.get_live_mandi_price", return_value=None):
        with patch("backend.services.dosage_service.AsyncAnthropic", return_value=mock_client):
            with patch("backend.services.dosage_service.get_settings") as mock_settings:
                mock_settings.return_value.ANTHROPIC_API_KEY = "test-key"
                result = run(lookup("armyworm", "maize", 45, 1.0, None))
    assert result.source == "db"
    assert result.total_quantity_ml > 0
    assert result.total_cost_inr > 0


# ---------------------------------------------------------------------------
# 3. Area scaling — 2 acres == exactly double 1 acre
# ---------------------------------------------------------------------------

def test_lookup_area_scaling():
    mock_client = _make_mock_anthropic("Apply pesticide per the recommended dosage. Follow instructions carefully.")
    with patch("backend.services.dosage_service.market.get_live_mandi_price", return_value=None):
        with patch("backend.services.dosage_service.AsyncAnthropic", return_value=mock_client):
            with patch("backend.services.dosage_service.get_settings") as mock_settings:
                mock_settings.return_value.ANTHROPIC_API_KEY = "test-key"
                r1 = run(lookup("armyworm", "maize", 45, 1.0, None))
                r2 = run(lookup("armyworm", "maize", 45, 2.0, None))
    assert r2.total_quantity_ml == pytest.approx(r1.total_quantity_ml * 2)
    assert r2.water_litres == pytest.approx(r1.water_litres * 2)


# ---------------------------------------------------------------------------
# 4. Unknown pest → llm_fallback
# ---------------------------------------------------------------------------

def test_lookup_unknown_pest_returns_llm_fallback():
    """Unknown pest should trigger LLM fallback and return source=='llm_fallback'."""
    llm_json = (
        '{"chemical_name": "Chlorpyrifos", "formulation": "EC 20%", '
        '"dose_ml_per_acre": 500, "water_l_per_acre": 200, '
        '"timing": "early morning", "reapply_days": 14, '
        '"cost_per_litre_inr": 450, "yield_loss_if_untreated_pct": 30}'
    )
    narrative_text = "Apply Chlorpyrifos early morning. Reapply after 14 days if needed."

    # First call returns JSON (llm_fallback system call), second returns narrative
    mock_content_json = MagicMock()
    mock_content_json.text = llm_json

    mock_content_narrative = MagicMock()
    mock_content_narrative.text = narrative_text

    mock_message_json = MagicMock()
    mock_message_json.content = [mock_content_json]

    mock_message_narrative = MagicMock()
    mock_message_narrative.content = [mock_content_narrative]

    mock_messages = MagicMock()
    mock_messages.create = AsyncMock(
        side_effect=[mock_message_json, mock_message_narrative]
    )

    mock_client = MagicMock()
    mock_client.messages = mock_messages

    with patch("backend.services.dosage_service.market.get_live_mandi_price", return_value=None):
        with patch("backend.services.dosage_service.AsyncAnthropic", return_value=mock_client):
            with patch("backend.services.dosage_service.get_settings") as mock_settings:
                mock_settings.return_value.ANTHROPIC_API_KEY = "test-key"
                result = run(lookup("unknown_pest_xyz", "maize", 45, 1.0, None))

    assert isinstance(result, DosageAdvice)
    assert result.source == "llm_fallback"


# ---------------------------------------------------------------------------
# 5. Normalization — mixed-case inputs equal lowercase result
# ---------------------------------------------------------------------------

def test_lookup_normalization():
    mock_client = _make_mock_anthropic("Apply pesticide correctly. Follow timing instructions.")
    with patch("backend.services.dosage_service.market.get_live_mandi_price", return_value=None):
        with patch("backend.services.dosage_service.AsyncAnthropic", return_value=mock_client):
            with patch("backend.services.dosage_service.get_settings") as mock_settings:
                mock_settings.return_value.ANTHROPIC_API_KEY = "test-key"
                r_lower = run(lookup("armyworm", "maize", 45, 1.0, None))
                r_mixed = run(lookup("Armyworm", "Maize", 45, 1.0, None))
    assert r_mixed.source == "db"
    assert r_mixed.chemical_name == r_lower.chemical_name
    assert r_mixed.total_quantity_ml == r_lower.total_quantity_ml


# ---------------------------------------------------------------------------
# 6. _generate_narrative returns a non-empty string
# ---------------------------------------------------------------------------

def test_generate_narrative_returns_string():
    """_generate_narrative should call Haiku and return a non-empty string."""
    expected_text = "Spray Chlorpyrifos EC at dawn. Reapply after 14 days if pests persist. The cost is worth it to protect your harvest."
    mock_client = _make_mock_anthropic(expected_text)

    with patch("backend.services.dosage_service.AsyncAnthropic", return_value=mock_client):
        with patch("backend.services.dosage_service.get_settings") as mock_settings:
            mock_settings.return_value.ANTHROPIC_API_KEY = "test-key"
            result = run(_generate_narrative(
                pest_id="armyworm",
                crop="maize",
                chemical_name="Chlorpyrifos",
                formulation="EC 20%",
                total_quantity_ml=500.0,
                water_litres=200.0,
                area_acres=1.0,
                total_cost_inr=225.0,
                roi_protected_inr=5000.0,
                reapply_days=14,
                timing="early morning",
            ))

    assert isinstance(result, str)
    assert len(result) > 0
    assert result == expected_text
