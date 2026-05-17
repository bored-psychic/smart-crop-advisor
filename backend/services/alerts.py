import json
import logging
import aiosqlite
from datetime import date

from backend.config import get_settings
from backend.services.weather_service import get_weather_service
from backend.services.sms import send_sms
from backend.services.webpush_service import send_web_push

logger = logging.getLogger(__name__)

PEST_CALENDAR: dict = {
    "armyworm":          {"crops": ["maize", "wheat", "rice", "cotton"],       "peak_months": [6, 7, 8, 9]},
    "aphids":            {"crops": ["cotton", "wheat", "tomato", "potato"],    "peak_months": [3, 4, 5, 10, 11]},
    "stem_borer":        {"crops": ["rice", "maize", "sugarcane"],             "peak_months": [7, 8, 9]},
    "whitefly":          {"crops": ["cotton", "tomato", "chili"],              "peak_months": [4, 5, 6, 9, 10]},
    "brown_planthopper": {"crops": ["rice"],                                   "peak_months": [7, 8, 9, 10]},
    "red_spider_mite":   {"crops": ["cotton", "tomato", "brinjal"],            "peak_months": [3, 4, 5, 11, 12]},
    "locust":            {"crops": ["wheat", "maize", "sorghum", "rice"],      "peak_months": [6, 7, 8]},
    "leaf_curl_virus":   {"crops": ["tomato", "cotton", "chili"],              "peak_months": [4, 5, 6, 10]},
    "blast":             {"crops": ["rice"],                                   "peak_months": [7, 8, 9]},
    "powdery_mildew":    {"crops": ["wheat", "grapes", "cucumber"],            "peak_months": [3, 4, 10, 11]},
}


async def check_frost_rule(sub: dict) -> dict | None:
    ws = get_weather_service()
    city = sub.get("district") or sub.get("state", "")
    weather = await ws.get_current(city)
    if not weather:
        return None
    temp = weather.get("temp", 20)
    if temp < 4:
        return {
            "type": "frost",
            "severity": "high",
            "message": (
                f"Frost alert: {city} temperature {temp:.1f}°C. "
                "Cover your seedlings tonight to protect them."
            ),
        }
    return None


async def check_heavy_rain_rule(sub: dict) -> dict | None:
    ws = get_weather_service()
    city = sub.get("district") or sub.get("state", "")
    weather = await ws.get_current(city)
    if not weather:
        return None
    forecast = await ws.get_forecast_rain(weather.get("lat", 0), weather.get("lon", 0))
    if forecast and forecast.get("rain_48h", 0) > 50:
        mm = forecast["rain_48h"]
        return {
            "type": "heavy_rain",
            "severity": "medium",
            "message": (
                f"Heavy rain warning: {mm:.0f}mm expected in {city} over 48h. "
                "Ensure field drainage and delay pesticide spraying."
            ),
        }
    return None


def check_pest_risk_rule(sub: dict) -> dict | None:
    raw_crops = sub.get("crops", "[]")
    crops = json.loads(raw_crops) if isinstance(raw_crops, str) else raw_crops
    crops_lower = {c.lower() for c in crops}
    month = date.today().month
    location = sub.get("district") or sub.get("state", "your area")

    for pest, info in PEST_CALENDAR.items():
        if month in info["peak_months"]:
            matches = [c for c in info["crops"] if c in crops_lower]
            if matches:
                crop_label = matches[0].title()
                pest_label = pest.replace("_", " ").title()
                return {
                    "type": "pest_risk",
                    "severity": "high",
                    "message": (
                        f"{pest_label} risk peak season for {crop_label} in {location}. "
                        "Monitor closely and prepare spray schedule."
                    ),
                }
    return None


async def check_and_send_alerts() -> None:
    logger.info("Running scheduled alert check...")
    settings = get_settings()

    async with aiosqlite.connect(settings.SQLITE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM alert_subscriptions WHERE active = 1"
        ) as cursor:
            subs = await cursor.fetchall()

        total_sent = 0
        for row in subs:
            sub = dict(row)
            raw_types = sub.get("alert_types", "[]")
            alert_types = json.loads(raw_types) if isinstance(raw_types, str) else raw_types
            triggered: list[dict] = []

            if "frost" in alert_types:
                a = await check_frost_rule(sub)
                if a:
                    triggered.append(a)

            if "heavy_rain" in alert_types:
                a = await check_heavy_rain_rule(sub)
                if a:
                    triggered.append(a)

            if "pest_risk" in alert_types:
                a = check_pest_risk_rule(sub)
                if a:
                    triggered.append(a)

            for alert in triggered:
                if sub.get("phone"):
                    await send_sms(sub["phone"], alert["message"])

                async with db.execute(
                    "SELECT * FROM webpush_subscriptions WHERE phone = ?",
                    (sub["phone"],),
                ) as cur:
                    push_rows = await cur.fetchall()

                for pr in push_rows:
                    pd = dict(pr)
                    await send_web_push(
                        pd["endpoint"], pd["p256dh"], pd["auth"],
                        {"title": f"KisanOS — {alert['type'].replace('_', ' ').title()}",
                         "body": alert["message"]},
                    )

                await db.execute(
                    """INSERT INTO alert_history
                       (subscription_id, alert_type, severity, message, sent_via)
                       VALUES (?, ?, ?, ?, ?)""",
                    (sub["id"], alert["type"], alert["severity"],
                     alert["message"], "sms+webpush"),
                )
                total_sent += 1

        if total_sent:
            await db.commit()

    logger.info(f"Alert check done — {total_sent} alerts sent across {len(subs)} subscriptions.")
