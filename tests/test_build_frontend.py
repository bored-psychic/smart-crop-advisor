"""Tests for scripts/build_frontend.py — the snapshot-time production frontend build.

These exercise the real esbuild binary and (in the full-build test) fetch the
React UMD vendor files, so they require network access on first run.
"""
import os

from scripts.build_frontend import ensure_esbuild, rewrite_index_html


def test_ensure_esbuild_returns_executable_path():
    path = ensure_esbuild()
    assert os.path.isfile(path)
    assert os.access(path, os.X_OK)
    # second call is cached (no re-download)
    assert ensure_esbuild() == path


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
