import json
import os
import streamlit as st

def load_price_models():
    from prophet.serialize import model_from_json
    import os
    all_crops = ['Apple', 'Banana', 'Blackgram', 'Chickpea', 'Coconut', 'Coffee',
                 'Cotton', 'Grapes', 'Jute', 'Kidneybeans', 'Lentil', 'Maize',
                 'Mango', 'Mothbeans', 'Mungbean', 'Muskmelon', 'Onion', 'Orange',
                 'Papaya', 'Pigeonpeas', 'Pomegranate', 'Potato', 'Rice', 'Tomato',
                 'Watermelon', 'Wheat']
    models = {}
    for crop in all_crops:
        path = f'price_model_{crop.lower()}.json'
        if os.path.exists(path):
            with open(path, 'r') as f:
                models[crop] = model_from_json(json.load(f))
    return models


