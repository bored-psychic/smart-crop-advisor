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
    client = TestClient(_make_app())
    r = client.get("/echo-lang", headers={"Accept-Language": "hi-IN,hi;q=0.9,en;q=0.8"})
    assert r.json() == {"lang": "hi"}


def test_explicit_two_letter_preferred_over_full_tag():
    client = TestClient(_make_app())
    r = client.get("/echo-lang", headers={"Accept-Language": "ta-IN"})
    assert r.json() == {"lang": "ta"}
