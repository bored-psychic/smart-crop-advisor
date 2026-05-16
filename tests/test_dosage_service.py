"""Tests for backend/services/dosage_service.py"""

import pytest
import asyncio
from unittest.mock import patch

from backend.services.dosage_service import _crop_stage_bucket, lookup


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


# ---------------------------------------------------------------------------
# 2. Basic lookup — source == db, positive quantities/cost
# ---------------------------------------------------------------------------

def test_lookup_armyworm_maize_returns_db():
    # Patch market to avoid HTTP calls
    with patch("backend.services.dosage_service.market.get_live_mandi_price", return_value=None):
        result = run(lookup("armyworm", "maize", 45, 1.0, None))
    assert result.source == "db"
    assert result.total_quantity_ml > 0
    assert result.total_cost_inr > 0


# ---------------------------------------------------------------------------
# 3. Area scaling — 2 acres == exactly double 1 acre
# ---------------------------------------------------------------------------

def test_lookup_area_scaling():
    with patch("backend.services.dosage_service.market.get_live_mandi_price", return_value=None):
        r1 = run(lookup("armyworm", "maize", 45, 1.0, None))
        r2 = run(lookup("armyworm", "maize", 45, 2.0, None))
    assert r2.total_quantity_ml == pytest.approx(r1.total_quantity_ml * 2)
    assert r2.water_litres == pytest.approx(r1.water_litres * 2)


# ---------------------------------------------------------------------------
# 4. Unknown pest → NotImplementedError
# ---------------------------------------------------------------------------

def test_lookup_unknown_pest_raises():
    with patch("backend.services.dosage_service.market.get_live_mandi_price", return_value=None):
        with pytest.raises(NotImplementedError):
            run(lookup("unknown_pest_xyz", "maize", 45, 1.0, None))


# ---------------------------------------------------------------------------
# 5. Normalization — mixed-case inputs equal lowercase result
# ---------------------------------------------------------------------------

def test_lookup_normalization():
    with patch("backend.services.dosage_service.market.get_live_mandi_price", return_value=None):
        r_lower = run(lookup("armyworm", "maize", 45, 1.0, None))
        r_mixed = run(lookup("Armyworm", "Maize", 45, 1.0, None))
    assert r_mixed.source == "db"
    assert r_mixed.chemical_name == r_lower.chemical_name
    assert r_mixed.total_quantity_ml == r_lower.total_quantity_ml
