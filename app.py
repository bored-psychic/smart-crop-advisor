import streamlit as st
import pickle
import numpy as np
from PIL import Image

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

# ── Load disease detection model ──────────────────────────────────────────────
@st.cache_resource
def load_disease_model():
    import tensorflow as tf
    model = tf.keras.models.load_model('disease_model.h5')
    class_names = np.load('class_names.npy', allow_pickle=True)
    return model, class_names

# ── Crop emoji map ────────────────────────────────────────────────────────────
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

DISEASE_TREATMENT = {
    'Apple___Apple_scab': '💊 Apply fungicide (Captan/Mancozeb). Remove infected leaves.',
    'Apple___Black_rot': '✂️ Prune infected branches. Apply copper-based fungicide.',
    'Apple___Cedar_apple_rust': '🍎 Apply myclobutanil fungicide early in the season.',
    'Corn___Common_rust': '🌽 Apply fungicide (Azoxystrobin). Use resistant varieties.',
    'Corn___Northern_Leaf_Blight': '🌽 Apply fungicide at early stages. Rotate crops.',
    'Corn___Cercospora_leaf_spot Gray_leaf_spot': '🌽 Improve air circulation. Apply strobilurin fungicide.',
    'Grape___Black_rot': '🍇 Remove mummified fruits. Apply mancozeb fungicide.',
    'Grape___Esca_(Black_Measles)': '🍇 No cure — remove infected vines to prevent spread.',
    'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)': '🍇 Apply copper fungicide. Avoid overhead irrigation.',
    'Orange___Haunglongbing_(Citrus_greening)': '🍊 No cure. Remove infected trees immediately.',
    'Peach___Bacterial_spot': '🍑 Apply copper sprays. Use resistant varieties.',
    'Pepper,_bell___Bacterial_spot': '🫑 Apply copper bactericide. Avoid working when wet.',
    'Potato___Early_blight': '🥔 Apply chlorothalonil fungicide. Rotate crops annually.',
    'Potato___Late_blight': '🥔 Apply mancozeb immediately. Destroy infected plants.',
    'Strawberry___Leaf_scorch': '🍓 Apply fungicide. Remove infected leaves.',
    'Tomato___Bacterial_spot': '🍅 Apply copper spray. Use disease-free seeds.',
    'Tomato___Early_blight': '🍅 Apply mancozeb fungicide. Mulch around plants.',
    'Tomato___Late_blight': '🍅 Apply chlorothalonil. Remove infected plants urgently.',
    'Tomato___Leaf_Mold': '🍅 Improve ventilation. Apply fungicide (copper/mancozeb).',
    'Tomato___Septoria_leaf_spot': '🍅 Remove lower leaves. Apply fungicide regularly.',
    'Tomato___Spider_mites Two-spotted_spider_mite': '🍅 Apply neem oil or miticide spray.',
    'Tomato___Target_Spot': '🍅 Apply azoxystrobin fungicide. Remove infected debris.',
    'Tomato___Tomato_mosaic_virus': '🍅 No cure. Remove infected plants. Control aphids.',
    'Tomato___Tomato_Yellow_Leaf_Curl_Virus': '🍅 Control whiteflies. Remove infected plants.',
    'Squash___Powdery_mildew': '🎃 Apply potassium bicarbonate or neem oil spray.',
    'Cherry___Powdery_mildew': '🍒 Apply sulfur-based fungicide. Improve air circulation.',
}

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🌾 Smart Crop Advisory System")
st.caption("AI-powered advisory for small and marginal farmers")
st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["🌾 Crop Recommender", "🌿 Disease Detector"])

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
        import pandas as pd
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
    st.subheader("Detect crop disease from a leaf photo")
    st.markdown("Upload a clear photo of a single leaf to get an instant diagnosis.")

    uploaded_file = st.file_uploader(
        "📸 Upload leaf image",
        type=["jpg", "jpeg", "png"],
        help="Take a close-up photo of the affected leaf in good lighting"
    )

    if uploaded_file is not None:
        image = Image.open(uploaded_file)

        col_img, col_info = st.columns([1, 1])
        with col_img:
            st.image(image, caption="Uploaded Leaf", use_container_width=True)

        with col_info:
            st.markdown("**📊 Analyzing your leaf...**")
            with st.spinner("Running AI diagnosis..."):
                import tensorflow as tf
                disease_model, class_names = load_disease_model()

                img = image.resize((224, 224))
                img_array = np.array(img) / 255.0
                if img_array.shape[-1] == 4:
                    img_array = img_array[:, :, :3]
                img_array = np.expand_dims(img_array, axis=0)

                predictions = disease_model.predict(img_array)
                top3_idx = np.argsort(predictions[0])[::-1][:3]

            top_disease = class_names[top3_idx[0]]
            top_conf = predictions[0][top3_idx[0]] * 100
            display_name = top_disease.replace('___', ' — ').replace('_', ' ')

            if 'healthy' in top_disease.lower():
                st.success(f"### ✅ Healthy Plant!")
                st.markdown(f"**Confidence:** {top_conf:.1f}%")
            else:
                st.error(f"### ⚠️ {display_name}")
                st.markdown(f"**Confidence:** {top_conf:.1f}%")

        st.divider()

        treatment = DISEASE_TREATMENT.get(top_disease,
            "🔍 Consult your local agricultural extension officer for treatment advice.")
        st.info(f"**💊 Recommended Action:**\n\n{treatment}")

        st.markdown("#### Top 3 Predictions")
        for rank, idx in enumerate(top3_idx, 1):
            disease = class_names[idx].replace('___', ' — ').replace('_', ' ')
            conf = predictions[0][idx] * 100
            st.progress(int(conf), text=f"#{rank} {disease} — {conf:.1f}%")

    else:
        st.markdown("""
        #### How to get the best results:
        - 📷 Take photo in **natural daylight**
        - 🍃 Focus on a **single leaf**
        - 🔍 Make sure the **affected area is clearly visible**
        - 📐 Hold the camera **close** to the leaf

        #### Supported crops:
        Apple · Blueberry · Cherry · Corn · Grape · Orange ·
        Peach · Pepper · Potato · Raspberry · Soybean · Squash ·
        Strawberry · Tomato
        """)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("Built with ❤️ | Random Forest + MobileNetV2 | 22 crops · 38 disease classes | Smart Crop Advisory System")
