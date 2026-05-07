from __future__ import annotations

import json
from pathlib import Path

LANGUAGES: dict[str, str] = {
    'English':            'en',
    'हिंदी (Hindi)':     'hi',
    'తెలుగు (Telugu)':   'te',
    'தமிழ் (Tamil)':     'ta',
    'ಕನ್ನಡ (Kannada)':   'kn',
    'मराठी (Marathi)':   'mr',
    'বাংলা (Bengali)':   'bn',
    'ગુજરાતી (Gujarati)': 'gu',
    'ਪੰਜਾਬੀ (Punjabi)':  'pa',
}

# Loaded once via C JSON parser — orders of magnitude faster than a Python dict literal.
BUNDLES: dict[str, dict[str, str]] = json.loads(
    (Path(__file__).parent / 'bundles.json').read_text(encoding='utf-8')
)

# Fallback bundle for module-level calls (before Streamlit session exists).
_active: dict[str, str] = BUNDLES['en']


def activate(lang_code: str) -> None:
    """Store active language per Streamlit session. Falls back to global for non-session contexts."""
    global _active
    bundle = BUNDLES.get(lang_code, BUNDLES['en'])
    _active = bundle
    try:
        import streamlit as st
        st.session_state['_lang_bundle'] = bundle
    except Exception:
        pass


def T(text: str) -> str:
    """Translate text. Per-session safe — reads from st.session_state when available."""
    if not text:
        return text
    try:
        import streamlit as st
        bundle = st.session_state.get('_lang_bundle', _active)
    except Exception:
        bundle = _active
    return bundle.get(str(text), str(text))


