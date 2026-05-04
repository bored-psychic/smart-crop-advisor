import streamlit as st
import asyncio
import pandas as pd
from frontend.api_client import APIClient
from frontend.ui_helpers import card, page_hero
from core.language import T

CROP_EMOJI = {
    'rice':'🌾','maize':'🌽','chickpea':'🫘','kidneybeans':'🫘','pigeonpeas':'🫘',
    'mothbeans':'🌿','mungbean':'🌿','blackgram':'🌿','lentil':'🌿','pomegranate':'🍎',
    'banana':'🍌','mango':'🥭','grapes':'🍇','watermelon':'🍉','muskmelon':'🍈',
    'apple':'🍎','orange':'🍊','papaya':'🍈','coconut':'🥥','cotton':'🌿',
    'jute':'🌿','coffee':'☕',
}

def render():
    page_hero("CROP ADVISOR", "Find what your soil", "wants to grow.", "Tell us about your field. We'll quietly look through 26 crops and suggest the one your land will love most.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**🧪 {T('Soil Nutrients')}**")
        N = st.slider(T("Nitrogen (N)"), 0, 140, 90)
        P = st.slider(T("Phosphorus (P)"), 5, 145, 42)
        K = st.slider(T("Potassium (K)"), 5, 205, 43)
        ph = st.slider(T("Soil pH"), 3.5, 9.5, 6.5, step=0.1)

    with col2:
        st.markdown(f"**🌦️ {T('Climate Conditions')}**")
        temperature = st.slider(T("Temperature (°C)"), 8.0, 45.0, 25.0, step=0.5)
        humidity = st.slider(T("Humidity (%)"), 14.0, 100.0, 80.0, step=0.5)
        rainfall = st.slider(T("Rainfall (mm)"), 20.0, 300.0, 200.0, step=5.0)

    if st.button("🔍 " + T("Get Crop Recommendation"), type="primary"):
        data = {
            "N": N, "P": P, "K": K,
            "temperature": temperature,
            "humidity": humidity,
            "ph": ph,
            "rainfall": rainfall
        }
        with st.spinner(T("Consulting the Swarm...")):
            res = asyncio.run(APIClient.recommend_crop(data))
            if res:
                top_obj  = res['top_crop']
                top_crop = top_obj['crop']
                top_conf = top_obj['confidence']
                emoji    = top_obj.get('emoji') or CROP_EMOJI.get(top_crop.lower(), '🌱')

                soil_obj    = res['soil']
                soil_type   = soil_obj['soil_type']
                soil_advice = soil_obj['advice']

                alt   = res.get('alternatives', [])
                crop2 = alt[0]['crop']       if len(alt) > 0 else ''
                conf2 = alt[0]['confidence'] if len(alt) > 0 else 0.0
                crop3 = alt[1]['crop']       if len(alt) > 1 else ''
                conf3 = alt[1]['confidence'] if len(alt) > 1 else 0.0

                card(f"""
                <div style='font-family:Space Grotesk,sans-serif;'>
                  <div style='font-size:1.7rem;font-weight:700;color:#22C55E;margin-bottom:2px;'>
                    {emoji}&nbsp;{top_crop.upper()}
                  </div>
                  <div style='font-family:JetBrains Mono,monospace;font-size:0.78rem;color:#4ADE80;'>
                    {T('Best Crop')} &middot; {T('confidence')} {top_conf:.1f}%
                  </div>
                </div>""", severity="success")
                card(f"<b style='color:#22C55E'>&#128161; {T('Tip')}:</b> {T(res['tip'])}", severity="info")
                card(f"<b style='color:#22C55E'>&#127757; {T('Soil')}:</b> {T(soil_type)} &nbsp;&#183;&nbsp; <b style='color:#22C55E'>{T('Advice')}:</b> {T(soil_advice)}", severity="warning")

                st.markdown(f"#### {T('Other Options')}")
                r2, r3 = st.columns(2)
                with r2:
                    st.metric(label=f"{CROP_EMOJI.get(crop2.lower(), '🌱')} #2 — {crop2.capitalize()}", value=f"{conf2:.1f}%")
                with r3:
                    st.metric(label=f"{CROP_EMOJI.get(crop3.lower(), '🌱')} #3 — {crop3.capitalize()}", value=f"{conf3:.1f}%")

                st.markdown(f"#### {T('Confidence Across Top 8 Crops')}")
                all_probs = res.get('all_probabilities', {})
                chart_df = pd.DataFrame({
                    'Crop': [c.capitalize() for c in all_probs],
                    'Confidence (%)': list(all_probs.values()),
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
            else:
                card(T("Swarm offline. Check backend connection."), severity="error")
