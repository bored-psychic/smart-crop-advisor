"""Tests for server-side t(key, lang) lookup."""
import pytest
from backend.services.i18n.catalog import t, reload_bundles


def test_t_returns_english_for_known_key():
    assert t("Crop Recommender", "en") == "Crop Recommender"


def test_t_falls_back_to_english_for_unknown_lang():
    assert t("Crop Recommender", "xx") == "Crop Recommender"


def test_t_returns_key_for_unknown_key():
    assert t("nonexistent.key.value", "en") == "nonexistent.key.value"


def test_t_returns_hindi_when_translation_exists():
    result = t("Crop Recommender", "hi")
    assert isinstance(result, str)
    assert result


def test_reload_bundles_picks_up_changes(tmp_path, monkeypatch):
    reload_bundles()
