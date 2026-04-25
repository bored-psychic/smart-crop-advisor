"""
services/satellite.py — Sentinel-2 NDVI temporal analysis.

Entirely decoupled from the CV inference path. Provides field-level vegetation
stress intelligence before visual disease symptoms appear (15-day window).

Authentication: Sentinel Hub OAuth2 client-credentials flow.
Add to .streamlit/secrets.toml:
    SENTINEL_CLIENT_ID     = "your-client-id"
    SENTINEL_CLIENT_SECRET = "your-client-secret"

If credentials are absent or the API is unreachable, every public function
returns a safe fallback dict — the UI degrades gracefully without crashing.

Design choices vs. provided snippets:
  - Module-level functions, NOT a class with @st.cache_data on methods.
    @st.cache_data hashes all arguments; 'self' in an instance method is not
    consistently hashable across Streamlit reruns and crashes on first call.
  - Sentinel Hub Statistical API (not WMS/OGC) — the WMS endpoint is legacy.
    The Statistical API returns per-interval mean NDVI in a single request,
    which is ideal for the 15-day trend window.
  - Real OAuth2 + real API calls. Stubs with pass or hardcoded 0.65 hide errors
    and make the feature appear to work when it doesn't.

Docs: https://docs.sentinel-hub.com/api/latest/api/statistical/
"""

import datetime
import math

import httpx
import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TOKEN_URL = (
    "https://services.sentinel-hub.com/auth/realms/main"
    "/protocol/openid-connect/token"
)
_STATS_URL = "https://services.sentinel-hub.com/api/v1/statistics"

# Half-width of the bounding box around the target point.
# 0.0009° ≈ 100 m at the equator; adjusted for longitude at higher latitudes.
_BBOX_HALF_DEG = 0.0009

# Evalscript: compute NDVI from Sentinel-2 L2A surface reflectance.
# B04 = Red (665 nm), B08 = NIR (842 nm).
# dataMask excludes cloud/shadow/water pixels from the mean.
_NDVI_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B04", "B08", "dataMask"] }],
    output: [
      { id: "ndvi",     bands: 1, sampleType: "FLOAT32" },
      { id: "dataMask", bands: 1, sampleType: "UINT8"   }
    ],
    mosaicking: "ORBIT"
  };
}
function evaluatePixel(s) {
  let ndvi = (s.B08[0] - s.B04[0]) / (s.B08[0] + s.B04[0] + 1e-10);
  return { ndvi: [ndvi], dataMask: [s.dataMask[0]] };
}
""".strip()

_FALLBACK = {
    "ndvi":    None,
    "stress":  "unknown",
    "status":  "Satellite data unavailable (API key not configured or unreachable).",
    "series":  [],
    "anomaly": None,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _credentials() -> tuple[str, str]:
    """Return (client_id, client_secret) from Streamlit secrets, or ('', '')."""
    try:
        return (
            st.secrets.get("SENTINEL_CLIENT_ID", ""),
            st.secrets.get("SENTINEL_CLIENT_SECRET", ""),
        )
    except Exception:
        return "", ""


@st.cache_data(ttl=3000)   # Sentinel Hub tokens expire after 3600 s; refresh at 3000 s
def _get_token() -> str | None:
    """
    Obtain an OAuth2 bearer token via the client-credentials flow.
    Returns None when credentials are missing or the request fails.
    """
    cid, secret = _credentials()
    if not cid or not secret:
        return None
    try:
        r = httpx.post(
            _TOKEN_URL,
            data={
                "grant_type":    "client_credentials",
                "client_id":     cid,
                "client_secret": secret,
            },
            timeout=12,
        )
        r.raise_for_status()
        return r.json()["access_token"]
    except Exception:
        return None


def _bbox(lat: float, lon: float) -> list[float]:
    """
    Return a [west, south, east, north] bounding box (~100 m × ~100 m) in WGS84.
    The longitude delta is corrected for latitude so the box stays square.
    """
    lon_half = _BBOX_HALF_DEG / max(math.cos(math.radians(lat)), 1e-6)
    return [
        round(lon - lon_half, 6),
        round(lat - _BBOX_HALF_DEG, 6),
        round(lon + lon_half, 6),
        round(lat + _BBOX_HALF_DEG, 6),
    ]


def _classify_ndvi(ndvi: float) -> tuple[str, str]:
    """Return (status_label, stress_level) for a given NDVI value."""
    if ndvi < 0.0:   return "bare soil or water body",   "high"
    if ndvi < 0.20:  return "severe vegetation stress",  "high"
    if ndvi < 0.40:  return "moderate canopy stress",    "moderate"
    if ndvi < 0.65:  return "healthy canopy",            "low"
    return                  "vigorous dense canopy",     "low"


def _stats_request(
    lat: float, lon: float,
    date_from: datetime.date, date_to: datetime.date,
    token: str,
) -> list[dict]:
    """
    Call the Sentinel Hub Statistical API for the given bounding box and date
    range. Returns a list of per-interval dicts with keys 'date' and 'ndvi'.
    Returns [] on any failure.
    """
    t_from = f"{date_from.isoformat()}T00:00:00Z"
    t_to   = f"{date_to.isoformat()}T23:59:59Z"

    body = {
        "input": {
            "bounds": {
                "bbox":       _bbox(lat, lon),
                "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"},
            },
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {
                    "timeRange":       {"from": t_from, "to": t_to},
                    "maxCloudCoverage": 40,
                },
            }],
        },
        "aggregation": {
            "timeRange":           {"from": t_from, "to": t_to},
            "aggregationInterval": {"of": "P1D"},   # daily granularity
            "evalscript":          _NDVI_EVALSCRIPT,
            "resx":                10,   # Sentinel-2 native resolution: 10 m/px
            "resy":                10,
        },
        "calculations": {
            "ndvi": {
                "histograms":  {},
                "statistics":  {"default": {"percentiles": {"k": [25, 50, 75]}}},
            }
        },
    }

    try:
        r = httpx.post(
            _STATS_URL,
            json=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            },
            timeout=25,
        )
        r.raise_for_status()
        data = r.json().get("data", [])
    except Exception:
        return []

    series = []
    for interval in data:
        try:
            mean_ndvi = interval["outputs"]["ndvi"]["bands"]["B0"]["stats"]["mean"]
            count     = interval["outputs"]["ndvi"]["bands"]["B0"]["stats"]["sampleCount"]
            if count == 0 or mean_ndvi is None:
                continue
            date_str  = interval["interval"]["from"][:10]   # "YYYY-MM-DD"
            series.append({"date": date_str, "ndvi": round(float(mean_ndvi), 3)})
        except (KeyError, TypeError):
            continue

    return series


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@st.cache_data(ttl=86400)   # Sentinel-2 revisit: 5 days; 24-h cache is sufficient
def get_ndvi_analysis(lat: float, lon: float) -> dict:
    """
    Return current NDVI and crop-stress classification for the given point.

    Keys in the returned dict:
      ndvi   : float | None
      status : str   (human-readable interpretation)
      stress : 'low' | 'moderate' | 'high' | 'unknown'
      series : []    (empty; use get_ndvi_trend for time series)
      anomaly: None
    """
    token = _get_token()
    if not token:
        return _FALLBACK.copy()

    today  = datetime.date.today()
    series = _stats_request(lat, lon, today - datetime.timedelta(days=5), today, token)

    if not series:
        return {**_FALLBACK,
                "status": "No cloud-free Sentinel-2 image found in the last 5 days."}

    ndvi              = series[-1]["ndvi"]
    status, stress    = _classify_ndvi(ndvi)
    return {"ndvi": ndvi, "status": status, "stress": stress, "series": [], "anomaly": None}


@st.cache_data(ttl=86400)
def get_ndvi_trend(lat: float, lon: float, days: int = 15) -> dict:
    """
    Return a {days}-day NDVI time series and a trend anomaly score.

    Keys in the returned dict:
      series  : list of {"date": "YYYY-MM-DD", "ndvi": float}
                (only dates with valid cloud-free pixels are included)
      anomaly : float | None  (latest NDVI minus period mean;
                               negative = declining canopy health)
      status  : str
      ndvi    : float | None  (latest valid observation)
      stress  : 'low' | 'moderate' | 'high' | 'unknown'
    """
    token = _get_token()
    if not token:
        return {**_FALLBACK, "series": []}

    today     = datetime.date.today()
    date_from = today - datetime.timedelta(days=days)
    series    = _stats_request(lat, lon, date_from, today, token)

    if not series:
        return {**_FALLBACK,
                "status": "Insufficient cloud-free data for the requested period.",
                "series": []}

    ndvi_vals = [p["ndvi"] for p in series]
    mean15    = sum(ndvi_vals) / len(ndvi_vals)
    latest    = ndvi_vals[-1]
    anomaly   = round(latest - mean15, 3)
    status, stress = _classify_ndvi(latest)

    return {
        "ndvi":    latest,
        "stress":  stress,
        "status":  status,
        "series":  series,
        "anomaly": anomaly,
    }


def get_crop_stress_advisory(lat: float, lon: float) -> str | None:
    """
    Return a one-line advisory string for display in the UI (st.info / st.warning),
    or None if no significant stress is detected.

    Suitable for pairing with the CV disease result to distinguish pathogenic
    stress from drought / nutrient stress before the farmer acts.
    """
    result = get_ndvi_analysis(lat, lon)
    ndvi   = result.get("ndvi")
    if ndvi is None:
        return None

    if result["stress"] == "high":
        return (
            f"📡 Satellite NDVI {ndvi:.2f} — {result['status']}. "
            "Severe canopy stress detected. Verify whether this is disease, "
            "drought stress, or post-harvest — consider irrigation before spraying."
        )
    if result["stress"] == "moderate":
        return (
            f"📡 Satellite NDVI {ndvi:.2f} — {result['status']}. "
            "Moderate stress. Re-photograph in 3–5 days after irrigation "
            "to confirm disease vs. water deficit."
        )
    return None
