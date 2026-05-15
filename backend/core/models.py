import os
import pickle
import json
import numpy as np
from functools import lru_cache

# Resolve model directory relative to this file so paths work regardless of cwd
_HERE = os.path.dirname(os.path.abspath(__file__))
_MODELS_DIR = os.path.normpath(os.path.join(_HERE, '..'))


def _model_path(filename: str) -> str:
    return os.path.join(_MODELS_DIR, filename)


class ModelManager:
    @staticmethod
    @lru_cache(maxsize=1)
    def load_crop_models():
        paths = [_model_path('crop_model.pkl'), _model_path('scaler.pkl'), _model_path('label_encoder.pkl')]
        if not all(os.path.exists(p) for p in paths):
            return None, None, None
        with open(paths[0], 'rb') as f:
            model = pickle.load(f)
        with open(paths[1], 'rb') as f:
            scaler = pickle.load(f)
        with open(paths[2], 'rb') as f:
            le = pickle.load(f)
        return model, scaler, le

    @staticmethod
    @lru_cache(maxsize=1)
    def load_vision_model():
        tflite_path  = _model_path('disease_model.tflite')
        h5_path      = _model_path('disease_model.h5')
        classes_path = _model_path('class_names.npy')

        if not os.path.exists(classes_path):
            return None, None

        class_names = np.load(classes_path, allow_pickle=True).tolist()

        try:
            import tensorflow as tf
            if os.path.exists(tflite_path):
                interp = tf.lite.Interpreter(model_path=tflite_path)
                interp.allocate_tensors()
                return interp, class_names
            if os.path.exists(h5_path):
                model = tf.keras.models.load_model(h5_path, compile=False)
                return model, class_names
        except ImportError:
            pass
        return None, None
