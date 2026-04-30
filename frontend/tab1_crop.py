import streamlit as st
import asyncio
from frontend.api_client import APIClient
from core.language import T

def render():
    st.subheader(T("Find the best crop for your field"))
    st.markdown(T("Enter your soil and climate details below."))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**🧪 {T('Soil Nutrients')}**")
        N = st.slider(T("Nitrogen (N)"), 0, 140, 90)
        P = st.slider(T("Phosphorus (P)"), 5, 145, 42)
        K = st.slider(T("Potassium (K)"), 5, 205, 43)
        ph = st.slider(T("Soil pH"), 3.5, 9.5, 6.5, step=0.1)

    with col2:
        st.markdown(f"**🌦️ {T('Climate Conditions')}**")
        # Add city lookup for auto-fill logic here as well
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
                st.success(f"### {res['top_crop'].upper()} — {res['top_conf']:.1f}% confidence")
                st.info(f"💡 **{T('Tip')}:** {T(res['tip'])}")
                # Render further metrics from res
            else:
                st.error(T("Swarm offline. Check backend connection."))
