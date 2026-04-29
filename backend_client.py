"""
backend_client.py — Centralized async HTTP layer for all external API calls.

All public functions are sync wrappers around httpx.AsyncClient calls,
decorated with @st.cache_data so repeated Streamlit renders are zero-cost.
API keys are read from .streamlit/secrets.toml — never hardcoded here.
"""
import asyncio
import streamlit as st
import httpx

# ── Data constants ────────────────────────────────────────────────────────────

# Disease prevalence by Indian state — sourced from ICAR / IRRI regional surveys.
# Used by state-aware inference to flag geographically unlikely predictions.
# Keys are lowercase substrings matched against the predicted disease name.
# Distinct from STATE_PRICE_FACTORS (market prices) — entirely separate data.
DISEASE_GEOGRAPHY: dict[str, dict[str, list[str]]] = {
    # Rice
    'blast': {
        'high':   ['West Bengal', 'Odisha', 'Assam', 'Uttarakhand', 'Himachal Pradesh', 'Karnataka', 'Kerala'],
        'medium': ['Bihar', 'Jharkhand', 'Tamil Nadu', 'Andhra Pradesh', 'Telangana'],
        'rare':   ['Punjab', 'Haryana', 'Rajasthan', 'Gujarat'],
    },
    'brown spot': {
        'high':   ['West Bengal', 'Odisha', 'Bihar', 'Assam'],
        'medium': ['Uttar Pradesh', 'Madhya Pradesh', 'Tamil Nadu', 'Jharkhand'],
        'rare':   ['Punjab', 'Haryana', 'Rajasthan'],
    },
    'leaf smut': {
        'high':   ['Andhra Pradesh', 'Telangana', 'Karnataka', 'Tamil Nadu', 'Kerala'],
        'medium': ['Odisha', 'West Bengal', 'Chhattisgarh'],
        'rare':   ['Punjab', 'Haryana', 'Rajasthan', 'Gujarat'],
    },
    # Maize / Corn
    'northern leaf blight': {
        'high':   ['Karnataka', 'Maharashtra', 'Andhra Pradesh', 'Telangana', 'Rajasthan'],
        'medium': ['Gujarat', 'Madhya Pradesh', 'Bihar', 'Uttar Pradesh'],
        'rare':   ['Punjab', 'Haryana'],
    },
    'common rust': {
        'high':   ['Bihar', 'Uttar Pradesh', 'Punjab', 'Haryana', 'Uttarakhand', 'Himachal Pradesh'],
        'medium': ['Madhya Pradesh', 'Jharkhand'],
        'rare':   ['Karnataka', 'Tamil Nadu', 'Kerala'],        # too warm for rust
    },
    'gray leaf spot': {
        'high':   ['Karnataka', 'Maharashtra', 'Andhra Pradesh', 'Telangana'],
        'medium': ['Gujarat', 'Madhya Pradesh', 'Odisha'],
        'rare':   ['Punjab', 'Haryana', 'Rajasthan'],
    },
    'cercospora': {                                            # alias for gray leaf spot
        'high':   ['Karnataka', 'Maharashtra', 'Andhra Pradesh', 'Telangana'],
        'medium': ['Gujarat', 'Madhya Pradesh', 'Odisha'],
        'rare':   ['Punjab', 'Haryana', 'Rajasthan'],
    },
    # Chickpea / Pulses  (ICAR 2023 All India Coordinated Research Project on MULLaRP data)
    'fusarium wilt': {
        'high':   ['Madhya Pradesh', 'Rajasthan', 'Uttar Pradesh', 'Maharashtra',
                   'Karnataka', 'Andhra Pradesh', 'Telangana'],
        'medium': ['Gujarat', 'Haryana', 'Punjab', 'Bihar', 'Chhattisgarh'],
        'rare':   ['West Bengal', 'Assam', 'Kerala', 'Odisha'],   # too humid; rice dominates
    },
    'ascochyta blight': {
        # Cool, humid conditions — peaks in north-west rabi belt and hills
        'high':   ['Rajasthan', 'Madhya Pradesh', 'Himachal Pradesh',
                   'Uttarakhand', 'Punjab', 'Haryana'],
        'medium': ['Uttar Pradesh', 'Maharashtra', 'Gujarat'],
        'rare':   ['Karnataka', 'Tamil Nadu', 'Kerala', 'West Bengal', 'Assam'],
    },
    'dry root rot': {
        # High-temperature + drought stress — widespread in peninsular & central belt
        'high':   ['Madhya Pradesh', 'Rajasthan', 'Maharashtra',
                   'Andhra Pradesh', 'Karnataka', 'Telangana'],
        'medium': ['Gujarat', 'Uttar Pradesh', 'Chhattisgarh'],
        'rare':   ['Punjab', 'Haryana', 'West Bengal', 'Assam', 'Himachal Pradesh'],
    },
    # Pigeonpea / Lentil  (ICAR-IIPR Kanpur data; ICRISAT SMD survey)
    'sterility mosaic': {
        # SMD belt: humid + warm — pigeonpea-growing states; vector Aceria cajani thrives
        'high':   ['Uttar Pradesh', 'Bihar', 'Maharashtra', 'Karnataka',
                   'Andhra Pradesh', 'Telangana', 'Odisha'],
        'medium': ['Madhya Pradesh', 'Gujarat', 'Rajasthan', 'West Bengal', 'Jharkhand'],
        'rare':   ['Punjab', 'Haryana', 'Himachal Pradesh', 'Uttarakhand'],
    },
    # 'wilt' key catches pigeonpea Fusarium udum; 'fusarium wilt' (above) catches chickpea.
    # 'fusarium wilt' appears first in the dict, so cn='fusarium wilt' matches that key first.
    'wilt': {
        'high':   ['Uttar Pradesh', 'Bihar', 'Maharashtra', 'Karnataka', 'Andhra Pradesh'],
        'medium': ['Madhya Pradesh', 'Gujarat', 'Rajasthan', 'Tamil Nadu', 'Telangana'],
        'rare':   ['Punjab', 'Haryana', 'West Bengal', 'Assam', 'Himachal Pradesh'],
    },
    # 'rust' key — placed after 'common rust' so cn='common rust' matches the specific key first.
    'rust': {
        # Lentil rust belt: cool-dry rabi regions
        'high':   ['Madhya Pradesh', 'Uttar Pradesh', 'Bihar', 'Rajasthan', 'West Bengal'],
        'medium': ['Odisha', 'Jharkhand', 'Maharashtra', 'Chhattisgarh'],
        'rare':   ['Punjab', 'Haryana', 'Karnataka', 'Tamil Nadu', 'Kerala'],
    },
    # Mungbean / Blackgram — Vigna species  (ICAR-IIPR 2023 YMD survey data)
    'yellow mosaic': {
        # YMD belt: warm, low-humidity zones where whitefly (Bemisia tabaci) thrives
        'high':   ['Uttar Pradesh', 'Bihar', 'Haryana', 'Madhya Pradesh',
                   'Rajasthan', 'Maharashtra'],
        'medium': ['Punjab', 'Karnataka', 'Andhra Pradesh', 'Telangana', 'Gujarat'],
        'rare':   ['Kerala', 'Himachal Pradesh', 'Uttarakhand', 'Assam',
                   'West Bengal'],    # cool/humid — whitefly less active
    },
}


def get_geographic_flag(disease: str, state: str) -> str | None:
    """
    Return an advisory string if the predicted disease is rarely reported in
    the user's state. Returns None when no geographic concern exists.
    NOTE: This supplements, never overrides, model output.
    """
    if not disease or not state:
        return None
    dl = disease.lower()
    for key, geo in DISEASE_GEOGRAPHY.items():
        if key in dl:
            if state in geo.get('rare', []):
                return (
                    f"{disease} is rarely reported in {state}. "
                    f"Verify with your local KVK or agriculture extension officer before acting."
                )
            break
    return None


INDIA_STATES = [
    "Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
    "Maharashtra", "Odisha", "Punjab", "Rajasthan", "Tamil Nadu", "Telangana",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
]

STATE_PRICE_FACTORS = {
    "Punjab":          {"Wheat":1.08,"Rice":1.05,"Maize":0.98,"Cotton":1.02,"Potato":0.94},
    "Haryana":         {"Wheat":1.06,"Rice":1.03,"Maize":0.97,"Cotton":1.01,"Potato":0.95},
    "Uttar Pradesh":   {"Wheat":1.04,"Rice":1.02,"Maize":1.00,"Sugarcane":1.10,"Potato":1.12},
    "Maharashtra":     {"Cotton":1.15,"Onion":1.20,"Soybean":1.08,"Grape":1.25,"Orange":1.18},
    "Karnataka":       {"Coffee":1.22,"Cotton":1.10,"Maize":1.05,"Tomato":1.08,"Mango":1.15},
    "Andhra Pradesh":  {"Rice":1.06,"Cotton":1.08,"Chilli":1.30,"Maize":1.04,"Tomato":1.10},
    "Telangana":       {"Rice":1.04,"Cotton":1.09,"Maize":1.06,"Tomato":1.12,"Soybean":1.07},
    "Tamil Nadu":      {"Rice":1.07,"Banana":1.18,"Coconut":1.22,"Cotton":1.05,"Groundnut":1.15},
    "Gujarat":         {"Cotton":1.12,"Groundnut":1.18,"Cumin":1.35,"Castor":1.20,"Wheat":1.02},
    "Madhya Pradesh":  {"Soybean":1.14,"Wheat":1.05,"Chickpea":1.10,"Maize":1.02,"Tomato":0.98},
    "Rajasthan":       {"Wheat":1.03,"Mustard":1.15,"Cumin":1.28,"Barley":1.08,"Cotton":1.06},
    "West Bengal":     {"Rice":1.08,"Potato":1.15,"Jute":1.25,"Banana":1.10,"Mustard":1.12},
    "Bihar":           {"Rice":1.05,"Wheat":1.03,"Maize":1.08,"Potato":1.18,"Litchi":1.40},
    "Odisha":          {"Rice":1.06,"Potato":1.10,"Tomato":1.05,"Banana":1.08,"Jute":1.15},
    "Kerala":          {"Coconut":1.30,"Rubber":1.45,"Banana":1.20,"Pepper":1.50,"Cardamom":1.60},
}

CALAMITY_TIPS = {
    'thunderstorm': ['⚡ Move livestock to shelter', '🚫 Stop all field work immediately', '💧 Clear drainage channels'],
    'rain':         ['🌱 Avoid fertilizer — will wash away', '🌊 Create bunds around fields', '📞 Contact agriculture office if flooding'],
    'drizzle':      ['💧 Good for germination', '🌱 Ideal time for transplanting', '✅ Reduce irrigation today'],
    'snow':         ['🌿 Cover sensitive crops with cloth', '🔥 Light irrigation before frost protects roots', '🌱 Avoid pruning until frost passes'],
    'mist':         ['🍄 Watch for fungal disease', '💊 Apply preventive fungicide', '🌬️ Improve air circulation'],
    'haze':         ['😷 Reduce outdoor work', '💧 Increase irrigation — heat stress likely', '🌿 Monitor crops for wilting'],
    'clear':        ['☀️ Good day for spraying pesticides', '🚜 Ideal for harvesting', '💧 Check soil moisture levels'],
    'clouds':       ['🌤️ Good day for transplanting', '💧 Moderate irrigation needed', '🌱 Apply fertilizers today'],
}


# ── Key loading ───────────────────────────────────────────────────────────────

def _keys() -> dict:
    """Read API keys from st.secrets; fall back to empty strings if unavailable."""
    try:
        s = st.secrets
        return {
            'owm':      s.get("OWM_KEY",      ""),
            'data_gov': s.get("DATA_GOV_KEY", ""),
            'firms':    s.get("FIRMS_KEY",    ""),
        }
    except Exception:
        return {'owm': '', 'data_gov': '', 'firms': ''}


# ── Async loop helper ─────────────────────────────────────────────────────────

def _run(coro):
    """Run a coroutine in a fresh event loop — safe to call from Streamlit's main thread."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Input validators ──────────────────────────────────────────────────────────

def _parse_firms_row(parts: list) -> tuple | None:
    """
    Validate a single FIRMS CSV row before it reaches proximity math.
    Returns (lat, lon) only when both values are finite and within WGS-84 bounds.
    """
    if len(parts) < 2:
        return None
    try:
        lat, lon = float(parts[0]), float(parts[1])
    except (ValueError, IndexError):
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    import math
    if not (math.isfinite(lat) and math.isfinite(lon)):
        return None
    return lat, lon


# ── Async implementations ─────────────────────────────────────────────────────

async def _async_get_weather(city: str, owm_key: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(
            "http://api.openweathermap.org/data/2.5/weather",
            params={"q": f"{city},IN", "appid": owm_key, "units": "metric"},
        )
        d = r.json()
        if d.get('cod') == 200:
            return {
                'temp':        d['main']['temp'],
                'humidity':    d['main']['humidity'],
                'description': d['weather'][0]['description'].title(),
                'wind_speed':  d['wind']['speed'] * 3.6,
                'rainfall':    d.get('rain', {}).get('1h', 0),
                'city':        d['name'],
            }
    return None


async def _async_get_mandi_price(crop: str, state: str, data_gov_key: str):
    crop_q  = crop.replace(' ', '%20')
    state_q = state.replace(' ', '%20')
    url = (
        f"https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
        f"?api-key={data_gov_key}&format=json&limit=10"
        f"&filters%5Bcommodity%5D={crop_q}&filters%5Bstate%5D={state_q}"
    )
    async with httpx.AsyncClient(timeout=6.0) as client:
        r = await client.get(url)
        records = r.json().get('records', [])
        if records:
            prices = []
            for rec in records:
                try:
                    prices.append(float(rec.get('modal_price', 0) or rec.get('max_price', 0)))
                except Exception:
                    pass
            if prices:
                state_f = STATE_PRICE_FACTORS.get(state, {}).get(crop, 1.0)
                return {
                    'today_price':    round(sum(prices) / len(prices), 0),
                    'source':         'Agmarknet Live',
                    'mandis_checked': len(prices),
                    'state_factor':   state_f,
                    'live':           True,
                }
    return None


async def _async_fetch_field_watch(city: str, owm_key: str, firms_key: str) -> dict:
    alerts = {
        'weather': None, 'fire': None, 'locust': None,
        'aqi': None, 'flood': None, 'city': city,
    }
    lat, lon = None, None

    async with httpx.AsyncClient(timeout=httpx.Timeout(7.0)) as client:
        # 1. Current weather (must run first to obtain lat/lon)
        try:
            r = await client.get(
                "http://api.openweathermap.org/data/2.5/weather",
                params={"q": f"{city},IN", "appid": owm_key, "units": "metric"},
            )
            w = r.json()
            if w.get('cod') == 200:
                lat, lon = w['coord']['lat'], w['coord']['lon']
                alerts['weather'] = {
                    'temp':       w['main']['temp'],
                    'feels_like': w['main']['feels_like'],
                    'humidity':   w['main']['humidity'],
                    'wind':       round(w['wind']['speed'] * 3.6, 1),
                    'desc':       w['weather'][0]['description'].title(),
                    'rain_1h':    w.get('rain', {}).get('1h', 0),
                    'lat': lat, 'lon': lon,
                }
        except Exception:
            pass

        if lat and lon:
            # 2. 48-hour flood forecast
            try:
                rf = await client.get(
                    "http://api.openweathermap.org/data/2.5/forecast",
                    params={"lat": lat, "lon": lon, "appid": owm_key, "units": "metric", "cnt": 8},
                )
                rain_48 = sum(
                    item.get('rain', {}).get('3h', 0)
                    for item in rf.json().get('list', [])
                )
                alerts['flood'] = {
                    'rain_48h':   round(rain_48, 1),
                    'flood_risk': 'HIGH' if rain_48 > 50 else 'MEDIUM' if rain_48 > 25 else 'LOW',
                }
            except Exception:
                pass

            # 3. NASA FIRMS wildfire hotspots
            try:
                rf = await client.get(
                    f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{firms_key}/MODIS_NRT/IND/1",
                )
                if rf.status_code == 200 and rf.text.strip():
                    nearby = 0
                    for line in rf.text.strip().split('\n')[1:]:
                        coords = _parse_firms_row(line.split(','))
                        if coords and ((coords[0] - lat) ** 2 + (coords[1] - lon) ** 2) ** 0.5 < 2.0:
                            nearby += 1
                    alerts['fire'] = {
                        'hotspots_nearby': nearby,
                        'risk':   'HIGH' if nearby > 5 else 'MEDIUM' if nearby > 0 else 'NONE',
                        'source': 'NASA FIRMS MODIS',
                    }
            except Exception:
                alerts['fire'] = {
                    'hotspots_nearby': 0, 'risk': 'UNKNOWN', 'source': 'NASA FIRMS (unavailable)',
                }

            # 4. FAO Desert Locust swarms
            try:
                rf = await client.get(
                    "https://locust-hub-hqfao.hub.arcgis.com/datasets/fao::desert-locust-presence-1.geojson",
                )
                nearby = 0
                if rf.status_code == 200:
                    for feat in rf.json().get('features', [])[:200]:
                        coords = feat.get('geometry', {}).get('coordinates', [])
                        if coords:
                            flon2, flat2 = coords[0], coords[1]
                            if ((flat2 - lat) ** 2 + (flon2 - lon) ** 2) ** 0.5 < 5.0:
                                nearby += 1
                alerts['locust'] = {
                    'swarms_nearby': nearby,
                    'risk':   'HIGH' if nearby > 2 else 'MEDIUM' if nearby > 0 else 'NONE',
                    'source': 'FAO Desert Locust Hub',
                }
            except Exception:
                alerts['locust'] = {
                    'swarms_nearby': 0, 'risk': 'UNKNOWN', 'source': 'FAO Hub (unavailable)',
                }

            # 5. Air Quality Index
            try:
                ra = await client.get(
                    "http://api.openweathermap.org/data/2.5/air_pollution",
                    params={"lat": lat, "lon": lon, "appid": owm_key},
                )
                aqi_val = ra.json()['list'][0]['main']['aqi']
                alerts['aqi'] = {
                    'value': aqi_val,
                    'label': {1: 'Good', 2: 'Fair', 3: 'Moderate', 4: 'Poor', 5: 'Very Poor'}.get(
                        aqi_val, 'Unknown'
                    ),
                }
            except Exception:
                pass

    return alerts


# ── Public cached API ─────────────────────────────────────────────────────────

@st.cache_data(ttl=1800)
def get_weather(city: str):
    """Fetch OWM current weather; cached 30 min. Returns None on error."""
    try:
        return _run(_async_get_weather(city, _keys()['owm']))
    except Exception:
        return None


@st.cache_data(ttl=1800)
def get_live_mandi_price(crop: str, state: str):
    """Fetch live Agmarknet price from data.gov.in; cached 30 min. Returns None on error."""
    try:
        return _run(_async_get_mandi_price(crop, state, _keys()['data_gov']))
    except Exception:
        return None


@st.cache_data(ttl=600)
def fetch_field_watch(city: str):
    """Aggregate OWM + NASA FIRMS + FAO + AQI; cached 10 min. Returns None on error."""
    try:
        k = _keys()
        return _run(_async_fetch_field_watch(city, k['owm'], k['firms']))
    except Exception:
        return None


def get_state_adjusted_forecast(future_forecast, crop: str, state: str):
    """Apply state-specific seasonal price factor to a Prophet forecast DataFrame."""
    factor = STATE_PRICE_FACTORS.get(state, {}).get(crop, 1.0)
    df = future_forecast.copy()
    df['Price'] = (df['Price'] * factor).round(0)
    df['Min']   = (df['Min']   * factor).round(0)
    df['Max']   = (df['Max']   * factor).round(0)
    return df, factor
