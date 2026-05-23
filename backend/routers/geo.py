"""GET /geo/cities — Public static endpoint returning city→state lookup list."""

from fastapi import APIRouter
from backend.data.cities import CITY_TO_STATE

router = APIRouter(prefix="/geo", tags=["Geo"])


@router.get("/cities")
async def list_cities() -> list[dict]:
    """Return all known Indian cities with their state, as a list of objects.

    No authentication required — this is public static reference data.
    Response shape: [{"city": "...", "state": "..."}, ...]
    """
    return [{"city": city, "state": state} for city, state in CITY_TO_STATE.items()]
