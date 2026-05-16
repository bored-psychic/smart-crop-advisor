"""Test soil analysis endpoint."""

import pytest
from backend.schemas.soil import SoilAnalysisRequest, NutrientDeficiency
from backend.services.soil_analyzer import (
    detect_deficiencies,
    get_amendments,
    get_compatible_crops,
)


def test_detect_deficiencies_all_deficient():
    """Test detection when all nutrients are deficient."""
    req = SoilAnalysisRequest(
        N=20,
        P=10,
        K=50,
        ph=5.0,
        organic_matter_pct=1.0,
    )

    deficiencies = detect_deficiencies(req)

    assert len(deficiencies) == 5  # N, P, K, pH, organic_matter
    assert any(d.nutrient == 'N' and d.severity == 'high' for d in deficiencies)
    assert any(d.nutrient == 'pH' and d.severity == 'high' for d in deficiencies)
    assert any(d.nutrient == 'organic_matter' and d.severity == 'high' for d in deficiencies)


def test_detect_deficiencies_none():
    """Test detection when soil is optimal."""
    req = SoilAnalysisRequest(
        N=80,
        P=50,
        K=150,
        ph=6.8,
        organic_matter_pct=3.5,
    )

    deficiencies = detect_deficiencies(req)

    assert len(deficiencies) == 0


def test_detect_deficiencies_ph_acidic():
    """Test pH detection for acidic soil."""
    req = SoilAnalysisRequest(
        N=80,
        P=50,
        K=150,
        ph=4.8,
        organic_matter_pct=3.5,
    )

    deficiencies = detect_deficiencies(req)

    assert any(d.nutrient == 'pH' for d in deficiencies)
    assert any(d.nutrient == 'pH' and d.severity == 'high' for d in deficiencies)


def test_detect_deficiencies_ph_alkaline():
    """Test pH detection for alkaline soil."""
    req = SoilAnalysisRequest(
        N=80,
        P=50,
        K=150,
        ph=7.8,
        organic_matter_pct=3.5,
    )

    deficiencies = detect_deficiencies(req)

    assert any(d.nutrient == 'pH' for d in deficiencies)
    assert any(d.nutrient == 'pH' and d.severity == 'medium' for d in deficiencies)


def test_get_amendments():
    """Test amendment lookup."""
    req = SoilAnalysisRequest(
        N=20,
        P=10,
        K=150,
        ph=5.0,
        organic_matter_pct=1.0,
    )

    deficiencies = detect_deficiencies(req)
    amendments = get_amendments(req, deficiencies)

    assert len(amendments) >= 3  # At least amendments for N, P, pH, OM
    assert any('Urea' in a.name or 'DAP' in a.name for a in amendments)  # N amendment


def test_get_compatible_crops():
    """Test crop recommendation based on soil."""
    req = SoilAnalysisRequest(
        N=80,
        P=50,
        K=150,
        ph=6.8,
        organic_matter_pct=3.5,
    )

    crops = get_compatible_crops(req)

    assert len(crops) > 0
    assert 'rice' in crops or 'wheat' in crops or 'cotton' in crops


def test_get_compatible_crops_acidic_soil():
    """Test crops for acidic soil (limited options)."""
    req = SoilAnalysisRequest(
        N=30,
        P=15,
        K=50,
        ph=4.8,
        organic_matter_pct=1.5,
    )

    crops = get_compatible_crops(req)

    # Should still return some crops (fallback to all)
    assert len(crops) > 0


@pytest.mark.asyncio
async def test_soil_analysis_endpoint(client):
    """Integration test for soil analysis endpoint."""
    response = await client.post(
        "/api/soil/analyze",
        json={
            "N": 20,
            "P": 10,
            "K": 150,
            "ph": 5.0,
            "organic_matter_pct": 1.0,
            "target_crop": "rice",
            "area_acres": 2.5,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["deficiencies"]) > 0
    assert len(data["amendments"]) > 0
    assert "narrative" in data
    assert len(data["narrative"]) > 0
    assert data["soil_type"] == "Acidic Soil"
