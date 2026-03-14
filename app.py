import streamlit as st
import pickle
import numpy as np

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Smart Crop Advisor",
    page_icon="🌾",
    layout="centered"
)

# ── Load models ───────────────────────────────────────────────────────────────
@st.cache_resource
def load_models():
    with open('crop_model.pkl', 'rb') as f:
        model = pickle.load(f)
    with open('scaler.pkl', 'rb') as f:
        scaler = pickle.load(f)
    with open('label_encoder.pkl', 'rb') as f:
        le = pickle.load(f)
    return model, scaler, le

model, scaler, le = load_models()

# ── Crop emoji map ────────────────────────────────────────────────────────────
CROP_EMOJI = {
    'rice': '🌾', 'maize': '🌽', 'chickpea': '🫘', 'kidneybeans': '🫘',
    'pigeonpeas': '🫘', 'mothbeans': '🫘', 'mungbean': '🫘', 'blackgram': '🫘',
    'lentil': '🫘', 'pomegranate': '🍎', 'banana': '🍌', 'mango': '🥭',
    'grapes': '🍇', 'watermelon': '🍉', 'muskmelon': '🍈', 'apple': '🍎',
    'orange': '🍊', 'papaya': '🫐', 'coconut': '🥥', 'cotton': '🌿',
    'jute': '🌿', 'coffee': '☕'
}

# ── Crop tips ─────────────────────────────────────────────────────────────────
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

# ── UI ────────────────────────────────────────────────────────────────────────
st.title("🌾 Smart Crop Advisory System")
st.caption("AI-powered crop recommendations for small and marginal farmers")
st.divider()

# Two-column layout
col1, col2 = st.columns(2)

with col1:
    st.subheader("🧪 Soil Nutrients")
    N = st.slider("Nitrogen (N) — kg/ha", min_value=0, max_value=140, value=90,
                  help="Amount of nitrogen in soil")
    P = st.slider("Phosphorus (P) — kg/ha", min_value=5, max_value=145, value=42,
                  help="Amount of phosphorus in soil")
    K = st.slider("Potassium (K) — kg/ha", min_value=5, max_value=205, value=43,
                  help="Amount of potassium in soil")
    ph = st.slider("Soil pH", min_value=3.5, max_value=9.5, value=6.5, step=0.1,
                   help="pH 6–7 is ideal for most crops")

with col2:
    st.subheader("🌦️ Climate Conditions")
    temperature = st.slider("Temperature (°C)", min_value=8.0, max_value=45.0,
                            value=25.0, step=0.5)
    humidity = st.slider("Humidity (%)", min_value=14.0, max_value=100.0,
                         value=80.0, step=0.5)
    rainfall = st.slider("Rainfall (mm)", min_value=20.0, max_value=300.0,
                         value=200.0, step=5.0)

st.divider()

# ── Predict button ────────────────────────────────────────────────────────────
if st.button("🔍 Get Crop Recommendation", use_container_width=True, type="primary"):

    input_data = np.array([[N, P, K, temperature, humidity, ph, rainfall]])
    input_scaled = scaler.transform(input_data)
    probs = model.predict_proba(input_scaled)[0]
    top3_idx = np.argsort(probs)[::-1][:3]

    st.subheader("📊 Recommendation Results")

    # Top recommendation — big card
    top_crop = le.classes_[top3_idx[0]]
    top_conf = probs[top3_idx[0]] * 100
    emoji = CROP_EMOJI.get(top_crop, '🌱')
    tip = CROP_TIPS.get(top_crop, '')

    st.success(f"### {emoji} Best Crop: **{top_crop.upper()}**  —  {top_conf:.1f}% confidence")
    if tip:
        st.info(f"💡 **Tip:** {tip}")

    st.markdown("#### Other Options")
    r2, r3 = st.columns(2)

    crop2 = le.classes_[top3_idx[1]]
    conf2 = probs[top3_idx[1]] * 100
    with r2:
        st.metric(
            label=f"{CROP_EMOJI.get(crop2,'🌱')} #{2} — {crop2.capitalize()}",
            value=f"{conf2:.1f}%"
        )

    crop3 = le.classes_[top3_idx[2]]
    conf3 = probs[top3_idx[2]] * 100
    with r3:
        st.metric(
            label=f"{CROP_EMOJI.get(crop3,'🌱')} #{3} — {crop3.capitalize()}",
            value=f"{conf3:.1f}%"
        )

    # Confidence bar chart
    st.markdown("#### Confidence Across All Crops")
    all_crops = le.classes_
    import pandas as pd
    chart_df = pd.DataFrame({
        'Crop': [c.capitalize() for c in all_crops],
        'Confidence (%)': [round(p * 100, 2) for p in probs]
    }).sort_values('Confidence (%)', ascending=False).head(8)
    st.bar_chart(chart_df.set_index('Crop'))

    # Input summary
    with st.expander("📋 Your Input Summary"):
        summary = pd.DataFrame({
            'Parameter': ['Nitrogen (N)', 'Phosphorus (P)', 'Potassium (K)',
                          'Temperature', 'Humidity', 'pH', 'Rainfall'],
            'Value': [f"{N} kg/ha", f"{P} kg/ha", f"{K} kg/ha",
                      f"{temperature} °C", f"{humidity} %", str(ph), f"{rainfall} mm"]
        })
        st.table(summary)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("Built with ❤️ using Random Forest · 99%+ accuracy · 22 crops · Smart Crop Advisory System")
