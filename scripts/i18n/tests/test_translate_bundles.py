# scripts/i18n/tests/test_translate_bundles.py
import json
from scripts.i18n.translate_bundles import compute_work_list

def test_force_all_includes_all_non_en_keys():
    bundles = {
        "en": {"a": {"text": "A", "context": "", "role": ""}},
        "hi": {"a": {"text": "ए", "context": "", "role": ""}},
    }
    work = compute_work_list(bundles, langs=["hi"], force_all=True, keys=None)
    assert work == [("hi", "a")]

def test_default_skips_already_translated():
    bundles = {
        "en": {"a": {"text": "A", "context": "", "role": ""},
                "b": {"text": "B", "context": "", "role": ""}},
        "hi": {"a": {"text": "ए", "context": "", "role": ""},
                "b": {"text": "", "context": "", "role": ""}},
    }
    work = compute_work_list(bundles, langs=["hi"], force_all=False, keys=None)
    assert work == [("hi", "b")]

def test_includes_when_translation_equals_en():
    bundles = {
        "en": {"a": {"text": "Submit", "context": "", "role": ""}},
        "hi": {"a": {"text": "Submit", "context": "", "role": ""}},
    }
    work = compute_work_list(bundles, langs=["hi"], force_all=False, keys=None)
    assert work == [("hi", "a")]
