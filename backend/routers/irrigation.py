"""Irrigation advisor router — FAO-56 Penman-Monteith."""

import numpy as np
from fastapi import APIRouter, Depends
from backend.schemas.errors import http_error
from backend.schemas.irrigation import IrrigationRequest, IrrigationResponse, FertilizerAdvice
from backend.core.constants import CROP_KC, FERTILIZER_SCHEDULE
from backend.auth import require_user_or_api_key

router = APIRouter(prefix="/api/irrigation", tags=["Irrigation Advisor"])


def calculate_ET0(temp: float, humidity: float, wind_speed_kmh: float) -> float:
    """FAO-56 simplified reference evapotranspiration."""
    wind_ms = wind_speed_kmh / 3.6
    es = 0.6108 * np.exp(17.27 * temp / (temp + 237.3))
    ea = es * humidity / 100
    vpd = max(es - ea, 0)
    ET0 = (0.408 * 0.0135 * (temp + 17.8) * (wind_ms + 1)) + (0.34 * vpd * wind_ms)
    return max(round(ET0, 2), 1.0)


@router.post("/advise", response_model=IrrigationResponse)
async def irrigation_advice(
    req: IrrigationRequest,
    _=Depends(require_user_or_api_key),
):
    """Calculate water + fertilizer needs using FAO-56."""
    if req.crop not in CROP_KC:
        raise http_error(404, "crop_not_found", f"Crop '{req.crop}' not found in Kc database")
    if req.growth_stage not in CROP_KC[req.crop]:
        raise http_error(400, "invalid_growth_stage", f"Invalid growth stage: {req.growth_stage}")

    ET0 = calculate_ET0(req.temperature, req.humidity, req.wind_speed)
    Kc = CROP_KC[req.crop][req.growth_stage]
    ETc = ET0 * Kc
    effective_rain = req.last_rain_mm * 0.7
    net_irrigation = max(ETc - effective_rain / 3, 0)
    litres_per_acre = net_irrigation * 4046.86
    total_litres = litres_per_acre * req.field_area

    # Determine urgency
    if net_irrigation < 1.0:
        urgency = "none"
        advice = "No irrigation needed today! Recent rainfall is sufficient."
    elif net_irrigation < 3.0:
        urgency = "light"
        advice = f"Light irrigation recommended: Apply {net_irrigation:.1f} mm ({total_litres/1000:.1f} kL)"
    else:
        urgency = "urgent"
        advice = f"Irrigation urgently needed: Apply {net_irrigation:.1f} mm ({total_litres/1000:.1f} kL)"

    fert = FERTILIZER_SCHEDULE[req.growth_stage]

    return IrrigationResponse(
        crop=req.crop,
        ET0=ET0,
        Kc=Kc,
        ETc=round(ETc, 2),
        net_irrigation_mm=round(net_irrigation, 2),
        total_litres=round(total_litres, 0),
        total_kl=round(total_litres / 1000, 2),
        field_area=req.field_area,
        urgency=urgency,
        advice=advice,
        fertilizer=FertilizerAdvice(
            nitrogen=fert['N'],
            tip=fert['tip'],
            growth_stage=req.growth_stage,
        ),
    )
