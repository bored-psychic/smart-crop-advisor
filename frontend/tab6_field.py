import streamlit as st
import asyncio
import datetime
from frontend.api_client import APIClient
from core.language import T


def render():
    st.markdown(f"### 🛰️ {T('Field Watch — Satellite Intelligence')}")
    st.markdown(T("Live satellite weather, wildfire alerts, flood warnings, locust swarm data, and air quality — all in one place."))

    fw_city = st.text_input(T("Your City / Nearest Town"), placeholder="e.g. Bellary, Nagpur, Warangal", key="fw_city")

    col_a, col_b = st.columns(2)
    with col_a:
        farmer_name_fw = st.text_input(T("Farmer Name"), value=st.session_state.get('farmer_name', ''), key="fw_name")
    with col_b:
        farmer_crop_fw = st.text_input(T("Your Crop"), value=st.session_state.get('farmer_crop', ''), key="fw_crop")

    if st.button(f"🛰️ {T('Scan My Field Now')}", use_container_width=True, type="primary", key="fw_scan"):
        if not fw_city.strip():
            st.error(T("Please enter your city name."))
        else:
            with st.spinner(T("Fetching satellite data, wildfire map, locust feed, weather forecast...")):
                fw_result = asyncio.run(APIClient.get_field_watch(fw_city.strip()))
            if fw_result:
                st.session_state['fw_result'] = fw_result
            else:
                st.error(T("Field Watch API unavailable. Check backend connection."))

    if 'fw_result' in st.session_state:
        fw = st.session_state['fw_result']

        fire_risk   = fw.get('fire',  {}).get('risk',        'NONE')
        flood_risk  = fw.get('flood', {}).get('flood_risk',  'LOW')
        locust_risk = fw.get('locust',{}).get('risk',        'NONE')

        if 'HIGH' in [fire_risk, flood_risk, locust_risk]:
            overall = 'HIGH';   badge_col = '#EF4444'
        elif 'MEDIUM' in [fire_risk, flood_risk, locust_risk]:
            overall = 'MEDIUM'; badge_col = '#F59E0B'
        else:
            overall = 'LOW';    badge_col = '#22C55E'

        st.markdown(f"""
        <div style="background:{badge_col}18;border:1px solid {badge_col}40;border-radius:12px;
                    padding:14px 18px;margin-bottom:16px;display:flex;align-items:center;gap:12px">
          <div style="font-size:2rem">{"🚨" if overall=="HIGH" else "⚠️" if overall=="MEDIUM" else "✅"}</div>
          <div>
            <div style="font-size:13px;font-weight:700;color:{badge_col}">{T("Overall Field Risk")}: {overall}</div>
            <div style="font-size:12px;color:#9ca3af">{fw_city} · {T("Live satellite scan")}</div>
          </div>
        </div>""", unsafe_allow_html=True)

        w = fw.get('weather')
        if w:
            st.markdown(f"#### 🌤️ {T('Current Weather')}")
            wc1, wc2, wc3, wc4 = st.columns(4)
            wc1.metric(T("Temperature"),   f"{w['temp']}°C",     f"{T('feels')} {w['feels_like']}°C")
            wc2.metric(T("Humidity"),       f"{w['humidity']}%")
            wc3.metric(T("Wind"),           f"{w['wind']} km/h")
            wc4.metric(T("Rain 1h"),        f"{w['rain_1h']} mm")
            st.caption(f"☁️ {w['desc']} · 📍 {fw_city}")

        fl = fw.get('flood')
        if fl:
            st.markdown(f"#### 🌊 {T('Flood Risk (Next 48 hours)')}")
            flr = fl['flood_risk']
            flood_msg = {
                'HIGH':   T("DANGER: Heavy rainfall forecast >50mm. Create field bunds immediately. Move low-lying crops to safer areas. Contact district agriculture office."),
                'MEDIUM': T("CAUTION: Moderate rainfall expected 25–50mm. Monitor drainage channels. Avoid fertilizer application. Prepare bunds."),
                'LOW':    T("LOW RISK: Rainfall <25mm forecast. Normal field operations permitted."),
            }.get(flr, '')
            if flr == 'HIGH':
                st.error(f"🌊 **{T('Flood Risk')}: {flr}** — {fl['rain_48h']}mm {T('forecast')}\n\n{flood_msg}")
            elif flr == 'MEDIUM':
                st.warning(f"🌊 **{T('Flood Risk')}: {flr}** — {fl['rain_48h']}mm {T('forecast')}\n\n{flood_msg}")
            else:
                st.success(f"✅ **{T('Flood Risk')}: {flr}** — {fl['rain_48h']}mm {T('forecast')}\n\n{flood_msg}")

        fire = fw.get('fire')
        if fire:
            st.markdown(f"#### 🔥 {T('Wildfire / Field Fire Alert')} — NASA FIRMS")
            hs = fire['hotspots_nearby']
            fr = fire['risk']
            fire_msg = {
                'HIGH':    T("DANGER: Multiple fire hotspots detected near your location. Evacuate field perimeter. Contact fire brigade: 101. Protect stored crops."),
                'MEDIUM':  T("WARNING: Fire hotspots detected within 220km. Monitor wind direction. Keep water pumps ready."),
                'NONE':    T("No active fire hotspots detected within 220km of your location."),
                'UNKNOWN': T("Fire data temporarily unavailable."),
            }.get(fr, T("Fire data unavailable."))
            if fr == 'HIGH':
                st.error(f"🔥 **{T('Wildfire Risk')}: HIGH** — {hs} {T('hotspots')}\n\n{fire_msg}")
            elif fr == 'MEDIUM':
                st.warning(f"🔥 **{T('Wildfire Risk')}: MEDIUM** — {hs} {T('hotspot(s)')}\n\n{fire_msg}")
            else:
                st.success(f"✅ **{T('No Wildfire Risk')}** — {fire_msg}")
            st.caption(f"📡 {T('Source')}: {fire['source']}")

        loc = fw.get('locust')
        if loc:
            st.markdown(f"#### 🦗 {T('Desert Locust Alert')} — FAO")
            lr = loc['risk']
            sw = loc['swarms_nearby']
            loc_msg = {
                'HIGH':    T("DANGER: Active locust swarms detected near your location. Contact State Agriculture Dept: 1800-180-1551. Spray Chlorpyrifos 50% EC @ 2ml/L."),
                'MEDIUM':  T("WARNING: Locust swarms detected within 500km. Stay alert. Apply preventive border spraying."),
                'NONE':    T("No active locust swarms detected in your region."),
                'UNKNOWN': T("Locust data temporarily unavailable. Monitor IMD advisories."),
            }.get(lr, T("Locust data unavailable."))
            if lr == 'HIGH':
                st.error(f"🦗 **{T('Locust Risk')}: HIGH** — {sw} {T('swarms')}\n\n{loc_msg}")
            elif lr == 'MEDIUM':
                st.warning(f"🦗 **{T('Locust Risk')}: MEDIUM** — {sw} {T('swarm(s)')}\n\n{loc_msg}")
            else:
                st.success(f"✅ **{T('No Locust Risk')}** — {loc_msg}")
            st.caption(f"📡 {T('Source')}: {loc['source']}")

        aqi = fw.get('aqi')
        if aqi:
            aqi_color = {1:'#22C55E',2:'#86efac',3:'#F59E0B',4:'#EF4444',5:'#7f1d1d'}.get(aqi['value'], '#6B8F6B')
            st.markdown(f"""
            <div style="background:{aqi_color}18;border:1px solid {aqi_color}40;border-radius:10px;
                        padding:12px 16px;margin-top:12px">
              <span style="font-size:12px;font-weight:600;color:{aqi_color}">
                💨 {T("Air Quality")}: {aqi['label']} (AQI {aqi['value']}/5)
              </span>
            </div>""", unsafe_allow_html=True)

        st.divider()
        st.markdown(f"#### 📞 {T('Emergency Helplines')}")
        helplines = [
            ("🌾 Kisan Helpline",  "18001801551", T("Free · 24/7 · All languages")),
            ("🌊 NDRF Emergency",  "1078",        T("Flood / Earthquake / Disaster")),
            ("🔥 Fire Brigade",    "101",         T("Field fire emergency")),
            ("🚑 Ambulance",       "108",         T("Medical emergency in field")),
            ("👮 Police",          "100",         T("Crop theft / trespass")),
        ]
        for name_h, num_h, note_h in helplines:
            c_a, c_b = st.columns([3, 1])
            with c_a:
                st.markdown(f"**{name_h}** — {note_h}")
            with c_b:
                st.markdown(f"[📞 {num_h}](tel:{num_h})")
