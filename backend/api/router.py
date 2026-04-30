from fastapi import APIRouter
from api.endpoints import weather, market, crop, vision, acoustic

router = APIRouter()

router.include_router(weather.router, prefix="/weather", tags=["Weather"])
router.include_router(market.router, prefix="/market", tags=["Market"])
router.include_router(crop.router, prefix="/crop", tags=["Crop"])
router.include_router(vision.router, prefix="/vision", tags=["Vision AI"])
router.include_router(acoustic.router, prefix="/acoustic", tags=["Acoustic"])
