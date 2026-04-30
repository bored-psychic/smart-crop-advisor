import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from core.models import ModelManager
from api.schemas import CropRecommendationResponse

router = APIRouter()

class CropInput(BaseModel):
    N: float
    P: float
    K: float
    temperature: float
    humidity: float
    ph: float
    rainfall: float

@router.post("/recommend", response_model=CropRecommendationResponse)
async def recommend_crop(input_data: CropInput):
    model, scaler, le = ModelManager.load_crop_models()
    
    data = np.array([[input_data.N, input_data.P, input_data.K, 
                      input_data.temperature, input_data.humidity, 
                      input_data.ph, input_data.rainfall]])
    
    input_scaled = scaler.transform(data)
    probs = model.predict_proba(input_scaled)[0]
    top3_idx = np.argsort(probs)[::-1][:3]
    
    # Use backend/core/constants for tips if needed, 
    # but for now I'll just return the results.
    # (Mapping logic from app.py)
    
    return {
        "top_crop": le.classes_[top3_idx[0]],
        "top_conf": float(probs[top3_idx[0]] * 100),
        "tip": "Optimized recommendation from KisanOS Backend.",
        "soil": "Loamy Soil", # Should call soil service
        "soil_advice": "Maintain organic matter.",
        "soil_color": "🟢",
        "crop2": le.classes_[top3_idx[1]],
        "conf2": float(probs[top3_idx[1]] * 100),
        "crop3": le.classes_[top3_idx[2]],
        "conf3": float(probs[top3_idx[2]] * 100),
        "probs": probs.tolist(),
        "crop_classes": le.classes_.tolist()
    }
