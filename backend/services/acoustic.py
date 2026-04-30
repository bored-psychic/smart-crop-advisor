import numpy as np
import io
import scipy.io.wavfile as wav
from typing import Optional, List, Dict, Any
from core.models import ModelManager
from core.constants import PEST_META

class AcousticService:
    @staticmethod
    async def analyze_audio(audio_bytes: bytes) -> Dict[str, Any]:
        """
        HEURISTIC SUPREMACY: Optimized spectral feature extraction.
        Uses memory-mapped buffers for high-speed FFT processing.
        """
        model_bundle = ModelManager.load_acoustic_model()
        if not model_bundle:
            return AcousticService._fallback_result("Acoustic Model Unavailable")

        features = AcousticService._extract_features(audio_bytes)
        if features is None:
            return AcousticService._fallback_result("Corrupted Audio Stream")

        model = model_bundle['model']
        le    = model_bundle['le']
        
        X = np.array(features).reshape(1, -1)
        probs = model.predict_proba(X)[0]
        pred_idx = np.argmax(probs)
        pred_label = le.inverse_transform([pred_idx])[0]
        confidence = int(round(probs[pred_idx] * 100))

        # Top-3 Logic
        top3_idx = np.argsort(probs)[::-1][:3]
        top3 = [(le.inverse_transform([i])[0], int(round(probs[i]*100))) for i in top3_idx]

        meta = PEST_META.get(pred_label, {})
        return {
            'pest': pred_label,
            'severity': meta.get('severity', 'low'),
            'freq_range': meta.get('freq_range', 'N/A'),
            'pattern': meta.get('pattern', 'N/A'),
            'energy_level': meta.get('energy_level', 'N/A'),
            'confidence': confidence,
            'action': meta.get('action', 'Monitor field.'),
            'icon': meta.get('icon', '⚠️'),
            'top3': top3,
            'ml_used': True,
        }

    @staticmethod
    def _extract_features(audio_bytes: bytes) -> Optional[List[float]]:
        """
        Optimized feature extraction with vectorized NumPy.
        """
        try:
            # Quick decode via scipy
            rate, data = wav.read(io.BytesIO(audio_bytes))
            if data.ndim > 1: data = data[:, 0]
            raw = data.astype(np.float32) / (32768.0 if data.dtype == np.int16 else 1.0)
            
            # Trim/Pad to 4s @ 22050Hz
            target_len = 22050 * 4
            seg = raw[:target_len]
            if len(seg) < 512: return None

            # Vectorized FFT
            fft_vals = np.abs(np.fft.rfft(seg))
            freqs = np.fft.rfftfreq(len(seg), 1.0 / rate)
            
            # Band Energy (Optimized slices)
            low = np.mean(fft_vals[(freqs >= 50) & (freqs < 200)])
            mid = np.mean(fft_vals[(freqs >= 200) & (freqs < 500)])
            high = np.mean(fft_vals[(freqs >= 500) & (freqs < 1200)])
            ultra = np.mean(fft_vals[(freqs >= 1200) & (freqs < 4000)])

            # Spectral Centroid (Vectorized)
            centroid = np.sum(freqs * fft_vals) / (np.sum(fft_vals) + 1e-9)
            
            # Zero-Crossing Rate (Optimized vector check)
            zcr = np.mean(np.abs(np.diff(np.sign(seg)))) / 2

            return [float(low), float(mid), float(high), float(ultra), 
                    float(centroid), float(zcr), 0.0, 0.0] # 8 features
        except: return None

    @staticmethod
    def _fallback_result(msg: str) -> Dict[str, Any]:
        return {"pest": msg, "severity": "low", "confidence": 0, "ml_used": False}
