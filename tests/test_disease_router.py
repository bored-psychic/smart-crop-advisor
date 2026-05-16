"""Tests for /api/disease/crops endpoint — both response shapes."""
import pytest
from fastapi.testclient import TestClient
from backend.main import app

DEV_KEY = "kisanos-dev-key-change-in-production"
HEADERS = {"X-API-Key": DEV_KEY}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_crops_simple_shape(client):
    """Default (no ?detailed) returns {crop: [symptom_string, ...]}."""
    resp = client.get("/api/disease/crops", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    # At least one crop
    assert len(data) > 0
    # Values are lists of strings
    first_crop = next(iter(data))
    assert isinstance(data[first_crop], list)
    assert isinstance(data[first_crop][0], str)


def test_crops_detailed_shape(client):
    """?detailed=true returns {crop: [{symptom, disease, severity, type}, ...]}."""
    resp = client.get("/api/disease/crops?detailed=true", headers=HEADERS)
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


def test_crops_detailed_false_matches_simple(client):
    """?detailed=false produces same shape as no param."""
    resp_no_param = client.get("/api/disease/crops", headers=HEADERS)
    resp_false = client.get("/api/disease/crops?detailed=false", headers=HEADERS)
    assert resp_no_param.json() == resp_false.json()


def test_crops_requires_api_key(client):
    """Endpoint rejects requests without X-API-Key."""
    resp = client.get("/api/disease/crops")
    assert resp.status_code in (401, 403)
