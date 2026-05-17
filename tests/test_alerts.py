import json, pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date


def make_sub(crops=["Rice"], alert_types=["frost", "heavy_rain", "pest_risk"],
             district="Shimla", state="Himachal Pradesh", phone="+919876543210"):
    return {"id": 1, "phone": phone, "district": district, "state": state,
            "crops": json.dumps(crops), "alert_types": json.dumps(alert_types)}


@pytest.mark.asyncio
async def test_frost_rule_triggers_below_4c():
    from backend.services.alerts import check_frost_rule
    mock_ws = MagicMock()
    mock_ws.get_current = AsyncMock(return_value={"temp": 2.5, "lat": 31.1, "lon": 77.1})
    mock_ws.get_forecast_rain = AsyncMock(return_value={"rain_48h": 0, "flood_risk": "LOW"})
    with patch("backend.services.alerts.get_weather_service", return_value=mock_ws):
        alert = await check_frost_rule(make_sub())
    assert alert is not None
    assert alert["type"] == "frost"
    assert "2.5" in alert["message"]


@pytest.mark.asyncio
async def test_frost_rule_no_trigger_above_4c():
    from backend.services.alerts import check_frost_rule
    mock_ws = MagicMock()
    mock_ws.get_current = AsyncMock(return_value={"temp": 10.0, "lat": 31.1, "lon": 77.1})
    mock_ws.get_forecast_rain = AsyncMock(return_value={"rain_48h": 0, "flood_risk": "LOW"})
    with patch("backend.services.alerts.get_weather_service", return_value=mock_ws):
        alert = await check_frost_rule(make_sub())
    assert alert is None


@pytest.mark.asyncio
async def test_heavy_rain_triggers_above_50mm():
    from backend.services.alerts import check_heavy_rain_rule
    mock_ws = MagicMock()
    mock_ws.get_current = AsyncMock(return_value={"temp": 25, "lat": 19.0, "lon": 73.0})
    mock_ws.get_forecast_rain = AsyncMock(return_value={"rain_48h": 75.0, "flood_risk": "HIGH"})
    with patch("backend.services.alerts.get_weather_service", return_value=mock_ws):
        alert = await check_heavy_rain_rule(make_sub())
    assert alert is not None
    assert alert["type"] == "heavy_rain"
    assert "75" in alert["message"]


def test_pest_risk_rule_matches_crop_in_peak_month():
    from backend.services.alerts import check_pest_risk_rule, PEST_CALENDAR
    pest_name = list(PEST_CALENDAR.keys())[0]
    info = PEST_CALENDAR[pest_name]
    peak_month = info["peak_months"][0]
    crop = info["crops"][0].title()
    sub = make_sub(crops=[crop])
    with patch("backend.services.alerts.date") as mock_date:
        mock_date.today.return_value = date(2026, peak_month, 10)
        alert = check_pest_risk_rule(sub)
    assert alert is not None
    assert alert["type"] == "pest_risk"


def test_pest_risk_rule_no_match_off_season():
    from backend.services.alerts import check_pest_risk_rule
    sub = make_sub(crops=["Coconut"])
    with patch("backend.services.alerts.date") as mock_date:
        mock_date.today.return_value = date(2026, 1, 10)
        alert = check_pest_risk_rule(sub)
    assert alert is None
