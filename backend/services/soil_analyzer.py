"""Soil Analyzer Service — Nutrient deficiency detection and amendment lookup."""

import json
import logging
from pathlib import Path
from typing import Optional

from backend.schemas.soil import NutrientDeficiency, Amendment, SoilAnalysisRequest

logger = logging.getLogger(__name__)

# Load amendments data at module import
_AMENDMENTS_FILE = Path(__file__).parent.parent.parent / "data" / "soil_amendments.json"

try:
    with open(_AMENDMENTS_FILE, 'r') as f:
        AMENDMENTS_DATA = json.load(f)
except FileNotFoundError:
    logger.warning(f"Amendments file not found at {_AMENDMENTS_FILE}")
    AMENDMENTS_DATA = {}

# Crop-soil compatibility map (ICAR guidelines)
CROP_SOIL_COMPATIBILITY = {
    'rice': {
        'optimal_ph_min': 5.5, 'optimal_ph_max': 7.0,
        'optimal_n_min': 60, 'optimal_p_min': 20, 'optimal_k_min': 40,
        'notes': 'Waterlogged tolerant, needs clayey soil'
    },
    'wheat': {
        'optimal_ph_min': 6.0, 'optimal_ph_max': 7.5,
        'optimal_n_min': 80, 'optimal_p_min': 25, 'optimal_k_min': 40,
        'notes': 'Well-drained alluvial/loamy soil'
    },
    'maize': {
        'optimal_ph_min': 5.5, 'optimal_ph_max': 7.5,
        'optimal_n_min': 100, 'optimal_p_min': 30, 'optimal_k_min': 60,
        'notes': 'Loamy soil, good drainage needed'
    },
    'cotton': {
        'optimal_ph_min': 6.0, 'optimal_ph_max': 7.5,
        'optimal_n_min': 80, 'optimal_p_min': 25, 'optimal_k_min': 120,
        'notes': 'Black/regur soil preferred, deep soil'
    },
    'chickpea': {
        'optimal_ph_min': 6.0, 'optimal_ph_max': 7.5,
        'optimal_n_min': 0, 'optimal_p_min': 20, 'optimal_k_min': 40,
        'notes': 'Fixes own N, avoid excess N. Well-drained loamy soil'
    },
    'groundnut': {
        'optimal_ph_min': 5.5, 'optimal_ph_max': 6.8,
        'optimal_n_min': 0, 'optimal_p_min': 25, 'optimal_k_min': 80,
        'notes': 'Sandy/loamy soil, fixes N. Calcium (gypsum) aids pod development'
    },
    'sugarcane': {
        'optimal_ph_min': 5.5, 'optimal_ph_max': 8.0,
        'optimal_n_min': 120, 'optimal_p_min': 30, 'optimal_k_min': 80,
        'notes': 'Heavy feeder, alluvial/loamy soil'
    },
}


def detect_deficiencies(req: SoilAnalysisRequest) -> list[NutrientDeficiency]:
    """Detect nutrient and pH deficiencies by comparing against ICAR optimal ranges."""
    deficiencies = []

    ranges = AMENDMENTS_DATA.get('nutrient_ranges', {})
    optimal = ranges.get('optimal', {})

    # Check each nutrient
    nutrients = {
        'N': {'value': req.N, 'unit': 'kg/ha'},
        'P': {'value': req.P, 'unit': 'kg/ha'},
        'K': {'value': req.K, 'unit': 'kg/ha'},
    }

    for nutrient, data in nutrients.items():
        opt = optimal.get(nutrient, {})
        opt_min = opt.get('min', 0)
        opt_max = opt.get('max', 200)
        current = data['value']

        if current < opt_min:
            deficit = opt_min - current
            deficiencies.append(NutrientDeficiency(
                nutrient=nutrient,
                current_value=current,
                optimal_min=opt_min,
                optimal_max=opt_max,
                deficit=deficit,
                severity='high' if deficit > opt_min * 0.3 else 'medium'
            ))

    # Check pH
    opt_ph = optimal.get('pH', {})
    ph_min = opt_ph.get('min', 6.0)
    ph_max = opt_ph.get('max', 7.5)

    if req.ph < ph_min:
        deficiencies.append(NutrientDeficiency(
            nutrient='pH',
            current_value=req.ph,
            optimal_min=ph_min,
            optimal_max=ph_max,
            deficit=ph_min - req.ph,
            severity='high' if req.ph < 5.5 else 'medium'
        ))
    elif req.ph > ph_max:
        deficiencies.append(NutrientDeficiency(
            nutrient='pH',
            current_value=req.ph,
            optimal_min=ph_min,
            optimal_max=ph_max,
            deficit=req.ph - ph_max,
            severity='medium' if req.ph <= 8.0 else 'high'
        ))

    # Check organic matter (< 2% is deficient)
    if req.organic_matter_pct < 2.0:
        deficiencies.append(NutrientDeficiency(
            nutrient='organic_matter',
            current_value=req.organic_matter_pct,
            optimal_min=2.0,
            optimal_max=5.0,
            deficit=2.0 - req.organic_matter_pct,
            severity='high'
        ))

    return deficiencies


def get_amendments(req: SoilAnalysisRequest, deficiencies: list[NutrientDeficiency]) -> list[Amendment]:
    """Look up amendment recommendations for each deficiency."""
    amendments = []
    amendments_db = AMENDMENTS_DATA.get('amendments', {})

    for deficiency in deficiencies:
        nutrient = deficiency.nutrient

        if nutrient == 'pH':
            if deficiency.current_value < 5.5:
                category = 'pH_correction'
                subcategory = 'acidic'
            else:
                category = 'pH_correction'
                subcategory = 'alkaline'

            amendments_list = amendments_db.get(category, {}).get(subcategory, [])
        elif nutrient == 'N':
            amendments_list = amendments_db.get('nitrogen', {}).get('deficient', [])
        elif nutrient == 'P':
            amendments_list = amendments_db.get('phosphorus', {}).get('deficient', [])
        elif nutrient == 'K':
            amendments_list = amendments_db.get('potassium', {}).get('deficient', [])
        elif nutrient == 'organic_matter':
            amendments_list = amendments_db.get('organic_matter', {}).get('deficient', [])
        else:
            continue

        # Add top amendment for this deficiency
        if amendments_list:
            top_amendment = amendments_list[0]
            amendments.append(Amendment(
                name=top_amendment.get('name', ''),
                deficiency_target=top_amendment.get('deficiency_target', nutrient),
                dose_kg_per_acre=top_amendment.get('dose_kg_per_acre'),
                dose_kg_per_hectare=top_amendment.get('dose_kg_per_hectare'),
                dose_tonnes_per_acre=top_amendment.get('dose_tonnes_per_acre'),
                dose_tonnes_per_hectare=top_amendment.get('dose_tonnes_per_hectare'),
                time_to_effect_days=top_amendment.get('time_to_effect_days', 30),
                application_method=top_amendment.get('application_method', ''),
                notes=top_amendment.get('notes', ''),
            ))

    return amendments


def get_compatible_crops(req: SoilAnalysisRequest) -> list[str]:
    """Return list of crops suited to the current soil profile."""
    compatible = []

    for crop, profile in CROP_SOIL_COMPATIBILITY.items():
        # Simple scoring: each matching criterion = +1
        score = 0
        max_score = 3

        if profile['optimal_ph_min'] <= req.ph <= profile['optimal_ph_max']:
            score += 1

        if req.N >= profile['optimal_n_min']:
            score += 1

        if req.P >= profile['optimal_p_min']:
            score += 1

        # Accept crops that score at least 2/3
        if score >= 2:
            compatible.append(crop)

    return compatible if compatible else list(CROP_SOIL_COMPATIBILITY.keys())
