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
