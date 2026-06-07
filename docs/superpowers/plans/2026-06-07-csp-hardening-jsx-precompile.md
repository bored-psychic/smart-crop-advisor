# CSP Hardening via Snapshot-Time JSX Precompile — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the production HF Space serve a precompiled frontend so its CSP can drop `unsafe-eval`, `script-src 'unsafe-inline'`, and the `unpkg.com` allowance — without changing the live-Babel dev workflow.

**Architecture:** A build script transforms the 16 in-browser-Babel sources to plain JS with esbuild (classic JSX, transform-not-bundle — preserves the global-`window.X`/load-order model), self-hosts React, and rewrites `index.html` to be Babel-free. The build runs only at deploy-snapshot time, so `main`/`web/` stay pure source. The CSP middleware emits a strict policy when `ENVIRONMENT=production` and the existing permissive one otherwise.

**Tech Stack:** Python (build script + FastAPI middleware), esbuild standalone binary, React 18.3.1 UMD (production), pytest.

---

## Context

Finding #5 from the 2026-06-06 security audit: the production CSP carries `script-src 'unsafe-inline' 'unsafe-eval' https://unpkg.com`. Root cause (verified): `web/index.html:621-623` loads React/ReactDOM/`@babel/standalone` from unpkg, then 16 `<script type="text/babel">` tags compile JSX **in the browser at runtime** — that runtime compile is what forces `unsafe-eval`, and Babel injecting compiled code is what forces script `unsafe-inline`. The components use a **global-script model** (0 `import`/`export`, 14 `window.X =`, strict load order; mount at `web/components/app.jsx:181` `ReactDOM.createRoot(rootEl).render(<App />)`), so we must **transform** each file (not bundle). We keep `style-src 'unsafe-inline'` (React `style={{}}` props; low XSS risk) per the approved "Pragmatic" scope. Build runs at snapshot time per the approved "Build at snapshot time" decision.

**The 16 `text/babel` sources (load order — the build's input contract):**
```
components/atoms.jsx
components/views/hooks/useViewCropForm.js
components/views/hooks/usePhotoPanelForm.js
components/views/hooks/useAcousticForm.js
components/views/hooks/useAcousticDisplayHelpers.js
components/views/hooks/useFieldData.js
components/views/hooks/useAlertSubscribe.js
components/views/ViewCrop.jsx
components/views/ViewDisease.jsx
components/views/ViewMarket.jsx
components/views/ViewIrrigation.jsx
components/views/ViewAcoustic.jsx
components/views/ViewField.jsx
tweaks-panel.jsx
components/Login.jsx
components/app.jsx
```
Plain (already JS, untouched): `config.js`, `lib/api.js`, `lib/langs.js`, `lib/i18n.js`, `lib/push.js`.

---

## File Structure

| File | Create/Modify | Responsibility |
|---|---|---|
| `scripts/build_frontend.py` | Create | Orchestrate the prod build: ensure esbuild, transform the 16 sources in place, vendor React, rewrite `index.html`. Pure helpers (`rewrite_index_html`) kept separate for unit testing. |
| `backend/middleware/security_headers.py` | Modify | Make the CSP env-conditional: strict when `is_production`, permissive otherwise. |
| `tests/test_build_frontend.py` | Create | Unit-test the pure `rewrite_index_html`; integration-test a full build on a temp copy. |
| `tests/test_security_headers.py` | Create | Assert prod CSP drops `unsafe-eval`/script-`unsafe-inline`/`unpkg`; dev keeps them. |
| `docs/deploy/huggingface.md` | Modify | Document the snapshot-time build step. |
| `.gitignore` | Modify | Ignore `scripts/.esbuild/` (downloaded binary) and `web/vendor/` (generated). |

---

## Task 1: esbuild acquisition helper

**Files:**
- Create: `scripts/build_frontend.py`
- Test: `tests/test_build_frontend.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_build_frontend.py
import os, stat
from scripts.build_frontend import ensure_esbuild

def test_ensure_esbuild_returns_executable_path():
    path = ensure_esbuild()
    assert os.path.isfile(path)
    assert os.access(path, os.X_OK)
    # second call is cached (no re-download)
    assert ensure_esbuild() == path
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_build_frontend.py::test_ensure_esbuild_returns_executable_path -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.build_frontend'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/build_frontend.py
"""Snapshot-time production frontend build for KisanOS.

Transforms the in-browser-Babel SPA into a precompiled, Babel-free build so the
production CSP can drop unsafe-eval / script unsafe-inline / unpkg. Runs on the
BUILD HOST only (e.g. when creating the HF deploy snapshot); the Python runtime
image never gains build tooling. Dev (main's web/) is untouched.
"""
from __future__ import annotations

import os
import platform
import tarfile
import urllib.request
from pathlib import Path

ESBUILD_VERSION = "0.24.0"
_CACHE_DIR = Path(__file__).resolve().parent / ".esbuild"


def _esbuild_npm_pkg() -> str:
    """Map host platform -> esbuild's per-platform npm package name."""
    sysname, machine = platform.system().lower(), platform.machine().lower()
    table = {
        ("darwin", "arm64"): "darwin-arm64",
        ("darwin", "x86_64"): "darwin-x64",
        ("linux", "x86_64"): "linux-x64",
        ("linux", "aarch64"): "linux-arm64",
    }
    key = (sysname, machine)
    if key not in table:
        raise RuntimeError(f"Unsupported build host {key}; add it to _esbuild_npm_pkg().")
    return table[key]


def ensure_esbuild() -> str:
    """Return a path to an executable esbuild binary, downloading once if needed."""
    binary = _CACHE_DIR / "esbuild"
    if binary.is_file() and os.access(binary, os.X_OK):
        return str(binary)
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    pkg = _esbuild_npm_pkg()
    url = (
        f"https://registry.npmjs.org/@esbuild/{pkg}/-/{pkg}-{ESBUILD_VERSION}.tgz"
    )
    tgz = _CACHE_DIR / "esbuild.tgz"
    urllib.request.urlretrieve(url, tgz)
    with tarfile.open(tgz) as tf:
        member = tf.getmember("package/bin/esbuild")
        member.name = "esbuild"
        tf.extract(member, _CACHE_DIR)
    tgz.unlink()
    binary.chmod(binary.stat().st_mode | 0o111)
    return str(binary)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_build_frontend.py::test_ensure_esbuild_returns_executable_path -v`
Expected: PASS (downloads esbuild once into `scripts/.esbuild/`)

- [ ] **Step 5: Commit**

```bash
git add scripts/build_frontend.py tests/test_build_frontend.py
git commit -m "build(frontend): esbuild acquisition helper for prod build"
```

---

## Task 2: `rewrite_index_html` (pure, the Babel-removal core)

**Files:**
- Modify: `scripts/build_frontend.py`
- Test: `tests/test_build_frontend.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_build_frontend.py  (append)
from scripts.build_frontend import rewrite_index_html

SAMPLE = '''
<script src="lib/api.js"></script>
<script src="https://unpkg.com/react@18.3.1/umd/react.development.js" integrity="sha384-x" crossorigin="anonymous"></script>
<script src="https://unpkg.com/react-dom@18.3.1/umd/react-dom.development.js" integrity="sha384-y" crossorigin="anonymous"></script>
<script src="https://unpkg.com/@babel/standalone@7.29.0/babel.min.js" integrity="sha384-z" crossorigin="anonymous"></script>
<script type="text/babel" src="components/atoms.jsx?v=1"></script>
<script type="text/babel" src="components/app.jsx?v=1"></script>
'''

def test_rewrite_index_html_removes_babel_and_unpkg():
    out = rewrite_index_html(SAMPLE)
    assert "text/babel" not in out          # no runtime compile -> drops unsafe-eval
    assert "@babel/standalone" not in out    # babel removed entirely
    assert "unpkg.com" not in out            # CDN removed
    # React self-hosted (production build)
    assert "vendor/react.production.min.js" in out
    assert "vendor/react-dom.production.min.js" in out
    # component scripts survive as plain <script src> (same paths, still ordered)
    assert '<script src="components/atoms.jsx?v=1"></script>' in out
    assert '<script src="components/app.jsx?v=1"></script>' in out
    assert out.index("components/atoms.jsx") < out.index("components/app.jsx")
    # untouched plain script preserved
    assert '<script src="lib/api.js"></script>' in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_build_frontend.py::test_rewrite_index_html_removes_babel_and_unpkg -v`
Expected: FAIL — `ImportError: cannot import name 'rewrite_index_html'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/build_frontend.py  (append)
import re

_VENDOR_REACT = '<script src="vendor/react.production.min.js"></script>'
_VENDOR_REACT_DOM = '<script src="vendor/react-dom.production.min.js"></script>'


def rewrite_index_html(html: str) -> str:
    """Make index.html Babel-free and CDN-free.

    1. Drop the `@babel/standalone` script entirely.
    2. Replace the two unpkg React scripts with self-hosted production vendor ones.
    3. Strip `type="text/babel"` from every script so the precompiled files load
       as ordinary JS (their paths/content were transformed in place by the build).
    """
    out = html
    # 1. remove the babel-standalone <script ...></script> line
    out = re.sub(
        r'[ \t]*<script[^>]*@babel/standalone[^>]*>\s*</script>\s*\n?',
        "",
        out,
    )
    # 2. swap the two unpkg react scripts for vendor scripts (order preserved)
    out = re.sub(
        r'<script[^>]*unpkg\.com/react@[^>]*>\s*</script>',
        _VENDOR_REACT,
        out,
    )
    out = re.sub(
        r'<script[^>]*unpkg\.com/react-dom@[^>]*>\s*</script>',
        _VENDOR_REACT_DOM,
        out,
    )
    # 3. drop the text/babel type attr (keep src + ordering intact)
    out = out.replace(' type="text/babel"', "")
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_build_frontend.py::test_rewrite_index_html_removes_babel_and_unpkg -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/build_frontend.py tests/test_build_frontend.py
git commit -m "build(frontend): rewrite_index_html removes babel + unpkg"
```

---

## Task 3: `transform_file`, `vendor_react`, `build` orchestration

**Files:**
- Modify: `scripts/build_frontend.py`
- Modify: `.gitignore`
- Test: `tests/test_build_frontend.py`

- [ ] **Step 1: Write the failing test (full build on a temp copy)**

```python
# tests/test_build_frontend.py  (append)
import shutil
from pathlib import Path
from scripts.build_frontend import build

REPO = Path(__file__).resolve().parent.parent

def test_build_produces_babel_free_frontend(tmp_path):
    web = tmp_path / "web"
    shutil.copytree(REPO / "web", web)
    build(str(web))
    index = (web / "index.html").read_text()
    # index is babel/unpkg free
    assert "text/babel" not in index and "unpkg.com" not in index
    # React vendored
    assert (web / "vendor" / "react.production.min.js").is_file()
    assert (web / "vendor" / "react-dom.production.min.js").is_file()
    # a representative component compiled to plain JS (no raw JSX angle-call left)
    atoms = (web / "components" / "atoms.jsx").read_text()
    assert "React.createElement" in atoms            # classic JSX output
    assert "import " not in atoms.split("\n")[0]      # NOT automatic-runtime imports
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_build_frontend.py::test_build_produces_babel_free_frontend -v`
Expected: FAIL — `ImportError: cannot import name 'build'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/build_frontend.py  (append)
import subprocess
import shutil

# The 16 in-browser-Babel sources, in load order (see index.html).
_BABEL_SOURCES = [
    "components/atoms.jsx",
    "components/views/hooks/useViewCropForm.js",
    "components/views/hooks/usePhotoPanelForm.js",
    "components/views/hooks/useAcousticForm.js",
    "components/views/hooks/useAcousticDisplayHelpers.js",
    "components/views/hooks/useFieldData.js",
    "components/views/hooks/useAlertSubscribe.js",
    "components/views/ViewCrop.jsx",
    "components/views/ViewDisease.jsx",
    "components/views/ViewMarket.jsx",
    "components/views/ViewIrrigation.jsx",
    "components/views/ViewAcoustic.jsx",
    "components/views/ViewField.jsx",
    "tweaks-panel.jsx",
    "components/Login.jsx",
    "components/app.jsx",
]

_REACT_VER = "18.3.1"
_VENDOR_FILES = {
    "react.production.min.js": f"https://unpkg.com/react@{_REACT_VER}/umd/react.production.min.js",
    "react-dom.production.min.js": f"https://unpkg.com/react-dom@{_REACT_VER}/umd/react-dom.production.min.js",
}


def transform_file(esbuild: str, path: Path) -> None:
    """Transform one JSX/text-babel file to plain classic-JSX JS, in place.

    Reads via stdin so `--loader=jsx` applies to BOTH .js and .jsx sources
    (some hooks are .js but contain JSX). Classic transform targets the global
    React/ReactDOM UMDs, matching the previous @babel/standalone behaviour.
    """
    src = path.read_text()
    proc = subprocess.run(
        [
            esbuild,
            "--loader=jsx",
            "--jsx=transform",
            "--jsx-factory=React.createElement",
            "--jsx-fragment=React.Fragment",
        ],
        input=src,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"esbuild failed on {path}:\n{proc.stderr}")
    path.write_text(proc.stdout)


def vendor_react(web_dir: Path) -> None:
    vendor = web_dir / "vendor"
    vendor.mkdir(exist_ok=True)
    for name, url in _VENDOR_FILES.items():
        urllib.request.urlretrieve(url, vendor / name)


def build(web_dir: str) -> None:
    """Transform `web_dir` in place into the production (Babel-free) frontend."""
    web = Path(web_dir)
    esbuild = ensure_esbuild()
    for rel in _BABEL_SOURCES:
        f = web / rel
        if not f.is_file():
            raise FileNotFoundError(f"expected source missing: {f}")
        transform_file(esbuild, f)
    vendor_react(web)
    index = web / "index.html"
    index.write_text(rewrite_index_html(index.read_text()))


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "web"
    build(target)
    print(f"✅ production frontend built in {target}/")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_build_frontend.py::test_build_produces_babel_free_frontend -v`
Expected: PASS

- [ ] **Step 5: Ignore generated/downloaded artifacts**

Add to `.gitignore`:
```
scripts/.esbuild/
web/vendor/
```

- [ ] **Step 6: Commit**

```bash
git add scripts/build_frontend.py tests/test_build_frontend.py .gitignore
git commit -m "build(frontend): full transform+vendor build orchestration"
```

---

## Task 4: Environment-conditional CSP

**Files:**
- Modify: `backend/middleware/security_headers.py:40-53`
- Test: `tests/test_security_headers.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_security_headers.py
import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.middleware.security_headers import SecurityHeadersMiddleware


def _client(monkeypatch, env):
    monkeypatch.setenv("ENVIRONMENT", env)
    monkeypatch.setenv("API_KEY", "x"); monkeypatch.setenv("JWT_SECRET", "y")
    monkeypatch.setenv("APP_PEPPER", "z")
    monkeypatch.setenv("FERNET_KEY", "44dN8b2b2y0n7n2n9k4Q1pX9c5kqV1mWnLrJ3yq3v3o=")
    from backend.config import get_settings
    get_settings.cache_clear()
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    @app.get("/")
    def root():
        return {"ok": True}
    return TestClient(app)


def test_production_csp_drops_unsafe_eval_inline_unpkg(monkeypatch):
    csp = _client(monkeypatch, "production").get("/").headers["content-security-policy"]
    script_src = [d for d in csp.split(";") if d.strip().startswith("script-src")][0]
    assert "unsafe-eval" not in script_src
    assert "unsafe-inline" not in script_src
    assert "unpkg.com" not in csp


def test_development_csp_keeps_permissive(monkeypatch):
    csp = _client(monkeypatch, "development").get("/").headers["content-security-policy"]
    assert "unsafe-eval" in csp and "unpkg.com" in csp
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_security_headers.py -v`
Expected: FAIL on `test_production_csp_drops_unsafe_eval_inline_unpkg` — current CSP is the same permissive string in all envs.

- [ ] **Step 3: Write minimal implementation**

Replace the CSP block (currently `backend/middleware/security_headers.py:40-53`, the single `response.headers["Content-Security-Policy"] = (...)` assignment) with:

```python
        # Content-Security-Policy. Production serves a PRECOMPILED frontend
        # (scripts/build_frontend.py) so we drop 'unsafe-eval', script
        # 'unsafe-inline' and the unpkg CDN. Dev keeps the permissive policy the
        # in-browser Babel SPA needs. style-src keeps 'unsafe-inline' in both for
        # React style={{}} props (low XSS risk) + Google Fonts.
        from backend.config import get_settings
        if get_settings().is_production:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "img-src 'self' data:; "
                "media-src 'self' blob:; "
                "connect-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com"
            )
        else:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "img-src 'self' data:; "
                "media-src 'self' blob:; "
                "connect-src 'self' https://unpkg.com; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com"
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_security_headers.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add backend/middleware/security_headers.py tests/test_security_headers.py
git commit -m "security: strict production CSP (no unsafe-eval/inline/unpkg)"
```

---

## Task 5: Wire the build into the deploy-snapshot process

**Files:**
- Modify: `docs/deploy/huggingface.md`

- [ ] **Step 1: Document the snapshot-time build**

Add a subsection to `docs/deploy/huggingface.md` under the snapshot/push steps, with the exact command sequence run while the orphan deploy snapshot's `web/` is checked out (before `git add -A`):

```bash
# Precompile the frontend so the production CSP can be strict.
# Runs on the orphan deploy branch only; main/web stays live-Babel source.
.venv/bin/python scripts/build_frontend.py web
# web/ is now Babel-free + has web/vendor/; force-add the generated vendor dir
# (it is gitignored) so it ships in the snapshot:
git add -f web/vendor
```

State explicitly: this step is part of building `deploy-snapN`, never run on `main`.

- [ ] **Step 2: Commit**

```bash
git add docs/deploy/huggingface.md
git commit -m "docs(deploy): snapshot-time frontend build step"
```

---

## Task 6: Local end-to-end regression (the go/no-go gate)

**Files:** none (verification task)

- [ ] **Step 1: Build a production-frontend snapshot tree locally**

Run:
```bash
rm -rf /tmp/web-prod && cp -r web /tmp/web-prod
.venv/bin/python scripts/build_frontend.py /tmp/web-prod
grep -c "text/babel\|unpkg.com\|@babel" /tmp/web-prod/index.html
```
Expected: `0` (index.html fully Babel/CDN-free), and `/tmp/web-prod/vendor/` contains both React files.

- [ ] **Step 2: Serve the built frontend standalone (does the transformed JS run at all?)**

This isolates "does the precompiled app execute" from CSP. A plain static server does NOT apply the production CSP (that's the FastAPI middleware) — that's deliberate; CSP-under-load is Step 3.
Run:
```bash
( cd /tmp/web-prod && python3 -m http.server 8099 ) &
SERVER_PID=$!
sleep 1
```
Then in the Chrome MCP browser: navigate to `http://localhost:8099/`, run `read_console_messages` filtered for `error`.
Expected: the KisanOS UI renders; **no** `React is not defined` / `createElement` / `Unexpected token <` errors (proves classic-JSX transform + global React work).
Stop the server: `kill $SERVER_PID`.

- [ ] **Step 3: Full-stack check on the real container under the production CSP (authoritative)**

Pre-build the frontend into the working `web/`, build+run the image with `ENVIRONMENT=production`, verify in-browser, then restore `web/` to source.
Run:
```bash
.venv/bin/python scripts/build_frontend.py web        # transform web/ in place (temporary)
docker build -t kisanos-csp . && \
docker run -d --name kisanos-csp -p 7860:7860 \
  -e ENVIRONMENT=production -e API_KEY=t -e JWT_SECRET=t -e APP_PEPPER=t \
  -e FERNET_KEY="$(.venv/bin/python -c 'from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())')" \
  -e DEMO_PHONE=1234567890 kisanos-csp
sleep 25
curl -s -o /dev/null -w 'frontend / -> %{http_code}\n' http://localhost:7860/   # expect 200
```
Then in the Chrome MCP browser: navigate to `http://localhost:7860/`, log in with demo number `1234567890`, open Crop Advisor, and run `read_console_messages` filtered for `Content Security|CSP|error`.
Expected: `200`; UI + login + a view render; **zero CSP-violation messages** in console.
Cleanup (restore source — critical, since the build mutated `web/`):
```bash
docker rm -f kisanos-csp
git checkout -- web/ && git clean -fd web/vendor
```

- [ ] **Step 4: Run the whole test suite**

Run: `.venv/bin/python -m pytest tests/test_build_frontend.py tests/test_security_headers.py tests/test_auth.py -q`
Expected: all pass.

---

## Verification (definition of done)

1. `pytest tests/test_build_frontend.py tests/test_security_headers.py` green.
2. `scripts/build_frontend.py` on a copy of `web/` yields an `index.html` with **zero** `text/babel`/`@babel`/`unpkg` and a populated `web/vendor/`; every component contains `React.createElement` (classic) and **no** automatic-runtime `import`.
3. The built frontend renders in a browser under the **production** CSP with **no console CSP violations** (Task 6 Steps 2–3).
4. Production CSP response has no `unsafe-eval`, no `unsafe-inline` in `script-src`, no `unpkg`; dev CSP unchanged.
5. Deploy runbook documents the snapshot-time build.

**Definition of done:** a production deploy snapshot built through `scripts/build_frontend.py` serves the app with the strict CSP and no functional/console regressions, while `main`'s dev workflow (live Babel) is byte-for-byte unchanged.

---

## Deploy note (out of plan scope, for the operator)

After this lands on `main`, the next deploy snapshot must run Task 5's build step. The agent cannot push to the Space (classifier blocks external whole-tree pushes); the user runs the force-push as in prior deploys. The strict CSP only activates when `ENVIRONMENT=production` (already set on the Space).
