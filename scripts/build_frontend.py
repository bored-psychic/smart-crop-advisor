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
