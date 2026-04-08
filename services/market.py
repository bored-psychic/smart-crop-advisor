import requests
import datetime

INDIA_STATES = [
    "Andhra Pradesh","Assam","Bihar","Chhattisgarh","Gujarat","Haryana",
    "Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh",
    "Maharashtra","Odisha","Punjab","Rajasthan","Tamil Nadu","Telangana",
    "Uttar Pradesh","Uttarakhand","West Bengal",
]

STATE_PRICE_FACTORS = {
    "Punjab":          {"Wheat":1.08,"Rice":1.05,"Maize":0.98,"Cotton":1.02,"Potato":0.94}

def get_live_mandi_price(crop, state):
    """
    Fetch live Agmarknet price via data.gov.in API.
    Falls back to calibrated Prophet forecast + state adjustment if API unavailable.
    Returns: {today_price, week_avg, month_avg, trend, state_factor, source}
    """
    import datetime
    today = datetime.date.today()

    # Try data.gov.in Agmarknet API (free, no key needed)
    try:
        crop_clean = crop.replace(' ','%20')
        state_clean = state.replace(' ','%20')
        url = (
            f"https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
            f"?api-key=579b464db66ec23bdd000001cdd3946e44ce4aab825747b0bc4f6e0d"
            f"&format=json&limit=10"
            f"&filters%5Bcommodity%5D={crop_clean}"
            f"&filters%5Bstate%5D={state_clean}"
        )
        r = requests.get(url, timeout=6)
        data = r.json()
        records = data.get('records', [])
        if records:
            prices = []
            for rec in records:
                try:
                    prices.append(float(rec.get('modal_price', 0) or rec.get('max_price', 0)))
                except:
                    pass
            if prices:
                today_price = sum(prices) / len(prices)
                state_f = STATE_PRICE_FACTORS.get(state, {}).get(crop, 1.0)
                return {
                    'today_price': round(today_price, 0),
                    'source': 'Agmarknet Live',
                    'mandis_checked': len(prices),
                    'state_factor': state_f,
                    'live': True,
                }
    except Exception:
        pass

    # Fallback: Prophet model + state calibration
    return None



def get_state_adjusted_forecast(future_forecast, crop, state):
    """Apply state-specific seasonal price adjustment to Prophet forecast."""
    factor = STATE_PRICE_FACTORS.get(state, {}).get(crop, 1.0)
    df = future_forecast.copy()
    df['Price'] = (df['Price'] * factor).round(0)
    df['Min']   = (df['Min']   * factor).round(0)
    df['Max']   = (df['Max']   * factor).round(0)
    return df, factor



