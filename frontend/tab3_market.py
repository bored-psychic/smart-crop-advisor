import streamlit as st
import asyncio
import json
import os
import pandas as pd
from core.language import T

INDIA_STATES = [
    "Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
    "Maharashtra", "Odisha", "Punjab", "Rajasthan", "Tamil Nadu", "Telangana",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
]

STATE_PRICE_FACTORS = {
    "Punjab":         {"Wheat": 1.08, "Rice": 1.05, "Maize": 0.98, "Cotton": 1.02, "Potato": 0.94},
    "Haryana":        {"Wheat": 1.06, "Rice": 1.03, "Maize": 0.97, "Cotton": 1.01, "Potato": 0.95},
    "Uttar Pradesh":  {"Wheat": 1.04, "Rice": 1.02, "Maize": 1.00, "Sugarcane": 1.10, "Potato": 1.12},
    "Maharashtra":    {"Cotton": 1.15, "Onion": 1.20, "Soybean": 1.08, "Grape": 1.25, "Orange": 1.18},
    "Karnataka":      {"Coffee": 1.22, "Cotton": 1.10, "Maize": 1.05, "Tomato": 1.08, "Mango": 1.15},
    "Andhra Pradesh": {"Rice": 1.06, "Cotton": 1.08, "Chilli": 1.30, "Maize": 1.04, "Tomato": 1.10},
    "Telangana":      {"Rice": 1.04, "Cotton": 1.09, "Maize": 1.06, "Tomato": 1.12, "Soybean": 1.07},
    "Tamil Nadu":     {"Rice": 1.07, "Banana": 1.18, "Coconut": 1.22, "Cotton": 1.05, "Groundnut": 1.15},
    "Gujarat":        {"Cotton": 1.12, "Groundnut": 1.18, "Cumin": 1.35, "Castor": 1.20, "Wheat": 1.02},
    "Madhya Pradesh": {"Soybean": 1.14, "Wheat": 1.05, "Chickpea": 1.10, "Maize": 1.02, "Tomato": 0.98},
    "Rajasthan":      {"Wheat": 1.03, "Mustard": 1.15, "Cumin": 1.28, "Barley": 1.08, "Cotton": 1.06},
    "West Bengal":    {"Rice": 1.08, "Potato": 1.15, "Jute": 1.25, "Banana": 1.10, "Mustard": 1.12},
    "Bihar":          {"Rice": 1.05, "Wheat": 1.03, "Maize": 1.08, "Potato": 1.18, "Litchi": 1.40},
    "Kerala":         {"Coconut": 1.30, "Rubber": 1.45, "Banana": 1.20, "Pepper": 1.50, "Cardamom": 1.60},
}

_BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'backend'))

ALL_CROPS = [
    'Apple', 'Banana', 'Blackgram', 'Chickpea', 'Coconut', 'Coffee',
    'Cotton', 'Grapes', 'Jute', 'Kidneybeans', 'Lentil', 'Maize',
    'Mango', 'Mothbeans', 'Mungbean', 'Muskmelon', 'Onion', 'Orange',
    'Papaya', 'Pigeonpeas', 'Pomegranate', 'Potato', 'Rice', 'Tomato',
    'Watermelon', 'Wheat',
]


@st.cache_resource
def load_price_models():
    try:
        from prophet.serialize import model_from_json
    except ImportError:
        return {}
    models = {}
    for crop in ALL_CROPS:
        path = os.path.join(_BACKEND_DIR, f'price_model_{crop.lower()}.json')
        if os.path.exists(path):
            with open(path, 'r') as f:
                models[crop] = model_from_json(json.load(f))
    return models


def get_live_mandi_price(crop, state):
    import requests
    try:
        crop_clean  = crop.replace(' ', '%20')
        state_clean = state.replace(' ', '%20')
        url = (
            f"https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
            f"?api-key=579b464db66ec23bdd000001cdd3946e44ce4aab825747b0bc4f6e0d"
            f"&format=json&limit=10"
            f"&filters%5Bcommodity%5D={crop_clean}"
            f"&filters%5Bstate%5D={state_clean}"
        )
        r = requests.get(url, timeout=6)
        records = r.json().get('records', [])
        if records:
            prices = [float(rec.get('modal_price', 0) or rec.get('max_price', 0)) for rec in records if rec.get('modal_price') or rec.get('max_price')]
            if prices:
                factor = STATE_PRICE_FACTORS.get(state, {}).get(crop, 1.0)
                return {'today_price': round(sum(prices)/len(prices), 0), 'source': 'Agmarknet Live', 'mandis_checked': len(prices), 'state_factor': factor, 'live': True}
    except Exception:
        pass
    return None


def get_state_adjusted_forecast(df, crop, state):
    factor = STATE_PRICE_FACTORS.get(state, {}).get(crop, 1.0)
    df = df.copy()
    df['Price'] = (df['Price'] * factor).round(0)
    df['Min']   = (df['Min']   * factor).round(0)
    df['Max']   = (df['Max']   * factor).round(0)
    return df, factor


def render():
    st.markdown(f"### 💰 {T('Live Mandi Prices')}")
    st.markdown(T("Real-time prices from Agmarknet. State-calibrated 30-day forecast powered by Prophet."))

    price_models = load_price_models()

    col_s, col_c = st.columns(2)
    with col_s:
        selected_state = st.selectbox(
            f"📍 {T('Your State')}", INDIA_STATES,
            index=INDIA_STATES.index("Karnataka") if "Karnataka" in INDIA_STATES else 0,
            key="mkt_state"
        )
    with col_c:
        available_crops = sorted(list(price_models.keys())) if price_models else ALL_CROPS
        crop_choice = st.selectbox(f"🌾 {T('Crop')}", available_crops, key="mkt_crop")

    forecast_days = st.slider(T("Forecast horizon (days)"), 7, 60, 30, key="mkt_days")

    if st.button(f"📈 {T('Get Live Price + Forecast')}", use_container_width=True, type="primary"):
        with st.spinner(T("Fetching live Agmarknet data and computing forecast...")):
            live_data = get_live_mandi_price(crop_choice, selected_state)

            forecast_df   = None
            state_factor  = STATE_PRICE_FACTORS.get(selected_state, {}).get(crop_choice, 1.0)
            if price_models and crop_choice in price_models:
                model  = price_models[crop_choice]
                future = model.make_future_dataframe(periods=forecast_days)
                fc     = model.predict(future)
                ff     = fc.tail(forecast_days)[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
                ff.columns = ['Date', 'Price', 'Min', 'Max']
                ff['Date'] = pd.to_datetime(ff['Date'])
                ff, state_factor = get_state_adjusted_forecast(ff, crop_choice, selected_state)
                forecast_df = ff.round(0)

            st.session_state['tab3_result'] = {
                'live_data':    live_data,
                'forecast':     forecast_df.to_dict() if forecast_df is not None else None,
                'crop':         crop_choice,
                'state':        selected_state,
                'state_factor': state_factor,
                'days':         forecast_days,
            }

    if 'tab3_result' in st.session_state:
        r3      = st.session_state['tab3_result']
        live    = r3['live_data']
        crop_r  = r3['crop']
        state_r = r3['state']
        factor  = r3['state_factor']

        if live and live.get('live'):
            tp = live['today_price']
            st.markdown(f"""
            <div style="background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);
                        border-radius:12px;padding:16px 20px;margin-bottom:16px">
              <div style="display:flex;align-items:center;gap:12px">
                <div>
                  <div style="font-size:11px;color:#6B8F6B;font-weight:600;text-transform:uppercase;letter-spacing:.08em">
                    LIVE · {live['source']} · {live['mandis_checked']} mandis
                  </div>
                  <div style="font-size:2rem;font-weight:700;color:#22C55E;font-family:monospace">
                    ₹{tp:,.0f}<span style="font-size:1rem;color:#6B8F6B"> /qtl</span>
                  </div>
                  <div style="font-size:12px;color:#6B8F6B">{crop_r} · {state_r}</div>
                </div>
                <div style="margin-left:auto;text-align:right">
                  <div style="font-size:11px;color:#6B8F6B">State adj. factor</div>
                  <div style="font-size:1.2rem;font-weight:600;color:#F59E0B">{factor:.2f}×</div>
                </div>
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            st.info(f"💡 {T('Agmarknet API unavailable — showing Prophet forecast calibrated for')} {state_r}. {T('Factor')}: {factor:.2f}×")

        if r3['forecast']:
            ff        = pd.DataFrame(r3['forecast'])
            ff['Date'] = pd.to_datetime(ff['Date'])
            best_row  = ff.loc[ff['Price'].idxmax()]
            worst_row = ff.loc[ff['Price'].idxmin()]
            avg_price = ff['Price'].mean()

            c1, c2, c3 = st.columns(3)
            with c1:
                delta = f"{((best_row['Price']-ff['Price'].iloc[0])/ff['Price'].iloc[0]*100):+.1f}%"
                st.metric(f"💰 {T('Best Price')}", f"₹{best_row['Price']:,.0f}", f"{best_row['Date'].strftime('%d %b')} · {delta}")
            with c2:
                st.metric(f"📉 {T('Lowest Price')}", f"₹{worst_row['Price']:,.0f}", f"{worst_row['Date'].strftime('%d %b')}")
            with c3:
                st.metric(f"📊 {T('Avg / 30d')}", f"₹{avg_price:,.0f}")

            today_p = ff['Price'].iloc[0]
            if best_row['Price'] > today_p * 1.06:
                st.success(f"⏳ {T('Wait to sell')} — {T('price expected to peak at')} ₹{best_row['Price']:,.0f} {T('on')} {best_row['Date'].strftime('%d %b %Y')}. {T('Potential gain')}: {((best_row['Price']-today_p)/today_p*100):.1f}%")
            else:
                st.warning(f"🚀 {T('Sell now')} — {T('prices not expected to rise significantly in next')} {r3['days']} {T('days')}.")

            st.markdown(f"#### {T('Price Forecast Chart')} — {crop_r} · {state_r}")
            chart_df = ff.set_index('Date')[['Price', 'Min', 'Max']]
            st.line_chart(chart_df)
            st.caption(f"📊 {T('State factor applied')}: {factor:.2f}× · Prophet trend decomposition")

            with st.expander(f"📋 {T('Full Forecast Table')}"):
                disp = ff.copy()
                disp['Date'] = disp['Date'].dt.strftime('%d %b %Y')
                st.dataframe(disp, use_container_width=True)
