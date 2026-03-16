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

# ── Irrigation data ───────────────────────────────────────────────────────────
# FAO crop coefficients (Kc) per growth stage — all 22 crops
CROP_KC = {
    'Rice':        {'Initial': 1.05, 'Development': 1.20, 'Mid-season': 1.20, 'Late season': 0.90},
    'Maize':       {'Initial': 0.30, 'Development': 0.70, 'Mid-season': 1.20, 'Late season': 0.35},
    'Chickpea':    {'Initial': 0.40, 'Development': 0.70, 'Mid-season': 1.00, 'Late season': 0.35},
    'Kidneybeans': {'Initial': 0.40, 'Development': 0.70, 'Mid-season': 1.15, 'Late season': 0.30},
    'Pigeonpeas':  {'Initial': 0.40, 'Development': 0.70, 'Mid-season': 1.05, 'Late season': 0.55},
    'Mothbeans':   {'Initial': 0.35, 'Development': 0.65, 'Mid-season': 1.00, 'Late season': 0.30},
    'Mungbean':    {'Initial': 0.40, 'Development': 0.70, 'Mid-season': 1.05, 'Late season': 0.35},
    'Blackgram':   {'Initial': 0.40, 'Development': 0.70, 'Mid-season': 1.05, 'Late season': 0.35},
    'Lentil':      {'Initial': 0.40, 'Development': 0.70, 'Mid-season': 1.10, 'Late season': 0.30},
    'Pomegranate': {'Initial': 0.40, 'Development': 0.70, 'Mid-season': 1.05, 'Late season': 0.75},
    'Banana':      {'Initial': 0.50, 'Development': 0.90, 'Mid-season': 1.20, 'Late season': 1.10},
    'Mango':       {'Initial': 0.40, 'Development': 0.70, 'Mid-season': 1.00, 'Late season': 0.85},
    'Grapes':      {'Initial': 0.30, 'Development': 0.70, 'Mid-season': 0.85, 'Late season': 0.45},
    'Watermelon':  {'Initial': 0.40, 'Development': 0.75, 'Mid-season': 1.00, 'Late season': 0.75},
    'Muskmelon':   {'Initial': 0.40, 'Development': 0.75, 'Mid-season': 1.00, 'Late season': 0.75},
    'Apple':       {'Initial': 0.45, 'Development': 0.75, 'Mid-season': 1.10, 'Late season': 0.85},
    'Orange':      {'Initial': 0.60, 'Development': 0.70, 'Mid-season': 0.75, 'Late season': 0.70},
    'Papaya':      {'Initial': 0.40, 'Development': 0.80, 'Mid-season': 1.05, 'Late season': 0.90},
    'Coconut':     {'Initial': 0.90, 'Development': 1.00, 'Mid-season': 1.00, 'Late season': 1.00},
    'Cotton':      {'Initial': 0.35, 'Development': 0.70, 'Mid-season': 1.20, 'Late season': 0.50},
    'Jute':        {'Initial': 0.40, 'Development': 0.70, 'Mid-season': 1.15, 'Late season': 0.50},
    'Coffee':      {'Initial': 0.90, 'Development': 0.95, 'Mid-season': 1.05, 'Late season': 1.05},
}

# Fertilizer schedule per growth stage
FERTILIZER_SCHEDULE = {
    'Initial':     {'N': '30% of total N dose', 'tip': 'Apply basal dose of P and K fully at sowing.'},
    'Development': {'N': '30% of total N dose', 'tip': 'Top-dress with urea. Monitor leaf color.'},
    'Mid-season':  {'N': '40% of total N dose', 'tip': 'Final N top-dress. Avoid excess — causes lodging.'},
    'Late season': {'N': 'No N needed',          'tip': 'Stop fertilizing. Focus on pest monitoring.'},
}

def calculate_ET0(temp, humidity, wind_speed_kmh):
    """Simplified ET0 estimation (mm/day) based on temp, humidity, wind"""
    wind_ms = wind_speed_kmh / 3.6  # convert km/h to m/s
    # Saturation and actual vapor pressure
    es = 0.6108 * np.exp(17.27 * temp / (temp + 237.3))
    ea = es * humidity / 100
    vpd = max(es - ea, 0)
    # Simplified Penman-Monteith approximation
    ET0 = (0.408 * 0.0135 * (temp + 17.8) * (wind_ms + 1)) + (0.34 * vpd * wind_ms)
    return max(round(ET0, 2), 1.0)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🌾 Smart Crop Advisory System")
st.caption("AI-powered advisory for small and marginal farmers")
st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🌾 Crop Recommender",
    "🌿 Disease Detector",
    "💰 Market Prices",
    "💧 Irrigation Advisor"
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
# TAB 2 — DISEASE CHECKER (Symptom Based)
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("🌿 Crop Disease Checker")
    st.markdown("Select your crop and symptoms — get instant disease diagnosis and treatment.")

    DISEASE_DB = {
        'Tomato': {
            'Yellow leaves + brown spots': {
                'disease': 'Early Blight (Alternaria solani)',
                'treatment': 'Apply Mancozeb 75% WP @ 2g/L. Remove infected leaves.',
                'prevention': 'Crop rotation every 2 years. Use resistant varieties.',
                'severity': 'Medium',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/2d/Alternaria_solani_on_tomato.jpg/320px-Alternaria_solani_on_tomato.jpg'
            },
            'Dark brown patches + white mold': {
                'disease': 'Late Blight (Phytophthora infestans)',
                'treatment': 'Apply Metalaxyl + Mancozeb immediately. Destroy infected plants.',
                'prevention': 'Avoid overhead irrigation. Use certified disease-free seeds.',
                'severity': 'High',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5d/Phytophthora_infestans_on_tomato_leaf.jpg/320px-Phytophthora_infestans_on_tomato_leaf.jpg'
            },
            'Curling yellow leaves + stunted growth': {
                'disease': 'Tomato Yellow Leaf Curl Virus',
                'treatment': 'No cure. Remove infected plants immediately to prevent spread.',
                'prevention': 'Control whitefly population. Use silver reflective mulch.',
                'severity': 'High',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6d/TYLCV_symptoms.jpg/320px-TYLCV_symptoms.jpg'
            },
            'Small dark spots with yellow halo': {
                'disease': 'Bacterial Spot (Xanthomonas)',
                'treatment': 'Spray copper hydroxide @ 3g/L every 7 days.',
                'prevention': 'Use disease-free transplants. Avoid working in wet conditions.',
                'severity': 'Medium',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/Xanthomonas_on_tomato.jpg/320px-Xanthomonas_on_tomato.jpg'
            },
            'White powdery coating on leaves': {
                'disease': 'Powdery Mildew (Leveillula taurica)',
                'treatment': 'Apply Sulphur 80% WP @ 2g/L or Hexaconazole.',
                'prevention': 'Improve air circulation. Avoid excess nitrogen.',
                'severity': 'Low',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Powdery_mildew_on_tomato.jpg/320px-Powdery_mildew_on_tomato.jpg'
            },
        },
        'Potato': {
            'Brown lesions with yellow border': {
                'disease': 'Early Blight (Alternaria solani)',
                'treatment': 'Apply Chlorothalonil @ 2g/L. Repeat every 10 days.',
                'prevention': 'Use certified seed tubers. Practice crop rotation.',
                'severity': 'Medium',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f0/Potato_early_blight.jpg/320px-Potato_early_blight.jpg'
            },
            'Water-soaked dark patches spreading fast': {
                'disease': 'Late Blight (Phytophthora infestans)',
                'treatment': 'Apply Cymoxanil + Mancozeb urgently. Destroy infected haulms.',
                'prevention': 'Plant in well-drained soil. Monitor weather forecasts.',
                'severity': 'High',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Phytophthora_on_potato_leaf.jpg/320px-Phytophthora_on_potato_leaf.jpg'
            },
            'Yellowing from bottom leaves upward': {
                'disease': 'Potato Virus Y (PVY)',
                'treatment': 'No cure. Rogue out infected plants.',
                'prevention': 'Use virus-free certified seed. Control aphid vectors.',
                'severity': 'High',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/PVY_on_potato.jpg/320px-PVY_on_potato.jpg'
            },
        },
        'Rice': {
            'Diamond-shaped lesions with grey center': {
                'disease': 'Rice Blast (Magnaporthe oryzae)',
                'treatment': 'Apply Tricyclazole 75% WP @ 0.6g/L at booting stage.',
                'prevention': 'Use blast-resistant varieties. Avoid excess nitrogen.',
                'severity': 'High',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Rice_blast_lesions.jpg/320px-Rice_blast_lesions.jpg'
            },
            'Yellow-orange stripes on leaves': {
                'disease': 'Bacterial Leaf Blight (Xanthomonas oryzae)',
                'treatment': 'Apply copper-based bactericide. Drain fields temporarily.',
                'prevention': 'Use resistant varieties. Balanced fertilization.',
                'severity': 'High',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Rice_bacterial_leaf_blight.jpg/320px-Rice_bacterial_leaf_blight.jpg'
            },
            'Brown spots with yellow halo': {
                'disease': 'Brown Spot (Cochliobolus miyabeanus)',
                'treatment': 'Apply Mancozeb or Iprodione fungicide.',
                'prevention': 'Balanced potassium nutrition. Use healthy seeds.',
                'severity': 'Medium',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Rice_brown_spot.jpg/320px-Rice_brown_spot.jpg'
            },
        },
        'Maize': {
            'Orange powdery pustules on leaves': {
                'disease': 'Common Rust (Puccinia sorghi)',
                'treatment': 'Apply Mancozeb or Azoxystrobin @ 1ml/L.',
                'prevention': 'Use rust-resistant hybrids. Early planting.',
                'severity': 'Medium',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/d7/Maize_common_rust.jpg/320px-Maize_common_rust.jpg'
            },
            'Long grey-green lesions on leaves': {
                'disease': 'Northern Leaf Blight (Exserohilum turcicum)',
                'treatment': 'Apply Propiconazole fungicide at early stage.',
                'prevention': 'Crop rotation. Use resistant varieties.',
                'severity': 'Medium',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Northern_leaf_blight_maize.jpg/320px-Northern_leaf_blight_maize.jpg'
            },
            'Galls/tumors on plant parts': {
                'disease': 'Common Smut (Ustilago maydis)',
                'treatment': 'No chemical cure. Remove and destroy galls before they burst.',
                'prevention': 'Avoid mechanical injury. Seed treatment with fungicide.',
                'severity': 'Medium',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Ustilago_maydis.jpg/320px-Ustilago_maydis.jpg'
            },
        },
        'Wheat': {
            'Yellow stripes along leaf veins': {
                'disease': 'Yellow/Stripe Rust (Puccinia striiformis)',
                'treatment': 'Apply Propiconazole 25% EC @ 1ml/L urgently.',
                'prevention': 'Use resistant varieties. Early sowing.',
                'severity': 'High',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/2/2e/Wheat_stripe_rust.jpg/320px-Wheat_stripe_rust.jpg'
            },
            'Orange-brown pustules scattered on leaves': {
                'disease': 'Brown/Leaf Rust (Puccinia triticina)',
                'treatment': 'Apply Tebuconazole or Propiconazole fungicide.',
                'prevention': 'Balanced nitrogen. Use tolerant varieties.',
                'severity': 'Medium',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/Wheat_leaf_rust.jpg/320px-Wheat_leaf_rust.jpg'
            },
            'Black powdery pustules on stems': {
                'disease': 'Stem/Black Rust (Puccinia graminis)',
                'treatment': 'Apply Mancozeb + Propiconazole immediately.',
                'prevention': 'Use Ug99-resistant varieties. Early detection critical.',
                'severity': 'High',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Wheat_stem_rust.jpg/320px-Wheat_stem_rust.jpg'
            },
        },
        'Cotton': {
            'Wilting + internal stem discoloration': {
                'disease': 'Fusarium Wilt (Fusarium oxysporum)',
                'treatment': 'No effective cure. Remove infected plants. Soil solarization.',
                'prevention': 'Use wilt-resistant varieties. Crop rotation with cereals.',
                'severity': 'High',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e5/Fusarium_wilt_cotton.jpg/320px-Fusarium_wilt_cotton.jpg'
            },
            'Angular water-soaked leaf spots': {
                'disease': 'Bacterial Blight (Xanthomonas citri)',
                'treatment': 'Apply copper oxychloride @ 3g/L. Avoid overhead irrigation.',
                'prevention': 'Use certified disease-free seeds. Balanced nutrition.',
                'severity': 'Medium',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Cotton_bacterial_blight.jpg/320px-Cotton_bacterial_blight.jpg'
            },
        },
        'Banana': {
            'Yellow streaks on young leaves': {
                'disease': 'Banana Bunchy Top Virus (BBTV)',
                'treatment': 'No cure. Destroy infected plants immediately.',
                'prevention': 'Use virus-free tissue culture plants. Control aphids.',
                'severity': 'High',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Banana_bunchy_top.jpg/320px-Banana_bunchy_top.jpg'
            },
            'Black streaks inside stem + wilting': {
                'disease': 'Panama Wilt / Fusarium Wilt',
                'treatment': 'No chemical cure. Destroy infected plants. Long fallow period.',
                'prevention': 'Use resistant Cavendish varieties. Clean tools between plants.',
                'severity': 'High',
                'image': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Panama_disease_banana.jpg/320px-Panama_disease_banana.jpg'
            },
        },
    }

    # Show symptom images for reference BEFORE selecting
    st.markdown("#### 👇 Select your crop and match your symptom to the cards below")

    col1, col2 = st.columns(2)
    with col1:
        selected_crop = st.selectbox("🌱 Select your crop", sorted(DISEASE_DB.keys()))
    with col2:
        symptoms_list = list(DISEASE_DB[selected_crop].keys())
        selected_symptom = st.selectbox("🔍 Select main symptom", symptoms_list)

    # Show visual cards for ALL diseases of selected crop
    st.markdown(f"#### 📋 Common diseases in {selected_crop}:")

    SEVERITY_COLOR = {'High': '🔴', 'Medium': '🟡', 'Low': '🟢'}
    SEVERITY_BG = {'High': '#FF4B4B', 'Medium': '#FFA500', 'Low': '#21BA45'}

    disease_items = list(DISEASE_DB[selected_crop].items())
    cols = st.columns(min(len(disease_items), 3))

    for i, (symptom, data) in enumerate(disease_items):
        with cols[i % 3]:
            severity = data['severity']
            color = SEVERITY_BG[severity]
            icon = SEVERITY_COLOR[severity]
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, {color}22, {color}44);
                border-left: 4px solid {color};
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 10px;
                min-height: 120px;
            ">
                <div style="font-size:13px; font-weight:bold; color:white;">
                    {icon} {data['disease']}
                </div>
                <div style="font-size:11px; color:#cccccc; margin-top:6px;">
                    🔍 {symptom}
                </div>
                <div style="font-size:11px; color:{color}; margin-top:6px; font-weight:bold;">
                    Severity: {severity}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    if st.button("🔬 Diagnose Disease", use_container_width=True, type="primary"):
        result = DISEASE_DB[selected_crop][selected_symptom]
        severity = result['severity']

        if severity == 'High':
            st.error(f"### ⚠️ {result['disease']}")
            st.markdown("**Severity: 🔴 HIGH — Act immediately!**")
        elif severity == 'Medium':
            st.warning(f"### ⚠️ {result['disease']}")
            st.markdown("**Severity: 🟡 MEDIUM — Monitor closely**")
        else:
            st.info(f"### ℹ️ {result['disease']}")
            st.markdown("**Severity: 🟢 LOW — Manageable**")

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**💊 Treatment:**\n\n{result['treatment']}")
        with col2:
            st.success(f"**🛡️ Prevention:**\n\n{result['prevention']}")

    st.divider()
    st.caption("📊 Database covers 7 crops · 20+ diseases · Treatment & prevention advice")

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

        best_idx = future_forecast['Price'].idxmax()
        worst_idx = future_forecast['Price'].idxmin()
        best_day = future_forecast.loc[best_idx]
        worst_day = future_forecast.loc[worst_idx]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 Best Price", f"₹{best_day['Price']:.0f}/qtl",
                      f"{best_day['Date'].strftime('%d %b')}")
        with col2:
            st.metric("📉 Lowest Price", f"₹{worst_day['Price']:.0f}/qtl",
                      f"{worst_day['Date'].strftime('%d %b')}")
        with col3:
            avg = future_forecast['Price'].mean()
            st.metric("📊 Avg Price", f"₹{avg:.0f}/qtl", f"next {forecast_days} days")

        today_price = future_forecast['Price'].iloc[0]
        if best_day['Price'] > today_price * 1.05:
            st.success(f"💡 **Advice: Wait to sell!** Price expected to rise to ₹{best_day['Price']:.0f}/qtl on {best_day['Date'].strftime('%d %b %Y')}")
        else:
            st.warning(f"💡 **Advice: Sell now.** Prices not expected to rise significantly in the next {forecast_days} days.")

        st.markdown("#### Price Forecast Chart")
        chart_data = future_forecast.set_index('Date')[['Price', 'Min', 'Max']]
        st.line_chart(chart_data)

        with st.expander("📋 Full Price Forecast Table"):
            display_df = future_forecast.copy()
            display_df['Date'] = display_df['Date'].dt.strftime('%d %b %Y')
            display_df.columns = ['Date', 'Expected Price (₹)', 'Min (₹)', 'Max (₹)']
            st.dataframe(display_df, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — IRRIGATION ADVISOR
# ════════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Smart Irrigation & Fertilizer Advisor")
    st.markdown("Get precise water and fertilizer recommendations based on your crop and weather.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**🌱 Crop Details**")
        irr_crop = st.selectbox("Crop", sorted(list(CROP_KC.keys())))
        growth_stage = st.selectbox(
            "Growth Stage",
            ['Initial', 'Development', 'Mid-season', 'Late season']
        )
        field_area = st.number_input("Field Area (acres)", min_value=0.5,
                                      max_value=100.0, value=1.0, step=0.5)
        last_rain = st.slider("Rainfall in last 3 days (mm)", 0, 100, 0)

    with col2:
        st.markdown("**🌡️ Today's Weather**")
        irr_temp = st.slider("Temperature (°C)", 10.0, 48.0, 30.0, step=0.5)
        irr_humidity = st.slider("Humidity (%)", 10.0, 100.0, 60.0, step=1.0)
        wind_speed = st.slider("Wind Speed (km/h)", 0.0, 50.0, 10.0, step=1.0)

    st.divider()

    if st.button("💧 Get Irrigation Advice", use_container_width=True, type="primary"):

        # Calculate ET0 and crop water need
        ET0 = calculate_ET0(irr_temp, irr_humidity, wind_speed)
        Kc = CROP_KC[irr_crop][growth_stage]
        ETc = ET0 * Kc  # actual crop water need (mm/day)

        # Net irrigation need (subtract rainfall)
        effective_rain = last_rain * 0.7  # 70% of rain is effective
        net_irrigation = max(ETc - effective_rain / 3, 0)

        # Convert to litres per acre
        litres_per_acre = net_irrigation * 4046.86  # 1 acre = 4046.86 m²
        total_litres = litres_per_acre * field_area

        # Fertilizer advice
        fert = FERTILIZER_SCHEDULE[growth_stage]

        # Results
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("💧 Water Need", f"{ETc:.1f} mm/day",
                      help="Crop evapotranspiration")
        with c2:
            st.metric("🚿 Net Irrigation", f"{net_irrigation:.1f} mm/day",
                      help="After accounting for rainfall")
        with c3:
            st.metric("🪣 Total Water", f"{total_litres/1000:.1f} kL",
                      f"for {field_area} acre(s)")

        st.divider()

        # Irrigation decision
        if net_irrigation < 1.0:
            st.success("✅ **No irrigation needed today!** Recent rainfall is sufficient.")
        elif net_irrigation < 3.0:
            st.warning(f"💧 **Light irrigation recommended:** Apply {net_irrigation:.1f} mm "
                      f"({total_litres/1000:.1f} kL for your field)")
        else:
            st.error(f"🚨 **Irrigation urgently needed:** Apply {net_irrigation:.1f} mm "
                    f"({total_litres/1000:.1f} kL for your field)")

        # Fertilizer advice
        st.markdown("#### 🌱 Fertilizer Recommendation")
        st.info(f"""
        **Growth Stage:** {growth_stage}

        **Nitrogen (N):** {fert['N']}

        **Tip:** {fert['tip']}
        """)

        # Calculation details
        with st.expander("🔬 Calculation Details (FAO-56 Method)"):
            st.markdown(f"""
            | Parameter | Value |
            |---|---|
            | Reference ET₀ | {ET0:.2f} mm/day |
            | Crop Coefficient (Kc) | {Kc} |
            | Crop Water Need (ETc) | {ETc:.2f} mm/day |
            | Effective Rainfall | {effective_rain/3:.2f} mm/day |
            | Net Irrigation Need | {net_irrigation:.2f} mm/day |
            | Field Area | {field_area} acres |
            | Total Water Required | {total_litres/1000:.2f} kL |

            *Using FAO Penman-Monteith method (FAO-56 guidelines)*
            """)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("Built with ❤️ | Random Forest · MobileNetV2 · Prophet · FAO-56 | Smart Crop Advisory System")
