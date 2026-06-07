"""Tests for scripts/build_frontend.py — the snapshot-time production frontend build.

These exercise the real esbuild binary and (in the full-build test) fetch the
React UMD vendor files, so they require network access on first run.
"""
import os

from scripts.build_frontend import ensure_esbuild


def test_ensure_esbuild_returns_executable_path():
    path = ensure_esbuild()
    assert os.path.isfile(path)
    assert os.access(path, os.X_OK)
    # second call is cached (no re-download)
    assert ensure_esbuild() == path
