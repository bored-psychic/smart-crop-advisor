import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import streamlit.components.v1 as components
import frontend.tab1_crop as tab1_crop
import frontend.tab2_disease as tab2_disease
import frontend.tab3_market as tab3_market
import frontend.tab4_irrigation as tab4_irrigation
import frontend.tab5_acoustic as tab5_acoustic
import frontend.tab6_field as tab6_field
from core.language import T, activate, LANGUAGES
from frontend.styles import STYLES, BOTANICAL_OVERLAY
from frontend.sidebar import render_sidebar

st.set_page_config(
    page_title="KisanOS Swarm · Smart Crop Advisory",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global styles ─────────────────────────────────────────────────────────────
st.markdown(STYLES, unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
render_sidebar()

# ── Main Navigation ───────────────────────────────────────────────────────────
st.markdown(
    '<div style="font-family:\'Fraunces\',Georgia,serif;font-size:1.05rem;font-weight:400;'
    'color:#8C9684;letter-spacing:0.04em;margin-bottom:8px;">KisanOS</div>',
    unsafe_allow_html=True
)
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🌾 " + T("Crop"), "🌿 " + T("Disease"), "💰 " + T("Market"),
    "💧 " + T("Irrigation"), "🎙️ " + T("Acoustic"), "🛰️ " + T("Field")
])

with tab1: tab1_crop.render()
with tab2: tab2_disease.render()
with tab3: tab3_market.render()
with tab4: tab4_irrigation.render()
with tab5: tab5_acoustic.render()
with tab6: tab6_field.render()

# ── Botanical Overlay (full-viewport vines + bottom-walking caterpillar) ──────
components.html(BOTANICAL_OVERLAY, height=1)
