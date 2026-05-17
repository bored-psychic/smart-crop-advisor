"""Tests for the i18n language registry (Python side) and codegen."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_codegen_runs_and_produces_files(tmp_path, monkeypatch):
    """codegen_langs.py should regenerate both JS and Python outputs."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/i18n/codegen_langs.py")],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert (ROOT / "web/lib/langs.js").exists()
    assert (ROOT / "backend/services/i18n/langs.py").exists()


def test_langs_py_exports_expected_codes():
    from backend.services.i18n.langs import LANGS, is_supported, bcp47

    expected = {"en", "hi", "te", "ta", "kn", "mr", "bn", "gu", "pa", "ml"}
    assert set(LANGS.keys()) == expected
    assert is_supported("hi")
    assert not is_supported("xx")
    assert bcp47("hi") == "hi-IN"
    assert bcp47("en") == "en-IN"


def test_langs_have_required_fields():
    from backend.services.i18n.langs import LANGS

    for code, entry in LANGS.items():
        assert entry["code"] == code
        assert entry["bcp47"].endswith("-IN")
        assert entry["english_name"]
        assert entry["native_name"]


def test_langs_js_is_well_formed():
    js = (ROOT / "web/lib/langs.js").read_text()
    assert "window.LANGS" in js
    assert "window.bcp47" in js
    assert "hi-IN" in js
