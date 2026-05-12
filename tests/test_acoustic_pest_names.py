"""Tests for acoustic pest-name normalization and Claude prediction coercion.

Covers the open-vocabulary contract: canonical names canonicalize, near-misses
canonicalize too (plurals, casing, short forms), genuinely novel pest names
pass through untouched, and the validator returns a structured (dict|None,
reason|None) pair instead of silently dropping malformed payloads.

Taxonomy is the YAMNet 7-class set (see backend/core/constants.PEST_META):
Bee, Locust, Cicada, Cricket, Grasshopper, Beetle, Wasp. Mosquito, Fly, and
Moth/Butterfly were dropped from the canonical set because public bioacoustic
datasets lack ≥100 clean recordings per class — they now flow through the
open-vocabulary API path. Crop-specific names (Helicoverpa armigera, Fall
Armyworm, Rice Stem Borer, Banana Pseudostem Weevil) and silent pests (aphid,
whitefly, spider mite, thrips, fungal infection) are also not in this
taxonomy and must NOT canonicalize from this router.
"""
from backend.routers.acoustic import (
    _normalize_pest_name,
    _coerce_claude_prediction,
)


# --- _normalize_pest_name ----------------------------------------------------

def test_normalize_canonical_returns_canonical():
    assert _normalize_pest_name("Locust") == "Locust"
    assert _normalize_pest_name("Bee") == "Bee"
    assert _normalize_pest_name("Cicada") == "Cicada"


def test_normalize_strips_whitespace():
    assert _normalize_pest_name("  Locust  ") == "Locust"


def test_normalize_case_insensitive():
    assert _normalize_pest_name("locust") == "Locust"
    assert _normalize_pest_name("CICADA") == "Cicada"
    assert _normalize_pest_name("cricket") == "Cricket"


def test_normalize_plural_substring_match():
    # "Locusts" → singular "locust" → exact lower match → "Locust"
    assert _normalize_pest_name("Locusts") == "Locust"
    assert _normalize_pest_name("Bees") == "Bee"
    assert _normalize_pest_name("Beetles") == "Beetle"


def test_normalize_short_form_via_substring():
    # "Cicad" is an unambiguous short form — only one canonical class contains it.
    assert _normalize_pest_name("Cicad") == "Cicada"


def test_normalize_unknown_pest_returns_none():
    # Truly novel names pass through; caller accepts the raw label.
    assert _normalize_pest_name("Mealybug") is None
    assert _normalize_pest_name("Leafhopper") is None
    assert _normalize_pest_name("Pink Bollworm") is None


def test_normalize_old_taxonomy_pests_return_none():
    # Crop-specific labels from the previous PEST_META are no longer canonical
    # — they belong to the API-fallback open-vocabulary path now.
    assert _normalize_pest_name("Helicoverpa armigera") is None
    assert _normalize_pest_name("Fall Armyworm") is None
    assert _normalize_pest_name("Rice Stem Borer") is None
    assert _normalize_pest_name("Banana Pseudostem Weevil") is None


def test_normalize_data_scarce_species_return_none():
    # Mosquito, Fly, and Moth/Butterfly were dropped from the canonical 7-class
    # set because public bioacoustic datasets lack ≥100 clean clips per class.
    # They now flow through the open-vocabulary path (API fallback).
    assert _normalize_pest_name("Mosquito") is None
    assert _normalize_pest_name("Fly") is None
    assert _normalize_pest_name("Moth/Butterfly") is None


def test_normalize_removed_silent_pests_return_none():
    # Sap-suckers / microbial labels — vision pipeline territory.
    assert _normalize_pest_name("Aphid Colony") is None
    assert _normalize_pest_name("Whitefly Infestation") is None
    assert _normalize_pest_name("Spider Mite") is None
    assert _normalize_pest_name("Thrips Infestation") is None
    assert _normalize_pest_name("Early Fungal Infection") is None


def test_normalize_empty_returns_none():
    assert _normalize_pest_name("") is None
    assert _normalize_pest_name("   ") is None


# --- _coerce_claude_prediction -----------------------------------------------

def test_coerce_canonical_full_input():
    raw = {
        "pest": "Beetle",
        "is_pest": True,
        "severity": "medium",
        "freq_range": "100-1000 Hz",
        "pattern": "Coleopteran flight buzz",
        "energy_level": "Moderate",
        "confidence": 65,
        "action": "Inspect leaves for chewing damage and round exit holes.",
        "icon": "🪲",
        "top3": [
            ["Beetle", 65],
            ["Wasp", 20],
            ["Fly", 15],
        ],
    }
    result, reason = _coerce_claude_prediction(raw)
    assert reason is None
    assert result is not None
    assert result["pest"] == "Beetle"
    assert result["confidence"] == 65
    assert result["is_pest"] is True
    # Canonical entry must surface its PEST_META role/low_signal.
    assert result["role"] == "pest"
    assert result["low_signal"] is False


def test_coerce_canonical_pollinator_carries_role():
    raw = {"pest": "Bee", "confidence": 70}
    result, reason = _coerce_claude_prediction(raw)
    assert reason is None
    assert result["pest"] == "Bee"
    assert result["role"] == "pollinator"
    assert result["low_signal"] is False


def test_coerce_canonical_ambient_carries_role():
    raw = {"pest": "Cricket", "confidence": 60}
    result, reason = _coerce_claude_prediction(raw)
    assert reason is None
    assert result["pest"] == "Cricket"
    assert result["role"] == "ambient"


def test_coerce_open_vocabulary_minimal_input():
    raw = {
        "pest": "Mealybug",
        "confidence": 60,
        "severity": "medium",
        "action": "Inspect stems and leaf bases for white waxy masses.",
        "icon": "🐛",
    }
    result, reason = _coerce_claude_prediction(raw)
    assert reason is None
    assert result is not None
    assert result["pest"] == "Mealybug"
    assert result["icon"] == "🐛"
    assert "white waxy masses" in result["action"]


def test_coerce_synonym_canonicalized_to_pest_meta_name():
    raw = {"pest": "Bees", "confidence": 60}
    result, reason = _coerce_claude_prediction(raw)
    assert reason is None
    assert result["pest"] == "Bee"
    assert result["role"] == "pollinator"


def test_coerce_top3_keeps_unknown_names():
    raw = {
        "pest": "Mealybug",
        "confidence": 65,
        "icon": "🐛",
        "action": "Inspect for cottony masses.",
        "top3": [
            ["Mealybug", 65],
            ["Scale Insect", 20],
            ["Bee", 15],
        ],
    }
    result, reason = _coerce_claude_prediction(raw)
    assert reason is None
    names = [n for n, _ in result["top3"]]
    assert "Mealybug" in names
    assert "Scale Insect" in names
    assert "Bee" in names


def test_coerce_missing_pest_returns_reason():
    result, reason = _coerce_claude_prediction({})
    assert result is None
    assert reason is not None
    assert "pest" in reason.lower()


def test_coerce_non_dict_returns_reason():
    result, reason = _coerce_claude_prediction(None)
    assert result is None
    assert reason is not None


def test_coerce_is_pest_default_true_when_missing():
    raw = {"pest": "Mealybug", "confidence": 60}
    result, _ = _coerce_claude_prediction(raw)
    assert result["is_pest"] is True


def test_coerce_is_pest_false_passthrough():
    raw = {
        "pest": "Wind / Ambient Noise",
        "is_pest": False,
        "confidence": 40,
        "icon": "🌬️",
        "action": "No pest signature detected. Try recording closer to the crop.",
    }
    result, _ = _coerce_claude_prediction(raw)
    assert result["is_pest"] is False
    assert result["pest"] == "Wind / Ambient Noise"


def test_coerce_strips_markdown_json_fences():
    # Validator-side handling for a plain dict (the JSON-fence stripping itself
    # lives at the parse layer, but the coercer should still tolerate the
    # processed dict). Mainly here as a sanity check that confidence coerces
    # from a string.
    raw = {"pest": "Mealybug", "confidence": "60"}
    result, reason = _coerce_claude_prediction(raw)
    assert reason is None
    assert result["confidence"] == 60


def test_coerce_low_confidence_floor_drops_only_empty():
    # Sanity floor of 5 — drops empty hallucinations only.
    raw = {"pest": "Mealybug", "confidence": 1}
    result, reason = _coerce_claude_prediction(raw)
    assert result is None
    assert reason is not None
