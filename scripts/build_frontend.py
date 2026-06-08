"""Snapshot-time production frontend build for KisanOS.

Transforms the in-browser-Babel SPA into a precompiled, Babel-free build so the
production CSP can drop unsafe-eval / script unsafe-inline / unpkg. Runs on the
BUILD HOST only (e.g. when creating the HF deploy snapshot); the Python runtime
image never gains build tooling. Dev (main's web/) is untouched.
"""
from __future__ import annotations

import os
import platform
import re
import subprocess
import tarfile
import urllib.request
from pathlib import Path

ESBUILD_VERSION = "0.24.0"
_VENDOR_REACT = '<script src="vendor/react.production.min.js"></script>'
_VENDOR_REACT_DOM = '<script src="vendor/react-dom.production.min.js"></script>'
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
    url = f"https://registry.npmjs.org/@esbuild/{pkg}/-/{pkg}-{ESBUILD_VERSION}.tgz"
    tgz = _CACHE_DIR / "esbuild.tgz"
    urllib.request.urlretrieve(url, tgz)
    with tarfile.open(tgz) as tf:
        member = tf.getmember("package/bin/esbuild")
        member.name = "esbuild"
        tf.extract(member, _CACHE_DIR)
    tgz.unlink()
    binary.chmod(binary.stat().st_mode | 0o111)
    return str(binary)


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


# The 16 in-browser-Babel sources, in load order (see web/index.html).
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
# (url, expected sha384 base64). Build-time integrity pin replacing the SRI the
# old unpkg <script> tags carried — a tampered/changed download fails loudly
# instead of being baked into the snapshot. The build still FETCHES from unpkg,
# but only on the build host; the served app loads these same-origin.
_VENDOR_FILES = {
    "react.production.min.js": (
        f"https://unpkg.com/react@{_REACT_VER}/umd/react.production.min.js",
        "DGyLxAyjq0f9SPpVevD6IgztCFlnMF6oW/XQGmfe+IsZ8TqEiDrcHkMLKI6fiB/Z",
    ),
    "react-dom.production.min.js": (
        f"https://unpkg.com/react-dom@{_REACT_VER}/umd/react-dom.production.min.js",
        "gTGxhz21lVGYNMcdJOyq01Edg0jhn/c22nsx0kyqP0TxaV5WVdsSH1fSDUf5YJj1",
    ),
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
    out = proc.stdout
    # Each source does a top-level `const { useState, ... } = React;`. Loaded as
    # separate CLASSIC scripts they share ONE global lexical environment, so the
    # 2nd+ such `const` throws "Identifier 'useState' has already been declared"
    # and aborts that script (Babel's text/babel ran each script isolated, so it
    # never collided). Demote that specific destructure to `var` — var lands on
    # `window` and tolerates redeclaration, while component `function`s stay
    # global as before. Other top-level consts have unique names (no collision).
    out = re.sub(r'(?m)^const(\s*\{[^}]*\}\s*=\s*React\s*;)', r'var\1', out)
    path.write_text(out)


def vendor_react(web_dir: Path) -> None:
    """Download the pinned React/ReactDOM UMDs, verify each against its expected
    sha384, and write them only after ALL pass — so any mismatch aborts before a
    single byte is written (fully atomic; nothing is left behind).

    To re-pin after bumping ``_REACT_VER``, recompute each hash with:
        curl -s <url> | openssl dgst -sha384 -binary | openssl base64 -A
    """
    import base64
    import hashlib

    verified: dict[str, bytes] = {}
    for name, (url, expected) in _VENDOR_FILES.items():
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = resp.read()
        actual = base64.b64encode(hashlib.sha384(data).digest()).decode()
        if actual != expected:
            raise RuntimeError(
                f"vendor integrity check failed for {name}: "
                f"expected sha384-{expected}, got sha384-{actual}"
            )
        verified[name] = data
    vendor = web_dir / "vendor"
    vendor.mkdir(exist_ok=True)
    for name, data in verified.items():
        (vendor / name).write_bytes(data)


def build(web_dir: str) -> None:
    """Transform `web_dir` in place into the production (Babel-free) frontend.

    All network work (esbuild download, React vendor download+verify) runs FIRST,
    before any file in `web_dir` is mutated, so a transient download failure
    leaves the source tree untouched rather than half-built.
    """
    web = Path(web_dir)
    esbuild = ensure_esbuild()
    vendor_react(web)
    for rel in _BABEL_SOURCES:
        f = web / rel
        if not f.is_file():
            raise FileNotFoundError(f"expected source missing: {f}")
        transform_file(esbuild, f)
    index = web / "index.html"
    index.write_text(rewrite_index_html(index.read_text()))


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "web"
    build(target)
    print(f"✅ production frontend built in {target}/")
