"""
models/vision_model.py — Vision model loaders for disease detection.

Two models in play:
  1. disease_model.tflite / .h5  — general 38-class PlantVillage model
  2. rice_model.tflite           — 4-class rice specialist (blast / brown_spot /
                                   healthy / leaf_smut_proxy)
                                   Trained by train_rice_head.py; optional.

The rice specialist is only activated when the user selects "Rice" as crop
and the model file exists. Otherwise the general model handles everything.
"""

import os
import importlib
import numpy as np
import streamlit as st


RICE_CLASSES     = ('blast', 'brown_spot', 'healthy', 'leaf_smut')
MAIZE_CLASSES    = ('common_rust', 'gray_leaf_spot', 'healthy', 'northern_leaf_blight')
CHICKPEA_CLASSES    = ('ascochyta_blight', 'dry_root_rot', 'fusarium_wilt', 'healthy')
PULSE_SWARM_CLASSES        = ('cercospora_spot', 'healthy', 'yellow_mosaic')
PIGEONPEA_LENTIL_CLASSES   = ('healthy', 'rust', 'sterility_mosaic', 'wilt')
# Fruit master: class list is read from fruit_master_classes.npy at runtime;
# this tuple is the fallback used only when the .npy file is missing.
FRUIT_MASTER_FALLBACK_CLASSES = (
    'apple_black_rot', 'apple_cedar_rust', 'apple_fire_blight', 'apple_scab',
    'banana_bunchy_top', 'banana_cordana', 'banana_fusarium_wilt', 'banana_sigatoka',
    'citrus_alternaria', 'citrus_canker', 'citrus_greening',
    'coconut_bud_rot', 'coconut_leaf_blight', 'coconut_root_wilt',
    'coffee_brown_eye_spot', 'coffee_rust',
    'cotton_alternaria', 'cotton_bacterial_blight', 'cotton_leaf_curl',
    'grape_black_rot', 'grape_downy_mildew', 'grape_esca',
    'healthy',
    'jute_anthracnose', 'jute_stem_rot',
    'mango_anthracnose', 'mango_bacterial_canker', 'mango_dieback',
    'mango_powdery_mildew', 'mango_sooty_mould',
    'papaya_anthracnose', 'papaya_powdery_mildew', 'papaya_ringspot',
    'pomegranate_blight', 'pomegranate_cercospora', 'pomegranate_fruit_rot',
)


def _load_tensorflow():
    """
    Import TensorFlow lazily and safely.
    Returns the tensorflow module, or None when unavailable.
    """
    try:
        return importlib.import_module('tensorflow')
    except ImportError:
        return None


@st.cache_resource
def load_general_model():
    """Load the 38-class PlantVillage TFLite/Keras model."""
    tflite_path  = 'disease_model.tflite'
    h5_path      = 'disease_model.h5'
    classes_path = 'class_names.npy'

    if not os.path.exists(classes_path):
        return None, None

    class_names = np.load(classes_path, allow_pickle=True).tolist()

    tf = _load_tensorflow()
    if tf is None:
        return None, None

    if os.path.exists(tflite_path):
        try:
            interp = tf.lite.Interpreter(model_path=tflite_path)
            interp.allocate_tensors()
            return interp, class_names
        except Exception:
            pass

    if os.path.exists(h5_path):
        try:
            model = tf.keras.models.load_model(h5_path, compile=False)
            return model, class_names
        except Exception:
            pass

    return None, None


@st.cache_resource
def load_rice_model():
    """
    Load the rice specialist TFLite model if it exists.
    Returns (interpreter, class_names) or (None, None) if not trained yet.
    """
    tflite_path  = 'rice_model.tflite'
    classes_path = 'rice_classes.npy'

    if not os.path.exists(tflite_path):
        return None, None

    classes = (
        np.load(classes_path, allow_pickle=True).tolist()
        if os.path.exists(classes_path)
        else list(RICE_CLASSES)
    )

    tf = _load_tensorflow()
    if tf is None:
        return None, None
    try:
        interp = tf.lite.Interpreter(model_path=tflite_path)
        interp.allocate_tensors()
        return interp, classes
    except Exception:
        return None, None


def rice_model_available() -> bool:
    return os.path.exists('rice_model.tflite')


@st.cache_resource
def load_maize_model():
    """
    Load the maize specialist TFLite model if it exists.
    Returns (interpreter, class_names) or (None, None) if not trained yet.

    NOTE: The general disease_model already covers all 4 maize classes.
    This specialist is faster and has less inter-class confusion on maize images.
    """
    tflite_path  = 'maize_model.tflite'
    classes_path = 'maize_classes.npy'

    if not os.path.exists(tflite_path):
        return None, None

    classes = (
        np.load(classes_path, allow_pickle=True).tolist()
        if os.path.exists(classes_path)
        else list(MAIZE_CLASSES)
    )

    tf = _load_tensorflow()
    if tf is None:
        return None, None
    try:
        interp = tf.lite.Interpreter(model_path=tflite_path)
        interp.allocate_tensors()               # required before any inference
        return interp, classes
    except Exception:
        return None, None


def maize_model_available() -> bool:
    return os.path.exists('maize_model.tflite')


@st.cache_resource
def load_chickpea_model():
    """
    Load the chickpea specialist TFLite model if it exists.
    Returns (interpreter, class_names) or (None, None) if not trained yet.
    """
    tflite_path  = 'chickpea_model.tflite'
    classes_path = 'chickpea_classes.npy'

    if not os.path.exists(tflite_path):
        return None, None

    classes = (
        np.load(classes_path, allow_pickle=True).tolist()
        if os.path.exists(classes_path)
        else list(CHICKPEA_CLASSES)
    )

    tf = _load_tensorflow()
    if tf is None:
        return None, None
    try:
        interp = tf.lite.Interpreter(model_path=tflite_path)
        interp.allocate_tensors()
        return interp, classes
    except Exception:
        return None, None


def chickpea_model_available() -> bool:
    return os.path.exists('chickpea_model.tflite')


@st.cache_resource
def load_pulse_swarm_model():
    """
    Load the unified Mungbean + Blackgram YMD specialist TFLite model.
    Returns (interpreter, class_names) or (None, None) if not trained yet.
    """
    tflite_path  = 'pulse_swarm_model.tflite'
    classes_path = 'pulse_swarm_classes.npy'

    if not os.path.exists(tflite_path):
        return None, None

    classes = (
        np.load(classes_path, allow_pickle=True).tolist()
        if os.path.exists(classes_path)
        else list(PULSE_SWARM_CLASSES)
    )

    tf = _load_tensorflow()
    if tf is None:
        return None, None
    try:
        interp = tf.lite.Interpreter(model_path=tflite_path)
        interp.allocate_tensors()
        return interp, classes
    except Exception:
        return None, None


def pulse_swarm_model_available() -> bool:
    return os.path.exists('pulse_swarm_model.tflite')


@st.cache_resource
def load_pigeonpea_lentil_model():
    """
    Load the Pigeonpea + Lentil disease specialist TFLite model.
    Returns (interpreter, class_names) or (None, None) if not trained yet.
    """
    tflite_path  = 'pigeonpea_lentil_model.tflite'
    classes_path = 'pigeonpea_lentil_classes.npy'

    if not os.path.exists(tflite_path):
        return None, None

    classes = (
        np.load(classes_path, allow_pickle=True).tolist()
        if os.path.exists(classes_path)
        else list(PIGEONPEA_LENTIL_CLASSES)
    )

    tf = _load_tensorflow()
    if tf is None:
        return None, None
    try:
        interp = tf.lite.Interpreter(model_path=tflite_path)
        interp.allocate_tensors()
        return interp, classes
    except Exception:
        return None, None


def pigeonpea_lentil_model_available() -> bool:
    return os.path.exists('pigeonpea_lentil_model.tflite')


@st.cache_resource
def load_fruit_master_model():
    """
    Load the Fruit & Industrial Crop master TFLite model (27+ classes).
    Returns (interpreter, class_names) or (None, None) if not trained yet.
    """
    tflite_path  = 'fruit_master_model.tflite'
    classes_path = 'fruit_master_classes.npy'

    if not os.path.exists(tflite_path):
        return None, None

    classes = (
        np.load(classes_path, allow_pickle=True).tolist()
        if os.path.exists(classes_path)
        else list(FRUIT_MASTER_FALLBACK_CLASSES)
    )

    tf = _load_tensorflow()
    if tf is None:
        return None, None
    try:
        interp = tf.lite.Interpreter(model_path=tflite_path)
        interp.allocate_tensors()
        return interp, classes
    except Exception:
        return None, None


def fruit_master_model_available() -> bool:
    return os.path.exists('fruit_master_model.tflite')
