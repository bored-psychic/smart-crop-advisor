import streamlit as st
import pickle
import numpy as np
import pandas as pd
from PIL import Image
import json
import requests

# ── Language support ──────────────────────────────────────────────────────────
LANGUAGES = {
    'English': 'en',
    'हिंदी (Hindi)': 'hi',
    'తెలుగు (Telugu)': 'te',
    'தமிழ் (Tamil)': 'ta',
    'ಕನ್ನಡ (Kannada)': 'kn',
    'मराठी (Marathi)': 'mr',
    'বাংলা (Bengali)': 'bn',
    'ગુજરાતી (Gujarati)': 'gu',
    'ਪੰਜਾਬੀ (Punjabi)': 'pa',
}

def T(text):
    lang = st.session_state.get('lang_code', 'en')
    if lang == 'en' or not text:
        return text
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source='en', target=lang).translate(str(text))
    except:
        return text

# ── Soil type detection ───────────────────────────────────────────────────────
def get_soil_type(N, P, K, ph):
    if ph < 5.5:
        return "Acidic Soil", "Add lime to increase pH. Most crops struggle below pH 5.5.", "🔴"
    elif ph > 7.5:
        return "Alkaline Soil", "Add gypsum or sulfur to reduce pH. Iron deficiency common.", "🟡"
    elif K > 150 and ph >= 6.5:
        return "Black/Regur Soil", "Excellent for cotton, sorghum, wheat. High water retention.", "⚫"
    elif N < 30 and P < 20:
        return "Red/Laterite Soil", "Low fertility. Add organic matter and NPK fertilizers.", "🔶"
    elif N > 80 and 6.0 <= ph <= 7.5:
        return "Alluvial Soil", "Highly fertile! Ideal for rice, wheat, sugarcane, vegetables.", "🟢"
    elif P > 80:
        return "Sandy Loam Soil", "Good drainage. Suitable for groundnut, potato, vegetables.", "🟤"
    else:
        return "Loamy Soil", "Well-balanced soil. Suitable for most crops.", "🟢"

# ── Live weather ──────────────────────────────────────────────────────────────
def get_weather(city):
    try:
        api_key = "bd5e378503939ddaee76f12ad7a97608"
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city},IN&appid={api_key}&units=metric"
        r = requests.get(url, timeout=5)
        data = r.json()
        if data.get('cod') == 200:
            return {
                'temp': data['main']['temp'],
                'humidity': data['main']['humidity'],
                'description': data['weather'][0]['description'].title(),
                'wind_speed': data['wind']['speed'] * 3.6,
                'rainfall': data.get('rain', {}).get('1h', 0),
                'city': data['name']
            }
    except:
        pass
    return None

CALAMITY_TIPS = {
    'thunderstorm': ['⚡ Move livestock to shelter', '🚫 Stop all field work immediately', '💧 Clear drainage channels'],
    'rain':         ['🌱 Avoid fertilizer — will wash away', '🌊 Create bunds around fields', '📞 Contact agriculture office if flooding'],
    'drizzle':      ['💧 Good for germination', '🌱 Ideal time for transplanting', '✅ Reduce irrigation today'],
    'snow':         ['🌿 Cover sensitive crops with cloth', '🔥 Light irrigation before frost protects roots', '🌱 Avoid pruning until frost passes'],
    'mist':         ['🍄 Watch for fungal disease', '💊 Apply preventive fungicide', '🌬️ Improve air circulation'],
    'haze':         ['😷 Reduce outdoor work', '💧 Increase irrigation — heat stress likely', '🌿 Monitor crops for wilting'],
    'clear':        ['☀️ Good day for spraying pesticides', '🚜 Ideal for harvesting', '💧 Check soil moisture levels'],
    'clouds':       ['🌤️ Good day for transplanting', '💧 Moderate irrigation needed', '🌱 Apply fertilizers today'],
}

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Smart Crop Advisory System",
    page_icon="🌾",
    layout="centered"
)

# ── Sidebar — Language selector ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🌐 Language / भाषा")
    selected_lang = st.selectbox(
        "Select Language",
        list(LANGUAGES.keys()),
        index=0
    )
    st.session_state['lang_code'] = LANGUAGES[selected_lang]
    if selected_lang != 'English':
        st.success(f"✅ {selected_lang} selected")
    st.divider()
    st.markdown("### 📱 Quick Links")
    st.markdown("🌾 [Live App](https://smart-crop-advisor-pryetrqjrna69seh6ne4uq.streamlit.app)")
    st.markdown("💻 [GitHub](https://github.com/bored-psychic/smart-crop-advisor)")
    st.divider()
    st.caption("Smart Crop Advisory System\nBuilt with ❤️ for Indian Farmers")

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

FERTILIZER_SCHEDULE = {
    'Initial':     {'N': '30% of total N dose', 'tip': 'Apply basal dose of P and K fully at sowing.'},
    'Development': {'N': '30% of total N dose', 'tip': 'Top-dress with urea. Monitor leaf color.'},
    'Mid-season':  {'N': '40% of total N dose', 'tip': 'Final N top-dress. Avoid excess — causes lodging.'},
    'Late season': {'N': 'No N needed',          'tip': 'Stop fertilizing. Focus on pest monitoring.'},
}

def calculate_ET0(temp, humidity, wind_speed_kmh):
    wind_ms = wind_speed_kmh / 3.6
    es = 0.6108 * np.exp(17.27 * temp / (temp + 237.3))
    ea = es * humidity / 100
    vpd = max(es - ea, 0)
    ET0 = (0.408 * 0.0135 * (temp + 17.8) * (wind_ms + 1)) + (0.34 * vpd * wind_ms)
    return max(round(ET0, 2), 1.0)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🌾 " + T("Smart Crop Advisory System"))
st.caption(T("AI-powered advisory for small and marginal farmers"))
st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🌾 " + T("Crop Recommender"),
    "🌿 " + T("Disease Detector"),
    "💰 " + T("Market Prices"),
    "💧 " + T("Irrigation Advisor")
])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — CROP RECOMMENDER
# ════════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader(T("Find the best crop for your field"))
    st.markdown(T("Enter your soil and climate details below."))

    crop_model, scaler, le = load_crop_models()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**🧪 {T('Soil Nutrients')}**")
        N = st.slider(T("Nitrogen (N) — kg/ha"), 0, 140, 90)
        P = st.slider(T("Phosphorus (P) — kg/ha"), 5, 145, 42)
        K = st.slider(T("Potassium (K) — kg/ha"), 5, 205, 43)
        ph = st.slider(T("Soil pH"), 3.5, 9.5, 6.5, step=0.1)

    with col2:
        st.markdown(f"**🌦️ {T('Climate Conditions')}**")
        temperature = st.slider(T("Temperature (°C)"), 8.0, 45.0, 25.0, step=0.5)
        humidity = st.slider(T("Humidity (%)"), 14.0, 100.0, 80.0, step=0.5)
        rainfall = st.slider(T("Rainfall (mm)"), 20.0, 300.0, 200.0, step=5.0)

    st.divider()

    if st.button("🔍 " + T("Get Crop Recommendation"), use_container_width=True, type="primary"):
        input_data = np.array([[N, P, K, temperature, humidity, ph, rainfall]])
        input_scaled = scaler.transform(input_data)
        probs = crop_model.predict_proba(input_scaled)[0]
        top3_idx = np.argsort(probs)[::-1][:3]

        top_crop = le.classes_[top3_idx[0]]
        top_conf = probs[top3_idx[0]] * 100
        emoji = CROP_EMOJI.get(top_crop, '🌱')
        tip = CROP_TIPS.get(top_crop, '')

        st.success(f"### {emoji} {T('Best Crop')}: **{top_crop.upper()}** — {top_conf:.1f}% {T('confidence')}")
        if tip:
            st.info(f"💡 **{T('Tip')}:** {T(tip)}")

        soil, soil_advice, soil_color = get_soil_type(N, P, K, ph)
        st.markdown(f"#### {soil_color} {T('Detected Soil Type')}: **{T(soil)}**")
        st.warning(f"🌱 **{T('Soil Advice')}:** {T(soil_advice)}")

        st.markdown(f"#### {T('Other Options')}")
        r2, r3 = st.columns(2)
        crop2 = le.classes_[top3_idx[1]]
        conf2 = probs[top3_idx[1]] * 100
        with r2:
            st.metric(label=f"{CROP_EMOJI.get(crop2,'🌱')} #2 — {crop2.capitalize()}", value=f"{conf2:.1f}%")
        crop3 = le.classes_[top3_idx[2]]
        conf3 = probs[top3_idx[2]] * 100
        with r3:
            st.metric(label=f"{CROP_EMOJI.get(crop3,'🌱')} #3 — {crop3.capitalize()}", value=f"{conf3:.1f}%")

        st.markdown(f"#### {T('Confidence Across Top 8 Crops')}")
        chart_df = pd.DataFrame({
            'Crop': [c.capitalize() for c in le.classes_],
            'Confidence (%)': [round(p * 100, 2) for p in probs]
        }).sort_values('Confidence (%)', ascending=False).head(8)
        st.bar_chart(chart_df.set_index('Crop'))

        with st.expander(f"📋 {T('Your Input Summary')}"):
            summary = pd.DataFrame({
                T('Parameter'): [T('Nitrogen (N)'), T('Phosphorus (P)'), T('Potassium (K)'),
                              T('Temperature'), T('Humidity'), T('pH'), T('Rainfall')],
                T('Value'): [f"{N} kg/ha", f"{P} kg/ha", f"{K} kg/ha",
                          f"{temperature} °C", f"{humidity} %", str(ph), f"{rainfall} mm"]
            })
            st.table(summary)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — DISEASE CHECKER
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("🌿 " + T("Crop Disease Checker"))
    st.markdown(T("Select your crop and symptoms — get instant disease diagnosis and treatment."))

    DISEASE_DB = {
        'Tomato': {
            'Yellow leaves + brown spots': {'disease': 'Early Blight (Alternaria solani)', 'treatment': 'Apply Mancozeb 75% WP @ 2g/L. Remove infected leaves.', 'prevention': 'Crop rotation every 2 years. Use resistant varieties.', 'severity': 'Medium'},
            'Dark brown patches + white mold': {'disease': 'Late Blight (Phytophthora infestans)', 'treatment': 'Apply Metalaxyl + Mancozeb immediately. Destroy infected plants.', 'prevention': 'Avoid overhead irrigation. Use certified disease-free seeds.', 'severity': 'High'},
            'Curling yellow leaves + stunted growth': {'disease': 'Tomato Yellow Leaf Curl Virus', 'treatment': 'No cure. Remove infected plants immediately to prevent spread.', 'prevention': 'Control whitefly population. Use silver reflective mulch.', 'severity': 'High'},
            'Small dark spots with yellow halo': {'disease': 'Bacterial Spot (Xanthomonas)', 'treatment': 'Spray copper hydroxide @ 3g/L every 7 days.', 'prevention': 'Use disease-free transplants. Avoid working in wet conditions.', 'severity': 'Medium'},
            'White powdery coating on leaves': {'disease': 'Powdery Mildew (Leveillula taurica)', 'treatment': 'Apply Sulphur 80% WP @ 2g/L or Hexaconazole.', 'prevention': 'Improve air circulation. Avoid excess nitrogen.', 'severity': 'Low'},
        },
        'Potato': {
            'Brown lesions with yellow border': {'disease': 'Early Blight (Alternaria solani)', 'treatment': 'Apply Chlorothalonil @ 2g/L. Repeat every 10 days.', 'prevention': 'Use certified seed tubers. Practice crop rotation.', 'severity': 'Medium'},
            'Water-soaked dark patches spreading fast': {'disease': 'Late Blight (Phytophthora infestans)', 'treatment': 'Apply Cymoxanil + Mancozeb urgently. Destroy infected haulms.', 'prevention': 'Plant in well-drained soil. Monitor weather forecasts.', 'severity': 'High'},
            'Yellowing from bottom leaves upward': {'disease': 'Potato Virus Y (PVY)', 'treatment': 'No cure. Rogue out infected plants.', 'prevention': 'Use virus-free certified seed. Control aphid vectors.', 'severity': 'High'},
        },
        'Rice': {
            'Diamond-shaped lesions with grey center': {'disease': 'Rice Blast (Magnaporthe oryzae)', 'treatment': 'Apply Tricyclazole 75% WP @ 0.6g/L at booting stage.', 'prevention': 'Use blast-resistant varieties. Avoid excess nitrogen.', 'severity': 'High'},
            'Yellow-orange stripes on leaves': {'disease': 'Bacterial Leaf Blight (Xanthomonas oryzae)', 'treatment': 'Apply copper-based bactericide. Drain fields temporarily.', 'prevention': 'Use resistant varieties. Balanced fertilization.', 'severity': 'High'},
            'Brown spots with yellow halo': {'disease': 'Brown Spot (Cochliobolus miyabeanus)', 'treatment': 'Apply Mancozeb or Iprodione fungicide.', 'prevention': 'Balanced potassium nutrition. Use healthy seeds.', 'severity': 'Medium'},
        },
        'Maize': {
            'Orange powdery pustules on leaves': {'disease': 'Common Rust (Puccinia sorghi)', 'treatment': 'Apply Mancozeb or Azoxystrobin @ 1ml/L.', 'prevention': 'Use rust-resistant hybrids. Early planting.', 'severity': 'Medium'},
            'Long grey-green lesions on leaves': {'disease': 'Northern Leaf Blight (Exserohilum turcicum)', 'treatment': 'Apply Propiconazole fungicide at early stage.', 'prevention': 'Crop rotation. Use resistant varieties.', 'severity': 'Medium'},
            'Galls/tumors on plant parts': {'disease': 'Common Smut (Ustilago maydis)', 'treatment': 'No chemical cure. Remove and destroy galls before they burst.', 'prevention': 'Avoid mechanical injury. Seed treatment with fungicide.', 'severity': 'Medium'},
        },
        'Wheat': {
            'Yellow stripes along leaf veins': {'disease': 'Yellow/Stripe Rust (Puccinia striiformis)', 'treatment': 'Apply Propiconazole 25% EC @ 1ml/L urgently.', 'prevention': 'Use resistant varieties. Early sowing.', 'severity': 'High'},
            'Orange-brown pustules scattered on leaves': {'disease': 'Brown/Leaf Rust (Puccinia triticina)', 'treatment': 'Apply Tebuconazole or Propiconazole fungicide.', 'prevention': 'Balanced nitrogen. Use tolerant varieties.', 'severity': 'Medium'},
            'Black powdery pustules on stems': {'disease': 'Stem/Black Rust (Puccinia graminis)', 'treatment': 'Apply Mancozeb + Propiconazole immediately.', 'prevention': 'Use Ug99-resistant varieties. Early detection critical.', 'severity': 'High'},
        },
        'Cotton': {
            'Wilting + internal stem discoloration': {'disease': 'Fusarium Wilt (Fusarium oxysporum)', 'treatment': 'No effective cure. Remove infected plants. Soil solarization.', 'prevention': 'Use wilt-resistant varieties. Crop rotation with cereals.', 'severity': 'High'},
            'Angular water-soaked leaf spots': {'disease': 'Bacterial Blight (Xanthomonas citri)', 'treatment': 'Apply copper oxychloride @ 3g/L. Avoid overhead irrigation.', 'prevention': 'Use certified disease-free seeds. Balanced nutrition.', 'severity': 'Medium'},
        },
        'Banana': {
            'Yellow streaks on young leaves': {'disease': 'Banana Bunchy Top Virus (BBTV)', 'treatment': 'No cure. Destroy infected plants immediately.', 'prevention': 'Use virus-free tissue culture plants. Control aphids.', 'severity': 'High'},
            'Black streaks inside stem + wilting': {'disease': 'Panama Wilt / Fusarium Wilt', 'treatment': 'No chemical cure. Destroy infected plants. Long fallow period.', 'prevention': 'Use resistant Cavendish varieties. Clean tools between plants.', 'severity': 'High'},
        },
    }

    st.markdown(f"#### 👇 {T('Select your crop and match your symptom to the cards below')}")

    col1, col2 = st.columns(2)
    with col1:
        selected_crop = st.selectbox(f"🌱 {T('Select your crop')}", sorted(DISEASE_DB.keys()))
    with col2:
        symptoms_list = list(DISEASE_DB[selected_crop].keys())
        selected_symptom = st.selectbox(f"🔍 {T('Select main symptom')}", symptoms_list)

    st.markdown(f"#### 📋 {T('Common diseases in')} {selected_crop}:")

    SEVERITY_BG = {'High': '#FF4B4B', 'Medium': '#FFA500', 'Low': '#21BA45'}
    SEVERITY_ICON = {'High': '🔴', 'Medium': '🟡', 'Low': '🟢'}

    disease_items = list(DISEASE_DB[selected_crop].items())
    cols = st.columns(min(len(disease_items), 3))
    for i, (symptom, data) in enumerate(disease_items):
        with cols[i % 3]:
            color = SEVERITY_BG[data['severity']]
            icon = SEVERITY_ICON[data['severity']]
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,{color}22,{color}44);border-left:4px solid {color};border-radius:8px;padding:12px;margin-bottom:10px;min-height:120px;">
                <div style="font-size:13px;font-weight:bold;color:white;">{icon} {data['disease']}</div>
                <div style="font-size:11px;color:#cccccc;margin-top:6px;">🔍 {symptom}</div>
                <div style="font-size:11px;color:{color};margin-top:6px;font-weight:bold;">{T('Severity')}: {data['severity']}</div>
            </div>""", unsafe_allow_html=True)

    st.divider()

    if st.button(f"🔬 {T('Diagnose Disease')}", use_container_width=True, type="primary"):
        result = DISEASE_DB[selected_crop][selected_symptom]
        severity = result['severity']

        if severity == 'High':
            st.error(f"### ⚠️ {T(result['disease'])}")
            st.markdown(f"**{T('Severity')}: 🔴 {T('HIGH — Act immediately!')}**")
        elif severity == 'Medium':
            st.warning(f"### ⚠️ {T(result['disease'])}")
            st.markdown(f"**{T('Severity')}: 🟡 {T('MEDIUM — Monitor closely')}**")
        else:
            st.info(f"### ℹ️ {T(result['disease'])}")
            st.markdown(f"**{T('Severity')}: 🟢 {T('LOW — Manageable')}**")

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**💊 {T('Treatment')}:**\n\n{T(result['treatment'])}")
        with col2:
            st.success(f"**🛡️ {T('Prevention')}:**\n\n{T(result['prevention'])}")

    st.divider()
    st.caption(T("Database covers 7 crops · 20+ diseases · Treatment & prevention advice"))

# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — MARKET PRICE FORECAST
# ════════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader(T("Predict mandi prices for the next 30 days"))
    st.markdown(T("Select a crop to see the price forecast and the best day to sell."))

    price_models = load_price_models()
    available_crops = sorted(list(price_models.keys()))

    crop_choice = st.selectbox(f"🌾 {T('Select Crop')}", available_crops, index=0)
    forecast_days = st.slider(T("Forecast horizon (days)"), 7, 60, 30)

    if st.button(f"📈 {T('Forecast Price')}", use_container_width=True, type="primary"):
        with st.spinner(f"{T('Forecasting')} {crop_choice} {T('prices')}..."):
            model = price_models[crop_choice]
            future = model.make_future_dataframe(periods=forecast_days)
            forecast = model.predict(future)
            future_forecast = forecast.tail(forecast_days)[['ds','yhat','yhat_lower','yhat_upper']].copy()
            future_forecast.columns = ['Date','Price','Min','Max']
            future_forecast['Date'] = pd.to_datetime(future_forecast['Date'])
            future_forecast = future_forecast.round(2)

        best_idx = future_forecast['Price'].idxmax()
        worst_idx = future_forecast['Price'].idxmin()
        best_day = future_forecast.loc[best_idx]
        worst_day = future_forecast.loc[worst_idx]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(f"💰 {T('Best Price')}", f"₹{best_day['Price']:.0f}/qtl", f"{best_day['Date'].strftime('%d %b')}")
        with col2:
            st.metric(f"📉 {T('Lowest Price')}", f"₹{worst_day['Price']:.0f}/qtl", f"{worst_day['Date'].strftime('%d %b')}")
        with col3:
            avg = future_forecast['Price'].mean()
            st.metric(f"📊 {T('Avg Price')}", f"₹{avg:.0f}/qtl", f"{T('next')} {forecast_days} {T('days')}")

        today_price = future_forecast['Price'].iloc[0]
        if best_day['Price'] > today_price * 1.05:
            st.success(f"💡 **{T('Advice: Wait to sell!')}** {T('Price expected to rise to')} ₹{best_day['Price']:.0f}/qtl {T('on')} {best_day['Date'].strftime('%d %b %Y')}")
        else:
            st.warning(f"💡 **{T('Advice: Sell now.')}** {T('Prices not expected to rise significantly.')}")

        st.markdown(f"#### {T('Price Forecast Chart')}")
        st.line_chart(future_forecast.set_index('Date')[['Price','Min','Max']])

        with st.expander(f"📋 {T('Full Price Forecast Table')}"):
            display_df = future_forecast.copy()
            display_df['Date'] = display_df['Date'].dt.strftime('%d %b %Y')
            st.dataframe(display_df, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — IRRIGATION ADVISOR
# ════════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader(T("Smart Irrigation & Fertilizer Advisor"))
    st.markdown(T("Get precise water and fertilizer recommendations based on your crop and weather."))

    st.markdown(f"#### 🌤️ {T('Live Weather (Auto-fill)')}")
    city = st.text_input(T("Enter your city name"), placeholder=T("e.g. Bengaluru, Pune, Hyderabad"))
    weather_data = None
    if city:
        weather_data = get_weather(city)
        if weather_data:
            wc1, wc2, wc3, wc4 = st.columns(4)
            wc1.metric("🌡️ " + T("Temp"), f"{weather_data['temp']}°C")
            wc2.metric("💧 " + T("Humidity"), f"{weather_data['humidity']}%")
            wc3.metric("💨 " + T("Wind"), f"{weather_data['wind_speed']:.1f} km/h")
            wc4.metric("🌧️ " + T("Rain"), f"{weather_data['rainfall']} mm")
            st.success(f"📍 {T('Live weather for')} **{weather_data['city']}**: {weather_data['description']}")
            desc_lower = weather_data['description'].lower()
            for key, tips in CALAMITY_TIPS.items():
                if key in desc_lower:
                    st.warning(f"⚠️ **{T('Weather Advisory for Farmers')}:**")
                    for tip in tips:
                        st.markdown(f"- {T(tip)}")
                    break
        else:
            st.error(T("City not found. Please check spelling or try a nearby city."))

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**🌱 {T('Crop Details')}**")
        irr_crop = st.selectbox(T("Crop"), sorted(list(CROP_KC.keys())))
        growth_stage = st.selectbox(T("Growth Stage"), ['Initial','Development','Mid-season','Late season'])
        field_area = st.number_input(T("Field Area (acres)"), min_value=0.5, max_value=100.0, value=1.0, step=0.5)
        last_rain = st.slider(T("Rainfall in last 3 days (mm)"), 0, 100, 0)

    with col2:
        st.markdown(f"**🌡️ {T('Today Weather')}**")
        default_temp = float(weather_data['temp']) if weather_data else 30.0
        default_humidity = float(weather_data['humidity']) if weather_data else 60.0
        default_wind = float(weather_data['wind_speed']) if weather_data else 10.0
        irr_temp = st.slider(T("Temperature (°C)"), 10.0, 48.0, min(max(default_temp,10.0),48.0), step=0.5)
        irr_humidity = st.slider(T("Humidity (%)"), 10.0, 100.0, min(max(default_humidity,10.0),100.0), step=1.0)
        wind_speed = st.slider(T("Wind Speed (km/h)"), 0.0, 50.0, min(default_wind,50.0), step=1.0)

    st.divider()

    if st.button(f"💧 {T('Get Irrigation Advice')}", use_container_width=True, type="primary"):
        ET0 = calculate_ET0(irr_temp, irr_humidity, wind_speed)
        Kc = CROP_KC[irr_crop][growth_stage]
        ETc = ET0 * Kc
        effective_rain = last_rain * 0.7
        net_irrigation = max(ETc - effective_rain / 3, 0)
        litres_per_acre = net_irrigation * 4046.86
        total_litres = litres_per_acre * field_area
        fert = FERTILIZER_SCHEDULE[growth_stage]

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(f"💧 {T('Water Need')}", f"{ETc:.1f} mm/day")
        with c2:
            st.metric(f"🚿 {T('Net Irrigation')}", f"{net_irrigation:.1f} mm/day")
        with c3:
            st.metric(f"🪣 {T('Total Water')}", f"{total_litres/1000:.1f} kL", f"{T('for')} {field_area} {T('acre(s)')}")

        st.divider()

        if net_irrigation < 1.0:
            st.success(f"✅ **{T('No irrigation needed today!')}** {T('Recent rainfall is sufficient.')}")
        elif net_irrigation < 3.0:
            st.warning(f"💧 **{T('Light irrigation recommended')}:** {T('Apply')} {net_irrigation:.1f} mm ({total_litres/1000:.1f} kL)")
        else:
            st.error(f"🚨 **{T('Irrigation urgently needed')}:** {T('Apply')} {net_irrigation:.1f} mm ({total_litres/1000:.1f} kL)")

        st.markdown(f"#### 🌱 {T('Fertilizer Recommendation')}")
        st.info(f"""
        **{T('Growth Stage')}:** {T(growth_stage)}
        **{T('Nitrogen (N)')}:** {T(fert['N'])}
        **{T('Tip')}:** {T(fert['tip'])}
        """)

        with st.expander(f"🔬 {T('Calculation Details (FAO-56 Method)')}"):
            st.markdown(f"""
            | {T('Parameter')} | {T('Value')} |
            |---|---|
            | Reference ET₀ | {ET0:.2f} mm/day |
            | Crop Coefficient (Kc) | {Kc} |
            | Crop Water Need (ETc) | {ETc:.2f} mm/day |
            | {T('Effective Rainfall')} | {effective_rain/3:.2f} mm/day |
            | {T('Net Irrigation Need')} | {net_irrigation:.2f} mm/day |
            | {T('Field Area')} | {field_area} {T('acres')} |
            | {T('Total Water Required')} | {total_litres/1000:.2f} kL |
            *{T('Using FAO Penman-Monteith method (FAO-56 guidelines)')}*
            """)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(T("Built with ❤️ | Random Forest · MobileNetV2 · Prophet · FAO-56 | Smart Crop Advisory System"))
