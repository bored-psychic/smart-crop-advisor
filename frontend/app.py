import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import asyncio
import frontend.tab1_crop as tab1_crop
import frontend.tab2_disease as tab2_disease
import frontend.tab3_market as tab3_market
import frontend.tab4_irrigation as tab4_irrigation
import frontend.tab5_acoustic as tab5_acoustic
import frontend.tab6_field as tab6_field
from core.language import T, T_batch, LANGUAGES

st.set_page_config(
    page_title="KisanOS Swarm · Smart Crop Advisory",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Swarm Global Styles ──────────────────────────────────────────────────────
st.markdown("""
    <style>
        /* 1. FORCE THE TOGGLE TO THE FRONT */
        [data-testid="stSidebarCollapseButton"] {
            visibility: visible !important;
            display: block !important;
            position: fixed !important;
            top: 10px !important;
            left: 10px !important;
            z-index: 1000000 !important;
            background-color: rgba(34, 197, 94, 0.1) !important; /* Subtle green glow */
            border-radius: 5px !important;
        }

        /* 2. FORCE ICON VISIBILITY (Kisan Green) */
        [data-testid="stSidebarCollapseButton"] svg {
            fill: #22C55E !important;
            width: 30px !important;
            height: 30px !important;
        }

        /* 3. PREVENT OVERFLOW CLIPPING */
        .stApp {
            background-color: #0A0F0A !important;
            overflow: visible !important;
        }

        /* 4. FIX HEADER DEPTH */
        header[data-testid="stHeader"] {
            background-color: transparent !important;
            z-index: 999999 !important;
        }
    </style>
""", unsafe_allow_html=True)

# ── Sidebar Swarm Logic ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🐝 Swarm Intelligence")
    # Language selector
    _lang_options = list(LANGUAGES.keys())
    _sel = st.selectbox("🌐 Language", _lang_options)
    st.session_state['lang_code'] = LANGUAGES[_sel]
    # (Translation cache logic omitted for brevity)

# ── Main Swarm Navigation ────────────────────────────────────────────────────
st.markdown("## 🌾 KisanOS Swarm")
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
