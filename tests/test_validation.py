"""Input-validation tests — Task 5 P1 remediation.

Covers the three injection points hardened in this task:
  1. phone field on /api/alerts/subscribe  (regex + crop allowlist)
  2. corrected_label on /api/acoustic/feedback  (path-traversal allowlist)
  3. crop_type on /api/disease/analyze-image  (crop allowlist)
"""
from __future__ import annotations

import io
import os

import numpy as np
import pytest
from fastapi.testclient import TestClient

# Required env vars before the app module is imported.
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-validation")
os.environ.setdefault("FAST2SMS_API_KEY", "")


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """In-process TestClient with an isolated SQLite database."""
    db_path = tmp_path_factory.mktemp("db") / "val_test.db"
    os.environ["SQLITE_PATH"] = str(db_path)

    from backend.config import get_settings
    get_settings.cache_clear()

    import importlib
    import backend.main
    importlib.reload(backend.main)

    with TestClient(backend.main.app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="module")
def auth_headers(client):
    """Mint a JWT via the OTP flow (OTP monkey-patched to a known value)."""
    from backend.routers import auth as _auth_router
    original_gen = _auth_router.generate_otp
    _auth_router.generate_otp = lambda: "222222"
    try:
        client.post("/api/auth/request-otp", json={"phone": "+919876543210"})
        r = client.post(
            "/api/auth/verify-otp",
            json={"phone": "+919876543210", "otp": "222222"},
        )
    finally:
        _auth_router.generate_otp = original_gen
    assert r.status_code == 200, f"JWT acquisition failed: {r.text}"
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def api_key_headers():
    """X-API-Key header for endpoints that use require_api_key."""
    return {"X-API-Key": "test-api-key"}


def _tiny_png() -> bytes:
    """Return a minimal 4x4 black PNG image as bytes."""
    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(np.zeros((4, 4, 3), dtype=np.uint8)).save(buf, format="PNG")
    return buf.getvalue()


# ── 1. phone validation on /api/alerts/subscribe ──────────────────────────


def test_sql_injection_phone_rejected(client, auth_headers):
    """SQL-injection-like phone string must be rejected with 422."""
    body = {
        "phone": "; DROP TABLE alert_subscriptions",
        "state": "Maharashtra",
        "crops": ["Rice"],
    }
    r = client.post("/api/alerts/subscribe", json=body, headers=auth_headers)
    assert r.status_code == 422, (
        f"Expected 422 for malicious phone, got {r.status_code}: {r.text}"
    )


def test_valid_phone_accepted(client, auth_headers):
    """A well-formed E.164 phone number must not be rejected by the validator."""
    body = {
        "phone": "+919876543210",
        "state": "Maharashtra",
        "crops": ["Rice"],
    }
    r = client.post("/api/alerts/subscribe", json=body, headers=auth_headers)
    # 200/201/204/409 (duplicate) are all acceptable — anything but 422.
    assert r.status_code != 422, (
        f"Valid phone '+919876543210' was unexpectedly rejected: {r.status_code}: {r.text}"
    )


def test_unknown_crop_in_subscription_rejected(client, auth_headers):
    """A crop name not in DISEASE_DB must be rejected with 422."""
    body = {
        "phone": "+919876543211",
        "state": "Maharashtra",
        "crops": ["UnicornCrop"],
    }
    r = client.post("/api/alerts/subscribe", json=body, headers=auth_headers)
    assert r.status_code == 422, (
        f"Expected 422 for unknown crop 'UnicornCrop', got {r.status_code}: {r.text}"
    )


def test_too_many_crops_rejected(client, auth_headers):
    """More than 20 crops in a single subscription must be rejected with 422."""
    body = {
        "phone": "+919876543212",
        "state": "Maharashtra",
        "crops": ["Rice"] * 21,  # 21 items exceeds max_length=20
    }
    r = client.post("/api/alerts/subscribe", json=body, headers=auth_headers)
    assert r.status_code == 422, (
        f"Expected 422 for >20 crops, got {r.status_code}: {r.text}"
    )


# ── 2. label path-traversal on /api/acoustic/feedback ────────────────────


def test_path_traversal_label_rejected(client, api_key_headers):
    """A label with path-traversal characters must be rejected with 400."""
    body = {
        "clip_id": "deadbeef-0000-0000-0000-000000000000",
        "corrected_label": "../../etc/passwd",
        "predicted_label": "Cricket",
        "confidence": 45,
    }
    r = client.post("/api/acoustic/feedback", json=body, headers=api_key_headers)
    assert r.status_code == 400, (
        f"Expected 400 for path-traversal label, got {r.status_code}: {r.text}"
    )


def test_unknown_label_rejected(client, api_key_headers):
    """An arbitrary string label not in PEST_META must be rejected with 400."""
    body = {
        "clip_id": "deadbeef-0000-0000-0000-000000000001",
        "corrected_label": "NotARealLabel",
        "predicted_label": "Cricket",
        "confidence": 45,
    }
    r = client.post("/api/acoustic/feedback", json=body, headers=api_key_headers)
    assert r.status_code == 400, (
        f"Expected 400 for unknown label, got {r.status_code}: {r.text}"
    )


def test_skip_label_bypasses_validation(client, api_key_headers):
    """'skip' is a special sentinel — it must not trigger the 400 allowlist check."""
    body = {
        "clip_id": "deadbeef-0000-0000-0000-000000000002",
        "corrected_label": "skip",
    }
    r = client.post("/api/acoustic/feedback", json=body, headers=api_key_headers)
    # Should return 200 {"status": "skipped"}, not 400.
    assert r.status_code == 200, (
        f"Expected 200 for 'skip' label, got {r.status_code}: {r.text}"
    )
    assert r.json().get("status") == "skipped"


def test_valid_label_proceeds_past_allowlist(client, api_key_headers):
    """A label in PEST_META is not rejected by the allowlist check itself.

    It will hit 404 because no real clip_id exists — that is expected and
    means the allowlist check passed (not a 400).
    """
    body = {
        "clip_id": "deadbeef-0000-0000-0000-000000000003",
        "corrected_label": "Cricket",
        "predicted_label": "Bee",
        "confidence": 55,
    }
    r = client.post("/api/acoustic/feedback", json=body, headers=api_key_headers)
    # 400 would mean the allowlist rejected it — any other code is fine here.
    assert r.status_code != 400, (
        f"Valid PEST_META label 'Cricket' was unexpectedly rejected with 400: {r.text}"
    )


# ── 3. crop_type validation on /api/disease/analyze-image ─────────────────


def test_xss_crop_type_rejected(client, auth_headers):
    """An XSS payload in crop_type must be rejected with 422."""
    png = _tiny_png()
    r = client.post(
        "/api/disease/analyze-image",
        files={"file": ("leaf.png", io.BytesIO(png), "image/png")},
        data={"crop_type": "<script>alert(1)</script>"},
        headers=auth_headers,
    )
    assert r.status_code == 422, (
        f"Expected 422 for XSS crop_type, got {r.status_code}: {r.text}"
    )


def test_arbitrary_string_crop_type_rejected(client, auth_headers):
    """A random invalid crop_type string must be rejected with 422."""
    png = _tiny_png()
    r = client.post(
        "/api/disease/analyze-image",
        files={"file": ("leaf.png", io.BytesIO(png), "image/png")},
        data={"crop_type": "NotACrop12345"},
        headers=auth_headers,
    )
    assert r.status_code == 422, (
        f"Expected 422 for invalid crop_type, got {r.status_code}: {r.text}"
    )


def test_unknown_sentinel_crop_type_accepted(client, auth_headers):
    """crop_type='Unknown' is the no-selection sentinel and must pass validation."""
    png = _tiny_png()
    r = client.post(
        "/api/disease/analyze-image",
        files={"file": ("leaf.png", io.BytesIO(png), "image/png")},
        data={"crop_type": "Unknown"},
        headers=auth_headers,
    )
    # Validation passes — any code except 422 is acceptable (likely 503 in tests).
    assert r.status_code != 422, (
        f"crop_type='Unknown' was unexpectedly rejected with 422: {r.text}"
    )


def test_valid_crop_type_accepted(client, auth_headers):
    """A known crop name from DISEASE_DB must pass crop_type validation."""
    png = _tiny_png()
    r = client.post(
        "/api/disease/analyze-image",
        files={"file": ("leaf.png", io.BytesIO(png), "image/png")},
        data={"crop_type": "Tomato"},
        headers=auth_headers,
    )
    # Not 422 — any other response means validation passed.
    assert r.status_code != 422, (
        f"Valid crop_type='Tomato' was unexpectedly rejected with 422: {r.text}"
    )
