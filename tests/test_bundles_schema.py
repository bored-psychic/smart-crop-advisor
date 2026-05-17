"""Tests that bundles.json is in structured form after migration."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_BUNDLES = ROOT / "web/lib/bundles.json"
BACKEND_BUNDLES_DIR = ROOT / "backend/services/i18n/bundles"


def test_web_bundles_use_structured_schema():
    data = json.loads(WEB_BUNDLES.read_text(encoding="utf-8"))
    for lang, entries in data.items():
        assert entries, f"lang {lang} empty"
        sample_key = next(iter(entries))
        sample = entries[sample_key]
        assert isinstance(sample, dict), f"{lang}/{sample_key} not structured"
        assert "text" in sample
        assert "context" in sample
        assert "role" in sample


def test_backend_bundles_mirror_web():
    web = json.loads(WEB_BUNDLES.read_text(encoding="utf-8"))
    for lang in web:
        path = BACKEND_BUNDLES_DIR / f"{lang}.json"
        assert path.exists(), f"missing backend bundle for {lang}"
        backend_entries = json.loads(path.read_text(encoding="utf-8"))
        assert set(backend_entries.keys()) == set(web[lang].keys())


def test_runtime_shim_handles_structured_entries(tmp_path):
    data = json.loads(WEB_BUNDLES.read_text(encoding="utf-8"))
    first_key = next(iter(data["en"]))
    assert isinstance(data["en"][first_key]["text"], str)
