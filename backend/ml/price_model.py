"""
Price Forecasting ML Models — Facebook Prophet.
Loads all 26 crop price models from JSON at startup.
"""

import functools
import json
import os
from datetime import date
import pandas as pd
from backend.config import get_settings
from backend.data.state_prices import STATE_PRICE_FACTORS

ALL_CROPS = (
    'Apple', 'Banana', 'Blackgram', 'Chickpea', 'Coconut', 'Coffee',
    'Cotton', 'Grapes', 'Jute', 'Kidneybeans', 'Lentil', 'Maize',
    'Mango', 'Mothbeans', 'Mungbean', 'Muskmelon', 'Onion', 'Orange',
    'Papaya', 'Pigeonpeas', 'Pomegranate', 'Potato', 'Rice', 'Tomato',
    'Watermelon', 'Wheat',
)


@functools.lru_cache(maxsize=32)
def get_model(crop: str):
    """Load a single Prophet model on demand and cache it."""
    settings = get_settings()
    path = settings.model_path(f'price_model_{crop.lower()}.json')
    if not os.path.exists(path):
        return None
    from prophet.serialize import model_from_json
    with open(path, 'r') as f:
        raw = f.read()
    parsed = json.loads(raw)
    return model_from_json(parsed if isinstance(parsed, str) else raw)


class _LazyPriceModels:
    """Dict-like facade that loads Prophet models on first access."""

    def __contains__(self, crop: str) -> bool:
        if crop not in ALL_CROPS:
            return False
        path = get_settings().model_path(f'price_model_{crop.lower()}.json')
        return os.path.exists(path)

    def __getitem__(self, crop: str):
        m = get_model(crop)
        if m is None:
            raise KeyError(crop)
        return m

    def __len__(self) -> int:
        settings = get_settings()
        return sum(
            1 for c in ALL_CROPS
            if os.path.exists(settings.model_path(f'price_model_{c.lower()}.json'))
        )


def load_all() -> _LazyPriceModels:
    """Return a lazy facade; models load on first use (one-time per crop)."""
    return _LazyPriceModels()


def forecast(models: dict, crop: str, state: str, days: int = 30) -> dict | None:
    """
    Generate state-adjusted Prophet forecast.
    Returns dict with forecast DataFrame + metadata, or None if no model available.
    """
    if crop not in models:
        return None

    model = models[crop]
    today = pd.Timestamp(date.today())

    # Models were trained on historical data (cutoff ~Jan 2024).
    # Extend future far enough to reach today + requested days.
    last_train_date = model.history['ds'].max()
    gap = max(0, (today - last_train_date).days)
    future = model.make_future_dataframe(periods=gap + days)
    prediction = model.predict(future)

    # Slice from today forward for exactly `days` rows
    ff = prediction[prediction['ds'] >= today].head(days)[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
    ff.columns = ['Date', 'Price', 'Min', 'Max']
    ff['Date'] = pd.to_datetime(ff['Date'])

    # Apply state-specific seasonal price adjustment
    factor = STATE_PRICE_FACTORS.get(state, {}).get(crop, 1.0)
    ff['Price'] = (ff['Price'] * factor).round(0)
    ff['Min'] = (ff['Min'] * factor).round(0)
    ff['Max'] = (ff['Max'] * factor).round(0)

    best_row = ff.loc[ff['Price'].idxmax()]
    worst_row = ff.loc[ff['Price'].idxmin()]
    avg_price = float(ff['Price'].mean())
    today_p = float(ff['Price'].iloc[0])

    if best_row['Price'] > today_p * 1.06:
        gain = ((best_row['Price'] - today_p) / today_p * 100)
        sell_advice = f"Wait to sell — price expected to peak at ₹{best_row['Price']:,.0f} on {best_row['Date'].strftime('%d %b %Y')}. Potential gain: {gain:.1f}%"
    else:
        sell_advice = f"Sell now — prices not expected to rise significantly in next {days} days."

    return {
        'forecast': [
            {
                'date': row['Date'].strftime('%Y-%m-%d'),
                'price': float(row['Price']),
                'min_price': float(row['Min']),
                'max_price': float(row['Max']),
            }
            for _, row in ff.iterrows()
        ],
        'best_price': float(best_row['Price']),
        'best_date': best_row['Date'].strftime('%Y-%m-%d'),
        'worst_price': float(worst_row['Price']),
        'worst_date': worst_row['Date'].strftime('%Y-%m-%d'),
        'avg_price': round(avg_price, 0),
        'state_factor': factor,
        'sell_advice': sell_advice,
    }
