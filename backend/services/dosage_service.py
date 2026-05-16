"""
Dosage Service — chemical dosage lookup for pest/crop combinations.
Loads data/dosage_db.json once and caches in module-level _DB.
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

from anthropic import AsyncAnthropic

from backend.config import get_settings
from backend.schemas.dosage import DosageAdvice
from backend.services import market

# ---------------------------------------------------------------------------
# Module-level DB cache
# ---------------------------------------------------------------------------

_DB: list[dict] | None = None

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DB_PATH = _REPO_ROOT / "data" / "dosage_db.json"


def _load_db() -> list:
    global _DB
    if _DB is None:
        try:
            with open(_DB_PATH) as f:
                _DB = json.load(f)
        except FileNotFoundError:
            raise RuntimeError(f"dosage_db.json not found at {_DB_PATH}")
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"dosage_db.json is malformed: {exc}")
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

async def _generate_narrative(
    pest_id: str,
    crop: str,
    chemical_name: str,
    formulation: str,
    total_quantity_ml: float,
    water_litres: float,
    area_acres: float,
    total_cost_inr: float,
    roi_protected_inr: Optional[float],
    reapply_days: int,
    timing: str,
) -> str:
    """Generate a plain-English farmer advisory narrative using claude-haiku-4-5-20251001."""
    if roi_protected_inr is not None:
        prompt = (
            f"You are advising an Indian farmer. A {pest_id} has been detected on their {crop}.\n"
            f"Dosage: {total_quantity_ml:.0f}ml of {chemical_name} {formulation} diluted in {water_litres:.0f}L water per acre.\n"
            f"Area: {area_acres} acres. Total chemical cost: ₹{total_cost_inr:.0f}.\n"
            f"Spray timing: {timing}. Reapply after {reapply_days} days if pest persists.\n"
            f"ROI: Treating protects an estimated ₹{roi_protected_inr:.0f} in yield value.\n"
            "Write 3 sentences in simple English: what to do, when, and why it's worth the cost.\n"
            "No markdown. No bullet points. Plain paragraph."
        )
    else:
        prompt = (
            f"You are advising an Indian farmer. A {pest_id} has been detected on their {crop}.\n"
            f"Dosage: {total_quantity_ml:.0f}ml of {chemical_name} {formulation} diluted in {water_litres:.0f}L water per acre.\n"
            f"Area: {area_acres} acres. Total chemical cost: ₹{total_cost_inr:.0f}.\n"
            f"Spray timing: {timing}. Reapply after {reapply_days} days if pest persists.\n"
            "Write 2 sentences in simple English: what to do and when.\n"
            "No markdown. No bullet points. Plain paragraph."
        )

    try:
        api_key = get_settings().ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        client = AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception:
        return f"Apply {chemical_name} {formulation} at the recommended dose. Follow label instructions."


async def _llm_fallback(pest_id: str, crop: str, area_acres: float = 1.0) -> DosageAdvice:
    """Use Haiku to generate a best-effort dosage advisory when the DB has no match."""
    _FALLBACK_ERROR = DosageAdvice(
        chemical_name="Consult local agricultural officer",
        formulation="",
        total_quantity_ml=0,
        water_litres=0,
        timing="As advised",
        reapply_after_days=14,
        total_cost_inr=0,
        roi_protected_inr=None,
        narrative="AI could not generate a recommendation for this pest. Please consult your local Krishi Vigyan Kendra.",
        source="llm_fallback",
    )

    try:
        api_key = get_settings().ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        client = AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system="You are an Indian agricultural expert. Provide practical pesticide recommendations for Indian farmers. Respond ONLY with valid JSON.",
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Pest/disease '{pest_id}' detected on '{crop}'. "
                        "Provide a pesticide recommendation for Indian farmers. "
                        'JSON format: {"chemical_name": "...", "formulation": "...", '
                        '"dose_ml_per_acre": 0, "water_l_per_acre": 0, "timing": "...", '
                        '"reapply_days": 0, "cost_per_litre_inr": 0, "yield_loss_if_untreated_pct": 0}'
                    ),
                }
            ],
        )

        raw = message.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)

        total_quantity_ml = data["dose_ml_per_acre"] * area_acres
        water_litres = data["water_l_per_acre"] * area_acres
        total_cost_inr = (total_quantity_ml / 1000) * data["cost_per_litre_inr"]
        roi_protected_inr = None

        narrative = await _generate_narrative(
            pest_id=pest_id,
            crop=crop,
            chemical_name=data["chemical_name"],
            formulation=data["formulation"],
            total_quantity_ml=total_quantity_ml,
            water_litres=water_litres,
            area_acres=area_acres,
            total_cost_inr=total_cost_inr,
            roi_protected_inr=roi_protected_inr,
            reapply_days=data["reapply_days"],
            timing=data["timing"],
        )

        return DosageAdvice(
            chemical_name=data["chemical_name"],
            formulation=data["formulation"],
            total_quantity_ml=total_quantity_ml,
            water_litres=water_litres,
            timing=data["timing"],
            reapply_after_days=data["reapply_days"],
            total_cost_inr=total_cost_inr,
            roi_protected_inr=roi_protected_inr,
            narrative=narrative,
            source="llm_fallback",
        )
    except Exception:
        return _FALLBACK_ERROR


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

    # e) No match — LLM fallback
    if entry is None:
        return await _llm_fallback(pest_id, crop, area_acres)

    # Compute derived fields
    total_quantity_ml = entry["dose_ml_per_acre"] * area_acres
    water_litres = entry["water_l_per_acre"] * area_acres
    total_cost_inr = (total_quantity_ml / 1000) * entry["cost_per_litre_inr"]
    roi_protected_inr = await _get_roi(entry, crop, state, area_acres)

    narrative = await _generate_narrative(
        pest_id=pest_id,
        crop=crop,
        chemical_name=entry["chemical_name"],
        formulation=entry["formulation"],
        total_quantity_ml=total_quantity_ml,
        water_litres=water_litres,
        area_acres=area_acres,
        total_cost_inr=total_cost_inr,
        roi_protected_inr=roi_protected_inr,
        reapply_days=entry["reapply_days"],
        timing=entry["timing"],
    )

    return DosageAdvice(
        chemical_name=entry["chemical_name"],
        formulation=entry["formulation"],
        total_quantity_ml=total_quantity_ml,
        water_litres=water_litres,
        timing=entry["timing"],
        reapply_after_days=entry["reapply_days"],
        total_cost_inr=total_cost_inr,
        roi_protected_inr=roi_protected_inr,
        narrative=narrative,
        source="db",
    )
