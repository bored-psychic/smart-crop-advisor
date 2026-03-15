import streamlit as st
import pickle
import numpy as np
import pandas as pd
from PIL import Image
import json

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Smart Crop Advisory System",
    page_icon="🌾",
    layout="centered"
)

# ── Load crop recommendation models ──────────────────────────────────────────
@st.cache_resource
def load_crop_models():
    with open('crop_model.pkl', 'rb') as f:
        model = pickle.load(f)
    with open('scaler.pkl', 'rb') as f:
        scaler = pickle.load(f)
    with open('label_encoder.pkl', 'rb') as f:
        le = pickle.load(f)
    return model, scaler, le

# ── Load price models ─────────────────────────────────────────────────────────
@st.cache_resource
def load_price_models():
    from prophet.serialize import model_from_json
    crops = ['Wheat', 'Rice', 'Tomato', 'Onion', 'Potato', 'Maize']
    models = {}
    for crop in crops:
        with open(f'price_model_{crop.lower()}.json', 'r') as f:
            models[crop] = model_from_json(json.load(f))
    return models

# ── Crop maps ─────────────────────────────────────────────────────────────────
CROP_EMOJI = {
    'rice': '🌾', 'maize': '🌽', 'chickpea': '🫘', 'kidneybeans': '🫘',
    'pigeonpeas': '🫘', 'mothbeans': '🫘', 'mungbean': '🫘', 'blackgram': '🫘',
    'lentil': '🫘', 'pomegranate': '🍎', 'banana': '🍌', 'mango': '🥭',
    'grapes': '🍇', 'watermelon': '🍉', 'muskmelon': '🍈', 'apple': '🍎',
    'orange': '🍊', 'papaya': '🫐', 'coconut': '🥥', 'cotton': '🌿',
    'jute': '🌿', 'coffee': '☕'
}

CROP_TIPS = {
    'rice':       'Best grown in waterlogged, clayey soil. Requires consistent irrigation.',
    'maize':      'Grows well in well-drained loamy soil. Needs moderate water.',
    'chickpea':   'Drought-tolerant. Thrives in cool, dry weather. Minimal irrigation needed.',
    'kidneybeans':'Needs well-drained soil and moderate rainfall. Avoid waterlogging.',
    'pigeonpeas': 'Highly drought resistant. Good for rain-fed areas.',
    'mothbeans':  'Extreme drought tolerance. Ideal for arid/semi-arid zones.',
    'mungbean':   'Short duration crop. Suitable for inter-cropping.',
    'blackgram':  'Prefers warm, humid climate. Good for mixed cropping.',
    'lentil':     'Cool season crop. Fixes nitrogen — great for soil health.',
    'pomegranate':'Thrives in hot, dry climate. Very water efficient.',
    'banana':     'Requires high humidity and warm temperatures year-round.',
    'mango':      'Requires a distinct dry season for flowering. Deep soil preferred.',
    'grapes':     'Needs well-drained sandy loam. Sensitive to waterlogging.',
    'watermelon': 'Grows best in sandy loam with warm temperatures.',
    'muskmelon':  'Warm-season crop. Needs dry climate during fruiting.',
    'apple':      'Requires cold winters for dormancy. Hilly terrain preferred.',
    'orange':     'Subtropical climate. Needs mild winters and warm summers.',
    'papaya':     'Grows year-round in tropical climates. Frost-sensitive.',
    'coconut':    'Thrives in coastal, humid regions with sandy soil.',
    'cotton':     'Requires long, frost-free season. Deep, well-drained soil.',
    'jute':       'Grows best in warm, humid climate with heavy rainfall.',
    'coffee':     'Needs high altitude, moderate temp, and well-distributed rainfall.'
}

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🌾 Smart Crop Advisory System")
st.caption("AI-powered advisory for small and marginal farmers")
st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "🌾 Crop Recommender",
    "🌿 Disease Detector",
    "💰 Market Price Forecast"
])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — CROP RECOMMENDER
# ════════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Find the best crop for your field")
    st.markdown("Enter your soil and climate details below.")

    crop_model, scaler, le = load_crop_models()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🧪 Soil Nutrients**")
        N = st.slider("Nitrogen (N) — kg/ha", 0, 140, 90)
        P = st.slider("Phosphorus (P) — kg/ha", 5, 145, 42)
        K = st.slider("Potassium (K) — kg/ha", 5, 205, 43)
        ph = st.slider("Soil pH", 3.5, 9.5, 6.5, step=0.1)

    with col2:
        st.markdown("**🌦️ Climate Conditions**")
        temperature = st.slider("Temperature (°C)", 8.0, 45.0, 25.0, step=0.5)
        humidity = st.slider("Humidity (%)", 14.0, 100.0, 80.0, step=0.5)
        rainfall = st.slider("Rainfall (mm)", 20.0, 300.0, 200.0, step=5.0)

    st.divider()

    if st.button("🔍 Get Crop Recommendation", use_container_width=True, type="primary"):
        input_data = np.array([[N, P, K, temperature, humidity, ph, rainfall]])
        input_scaled = scaler.transform(input_data)
        probs = crop_model.predict_proba(input_scaled)[0]
        top3_idx = np.argsort(probs)[::-1][:3]

        top_crop = le.classes_[top3_idx[0]]
        top_conf = probs[top3_idx[0]] * 100
        emoji = CROP_EMOJI.get(top_crop, '🌱')
        tip = CROP_TIPS.get(top_crop, '')

        st.success(f"### {emoji} Best Crop: **{top_crop.upper()}** — {top_conf:.1f}% confidence")
        if tip:
            st.info(f"💡 **Tip:** {tip}")

        st.markdown("#### Other Options")
        r2, r3 = st.columns(2)
        crop2 = le.classes_[top3_idx[1]]
        conf2 = probs[top3_idx[1]] * 100
        with r2:
            st.metric(label=f"{CROP_EMOJI.get(crop2,'🌱')} #{2} — {crop2.capitalize()}", value=f"{conf2:.1f}%")
        crop3 = le.classes_[top3_idx[2]]
        conf3 = probs[top3_idx[2]] * 100
        with r3:
            st.metric(label=f"{CROP_EMOJI.get(crop3,'🌱')} #{3} — {crop3.capitalize()}", value=f"{conf3:.1f}%")

        st.markdown("#### Confidence Across Top 8 Crops")
        chart_df = pd.DataFrame({
            'Crop': [c.capitalize() for c in le.classes_],
            'Confidence (%)': [round(p * 100, 2) for p in probs]
        }).sort_values('Confidence (%)', ascending=False).head(8)
        st.bar_chart(chart_df.set_index('Crop'))

        with st.expander("📋 Your Input Summary"):
            summary = pd.DataFrame({
                'Parameter': ['Nitrogen (N)', 'Phosphorus (P)', 'Potassium (K)',
                              'Temperature', 'Humidity', 'pH', 'Rainfall'],
                'Value': [f"{N} kg/ha", f"{P} kg/ha", f"{K} kg/ha",
                          f"{temperature} °C", f"{humidity} %", str(ph), f"{rainfall} mm"]
            })
            st.table(summary)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — DISEASE DETECTOR
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("🌿 Plant Disease Detector")
    st.info("🚧 Coming Soon — upgrade in progress.")
    st.markdown("""
    **Model details:**
    - MobileNetV2 Transfer Learning
    - 54,000+ leaf images · 38 disease classes · 96%+ accuracy

    **Currently works locally** on your machine.
    Cloud deployment coming in the next update.
    """)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — MARKET PRICE FORECAST
# ════════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Predict mandi prices for the next 30 days")
    st.markdown("Select a crop to see the price forecast and the best day to sell.")

    crop_choice = st.selectbox(
        "🌾 Select Crop",
        ['Wheat', 'Rice', 'Tomato', 'Onion', 'Potato', 'Maize'],
        index=0
    )

    forecast_days = st.slider("Forecast horizon (days)", 7, 60, 30)

    if st.button("📈 Forecast Price", use_container_width=True, type="primary"):
        with st.spinner(f"Forecasting {crop_choice} prices..."):
            price_models = load_price_models()
            model = price_models[crop_choice]

            future = model.make_future_dataframe(periods=forecast_days)
            forecast = model.predict(future)
            future_forecast = forecast.tail(forecast_days)[
                ['ds', 'yhat', 'yhat_lower', 'yhat_upper']
            ].copy()
            future_forecast.columns = ['Date', 'Price', 'Min', 'Max']
            future_forecast['Date'] = pd.to_datetime(future_forecast['Date'])
            future_forecast = future_forecast.round(2)

        # Best and worst day
        best_idx = future_forecast['Price'].idxmax()
        worst_idx = future_forecast['Price'].idxmin()
        best_day = future_forecast.loc[best_idx]
        worst_day = future_forecast.loc[worst_idx]

        # Metrics row
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "💰 Best Price",
                f"₹{best_day['Price']:.0f}/qtl",
                f"{best_day['Date'].strftime('%d %b')}"
            )
        with col2:
            st.metric(
                "📉 Lowest Price",
                f"₹{worst_day['Price']:.0f}/qtl",
                f"{worst_day['Date'].strftime('%d %b')}"
            )
        with col3:
            avg = future_forecast['Price'].mean()
            st.metric("📊 Avg Price", f"₹{avg:.0f}/qtl", f"next {forecast_days} days")

        # Sell advice
        today_price = future_forecast['Price'].iloc[0]
        if best_day['Price'] > today_price * 1.05:
            st.success(f"💡 **Advice: Wait to sell!** Price expected to rise to ₹{best_day['Price']:.0f}/qtl on {best_day['Date'].strftime('%d %b %Y')}")
        else:
            st.warning(f"💡 **Advice: Sell now.** Prices are not expected to rise significantly in the next {forecast_days} days.")

        # Price chart
        st.markdown("#### Price Forecast Chart")
        chart_data = future_forecast.set_index('Date')[['Price', 'Min', 'Max']]
        st.line_chart(chart_data)

        # Table
        with st.expander("📋 Full Price Forecast Table"):
            display_df = future_forecast.copy()
            display_df['Date'] = display_df['Date'].dt.strftime('%d %b %Y')
            display_df.columns = ['Date', 'Expected Price (₹)', 'Min (₹)', 'Max (₹)']
            st.dataframe(display_df, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("Built with ❤️ | Random Forest + MobileNetV2 + Prophet | 22 crops · 38 diseases · 6 price models | Smart Crop Advisory System")
