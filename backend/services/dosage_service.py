"""
Dosage Service — chemical dosage lookup for pest/crop combinations.
Loads data/dosage_db.json once and caches in module-level _DB.
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

from backend.schemas.dosage import DosageAdvice
from backend.services import market

# ---------------------------------------------------------------------------
# Module-level DB cache
# ---------------------------------------------------------------------------

_DB: list[dict] | None = None

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DB_PATH = _REPO_ROOT / "data" / "dosage_db.json"


def _load_db() -> list[dict]:
    global _DB
    if _DB is None:
        with open(_DB_PATH, "r", encoding="utf-8") as f:
            _DB = json.load(f)
    return _DB


# ---------------------------------------------------------------------------
# Stage bucket helpers
# ---------------------------------------------------------------------------

_STAGE_ORDER = ["seedling", "vegetative", "flowering", "harvest"]


def _crop_stage_bucket(days: int) -> str:
    if days <= 30:
        return "seedling"
    elif days <= 60:
        return "vegetative"
    elif days <= 90:
        return "flowering"
    else:
        return "harvest"


def _stage_distance(a: str, b: str) -> int:
    """Absolute distance between two stage bucket names in the ordering."""
    try:
        return abs(_STAGE_ORDER.index(a) - _STAGE_ORDER.index(b))
    except ValueError:
        return 999


# ---------------------------------------------------------------------------
# Yield defaults for ROI calculation
# ---------------------------------------------------------------------------

_YIELD_T_PER_ACRE = {
    "rice": 1.5,
    "wheat": 1.6,
    "maize": 3.5,
    "tomato": 8.0,
    "cotton": 0.4,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _llm_fallback(pest_id: str, crop: str) -> DosageAdvice:
    raise NotImplementedError("llm_fallback not yet implemented")


async def _get_roi(
    entry: dict,
    crop: str,
    state: str | None,
    area_acres: float,
) -> Optional[float]:
    expected_yield = _YIELD_T_PER_ACRE.get(crop.lower())
    if expected_yield is None:
        return None

    try:
        # Run the blocking sync HTTP call in a thread pool to avoid blocking the event loop.
        market_data = await asyncio.to_thread(
            market.get_live_mandi_price, crop.capitalize(), state
        )
        if market_data is None:
            return None
        # Agmarknet price is per quintal (100 kg = 0.1 t) → multiply by 10 for per-tonne
        price_per_t = market_data["today_price"] * 10
    except Exception:
        return None

    yield_loss_pct = entry["yield_loss_if_untreated_pct"] / 100.0
    roi = yield_loss_pct * expected_yield * price_per_t * area_acres
    return round(roi, 0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def lookup(
    pest_id: str,
    crop: str,
    crop_stage_days: int,
    area_acres: float,
    state: str | None,
) -> DosageAdvice:
    # Normalize inputs
    pest_id = pest_id.lower().strip().replace(" ", "_")
    crop = crop.lower().strip()

    db = _load_db()
    stage_bucket = _crop_stage_bucket(crop_stage_days)

    # Build candidate pools in priority order
    entry = None

    # a) Exact match: pest_id AND crop AND crop_stage_bucket
    for e in db:
        if (
            e["pest_id"] == pest_id
            and e["crop"] == crop
            and e["crop_stage_bucket"] == stage_bucket
        ):
            entry = e
            break

    # b) Same pest_id AND crop, any stage bucket (nearest wins)
    if entry is None:
        candidates = [
            e for e in db if e["pest_id"] == pest_id and e["crop"] == crop
        ]
        if candidates:
            entry = min(
                candidates,
                key=lambda e: _stage_distance(e["crop_stage_bucket"], stage_bucket),
            )

    # c) pest_id AND crop == "all" AND crop_stage_bucket matches
    if entry is None:
        for e in db:
            if (
                e["pest_id"] == pest_id
                and e["crop"] == "all"
                and e["crop_stage_bucket"] == stage_bucket
            ):
                entry = e
                break

    # d) pest_id AND crop == "all", any stage bucket
    if entry is None:
        candidates = [
            e for e in db if e["pest_id"] == pest_id and e["crop"] == "all"
        ]
        if candidates:
            entry = min(
                candidates,
                key=lambda e: _stage_distance(e["crop_stage_bucket"], stage_bucket),
            )

    # e) No match — LLM fallback (stub)
    if entry is None:
        return _llm_fallback(pest_id, crop)

    # Compute derived fields
    total_quantity_ml = entry["dose_ml_per_acre"] * area_acres
    water_litres = entry["water_l_per_acre"] * area_acres
    total_cost_inr = (total_quantity_ml / 1000) * entry["cost_per_litre_inr"]
    roi_protected_inr = await _get_roi(entry, crop, state, area_acres)

    return DosageAdvice(
        chemical_name=entry["chemical_name"],
        formulation=entry["formulation"],
        total_quantity_ml=total_quantity_ml,
        water_litres=water_litres,
        timing=entry["timing"],
        reapply_after_days=entry["reapply_days"],
        total_cost_inr=total_cost_inr,
        roi_protected_inr=roi_protected_inr,
        narrative="",
        source="db",
    )
