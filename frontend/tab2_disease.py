import streamlit as st
from PIL import Image as PILImage
from frontend.api_client import APIClient, run_async
from frontend.ui_helpers import card, page_hero
from core.language import T
from core.disease_db import DISEASE_DB

SEVERITY_BG   = {'High': '#EF4444', 'Medium': '#F59E0B', 'Low': '#22C55E'}
SEVERITY_ICON = {'High': '🔴', 'Medium': '🟡', 'Low': '🟢'}
TYPE_ICON     = {'Disease': '🦠', 'Pest': '🐛'}


@st.cache_data(ttl=3600)
def _sorted_crops() -> list[str]:
    return sorted(DISEASE_DB.keys())


@st.cache_data(ttl=3600)
def _crop_items(crop: str) -> list[tuple]:
    return list(DISEASE_DB[crop].items())


def render():
    page_hero("LEAF DOCTOR", "See what your leaves", "are trying to say.", "Upload a photo. Claude reads the signs — spots, yellowing, lesions — before the damage spreads.")

    st.markdown(f"#### 📸 {T('Method 1 — Photo Diagnosis (Recommended)')}")

    _all_crops_d = _sorted_crops()
    selected_crop_v = st.selectbox(f"🌱 {T('Select Crop for Diagnosis')}", _all_crops_d, key="v2_crop")

    vision_file = st.file_uploader(
        T("Upload leaf / stem / fruit photo"),
        type=["jpg", "jpeg", "png", "webp"],
        key="tab2_vision_upload",
        help=T("Clear daylight photo, close-up of affected area.")
    )

    if vision_file is not None:
        v_img = PILImage.open(vision_file)
        col_v1, col_v2 = st.columns([1, 1])
        with col_v1:
            st.image(v_img, caption=T("Uploaded photo"), use_container_width=True)
        with col_v2:
            st.markdown(f"**{T('File')}:** `{vision_file.name}`")
            st.markdown(f"**{T('Dimensions')}:** {v_img.width}×{v_img.height}px")
            st.info(f"☀️ {T('Daylight')} · 🎯 {T('Close-up on affected area')} · 📷 {T('Sharp, no blur')}")

        if st.button(f"🔍 {T('Diagnose from Photo')}", use_container_width=True, type="primary", key="tab2_vision_btn"):
            with st.spinner("▶ Claude Vision scanning plant tissue..."):
                img_bytes = vision_file.getvalue()
                vr = run_async(APIClient.diagnose_vision(img_bytes, crop_type=selected_crop_v))
            if vr:
                st.session_state['tab2_vision_result'] = vr
            else:
                card(T("Vision API unavailable. Check backend connection."), severity="error")

    if 'tab2_vision_result' in st.session_state:
        vr = st.session_state['tab2_vision_result']
        model_badge = vr.get('model_used', 'Vision AI')
        st.markdown(
            f'<span style="background:rgba(34,197,94,0.12);color:#4ADE80;padding:3px 12px;'
            f'border-radius:20px;font-size:11px;font-weight:600;font-family:JetBrains Mono,monospace;'
            f'border:1px solid rgba(34,197,94,0.3);">&#128247; {model_badge}</span>',
            unsafe_allow_html=True)
        st.markdown("")

        _sev   = vr.get('severity', 'Medium')
        _smap  = {"High": "error", "Medium": "warning", "Low": "success", "None": "success"}
        _conf  = vr.get('confidence', 0)
        _icons = {"High": "&#128308;", "Medium": "&#128993;", "Low": "&#128994;", "None": "&#128994;"}
        card(f"""
        <div style='font-family:Space Grotesk,sans-serif;'>
          <div style='font-size:1.3rem;font-weight:700;color:#2A3328;margin-bottom:3px;'>
            {_icons.get(_sev,'&#9888;')}&nbsp;{T(vr['disease'])}
          </div>
          <div style='font-family:JetBrains Mono,monospace;font-size:0.72rem;color:#3E6B3E;margin-bottom:12px;'>
            {T('confidence')} &middot; {_conf}%
          </div>
          <div style='font-size:0.88rem;color:#2A3328;margin-bottom:6px;'>
            <b style='color:#3E6B3E;'>&#128138; {T('Treatment')}:</b> {T(vr['treatment'])}
          </div>
          <div style='font-size:0.88rem;color:#2A3328;margin-bottom:6px;'>
            <b style='color:#3E6B3E;'>&#128737; {T('Prevention')}:</b> {T(vr['prevention'])}
          </div>
          <div style='font-size:0.8rem;color:#1A2E1A;font-family:JetBrains Mono,monospace;'>
            &#9889; {T(vr['action'])}
          </div>
        </div>
        """, severity=_smap.get(_sev, "warning"))
        st.progress(_conf / 100)

    st.divider()
    st.markdown(f"#### 🔬 {T('Method 2 — Symptom / Pest Checker')}")
    st.caption(T("Covers diseases AND pests. All crops included."))

    fcol1, fcol2, fcol3 = st.columns([2, 1, 1])
    with fcol1:
        selected_crop = st.selectbox(f"🌱 {T('Crop')}", _sorted_crops(), key="symp_crop")
    with fcol2:
        filter_type = st.selectbox(T("Type"), ["All", "Disease", "Pest"], key="symp_type")
    with fcol3:
        filter_sev = st.selectbox(T("Severity"), ["All", "High", "Medium", "Low"], key="symp_sev")

    all_items = list(_crop_items(selected_crop))
    if filter_type != "All":
        all_items = [(s, d) for s, d in all_items if d.get('type', 'Disease') == filter_type]
    if filter_sev != "All":
        all_items = [(s, d) for s, d in all_items if d['severity'] == filter_sev]

    if not all_items:
        st.info(T("No entries match the selected filters."))
    else:
        symptoms_filtered = [s for s, _ in all_items]
        selected_symptom = st.selectbox(f"🔍 {T('Symptom observed')}", symptoms_filtered, key="symp_symptom")

        cols = st.columns(min(len(all_items), 3))
        for i, (symptom, data) in enumerate(all_items):
            with cols[i % 3]:
                color = SEVERITY_BG[data['severity']]
                icon  = SEVERITY_ICON[data['severity']]
                ticon = TYPE_ICON.get(data.get('type', 'Disease'), '🦠')
                is_selected = (symptom == selected_symptom)
                bg_alpha    = "30" if is_selected else "15"
                border_w    = "4px" if is_selected else "3px"
                glow        = f"box-shadow:0 0 14px {color}aa;" if is_selected else ""
                sel_badge   = (
                    f'<div style="display:inline-block;background:{color};color:#0a0a0a;'
                    'font-size:9px;font-weight:700;letter-spacing:.6px;'
                    'padding:1px 6px;border-radius:4px;margin-bottom:4px;">'
                    '▼ SELECTED</div>'
                ) if is_selected else ''
                st.markdown(f"""
                <div style="background:{color}{bg_alpha};border-left:{border_w} solid {color};border-radius:8px;
                            padding:10px;margin-bottom:8px;min-height:90px;{glow}">
                  {sel_badge}
                  <div style="font-size:12px;font-weight:600;color:{color}">{icon} {ticon} {data['disease']}</div>
                  <div style="font-size:10px;color:#9ca3af;margin-top:3px">{symptom[:55]}{'...' if len(symptom)>55 else ''}</div>
                  <div style="font-size:10px;color:{color};margin-top:3px;font-weight:600">{data.get('type','Disease')} · {data['severity']}</div>
                </div>""", unsafe_allow_html=True)

        if st.button(f"🔬 {T('Diagnose by Symptom / Pest')}", use_container_width=True, type="primary", key="symp_diagnose_btn"):
            with st.spinner(T("Consulting the Swarm...")):
                api_res = run_async(APIClient.diagnose_symptom(selected_crop, selected_symptom))
            if api_res:
                st.session_state['tab2_symp_result'] = {
                    'disease': {
                        'disease':   api_res['disease'],
                        'severity':  api_res['severity'],
                        'type':      api_res['disease_type'],
                        'treatment': api_res['treatment'],
                        'prevention': api_res['prevention'],
                    },
                    'crop': api_res['crop'], 'symptom': api_res['symptom'],
                }
            else:
                st.session_state['tab2_symp_result'] = {
                    'disease': DISEASE_DB[selected_crop][selected_symptom],
                    'crop': selected_crop, 'symptom': selected_symptom,
                }

    if 'tab2_symp_result' in st.session_state:
        result   = st.session_state['tab2_symp_result']['disease']
        severity = result['severity']
        dtype    = result.get('type', 'Disease')
        dicon    = TYPE_ICON.get(dtype, '🦠')
        _smap2   = {"High": "error", "Medium": "warning", "Low": "info"}
        _slabels = {
            "High":   T("HIGH &#8212; Act immediately!"),
            "Medium": T("MEDIUM &#8212; Monitor closely"),
            "Low":    T("LOW &#8212; Manageable"),
        }
        card(f"""
        <div style='font-family:Space Grotesk,sans-serif;'>
          <div style='font-size:1.2rem;font-weight:700;color:#2A3328;margin-bottom:3px;'>
            {dicon} {T(result['disease'])}
          </div>
          <div style='font-family:JetBrains Mono,monospace;font-size:0.72rem;color:#3E6B3E;margin-bottom:12px;'>
            severity &middot; {_slabels.get(severity, severity)}
          </div>
          <div style='font-size:0.88rem;color:#2A3328;margin-bottom:6px;'>
            <b style='color:#3E6B3E;'>&#128138; {T('Treatment')}:</b> {T(result['treatment'])}
          </div>
          <div style='font-size:0.88rem;color:#2A3328;'>
            <b style='color:#3E6B3E;'>&#128737; {T('Prevention')}:</b> {T(result['prevention'])}
          </div>
        </div>
        """, severity=_smap2.get(severity, "info"))

    st.divider()
    st.caption(T("Vision AI: disease_model.tflite/h5 when TensorFlow available · 26+ crops · 50+ diseases & pests"))
