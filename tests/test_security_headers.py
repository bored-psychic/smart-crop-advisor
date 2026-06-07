"""Tests for the environment-conditional Content-Security-Policy.

Production must serve a strict CSP (precompiled frontend → no unsafe-eval,
no script unsafe-inline, no unpkg). Development keeps the permissive policy the
in-browser Babel SPA needs.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.middleware.security_headers import SecurityHeadersMiddleware


def _client(monkeypatch, env):
    monkeypatch.setenv("ENVIRONMENT", env)
    monkeypatch.setenv("API_KEY", "x")
    monkeypatch.setenv("JWT_SECRET", "y")
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
