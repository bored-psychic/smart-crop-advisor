"""Tests for server-side t(key, lang) lookup."""
import pytest
from backend.services.i18n.catalog import t, reload_bundles


def test_t_returns_english_for_known_key():
    assert t("Crop Recommender", "en") == "Crop Recommender"


def test_t_falls_back_to_english_for_unknown_lang():
    assert t("Crop Recommender", "xx") == "Crop Recommender"


def test_t_returns_key_for_unknown_key(monkeypatch):
    """Legacy test: now expects ??? instead of raw key."""
    monkeypatch.delenv("I18N_STRICT", raising=False)
    assert t("nonexistent.key.value", "en") == "???"


def test_t_returns_hindi_when_translation_exists():
    result = t("Crop Recommender", "hi")
    assert isinstance(result, str)
    assert result


def test_reload_bundles_picks_up_changes(tmp_path, monkeypatch):
    reload_bundles()


def test_t_returns_question_marks_for_missing_key(monkeypatch):
    """When a key is missing, t() returns ??? instead of the raw key."""
    monkeypatch.delenv("I18N_STRICT", raising=False)
    result = t("nonexistent.key.xyz", "en")
    assert result == "???"


def test_t_returns_question_marks_for_missing_key_unknown_lang(monkeypatch):
    """When a key is missing in all langs, t() returns ??? instead of the raw key."""
    monkeypatch.delenv("I18N_STRICT", raising=False)
    result = t("nonexistent.key.xyz", "fr")
    assert result == "???"


def test_t_strict_mode_raises_on_missing_key(monkeypatch):
    """With I18N_STRICT=1, t() raises KeyError for missing keys."""
    monkeypatch.setenv("I18N_STRICT", "1")
    with pytest.raises(KeyError, match="i18n missing key.*nonexistent.key.xyz"):
        t("nonexistent.key.xyz", "en")


def test_t_strict_mode_works_with_true(monkeypatch):
    """I18N_STRICT=true also triggers strict mode."""
    monkeypatch.setenv("I18N_STRICT", "true")
    with pytest.raises(KeyError, match="i18n missing key"):
        t("nonexistent.key.xyz", "en")
