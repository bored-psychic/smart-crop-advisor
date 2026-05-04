import streamlit as st
import asyncio
from PIL import Image as PILImage
from frontend.api_client import APIClient
from frontend.ui_helpers import card, page_hero
from core.language import T

DISEASE_DB = {
    'Tomato': {
        'Yellow leaves + brown spots': {'disease': 'Early Blight (Alternaria solani)', 'treatment': 'Mancozeb 75% WP @ 2g/L. Remove infected leaves. Repeat after 10 days.', 'prevention': 'Crop rotation every 2 years. Use resistant varieties.', 'severity': 'Medium', 'type': 'Disease'},
        'Dark brown patches + white mold undersides': {'disease': 'Late Blight (Phytophthora infestans)', 'treatment': 'Metalaxyl + Mancozeb @ 2g/L immediately. Destroy infected plants.', 'prevention': 'Avoid overhead irrigation. Certified disease-free seeds.', 'severity': 'High', 'type': 'Disease'},
        'Curling yellow leaves + stunted growth': {'disease': 'Tomato Yellow Leaf Curl Virus', 'treatment': 'No cure. Remove infected plants immediately.', 'prevention': 'Control whitefly. Silver reflective mulch.', 'severity': 'High', 'type': 'Disease'},
        'Small dark spots with yellow halo': {'disease': 'Bacterial Spot (Xanthomonas)', 'treatment': 'Copper hydroxide @ 3g/L every 7 days.', 'prevention': 'Disease-free transplants. Avoid wet fieldwork.', 'severity': 'Medium', 'type': 'Disease'},
        'White powdery coating on leaves': {'disease': 'Powdery Mildew (Leveillula taurica)', 'treatment': 'Sulphur 80% WP @ 2g/L or Hexaconazole.', 'prevention': 'Improve air circulation. Avoid excess nitrogen.', 'severity': 'Low', 'type': 'Disease'},
        'Tiny white flying insects under leaves': {'disease': 'Whitefly (Bemisia tabaci)', 'treatment': 'Buprofezin 25 SC @ 1.0 L/ha. Neem oil 0.5%.', 'prevention': 'Yellow sticky traps. Silver reflective mulch.', 'severity': 'Medium', 'type': 'Pest'},
    },
    'Potato': {
        'Brown lesions with yellow border on leaves': {'disease': 'Early Blight (Alternaria solani)', 'treatment': 'Chlorothalonil @ 2g/L. Repeat every 10 days.', 'prevention': 'Certified seed tubers. Crop rotation.', 'severity': 'Medium', 'type': 'Disease'},
        'Water-soaked dark patches spreading fast': {'disease': 'Late Blight (Phytophthora infestans)', 'treatment': 'Cymoxanil + Mancozeb urgently. Destroy infected haulms.', 'prevention': 'Well-drained soil. Monitor weather.', 'severity': 'High', 'type': 'Disease'},
        'Yellowing from bottom leaves upward': {'disease': 'Potato Virus Y (PVY)', 'treatment': 'No cure. Rogue out infected plants.', 'prevention': 'Virus-free seed. Control aphid vectors.', 'severity': 'High', 'type': 'Disease'},
    },
    'Rice': {
        'Diamond-shaped lesions with grey center': {'disease': 'Rice Blast (Magnaporthe oryzae)', 'treatment': 'Tricyclazole 75% WP @ 0.6g/L at booting stage.', 'prevention': 'Blast-resistant varieties. Avoid excess nitrogen.', 'severity': 'High', 'type': 'Disease'},
        'Yellow-orange stripes on leaf margins': {'disease': 'Bacterial Leaf Blight (Xanthomonas oryzae)', 'treatment': 'Copper-based bactericide. Drain fields temporarily.', 'prevention': 'Resistant varieties. Balanced fertilization.', 'severity': 'High', 'type': 'Disease'},
        'Brown spots with yellow halo': {'disease': 'Brown Spot (Cochliobolus miyabeanus)', 'treatment': 'Mancozeb or Iprodione fungicide.', 'prevention': 'Balanced K nutrition. Healthy seeds.', 'severity': 'Medium', 'type': 'Disease'},
        'Dead heart / wilting tillers': {'disease': 'Yellow Stem Borer (Scirpophaga incertulas)', 'treatment': 'Cartap Hydrochloride 4G @ 12-15 kg/ha.', 'prevention': 'Pheromone traps. Avoid excess nitrogen.', 'severity': 'High', 'type': 'Pest'},
    },
    'Maize': {
        'Orange powdery pustules on leaves': {'disease': 'Common Rust (Puccinia sorghi)', 'treatment': 'Mancozeb or Azoxystrobin @ 1ml/L.', 'prevention': 'Rust-resistant hybrids. Early planting.', 'severity': 'Medium', 'type': 'Disease'},
        'Long grey-green lesions on leaves': {'disease': 'Northern Leaf Blight (Exserohilum turcicum)', 'treatment': 'Propiconazole fungicide at early stage.', 'prevention': 'Resistant varieties. Crop rotation.', 'severity': 'Medium', 'type': 'Disease'},
        'Ragged leaf feeding + frass in whorl': {'disease': 'Fall Armyworm (Spodoptera frugiperda)', 'treatment': 'Chlorantraniliprole 18.5 SC @ 0.4ml/L.', 'prevention': 'Pheromone traps. Early sowing.', 'severity': 'High', 'type': 'Pest'},
    },
    'Wheat': {
        'Yellow stripes along leaf veins': {'disease': 'Yellow/Stripe Rust (Puccinia striiformis)', 'treatment': 'Propiconazole 25% EC @ 1ml/L urgently.', 'prevention': 'Resistant varieties. Early sowing.', 'severity': 'High', 'type': 'Disease'},
        'Orange-brown pustules scattered on leaves': {'disease': 'Brown/Leaf Rust (Puccinia triticina)', 'treatment': 'Tebuconazole or Propiconazole fungicide.', 'prevention': 'Balanced nitrogen. Tolerant varieties.', 'severity': 'Medium', 'type': 'Disease'},
        'Black powdery pustules on stems': {'disease': 'Stem/Black Rust (Puccinia graminis)', 'treatment': 'Mancozeb + Propiconazole immediately.', 'prevention': 'Ug99-resistant varieties. Early detection critical.', 'severity': 'High', 'type': 'Disease'},
    },
    'Cotton': {
        'Wilting + internal stem discoloration': {'disease': 'Fusarium Wilt (Fusarium oxysporum)', 'treatment': 'No cure. Remove infected plants. Soil solarization.', 'prevention': 'Wilt-resistant varieties. Crop rotation.', 'severity': 'High', 'type': 'Disease'},
        'Pink larvae inside bolls': {'disease': 'Pink Bollworm (Pectinophora gossypiella)', 'treatment': 'Chlorpyrifos 50% + Cypermethrin 5% EC @ 2ml/L.', 'prevention': 'Destroy crop residue. Pheromone traps early.', 'severity': 'High', 'type': 'Pest'},
        'Small greenish insects on tender shoots': {'disease': 'Cotton Aphid (Aphis gossypii)', 'treatment': 'Acetamiprid 20 SP @ 50g/ha or Imidacloprid 17.8 SL @ 100ml/ha.', 'prevention': 'Natural enemies (ladybird beetles). Avoid excess nitrogen.', 'severity': 'Medium', 'type': 'Pest'},
    },
    'Banana': {
        'Yellow streaks on young leaves': {'disease': 'Banana Bunchy Top Virus (BBTV)', 'treatment': 'No cure. Destroy infected plants immediately.', 'prevention': 'Virus-free tissue culture plants. Control aphids.', 'severity': 'High', 'type': 'Disease'},
        'Black streaks inside stem + wilting': {'disease': 'Panama Wilt / Fusarium Wilt', 'treatment': 'No chemical cure. Destroy infected plants.', 'prevention': 'Resistant varieties. Clean tools between plants.', 'severity': 'High', 'type': 'Disease'},
    },
    'Chickpea': {
        'Wilting + brown discoloration at soil level': {'disease': 'Fusarium Wilt (Fusarium oxysporum f.sp. ciceri)', 'treatment': 'Seed treatment with Carbendazim 2g/kg. Trichoderma application.', 'prevention': 'Resistant varieties. Deep summer ploughing.', 'severity': 'High', 'type': 'Disease'},
        'Greenish caterpillar boring into pods': {'disease': 'Gram Pod Borer (Helicoverpa armigera)', 'treatment': 'Indoxacarb 14.5 SC @ 1ml/L or Quinalphos 25 EC @ 2 L/ha.', 'prevention': 'Pheromone traps. Intercropping with coriander.', 'severity': 'High', 'type': 'Pest'},
    },
    'Mango': {
        'Mummified blackened inflorescences': {'disease': 'Mango Malformation (Fusarium mangiferae)', 'treatment': 'Remove and destroy malformed parts. NAA spray 200ppm.', 'prevention': 'Avoid injury. Certified nursery plants.', 'severity': 'High', 'type': 'Disease'},
        'Maggot in fruit (puncture marks on skin)': {'disease': 'Fruit Fly (Bactrocera dorsalis)', 'treatment': 'Methyl eugenol traps 5-6 per acre. Spinosad 45 SC @ 0.4ml/L.', 'prevention': 'Collect and destroy fallen fruit daily.', 'severity': 'High', 'type': 'Pest'},
    },
    'Apple': {
        'Olive-green scab on leaves and fruit': {'disease': 'Apple Scab (Venturia inaequalis)', 'treatment': 'Captan 50% WP @ 2g/L or Myclobutanil from bud break.', 'prevention': 'Resistant varieties. Remove fallen leaves.', 'severity': 'Medium', 'type': 'Disease'},
        'Brown/black cankers on fruit': {'disease': 'Apple Black Rot (Botryosphaeria obtusa)', 'treatment': 'Captan or Thiophanate-methyl @ 2g/L.', 'prevention': 'Prune infected branches. Remove mummified fruit.', 'severity': 'High', 'type': 'Disease'},
    },
    'Grape': {
        'Downy white growth on leaf undersides': {'disease': 'Downy Mildew (Plasmopara viticola)', 'treatment': 'Fosetyl-Al 80 WP @ 2.5g/L or Metalaxyl + Mancozeb @ 2g/L.', 'prevention': 'Prune for airflow. Spray preventively before rains.', 'severity': 'High', 'type': 'Disease'},
        'Powdery white coating on young shoots/berries': {'disease': 'Powdery Mildew (Uncinula necator)', 'treatment': 'Sulphur 80 WP @ 3g/L or Hexaconazole 5 EC @ 1ml/L.', 'prevention': 'Prune dense canopy. Avoid excess nitrogen.', 'severity': 'Medium', 'type': 'Disease'},
    },
}

SEVERITY_BG   = {'High': '#EF4444', 'Medium': '#F59E0B', 'Low': '#22C55E'}
SEVERITY_ICON = {'High': '🔴', 'Medium': '🟡', 'Low': '🟢'}
TYPE_ICON     = {'Disease': '🦠', 'Pest': '🐛'}


def render():
    page_hero("LEAF DOCTOR", "See what your leaves", "are trying to say.", "Upload a photo. Claude reads the signs — spots, yellowing, lesions — before the damage spreads.")

    st.markdown(f"#### 📸 {T('Method 1 — Photo Diagnosis (Recommended)')}")

    _all_crops_d = sorted(DISEASE_DB.keys())
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
            st.image(v_img, caption=T("Uploaded photo"), use_column_width=True)
        with col_v2:
            st.markdown(f"**{T('File')}:** `{vision_file.name}`")
            st.markdown(f"**{T('Dimensions')}:** {v_img.width}×{v_img.height}px")
            st.info(f"☀️ {T('Daylight')} · 🎯 {T('Close-up on affected area')} · 📷 {T('Sharp, no blur')}")

        if st.button(f"🔍 {T('Diagnose from Photo')}", use_container_width=True, type="primary", key="tab2_vision_btn"):
            with st.spinner("▶ Claude Vision scanning plant tissue..."):
                img_bytes = vision_file.getvalue()
                vr = asyncio.run(APIClient.diagnose_vision(img_bytes, crop_type=selected_crop_v))
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
          <div style='font-size:1.3rem;font-weight:700;color:#E2F5DF;margin-bottom:3px;'>
            {_icons.get(_sev,'&#9888;')}&nbsp;{T(vr['disease'])}
          </div>
          <div style='font-family:JetBrains Mono,monospace;font-size:0.72rem;color:#4ADE80;margin-bottom:12px;'>
            {T('confidence')} &middot; {_conf}%
          </div>
          <div style='font-size:0.88rem;color:#E2F5DF;margin-bottom:6px;'>
            <b style='color:#22C55E;'>&#128138; {T('Treatment')}:</b> {T(vr['treatment'])}
          </div>
          <div style='font-size:0.88rem;color:#E2F5DF;margin-bottom:6px;'>
            <b style='color:#22C55E;'>&#128737; {T('Prevention')}:</b> {T(vr['prevention'])}
          </div>
          <div style='font-size:0.8rem;color:#4ADE80;font-family:JetBrains Mono,monospace;'>
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
        selected_crop = st.selectbox(f"🌱 {T('Crop')}", sorted(DISEASE_DB.keys()), key="symp_crop")
    with fcol2:
        filter_type = st.selectbox(T("Type"), ["All", "Disease", "Pest"], key="symp_type")
    with fcol3:
        filter_sev = st.selectbox(T("Severity"), ["All", "High", "Medium", "Low"], key="symp_sev")

    all_items = list(DISEASE_DB[selected_crop].items())
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
                st.markdown(f"""
                <div style="background:{color}15;border-left:3px solid {color};border-radius:8px;
                            padding:10px;margin-bottom:8px;min-height:90px;">
                  <div style="font-size:12px;font-weight:600;color:{color}">{icon} {ticon} {data['disease']}</div>
                  <div style="font-size:10px;color:#9ca3af;margin-top:3px">{symptom[:55]}{'...' if len(symptom)>55 else ''}</div>
                  <div style="font-size:10px;color:{color};margin-top:3px;font-weight:600">{data.get('type','Disease')} · {data['severity']}</div>
                </div>""", unsafe_allow_html=True)

        if st.button(f"🔬 {T('Diagnose by Symptom / Pest')}", use_container_width=True, type="primary", key="symp_diagnose_btn"):
            with st.spinner(T("Consulting the Swarm...")):
                api_res = asyncio.run(APIClient.diagnose_symptom(selected_crop, selected_symptom))
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
          <div style='font-size:1.2rem;font-weight:700;color:#E2F5DF;margin-bottom:3px;'>
            {dicon} {T(result['disease'])}
          </div>
          <div style='font-family:JetBrains Mono,monospace;font-size:0.72rem;color:#4ADE80;margin-bottom:12px;'>
            severity &middot; {_slabels.get(severity, severity)}
          </div>
          <div style='font-size:0.88rem;color:#E2F5DF;margin-bottom:6px;'>
            <b style='color:#22C55E;'>&#128138; {T('Treatment')}:</b> {T(result['treatment'])}
          </div>
          <div style='font-size:0.88rem;color:#E2F5DF;'>
            <b style='color:#22C55E;'>&#128737; {T('Prevention')}:</b> {T(result['prevention'])}
          </div>
        </div>
        """, severity=_smap2.get(severity, "info"))

    st.divider()
    st.caption(T("Vision AI: disease_model.tflite/h5 when TensorFlow available · 26+ crops · 50+ diseases & pests"))
