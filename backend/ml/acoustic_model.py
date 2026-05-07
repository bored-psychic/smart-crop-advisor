"""
Acoustic Pest Detection ML Model — Random Forest fallback (8 classes).

Trained on synthetic Gaussian profiles per pest class. Cross-validation accuracy
is measured on the same synthetic distribution and reported honestly with that
caveat — it is NOT a real-world generalization estimate.
"""

import pickle
import os
import numpy as np
from backend.config import get_settings
from backend.core.constants import PEST_META


CROP_PEST_PRIOR: dict[str, dict[str, float]] = {
    'Tomato':   {'Whitefly Infestation': 1.4, 'Aphid Colony': 1.2, 'Spider Mite': 1.3,
                 'Thrips Infestation': 1.2, 'Early Fungal Infection': 1.2,
                 'Locust Activity': 0.4, 'Stem Borer': 0.6},
    'Rice':     {'Stem Borer': 1.5, 'Locust Activity': 1.2, 'Early Fungal Infection': 1.2,
                 'Aphid Colony': 0.8, 'Spider Mite': 0.7,
                 'Whitefly Infestation': 0.7, 'Thrips Infestation': 0.9},
    'Wheat':    {'Aphid Colony': 1.4, 'Locust Activity': 1.3, 'Stem Borer': 1.1,
                 'Early Fungal Infection': 1.2,
                 'Whitefly Infestation': 0.6, 'Spider Mite': 0.7, 'Thrips Infestation': 0.8},
    'Cotton':   {'Whitefly Infestation': 1.5, 'Aphid Colony': 1.3, 'Spider Mite': 1.3,
                 'Thrips Infestation': 1.2, 'Stem Borer': 1.2,
                 'Locust Activity': 0.7, 'Early Fungal Infection': 0.9},
    'Maize':    {'Stem Borer': 1.5, 'Locust Activity': 1.3, 'Aphid Colony': 1.1,
                 'Whitefly Infestation': 0.8, 'Spider Mite': 0.7,
                 'Thrips Infestation': 0.8, 'Early Fungal Infection': 1.1},
    'Potato':   {'Aphid Colony': 1.3, 'Whitefly Infestation': 1.3,
                 'Early Fungal Infection': 1.4, 'Spider Mite': 0.9,
                 'Thrips Infestation': 1.0, 'Stem Borer': 0.6, 'Locust Activity': 0.5},
    'Banana':   {'Thrips Infestation': 1.3, 'Spider Mite': 1.2,
                 'Aphid Colony': 1.0, 'Whitefly Infestation': 1.0,
                 'Stem Borer': 1.3, 'Early Fungal Infection': 1.3,
                 'Locust Activity': 0.5},
    'Chickpea': {'Aphid Colony': 1.3, 'Stem Borer': 1.2, 'Locust Activity': 1.2,
                 'Early Fungal Infection': 1.1,
                 'Whitefly Infestation': 0.8, 'Spider Mite': 0.8, 'Thrips Infestation': 0.8},
}


def _normalize_crop_type(crop_type: str) -> str:
    """Normalize user-provided crop labels to supported prior keys."""
    if not crop_type:
        return "Unknown"

    cleaned = " ".join(str(crop_type).strip().split())
    if not cleaned:
        return "Unknown"

    alias_map = {
        "corn": "Maize",
        "paddy": "Rice",
        "chana": "Chickpea",
    }
    lower = cleaned.lower()
    if lower in alias_map:
        return alias_map[lower]

    # Case-insensitive exact matching against configured prior keys.
    for known in CROP_PEST_PRIOR:
        if known.lower() == lower:
            return known

    return cleaned.title()


class AcousticModelBundle:
    """RF model + label encoder + CV diagnostics."""

    def __init__(self, model, label_encoder, classes,
                 cv_accuracy: float | None = None,
                 cv_label: str | None = None):
        self.model = model
        self.le = label_encoder
        self.classes = classes
        self.cv_accuracy = cv_accuracy
        self.cv_label = cv_label or "synthetic-seed cross-validation"

    def predict(self, features: list[float], crop_type: str = "Unknown") -> dict:
        X = np.array(features).reshape(1, -1)
        probs = self.model.predict_proba(X)[0]

        normalized_crop = _normalize_crop_type(crop_type)
        prior = CROP_PEST_PRIOR.get(normalized_crop, {})
        if prior:
            adj = np.array([prior.get(c, 1.0) for c in self.le.classes_])
            probs = probs * adj
            probs = probs / probs.sum()

        pred_idx = int(np.argmax(probs))
        pred_label = self.le.inverse_transform([pred_idx])[0]
        confidence = int(round(float(probs[pred_idx]) * 100))

        top3_idx = np.argsort(probs)[::-1][:3]
        top3 = [
            (self.le.inverse_transform([i])[0], int(round(float(probs[i]) * 100)))
            for i in top3_idx
        ]

        meta = PEST_META[pred_label]
        return {
            'pest': pred_label,
            'severity': meta['severity'],
            'freq_range': meta['freq_range'],
            'pattern': meta['pattern'],
            'energy_level': meta['energy_level'],
            'confidence': confidence,
            'action': meta['action'],
            'icon': meta['icon'],
            'top3': top3,
            'ml_used': True,
            'cv_accuracy': self.cv_accuracy,
            'cv_label': self.cv_label,
        }


def _features_from_pcm(raw: np.ndarray, rate: int) -> list[float] | None:
    """Compute the 8 spectral features from already-decoded mono PCM."""
    if raw is None or len(raw) < int(rate * 0.5):
        return None

    seg = raw[:min(len(raw), int(rate * 4))]

    fft_vals = np.abs(np.fft.rfft(seg))
    freqs = np.fft.rfftfreq(len(seg), 1.0 / rate)
    eps = 1e-9

    def band(lo, hi):
        mask = (freqs >= lo) & (freqs < hi)
        return float(np.mean(fft_vals[mask])) if mask.any() else 0.0

    low = band(50, 200)
    mid = band(200, 500)
    high = band(500, 1200)
    ultra = band(1200, 4000)

    centroid = float(np.sum(freqs * fft_vals) / (np.sum(fft_vals) + eps))
    zcr = float(np.mean(np.abs(np.diff(np.sign(seg)))) / 2)
    peak_bin = float(min(int(np.argmax(fft_vals) * 15 / (len(fft_vals) + 1)), 15))

    frame_size = 512
    frames = [seg[i:i + frame_size] for i in range(0, len(seg) - frame_size, frame_size)]
    energies = [float(np.mean(f ** 2)) for f in frames] if frames else [0.0]
    variance = float(np.var(energies))

    return [low, mid, high, ultra, centroid, zcr, peak_bin, variance]


def _build_synthetic_dataset(seed: int = 42, n_per_class: int = 300):
    profiles = {
        'Healthy Plant':          {'mu': [0.05,0.05,0.04,0.03, 120, 0.02, 1, 0.001], 'sd': [0.02,0.02,0.02,0.01, 40, 0.01,1,0.0005]},
        'Aphid Colony':           {'mu': [0.12,0.45,0.20,0.08, 320, 0.08, 3, 0.04],  'sd': [0.04,0.08,0.06,0.03, 60, 0.02,1,0.01]},
        'Whitefly Infestation':   {'mu': [0.10,0.30,0.38,0.15, 550, 0.12, 5, 0.06],  'sd': [0.03,0.07,0.08,0.04, 80, 0.03,1,0.015]},
        'Locust Activity':        {'mu': [0.50,0.30,0.12,0.05, 180, 0.18, 2, 0.12],  'sd': [0.10,0.08,0.04,0.02, 50, 0.05,1,0.03]},
        'Stem Borer':             {'mu': [0.60,0.20,0.10,0.04, 110, 0.04, 1, 0.08],  'sd': [0.12,0.06,0.04,0.02, 40, 0.01,1,0.02]},
        'Early Fungal Infection': {'mu': [0.08,0.18,0.52,0.28, 900, 0.22, 8, 0.09],  'sd': [0.03,0.05,0.10,0.07,120, 0.05,2,0.02]},
        'Spider Mite':            {'mu': [0.06,0.15,0.42,0.35,1800, 0.30,14, 0.07],  'sd': [0.02,0.04,0.09,0.08,200, 0.07,3,0.02]},
        'Thrips Infestation':     {'mu': [0.09,0.38,0.32,0.18, 420, 0.15, 4, 0.05],  'sd': [0.03,0.08,0.07,0.05, 70, 0.04,1,0.012]},
    }
    rng = np.random.default_rng(seed)
    X, y = [], []
    for label, prof in profiles.items():
        samp = rng.normal(prof['mu'], prof['sd'], (n_per_class, 8))
        samp = np.clip(samp, 0, None)
        X.extend(samp.tolist())
        y.extend([label] * n_per_class)
    return np.array(X), np.array(y)


def load() -> AcousticModelBundle:
    """Load saved bundle if present and complete; otherwise rebuild."""
    settings = get_settings()
    pkl_path = settings.model_path('acoustic_model.pkl')

    if os.path.exists(pkl_path):
        try:
            with open(pkl_path, 'rb') as f:
                bundle = pickle.load(f)
            model = bundle.get('model')
            le = bundle.get('le')
            if model is not None and le is not None and getattr(model, 'predict_proba', None):
                cv_acc = bundle.get('cv_accuracy')
                cv_label = bundle.get('cv_label')
                classes = bundle.get('classes') or le.classes_.tolist()
                return AcousticModelBundle(model, le, classes,
                                           cv_accuracy=cv_acc, cv_label=cv_label)
        except Exception:
            pass

    return _train_and_save(pkl_path)


def _train_and_save(pkl_path: str) -> AcousticModelBundle:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import StratifiedKFold, cross_val_score

    X, y = _build_synthetic_dataset()
    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    pipe = Pipeline([
        ('scaler', StandardScaler()),
        ('clf', RandomForestClassifier(
            n_estimators=200, max_depth=12,
            random_state=42, class_weight='balanced'
        ))
    ])

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(pipe, X, y_enc, cv=cv, scoring='accuracy')
    cv_acc = float(cv_scores.mean())

    pipe.fit(X, y_enc)

    bundle_dict = {
        'model': pipe,
        'le': le,
        'classes': le.classes_.tolist(),
        'cv_accuracy': cv_acc,
        'cv_label': 'synthetic-seed 5-fold cross-validation (NOT real-world accuracy)',
    }
    try:
        with open(pkl_path, 'wb') as f:
            pickle.dump(bundle_dict, f)
    except Exception:
        pass

    return AcousticModelBundle(pipe, le, le.classes_.tolist(),
                               cv_accuracy=cv_acc,
                               cv_label=bundle_dict['cv_label'])


def extract_features(audio_bytes: bytes, filename: str = "audio") -> list[float] | None:
    """
    Decode WAV bytes and extract the 8 features. Returns None on decode failure.

    Note: caller is responsible for converting non-WAV formats to WAV first.
    Unlike older versions, this does NOT have a "treat random bytes as int8"
    fallback — that produced garbage features for MP3/M4A inputs.
    """
    import io
    try:
        import scipy.io.wavfile as wav
        rate, data = wav.read(io.BytesIO(audio_bytes))
    except Exception:
        return None

    if data.ndim > 1:
        data = data[:, 0]

    if data.dtype == np.int16:
        raw = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        raw = data.astype(np.float32) / 2147483648.0
    elif data.dtype == np.uint8:
        raw = (data.astype(np.float32) - 128.0) / 128.0
    else:
        raw = data.astype(np.float32)

    return _features_from_pcm(raw, rate)
