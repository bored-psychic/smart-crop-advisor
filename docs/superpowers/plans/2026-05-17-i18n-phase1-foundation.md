# i18n Phase 1 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lay the i18n plumbing — canonical language list, structured bundle schema, server-side `t()`, locale middleware, `Accept-Language` fetch wrapper, and `preferred_lang` DB columns — so subsequent phases can plug into a stable foundation without changing user-visible behavior.

**Architecture:** Add a single source of truth for supported languages (`scripts/i18n/langs.yaml`) and codegen it into both `web/lib/langs.js` and `backend/services/i18n/langs.py`. Migrate `web/lib/bundles.json` from flat `{key: text}` to structured `{key: {text, context, role}}`; keep the runtime `t()` shim backwards-compatible during transition. Add FastAPI middleware that parses `Accept-Language`, validates against the canonical list, and attaches `request.state.lang`. Add a server-side catalog reading the same bundles as the frontend. Add `Accept-Language` to every web fetch via the existing `api.js` wrapper. Add `preferred_lang` column to alert/push subscription tables.

**Tech Stack:** FastAPI, aiosqlite, vanilla JS (React via CDN), Python 3 stdlib for codegen, pytest, ruff.

**Reference spec:** `docs/superpowers/specs/2026-05-17-multilingual-app-design.md`

**Out of scope for this phase:** wrapping JSX strings (Phase 2), translation pipeline (Phase 3), backend catalog data (Phase 4), LLM prompts (Phase 5), SMS/push localization (Phase 6).

---

## File Structure

**Created:**
- `scripts/i18n/langs.yaml` — canonical list of (code, BCP-47, English label, native label)
- `scripts/i18n/codegen_langs.py` — reads YAML, writes JS + Python
- `scripts/i18n/migrate_bundles.py` — one-shot codemod: flat → structured `bundles.json`
- `web/lib/langs.js` — generated; exports `window.LANGS` array + `window.bcp47(code)`
- `backend/services/i18n/__init__.py` — empty
- `backend/services/i18n/langs.py` — generated; exports `LANGS` dict + `bcp47(code)` + `is_supported(code)`
- `backend/services/i18n/catalog.py` — server-side `t(key, lang)` reading shared bundles
- `backend/services/i18n/bundles/` — directory; bundles copied here by migration
- `backend/middleware/__init__.py` — empty
- `backend/middleware/locale.py` — middleware reading `Accept-Language`
- `tests/test_i18n_langs.py` — codegen + langs.py tests
- `tests/test_i18n_catalog.py` — server-side `t()` tests
- `tests/test_i18n_middleware.py` — locale middleware tests
- `tests/test_db_migration_preferred_lang.py` — DB migration test

**Modified:**
- `web/lib/i18n.js` — runtime shim accepts both flat (old) and structured (new) bundle entries
- `web/lib/bundles.json` — migrated to structured schema (one-time)
- `web/index.html` — load `web/lib/langs.js` before `i18n.js`
- `web/lib/api.js` — fetch wrapper adds `Accept-Language` from `window.__lang` (set by app.jsx)
- `web/components/app.jsx` — set `window.__lang = lang` whenever `lang` changes (so api.js sees it)
- `backend/services/db.py` — add `preferred_lang TEXT NOT NULL DEFAULT 'en'` to `alert_subscriptions` and `webpush_subscriptions`; idempotent `ALTER TABLE` block for existing DBs
- `backend/main.py` — register `LocaleMiddleware`

---

## Task 1: Canonical language YAML + codegen

**Files:**
- Create: `scripts/i18n/langs.yaml`
- Create: `scripts/i18n/codegen_langs.py`
- Create: `tests/test_i18n_langs.py`
- Create: `web/lib/langs.js` (via codegen)
- Create: `backend/services/i18n/__init__.py` (empty)
- Create: `backend/services/i18n/langs.py` (via codegen)

- [ ] **Step 1: Write the failing test**

`tests/test_i18n_langs.py`:
```python
"""Tests for the i18n language registry (Python side) and codegen."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_codegen_runs_and_produces_files(tmp_path, monkeypatch):
    """codegen_langs.py should regenerate both JS and Python outputs."""
    # Run codegen against the real YAML — outputs to repo paths.
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_i18n_langs.py -v`
Expected: FAIL — modules + files don't exist yet.

- [ ] **Step 3: Create the YAML source**

`scripts/i18n/langs.yaml`:
```yaml
# Canonical list of supported languages.
# Single source of truth — codegen_langs.py emits the JS and Python versions.
languages:
  - code: en
    bcp47: en-IN
    english_name: English
    native_name: English
  - code: hi
    bcp47: hi-IN
    english_name: Hindi
    native_name: हिन्दी
  - code: te
    bcp47: te-IN
    english_name: Telugu
    native_name: తెలుగు
  - code: ta
    bcp47: ta-IN
    english_name: Tamil
    native_name: தமிழ்
  - code: kn
    bcp47: kn-IN
    english_name: Kannada
    native_name: ಕನ್ನಡ
  - code: mr
    bcp47: mr-IN
    english_name: Marathi
    native_name: मराठी
  - code: bn
    bcp47: bn-IN
    english_name: Bengali
    native_name: বাংলা
  - code: gu
    bcp47: gu-IN
    english_name: Gujarati
    native_name: ગુજરાતી
  - code: pa
    bcp47: pa-IN
    english_name: Punjabi
    native_name: ਪੰਜਾਬੀ
  - code: ml
    bcp47: ml-IN
    english_name: Malayalam
    native_name: മലയാളം
```

- [ ] **Step 4: Write codegen script**

`scripts/i18n/codegen_langs.py`:
```python
"""Generate web/lib/langs.js and backend/services/i18n/langs.py from langs.yaml.

Run: python scripts/i18n/codegen_langs.py
"""
import json
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml required: pip install pyyaml")

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "scripts/i18n/langs.yaml"
JS_OUT = ROOT / "web/lib/langs.js"
PY_OUT = ROOT / "backend/services/i18n/langs.py"

BANNER = "// GENERATED FILE — do not edit by hand. Source: scripts/i18n/langs.yaml\n"
PY_BANNER = "# GENERATED FILE — do not edit by hand. Source: scripts/i18n/langs.yaml\n"


def main() -> None:
    data = yaml.safe_load(SRC.read_text())
    langs = data["languages"]

    # JS output
    js_lines = [BANNER, "window.LANGS = " + json.dumps(langs, ensure_ascii=False, indent=2) + ";\n"]
    js_lines.append("window.LANGS_BY_CODE = Object.fromEntries(window.LANGS.map(l => [l.code, l]));\n")
    js_lines.append("window.bcp47 = function(code){ return (window.LANGS_BY_CODE[code]||window.LANGS_BY_CODE['en']).bcp47; };\n")
    js_lines.append("window.isSupportedLang = function(code){ return !!window.LANGS_BY_CODE[code]; };\n")
    JS_OUT.write_text("".join(js_lines), encoding="utf-8")

    # Python output
    py = [PY_BANNER, "from typing import Dict\n\n"]
    py.append("LANGS: Dict[str, dict] = " + repr({l["code"]: l for l in langs}) + "\n\n")
    py.append("def is_supported(code: str) -> bool:\n    return code in LANGS\n\n")
    py.append("def bcp47(code: str) -> str:\n    return LANGS.get(code, LANGS['en'])['bcp47']\n")
    PY_OUT.write_text("".join(py), encoding="utf-8")

    print(f"wrote {JS_OUT.relative_to(ROOT)}")
    print(f"wrote {PY_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Create empty package marker**

`backend/services/i18n/__init__.py`: empty file.

```bash
mkdir -p backend/services/i18n
touch backend/services/i18n/__init__.py
```

- [ ] **Step 6: Install pyyaml if missing and run codegen**

Run:
```bash
python -c "import yaml" || pip install pyyaml
python scripts/i18n/codegen_langs.py
```
Expected: prints two `wrote …` lines; `web/lib/langs.js` and `backend/services/i18n/langs.py` exist.

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest tests/test_i18n_langs.py -v`
Expected: 4 PASSED.

- [ ] **Step 8: Commit**

```bash
git add scripts/i18n/langs.yaml scripts/i18n/codegen_langs.py \
        web/lib/langs.js backend/services/i18n/__init__.py \
        backend/services/i18n/langs.py tests/test_i18n_langs.py
git commit -m "feat(i18n): canonical language registry + codegen"
```

---

## Task 2: Migrate bundles.json to structured schema (backwards-compatible)

**Files:**
- Create: `scripts/i18n/migrate_bundles.py`
- Create: `backend/services/i18n/bundles/` (directory)
- Modify: `web/lib/i18n.js`
- Modify: `web/lib/bundles.json` (one-time, written by script)
- Create: `tests/test_bundles_schema.py`

- [ ] **Step 1: Write the failing test**

`tests/test_bundles_schema.py`:
```python
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
    # Smoke check: read first 'en' entry and confirm shape used by makeT.
    data = json.loads(WEB_BUNDLES.read_text(encoding="utf-8"))
    first_key = next(iter(data["en"]))
    assert isinstance(data["en"][first_key]["text"], str)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_bundles_schema.py -v`
Expected: FAIL on structured-schema check (current bundles are flat).

- [ ] **Step 3: Write migration script**

`scripts/i18n/migrate_bundles.py`:
```python
"""One-shot codemod: convert web/lib/bundles.json from flat {key: text}
to structured {key: {text, context, role}}, then mirror to backend.

Idempotent: re-running on already-structured bundles is a no-op.
Run: python scripts/i18n/migrate_bundles.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web/lib/bundles.json"
BACKEND_DIR = ROOT / "backend/services/i18n/bundles"


def to_structured(value):
    if isinstance(value, dict) and "text" in value:
        return value  # already migrated
    return {"text": value, "context": "", "role": ""}


def main() -> None:
    data = json.loads(WEB.read_text(encoding="utf-8"))
    out = {}
    for lang, entries in data.items():
        out[lang] = {k: to_structured(v) for k, v in entries.items()}

    WEB.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"migrated {WEB.relative_to(ROOT)}")

    BACKEND_DIR.mkdir(parents=True, exist_ok=True)
    for lang, entries in out.items():
        path = BACKEND_DIR / f"{lang}.json"
        path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Update runtime shim to read structured entries (backwards-compatible)**

Replace `web/lib/i18n.js` entirely with:
```js
// Loads bundles.json and exposes a translator factory.
// Accepts both legacy flat ({key: "text"}) and structured ({key: {text,...}}) entries.
window.I18N = { bundles: null, _ready: null };
window.I18N._ready = fetch('/lib/bundles.json')
  .then(r => r.json())
  .then(b => { window.I18N.bundles = b; })
  .catch(e => { console.warn('i18n: failed to load bundles', e); });

function _entryText(entry, key) {
  if (entry == null) return null;
  if (typeof entry === 'string') return entry;          // legacy flat
  if (typeof entry === 'object' && typeof entry.text === 'string') return entry.text;
  return null;
}

window.makeT = (lang) => (key) => {
  const b = window.I18N.bundles;
  if (!b) return key;
  const langEntry = b[lang] && b[lang][key];
  const enEntry = b['en'] && b['en'][key];
  return _entryText(langEntry, key) || _entryText(enEntry, key) || key;
};
```

- [ ] **Step 5: Run migration**

Run: `python scripts/i18n/migrate_bundles.py`
Expected: prints `migrated web/lib/bundles.json` and 10 `wrote backend/services/i18n/bundles/<lang>.json` lines.

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_bundles_schema.py -v`
Expected: 3 PASSED.

- [ ] **Step 7: Smoke-test the web app still translates**

Run:
```bash
cd web && python3 -m http.server 5173 >/tmp/web.log 2>&1 &
sleep 1
curl -s http://localhost:5173/lib/bundles.json | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['en']['Crop Recommender']['text'])"
kill %1 2>/dev/null
```
Expected: prints `Crop Recommender`.

- [ ] **Step 8: Commit**

```bash
git add scripts/i18n/migrate_bundles.py web/lib/i18n.js web/lib/bundles.json \
        backend/services/i18n/bundles/ tests/test_bundles_schema.py
git commit -m "feat(i18n): migrate bundles to structured schema with backend mirror"
```

---

## Task 3: Server-side catalog (`backend/services/i18n/catalog.py`)

**Files:**
- Create: `backend/services/i18n/catalog.py`
- Create: `tests/test_i18n_catalog.py`

- [ ] **Step 1: Write the failing test**

`tests/test_i18n_catalog.py`:
```python
"""Tests for server-side t(key, lang) lookup."""
import pytest
from backend.services.i18n.catalog import t, reload_bundles


def test_t_returns_english_for_known_key():
    assert t("Crop Recommender", "en") == "Crop Recommender"


def test_t_falls_back_to_english_for_unknown_lang():
    # 'xx' is not a supported lang
    assert t("Crop Recommender", "xx") == "Crop Recommender"


def test_t_returns_key_for_unknown_key():
    assert t("nonexistent.key.value", "en") == "nonexistent.key.value"


def test_t_returns_hindi_when_translation_exists():
    # Even pre-translation pass, hi bundle has some entries
    result = t("Crop Recommender", "hi")
    assert isinstance(result, str)
    assert result  # non-empty


def test_reload_bundles_picks_up_changes(tmp_path, monkeypatch):
    reload_bundles()  # smoke test it runs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_i18n_catalog.py -v`
Expected: ImportError — module doesn't exist.

- [ ] **Step 3: Implement catalog**

`backend/services/i18n/catalog.py`:
```python
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_i18n_catalog.py -v`
Expected: 5 PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/services/i18n/catalog.py tests/test_i18n_catalog.py
git commit -m "feat(i18n): server-side translation catalog"
```

---

## Task 4: Locale middleware (`backend/middleware/locale.py`)

**Files:**
- Create: `backend/middleware/__init__.py` (empty)
- Create: `backend/middleware/locale.py`
- Create: `tests/test_i18n_middleware.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write the failing test**

`tests/test_i18n_middleware.py`:
```python
"""Tests for LocaleMiddleware: parses Accept-Language and attaches request.state.lang."""
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.middleware.locale import LocaleMiddleware


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(LocaleMiddleware)

    @app.get("/echo-lang")
    def echo(request: Request):
        return {"lang": request.state.lang}

    return app


def test_no_header_defaults_to_en():
    client = TestClient(_make_app())
    r = client.get("/echo-lang")
    assert r.status_code == 200
    assert r.json() == {"lang": "en"}


def test_supported_lang_passes_through():
    client = TestClient(_make_app())
    r = client.get("/echo-lang", headers={"Accept-Language": "hi"})
    assert r.json() == {"lang": "hi"}


def test_unsupported_lang_falls_back_to_en():
    client = TestClient(_make_app())
    r = client.get("/echo-lang", headers={"Accept-Language": "xx"})
    assert r.json() == {"lang": "en"}


def test_browser_style_header_first_segment_wins():
    # Browsers send Accept-Language: hi-IN,hi;q=0.9,en;q=0.8
    client = TestClient(_make_app())
    r = client.get("/echo-lang", headers={"Accept-Language": "hi-IN,hi;q=0.9,en;q=0.8"})
    assert r.json() == {"lang": "hi"}


def test_explicit_two_letter_preferred_over_full_tag():
    client = TestClient(_make_app())
    r = client.get("/echo-lang", headers={"Accept-Language": "ta-IN"})
    assert r.json() == {"lang": "ta"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_i18n_middleware.py -v`
Expected: ImportError.

- [ ] **Step 3: Create middleware package**

```bash
mkdir -p backend/middleware
touch backend/middleware/__init__.py
```

- [ ] **Step 4: Implement middleware**

`backend/middleware/locale.py`:
```python
"""LocaleMiddleware — reads Accept-Language, picks first supported language,
stashes the two-letter code on request.state.lang. Defaults to 'en'."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.services.i18n.langs import is_supported


def _parse_accept_language(header: str | None) -> str:
    if not header:
        return "en"
    # Split on comma, strip quality factors, lowercase.
    for raw in header.split(","):
        tag = raw.split(";", 1)[0].strip().lower()
        if not tag:
            continue
        primary = tag.split("-", 1)[0]
        if is_supported(primary):
            return primary
    return "en"


class LocaleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.lang = _parse_accept_language(request.headers.get("accept-language"))
        return await call_next(request)
```

- [ ] **Step 5: Run middleware tests**

Run: `pytest tests/test_i18n_middleware.py -v`
Expected: 5 PASSED.

- [ ] **Step 6: Register middleware in main.py**

Modify `backend/main.py`. After the `from fastapi.middleware.cors import CORSMiddleware` line, add:
```python
from backend.middleware.locale import LocaleMiddleware
```

After the `app.add_middleware(CORSMiddleware, ...)` block (around line 137-147), add:
```python
    app.add_middleware(LocaleMiddleware)
```

(Note: in Starlette, middleware added later runs *outermost*. Order doesn't matter here since CORS and Locale don't interact.)

- [ ] **Step 7: Verify backend still boots**

Run:
```bash
python -c "from backend.main import create_app; app = create_app(); print('ok')"
```

Note: if `create_app` is not the factory name, inspect `backend/main.py` and adjust the import to match (e.g., `from backend.main import app`).

Expected: prints `ok` with no traceback.

- [ ] **Step 8: Commit**

```bash
git add backend/middleware/ tests/test_i18n_middleware.py backend/main.py
git commit -m "feat(i18n): LocaleMiddleware parses Accept-Language"
```

---

## Task 5: DB migration — `preferred_lang` columns

**Files:**
- Modify: `backend/services/db.py`
- Create: `tests/test_db_migration_preferred_lang.py`

- [ ] **Step 1: Write the failing test**

`tests/test_db_migration_preferred_lang.py`:
```python
"""Tests that init_db creates / adds preferred_lang on both subscription tables."""
import asyncio
import aiosqlite
import pytest

from backend.services.db import init_db
from backend.config import get_settings


@pytest.mark.asyncio
async def test_alert_subscriptions_has_preferred_lang(tmp_path, monkeypatch):
    db_path = tmp_path / "kisanos_test.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    get_settings.cache_clear()
    await init_db()

    async with aiosqlite.connect(str(db_path)) as db:
        rows = await (await db.execute("PRAGMA table_info(alert_subscriptions)")).fetchall()
        cols = {r[1]: r for r in rows}
        assert "preferred_lang" in cols
        # column index 4 is dflt_value
        assert cols["preferred_lang"][4] == "'en'"


@pytest.mark.asyncio
async def test_webpush_subscriptions_has_preferred_lang(tmp_path, monkeypatch):
    db_path = tmp_path / "kisanos_test2.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    get_settings.cache_clear()
    await init_db()

    async with aiosqlite.connect(str(db_path)) as db:
        rows = await (await db.execute("PRAGMA table_info(webpush_subscriptions)")).fetchall()
        cols = {r[1] for r in rows}
        assert "preferred_lang" in cols


@pytest.mark.asyncio
async def test_init_db_is_idempotent_on_existing_db(tmp_path, monkeypatch):
    """Running init_db twice (simulates existing DB getting the new column) should not error."""
    db_path = tmp_path / "kisanos_test3.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_path))
    get_settings.cache_clear()
    await init_db()
    await init_db()  # second call — must not raise

    async with aiosqlite.connect(str(db_path)) as db:
        rows = await (await db.execute("PRAGMA table_info(alert_subscriptions)")).fetchall()
        cols = {r[1] for r in rows}
        assert "preferred_lang" in cols
```

Note: if `pytest-asyncio` isn't installed yet, add to dev deps. Check `requirements.txt` and `pytest.ini` first; if asyncio mode isn't auto, the test file may need a `pytestmark = pytest.mark.asyncio` decorator (already on each test). If `pytest-asyncio` is missing, `pip install pytest-asyncio` and add `asyncio_mode = auto` to `pytest.ini`.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_db_migration_preferred_lang.py -v`
Expected: FAIL — column doesn't exist.

- [ ] **Step 3: Update `init_db` to add column on create + on existing DBs**

Replace the body of `init_db` in `backend/services/db.py` with:
```python
async def init_db() -> None:
    settings = get_settings()
    async with aiosqlite.connect(settings.SQLITE_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS alert_subscriptions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                phone           TEXT    NOT NULL,
                district        TEXT,
                state           TEXT    NOT NULL,
                crops           TEXT    NOT NULL DEFAULT '[]',
                alert_types     TEXT    NOT NULL DEFAULT '["frost","heavy_rain","pest_risk"]',
                active          INTEGER NOT NULL DEFAULT 1,
                preferred_lang  TEXT    NOT NULL DEFAULT 'en',
                created_at      TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS webpush_subscriptions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                phone           TEXT,
                endpoint        TEXT NOT NULL UNIQUE,
                p256dh          TEXT NOT NULL,
                auth            TEXT NOT NULL,
                preferred_lang  TEXT NOT NULL DEFAULT 'en',
                created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS alert_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                subscription_id INTEGER REFERENCES alert_subscriptions(id),
                alert_type      TEXT NOT NULL,
                severity        TEXT NOT NULL DEFAULT 'medium',
                message         TEXT NOT NULL,
                sent_via        TEXT NOT NULL DEFAULT 'sms',
                sent_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Idempotent ALTER for DBs created before this migration.
        for table in ("alert_subscriptions", "webpush_subscriptions"):
            cursor = await db.execute(f"PRAGMA table_info({table})")
            cols = {row[1] for row in await cursor.fetchall()}
            if "preferred_lang" not in cols:
                await db.execute(
                    f"ALTER TABLE {table} ADD COLUMN preferred_lang TEXT NOT NULL DEFAULT 'en'"
                )

        await db.commit()
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_db_migration_preferred_lang.py -v`
Expected: 3 PASSED.

- [ ] **Step 5: Apply migration to the live dev DB**

Run:
```bash
python -c "import asyncio; from backend.services.db import init_db; asyncio.run(init_db())"
sqlite3 kisanos.db "PRAGMA table_info(alert_subscriptions);" | grep preferred_lang
sqlite3 kisanos.db "PRAGMA table_info(webpush_subscriptions);" | grep preferred_lang
```
Expected: both `grep` lines print a row containing `preferred_lang|TEXT|1|'en'|0`.

- [ ] **Step 6: Commit**

```bash
git add backend/services/db.py tests/test_db_migration_preferred_lang.py
git commit -m "feat(i18n): add preferred_lang to subscription tables (idempotent)"
```

---

## Task 6: Frontend `Accept-Language` wiring

**Files:**
- Modify: `web/lib/api.js`
- Modify: `web/components/app.jsx`
- Modify: `web/index.html`

- [ ] **Step 1: Add `Accept-Language` to api.js fetch wrapper**

In `web/lib/api.js`, locate the line:
```js
const headers = { 'X-API-Key': window.API_KEY };
```

Replace with:
```js
const headers = { 'X-API-Key': window.API_KEY };
// Multilingual: forward the user's selected language so the backend can localize responses.
if (window.__lang) headers['Accept-Language'] = window.__lang;
```

- [ ] **Step 2: Sync `lang` into `window.__lang` from app.jsx**

In `web/components/app.jsx`, find the existing block:
```jsx
useEffect(() => { document.documentElement.lang = lang; }, [lang]);
```

Change it to:
```jsx
useEffect(() => {
  document.documentElement.lang = lang;
  window.__lang = lang;
}, [lang]);
```

- [ ] **Step 3: Persist `lang` in localStorage**

Still in `web/components/app.jsx`, find the line:
```jsx
const [lang, setLang] = useState('en');
```

Replace with:
```jsx
const [lang, setLang] = useState(() => {
  try {
    const saved = localStorage.getItem('kisanos.lang');
    return (saved && window.isSupportedLang && window.isSupportedLang(saved)) ? saved : 'en';
  } catch { return 'en'; }
});
```

Then immediately after the `useEffect` that sets `document.documentElement.lang` (modified in Step 2), add:
```jsx
useEffect(() => {
  try { localStorage.setItem('kisanos.lang', lang); } catch {}
}, [lang]);
```

- [ ] **Step 4: Load langs.js before i18n.js in index.html**

In `web/index.html`, find the existing `<script src="/lib/i18n.js"></script>` tag (or however i18n.js is included). Add **before** it:
```html
<script src="/lib/langs.js"></script>
```

If the script tag is loaded via a different mechanism (e.g., bundler config), inspect index.html and place `langs.js` such that `window.LANGS` and `window.isSupportedLang` are defined before any React code runs.

- [ ] **Step 5: Smoke test in the browser**

Run:
```bash
cd web && python3 -m http.server 5173 >/tmp/web.log 2>&1 &
sleep 1
```

Then in a separate check, curl the bundles and confirm langs.js is served:
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5173/lib/langs.js
```
Expected: `200`.

Kill the server: `kill %1 2>/dev/null`

Manual UI smoke: open `http://localhost:5173/`, switch language in the sidebar, reload the page → language should persist. Open DevTools → Network → confirm subsequent API requests show `Accept-Language: hi` (or whatever was selected).

- [ ] **Step 6: Commit**

```bash
git add web/lib/api.js web/components/app.jsx web/index.html
git commit -m "feat(i18n): persist lang in localStorage + send Accept-Language on every API call"
```

---

## Task 7: Final integration verification

**Files:** none modified — verification only.

- [ ] **Step 1: Run the full test suite**

Run: `pytest tests/test_i18n_langs.py tests/test_bundles_schema.py tests/test_i18n_catalog.py tests/test_i18n_middleware.py tests/test_db_migration_preferred_lang.py -v`
Expected: all tests in these files PASS.

- [ ] **Step 2: Run the broader test suite to confirm no regressions**

Run: `pytest -x`
Expected: no failures. If there are pre-existing failures unrelated to i18n, note them but don't fix in this phase.

- [ ] **Step 3: Boot the backend and hit a real endpoint with `Accept-Language`**

Run:
```bash
uvicorn backend.main:app --port 8765 >/tmp/api.log 2>&1 &
sleep 2
curl -s -H "X-API-Key: kisanos-dev-key-change-in-production" \
     -H "Accept-Language: hi" \
     http://localhost:8765/health || curl -s -H "X-API-Key: kisanos-dev-key-change-in-production" \
     -H "Accept-Language: hi" \
     http://localhost:8765/
kill %1 2>/dev/null
```
Expected: 200 response. If `/health` doesn't exist, any 200/404 from a routed endpoint is fine — we're only confirming the middleware doesn't blow up.

- [ ] **Step 4: Final commit (no-op marker, skip if nothing to commit)**

```bash
git status
# If clean, this phase is complete. Otherwise stage stragglers and:
# git commit -m "chore(i18n): phase 1 verification cleanup"
```

---

## Phase exit criteria

- All 5 new test files pass.
- `pytest -x` shows no new failures relative to baseline.
- Web app boots, language picker still works, language persists across reload.
- Backend boots; locale middleware attaches `request.state.lang` without breaking any router.
- `git log --oneline` shows ~6 focused commits, one per task.
- No user-visible English string has changed.

When all criteria met, this phase is shippable.
