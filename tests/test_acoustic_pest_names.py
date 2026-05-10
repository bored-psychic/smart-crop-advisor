"""Tests for acoustic pest-name normalization and Claude prediction coercion.

Covers the open-vocabulary contract: canonical names canonicalize, near-misses
canonicalize too (plurals, casing, short forms), genuinely novel pest names
pass through untouched, and the validator returns a structured (dict|None,
reason|None) pair instead of silently dropping malformed payloads.
"""
from backend.routers.acoustic import (
    _normalize_pest_name,
    _coerce_claude_prediction,
)


# --- _normalize_pest_name ----------------------------------------------------

def test_normalize_canonical_returns_canonical():
    assert _normalize_pest_name("Spider Mite") == "Spider Mite"
    assert _normalize_pest_name("Aphid Colony") == "Aphid Colony"
    assert _normalize_pest_name("Healthy Plant") == "Healthy Plant"


def test_normalize_strips_whitespace():
    assert _normalize_pest_name("  Spider Mite  ") == "Spider Mite"


def test_normalize_case_insensitive():
    assert _normalize_pest_name("aphid colony") == "Aphid Colony"
    assert _normalize_pest_name("HEALTHY PLANT") == "Healthy Plant"


def test_normalize_plural_fold_to_canonical():
    assert _normalize_pest_name("Spider Mites") == "Spider Mite"


def test_normalize_short_form_via_substring():
    # "Aphids" → singular "Aphid" → unambiguously a substring of "Aphid Colony"
    assert _normalize_pest_name("Aphids") == "Aphid Colony"


def test_normalize_unknown_pest_returns_none():
    # Truly novel names pass through; caller accepts the raw label.
    assert _normalize_pest_name("Mealybug") is None
    assert _normalize_pest_name("Leafhopper") is None
    assert _normalize_pest_name("Fall Armyworm") is None


def test_normalize_empty_returns_none():
    assert _normalize_pest_name("") is None
    assert _normalize_pest_name("   ") is None


# --- _coerce_claude_prediction -----------------------------------------------

def test_coerce_canonical_full_input():
    raw = {
        "pest": "Spider Mite",
        "is_pest": True,
        "severity": "medium",
        "freq_range": "1200-4000 Hz",
        "pattern": "Ultra-high freq scratching",
        "energy_level": "Moderate-high",
        "confidence": 60,
        "action": "Apply Abamectin 1.8% EC @ 0.5 ml/L.",
        "icon": "🟡",
        "top3": [["Spider Mite", 60], ["Thrips Infestation", 25], ["Healthy Plant", 15]],
    }
    result, reason = _coerce_claude_prediction(raw)
    assert reason is None
    assert result is not None
    assert result["pest"] == "Spider Mite"
    assert result["confidence"] == 60
    assert result["is_pest"] is True


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
    raw = {"pest": "Aphids", "confidence": 60}
    result, reason = _coerce_claude_prediction(raw)
    assert reason is None
    assert result["pest"] == "Aphid Colony"


def test_coerce_top3_keeps_unknown_names():
    raw = {
        "pest": "Mealybug",
        "confidence": 65,
        "icon": "🐛",
        "action": "Inspect for cottony masses.",
        "top3": [["Mealybug", 65], ["Scale Insect", 20], ["Healthy Plant", 15]],
    }
    result, reason = _coerce_claude_prediction(raw)
    assert reason is None
    names = [n for n, _ in result["top3"]]
    assert "Mealybug" in names
    assert "Scale Insect" in names
    assert "Healthy Plant" in names


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
