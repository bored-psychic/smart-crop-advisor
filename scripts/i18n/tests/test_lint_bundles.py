# scripts/i18n/tests/test_lint_bundles.py
import pytest
from scripts.i18n.lint_bundles import lint

def _entry(text): return {"text": text, "context": "", "role": ""}

def test_passes_on_clean_bundle():
    bundles = {
        "en": {"a": _entry("Hello {name}")},
        "hi": {"a": _entry("नमस्ते {name}")},
    }
    errors = lint(bundles, non_en_langs=["hi"])
    assert errors == []

def test_fails_when_key_missing():
    bundles = {"en": {"a": _entry("A"), "b": _entry("B")},
               "hi": {"a": _entry("ए")}}
    errors = lint(bundles, non_en_langs=["hi"])
    assert any("missing key" in e and "b" in e for e in errors)

def test_fails_when_translation_equals_en():
    bundles = {"en": {"a": _entry("Submit")},
               "hi": {"a": _entry("Submit")}}
    errors = lint(bundles, non_en_langs=["hi"])
    assert any("equals en" in e for e in errors)

def test_fails_on_placeholder_mismatch():
    bundles = {"en": {"a": _entry("Hi {name}")},
               "hi": {"a": _entry("नमस्ते")}}
    errors = lint(bundles, non_en_langs=["hi"])
    assert any("placeholder" in e for e in errors)

def test_fails_on_extra_key_in_non_en():
    bundles = {"en": {"a": _entry("A")},
               "hi": {"a": _entry("ए"), "z": _entry("zed")}}
    errors = lint(bundles, non_en_langs=["hi"])
    assert any("extra key" in e and "z" in e for e in errors)
