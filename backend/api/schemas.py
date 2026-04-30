from pydantic import BaseModel
from typing import Optional, List, Dict

class WeatherResponse(BaseModel):
    temp: float
    humidity: float
    description: str
    wind_speed: float
    rainfall: float
    city: str

class FieldWatchResponse(BaseModel):
    weather: Optional[WeatherResponse]
    fire: Optional[Dict]
    locust: Optional[Dict]
    aqi: Optional[Dict]
    flood: Optional[Dict]
    city: str

class CropRecommendationResponse(BaseModel):
    top_crop: str
    top_conf: float
    tip: str
    soil: str
    soil_advice: str
    soil_color: str
    crop2: str
    conf2: float
    crop3: str
    conf3: float
    probs: List[float]
    crop_classes: List[str]

class VisionResult(BaseModel):
    disease: str
    severity: str
    confidence: int
    color: str
    treatment: str
    prevention: str
    action: str
    top3: List[tuple]
    model_used: str

class AcousticResult(BaseModel):
    pest: str
    severity: str
    freq_range: str
    pattern: str
    energy_level: str
    confidence: int
    action: str
    icon: str
    top3: List[tuple]
    ml_used: bool
