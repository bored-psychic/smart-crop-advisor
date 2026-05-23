"""
Sidebar configuration for KisanOS.
Call render_sidebar() once from app.py after page config is set.
"""

import streamlit as st
from core.language import T, activate, LANGUAGES


def render_sidebar() -> None:
    """Render the KisanOS sidebar: branding, language selector, farmer profile."""
    with st.sidebar:
        st.markdown("""
    <div style="padding:12px 0 16px;border-bottom:1px solid rgba(42,51,40,0.10);margin-bottom:4px;">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
        <svg width="32" height="32" viewBox="0 0 34 34">
          <path d="M17 30 L17 14" stroke="#3E6B3E" stroke-width="1.6" stroke-linecap="round"/>
          <path d="M17 18 C 8 18, 5 10, 5 10 C 5 10, 9 22, 17 22 Z" fill="#82B082"/>
          <path d="M17 14 C 26 14, 29 6, 29 6 C 29 6, 25 18, 17 18 Z" fill="#6B9B6B"/>
        </svg>
        <div>
          <div style="font-family:'Fraunces',Georgia,serif;font-size:1.3rem;color:#2A3328;font-weight:400;letter-spacing:-0.01em;line-height:1.1;">
            Kisan<em style="font-style:italic;color:#3E6B3E;">OS</em>
          </div>
          <div style="display:flex;align-items:center;gap:5px;font-size:0.7rem;color:#8C9684;margin-top:2px;">
            <span style="width:6px;height:6px;border-radius:50%;background:#3E6B3E;box-shadow:0 0 0 3px rgba(62,107,62,0.18);display:inline-block;"></span>
            a quiet companion
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

        # Language selector
        _lang_options = list(LANGUAGES.keys())
        _sel = st.selectbox("🌐 Language", _lang_options)
        st.session_state['lang_code'] = LANGUAGES[_sel]
        activate(st.session_state['lang_code'])

        st.divider()
        st.markdown("""
    <div style="font-family:'Inter',sans-serif;font-size:10px;color:#4A5545;letter-spacing:0.14em;text-transform:uppercase;margin-bottom:8px;">
      Your Profile
    </div>
    """, unsafe_allow_html=True)
        st.session_state['farmer_name']    = st.text_input("Name",              value=st.session_state.get('farmer_name', ''),    placeholder="your name",            key="profile_name")
        st.session_state['farmer_village'] = st.text_input("📍 Village / District", value=st.session_state.get('farmer_village', ''), placeholder="village or town",   key="profile_village")
        st.session_state['farmer_crop']    = st.text_input("🌱 Main Crop",      value=st.session_state.get('farmer_crop', ''),    placeholder="primary crop",         key="profile_crop")
        st.session_state['farmer_phone']   = st.text_input("📞 WhatsApp (91+)", value=st.session_state.get('farmer_phone', ''),   placeholder="919876543210",         key="profile_phone")

        st.divider()
        st.markdown("""
    <div style="font-family:'Kalam',cursive;font-size:15px;color:#3A4A35;line-height:1.6;padding:8px 4px;">
      "a calm field today<br>is a good harvest tomorrow."
    </div>
    """, unsafe_allow_html=True)
