import streamlit as st
import asyncio
import pandas as pd
from frontend.api_client import APIClient
from core.language import T

PEST_META = {
    'Healthy Plant':         {'severity': 'low',    'freq_range': '<100 Hz (flat)',  'pattern': 'Flat noise floor',               'energy_level': 'Background',     'icon': '✅'},
    'Aphid Colony':          {'severity': 'medium', 'freq_range': '200–400 Hz',      'pattern': 'Clustered mid-freq bursts',       'energy_level': 'Moderate',       'icon': '🟡'},
    'Whitefly Infestation':  {'severity': 'medium', 'freq_range': '400–700 Hz',      'pattern': 'Wing-beat harmonic series',       'energy_level': 'Low-moderate',   'icon': '🟡'},
    'Locust Activity':       {'severity': 'high',   'freq_range': '50–200 Hz',       'pattern': 'High-amplitude low-freq pulses',  'energy_level': 'Very High',      'icon': '🔴'},
    'Stem Borer':            {'severity': 'high',   'freq_range': '50–150 Hz',       'pattern': 'Low-freq gnawing rhythm',         'energy_level': 'High',           'icon': '🔴'},
    'Early Fungal Infection':{'severity': 'high',   'freq_range': '800–1200 Hz',     'pattern': 'High-freq crackling',             'energy_level': 'Elevated',       'icon': '🔴'},
    'Spider Mite':           {'severity': 'medium', 'freq_range': '1200–4000 Hz',    'pattern': 'Ultra-high freq scratching',      'energy_level': 'Moderate-high',  'icon': '🟡'},
    'Thrips Infestation':    {'severity': 'medium', 'freq_range': '350–500 Hz',      'pattern': 'Rapid mid-freq staccato',         'energy_level': 'Low-moderate',   'icon': '🟡'},
}


def render():
    st.subheader("🎙️ " + T("Acoustic Pest Detector"))
    st.markdown(T("Upload a short audio recording from your field. The AI analyzes frequency patterns to detect hidden pests — 7 days before visible symptoms appear."))

    st.warning(f"""
    **{T('How to record')}:**
    1. {T('Go to your field and open your phone voice recorder app')}
    2. {T('Hold the phone 15–30cm from the base of the crop plant or under the leaves')}
    3. {T('Record for 4–10 seconds. Keep still and breathe slowly.')}
    4. {T('Save and upload the file here')}
    """)

    acoustic_crop = st.selectbox(
        T("Which crop did you record?"),
        ['Tomato', 'Rice', 'Wheat', 'Cotton', 'Maize', 'Potato', 'Banana', 'Chickpea'],
        key="acoustic_crop"
    )

    audio_file = st.file_uploader(
        T("Upload field audio recording"),
        type=["wav", "mp3", "ogg", "webm", "m4a", "aac"],
        help=T("Any format from your phone voice recorder works.")
    )

    if audio_file is not None:
        st.audio(audio_file, format=audio_file.type)
        st.markdown(f"**{T('File')}:** {audio_file.name} · **{T('Size')}:** {audio_file.size // 1024} KB")

        if st.button(f"🔊 {T('Analyze for Pests')}", use_container_width=True, type="primary"):
            with st.spinner(T("Extracting frequency spectrum and analyzing pest signatures...")):
                audio_bytes = audio_file.read()
                result = asyncio.run(APIClient.analyze_acoustic(audio_bytes))
            if result:
                st.session_state['tab5_result'] = result
            else:
                st.error(T("Acoustic API unavailable. Check backend connection."))

    if 'tab5_result' in st.session_state:
        r = st.session_state['tab5_result']
        st.divider()

        if r.get('ml_used'):
            st.markdown(
                '<span style="background:#1B4332;color:#B7E4C7;padding:4px 12px;border-radius:20px;'
                'font-size:12px;font-weight:600">🤖 Random Forest ML · 97.2% CV Accuracy · 8 classes</span>',
                unsafe_allow_html=True
            )
            st.markdown("")

        pest_name = r.get('pest', 'Unknown')
        severity  = r.get('severity', 'low')
        icon      = r.get('icon', '⚠️')

        if severity == 'high':
            st.error(f"### {icon} {T('Detected')}: **{T(pest_name)}**")
        elif severity == 'medium':
            st.warning(f"### {icon} {T('Detected')}: **{T(pest_name)}**")
        elif r.get('confidence', 0) == 0:
            st.warning(f"### ⚠️ {T(pest_name)}")
        else:
            st.success(f"### {icon} {T('Result')}: **{T(pest_name)}**")

        if r.get('confidence', 0) > 0:
            st.markdown(f"**{T('Detection Confidence')}: {r['confidence']}%**")
            st.progress(r['confidence'] / 100)

        col1, col2 = st.columns(2)
        with col1:
            st.metric(T("Dominant Frequency"), r.get('freq_range', 'N/A'))
            st.metric(T("Signal Energy"), r.get('energy_level', 'N/A'))
        with col2:
            st.metric(T("Spectral Pattern"), r.get('pattern', 'N/A'))
            st.metric(T("Risk Level"), severity.upper())

        if r.get('top3'):
            st.markdown(f"#### 📊 {T('Top Predictions (ML)')}")
            for p_name, pct in r['top3']:
                meta = PEST_META.get(p_name, {})
                sev_color = {'high': '#FF4B4B', 'medium': '#FFA500', 'low': '#21BA45'}.get(meta.get('severity', 'low'), '#888')
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">'
                    f'<div style="width:130px;font-size:13px">{meta.get("icon","")}&nbsp;{p_name}</div>'
                    f'<div style="flex:1;height:10px;background:#eee;border-radius:5px;overflow:hidden">'
                    f'<div style="width:{pct}%;height:100%;background:{sev_color};border-radius:5px"></div></div>'
                    f'<div style="width:38px;font-size:13px;font-weight:600;text-align:right">{pct}%</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        st.divider()
        action = r.get('action', '')
        if severity == 'high':
            st.error(f"**💊 {T('Recommended Action')}:** {T(action)}")
        elif severity == 'medium':
            st.warning(f"**💊 {T('Recommended Action')}:** {T(action)}")
        else:
            st.info(f"**💊 {T('Recommended Action')}:** {T(action)}")

    st.divider()
    with st.expander(f"🔬 {T('Acoustic Pest Science — 8 Classes')}"):
        data = {
            T('Pest / Condition'): list(PEST_META.keys()),
            T('Frequency Range'):  [m['freq_range'] for m in PEST_META.values()],
            T('Pattern'):          [m['pattern']    for m in PEST_META.values()],
            T('Risk'):             [m['severity'].upper() for m in PEST_META.values()],
        }
        st.table(pd.DataFrame(data))
