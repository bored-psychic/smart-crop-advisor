"""Server-side translation catalog.

Mirrors the frontend t() semantics: structured entries with `.text`,
English fallback, key fallback. Loaded lazily; can be reloaded for tests.
"""
import json
from pathlib import Path
from threading import Lock
from typing import Dict, Any

_BUNDLES_DIR = Path(__file__).parent / "bundles"
_cache: Dict[str, Dict[str, Any]] = {}
_lock = Lock()


def _load_lang(lang: str) -> Dict[str, Any]:
    path = _BUNDLES_DIR / f"{lang}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_loaded() -> None:
    with _lock:
        if _cache:
            return
        for path in _BUNDLES_DIR.glob("*.json"):
            _cache[path.stem] = json.loads(path.read_text(encoding="utf-8"))


def reload_bundles() -> None:
    """Clear cache; next t() call reloads from disk."""
    with _lock:
        _cache.clear()


def _entry_text(entry):
    if entry is None:
        return None
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        text = entry.get("text")
        if isinstance(text, str):
            return text
    return None


def t(key: str, lang: str) -> str:
    """Translate `key` into `lang`. Falls back to English, then to the key itself."""
    _ensure_loaded()
    lang_bundle = _cache.get(lang) or {}
    en_bundle = _cache.get("en") or {}
    return (
        _entry_text(lang_bundle.get(key))
        or _entry_text(en_bundle.get(key))
        or key
    )
