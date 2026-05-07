"""
Crop Recommendation ML Model — Random Forest.
Loads crop_model.pkl, scaler.pkl, label_encoder.pkl once at startup.
"""

import pickle
import numpy as np
import pandas as pd
from backend.config import get_settings


class CropModelBundle:
    """Encapsulates crop recommendation model, scaler, and label encoder."""

    def __init__(self, model, scaler, label_encoder):
        self.model = model
        self.scaler = scaler
        self.le = label_encoder

    def predict(self, N: float, P: float, K: float,
                temperature: float, humidity: float,
                ph: float, rainfall: float) -> dict:
        """
        Run crop prediction.
        Returns: {top_crop, top_conf, alternatives: [(crop, conf)], all_probs: {crop: conf}}
        """
        values = [[N, P, K, temperature, humidity, ph, rainfall]]
        feature_names = getattr(self.scaler, 'feature_names_in_', None)
        input_data = (
            pd.DataFrame(values, columns=feature_names)
            if feature_names is not None
            else np.array(values)
        )
        input_scaled = self.scaler.transform(input_data)
        probs = self.model.predict_proba(input_scaled)[0]
        top3_idx = np.argsort(probs)[::-1][:3]

        top_crop = self.le.classes_[top3_idx[0]]
        top_conf = round(float(probs[top3_idx[0]] * 100), 1)

        alternatives = [
            (self.le.classes_[i], round(float(probs[i] * 100), 1))
            for i in top3_idx[1:]
        ]

        all_probs = {
            c: round(float(p * 100), 2)
            for c, p in zip(self.le.classes_, probs)
        }

        return {
            'top_crop': top_crop,
            'top_conf': top_conf,
            'alternatives': alternatives,
            'all_probs': all_probs,
        }


def load() -> CropModelBundle:
    """Load crop model bundle from disk. Called once at startup."""
    settings = get_settings()
    with open(settings.model_path(settings.CROP_MODEL_PATH), 'rb') as f:
        model = pickle.load(f)
    with open(settings.model_path(settings.SCALER_PATH), 'rb') as f:
        scaler = pickle.load(f)
    with open(settings.model_path(settings.LABEL_ENCODER_PATH), 'rb') as f:
        le = pickle.load(f)
    return CropModelBundle(model, scaler, le)
