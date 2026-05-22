"""Tests for /api/disease/crops endpoint — both response shapes.

/crops is gated by require_user (per-user JWT). Tests mint a JWT inline
via backend.auth.issue_token for a synthetic phone.
"""
import pytest
from fastapi.testclient import TestClient
from backend.auth import issue_token
from backend.main import app


@pytest.fixture(scope="module")
def headers():
    token, _ = issue_token("+919999999999")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_crops_simple_shape(client, headers):
    """Default (no ?detailed) returns {crop: [symptom_string, ...]}."""
    resp = client.get("/api/disease/crops", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    # At least one crop
    assert len(data) > 0
    # Values are lists of strings
    first_crop = next(iter(data))
    assert isinstance(data[first_crop], list)
    assert isinstance(data[first_crop][0], str)


def test_crops_detailed_shape(client, headers):
    """?detailed=true returns {crop: [{symptom, disease, severity, type}, ...]}."""
    resp = client.get("/api/disease/crops?detailed=true", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert len(data) > 0
    first_crop = next(iter(data))
    assert isinstance(data[first_crop], list)
    first_item = data[first_crop][0]
    assert "symptom" in first_item
    assert "disease" in first_item
    assert "severity" in first_item
    assert "type" in first_item


def test_crops_detailed_false_matches_simple(client, headers):
    """?detailed=false produces same shape as no param."""
    resp_no_param = client.get("/api/disease/crops", headers=headers)
    resp_false = client.get("/api/disease/crops?detailed=false", headers=headers)
    assert resp_no_param.json() == resp_false.json()


def test_crops_requires_auth(client):
    """Endpoint rejects requests without an Authorization header."""
    resp = client.get("/api/disease/crops")
    assert resp.status_code in (401, 403)
