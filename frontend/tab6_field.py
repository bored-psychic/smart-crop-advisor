import streamlit as st
import datetime
import urllib.parse
from frontend.api_client import APIClient, run_async
from frontend.ui_helpers import card, page_hero
from core.language import T


def render():
    page_hero("FIELD WATCH", "Your land, seen", "from above.", "Live satellite weather, wildfire alerts, flood warnings, locust data, and air quality — all in one place.")

    _default_city = st.session_state.get('farmer_village', '').split(',')[0].strip()
    fw_city = st.text_input(T("Your City / Nearest Town"), value=_default_city, placeholder="e.g. Bellary, Nagpur, Warangal", key="fw_city")

    if st.button(f"🛰️ {T('Scan My Field Now')}", use_container_width=True, type="primary", key="fw_scan"):
        if not fw_city.strip():
            st.error(T("Please enter your city name."))
        else:
            with st.spinner(T("Fetching satellite data, wildfire map, locust feed, weather forecast...")):
                try:
                    fw_result = run_async(APIClient.get_field_watch(fw_city.strip()))
                except Exception:
                    fw_result = None
            if fw_result:
                st.session_state['fw_result'] = fw_result
            else:
                card(T("Field Watch request timed out or backend is unavailable. Please try again."), severity="error")

    if 'fw_result' in st.session_state:
        fw = st.session_state['fw_result']

        fire_risk   = (fw.get('fire')   or {}).get('risk',       'NONE')
        flood_risk  = (fw.get('flood')  or {}).get('flood_risk', 'LOW')
        locust_risk = (fw.get('locust') or {}).get('risk',       'NONE')

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
            st.caption(f"☁️ {w['description']} · 📍 {fw_city}")

        fl = fw.get('flood')
        if fl:
            st.markdown(f"#### 🌊 {T('Flood Risk (Next 48 hours)')}")
            flr = fl['flood_risk']
            flood_msg = {
                'HIGH':   T("DANGER: Heavy rainfall forecast >50mm. Create field bunds immediately. Move low-lying crops to safer areas. Contact district agriculture office."),
                'MEDIUM': T("CAUTION: Moderate rainfall expected 25–50mm. Monitor drainage channels. Avoid fertilizer application. Prepare bunds."),
                'LOW':    T("LOW RISK: Rainfall <25mm forecast. Normal field operations permitted."),
            }.get(flr, '')
            _fsmap = {'HIGH': 'error', 'MEDIUM': 'warning', 'LOW': 'success'}
            card(f"<b>&#127754; {T('Flood Risk')}: {flr}</b> &#8212; {fl['rain_48h']}mm {T('forecast')}<br><span style='font-size:0.88rem;'>{flood_msg}</span>", severity=_fsmap.get(flr, 'info'))

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
            _frsmap = {'HIGH': 'error', 'MEDIUM': 'warning'}
            _frlabel = '&#128293; ' + (f"<b>{T('Wildfire Risk')}: {fr}</b> &#8212; {hs} {T('hotspots')}" if fr in ('HIGH','MEDIUM') else f"<b>{T('No Wildfire Risk')}</b>")
            card(f"{_frlabel}<br><span style='font-size:0.88rem;'>{fire_msg}</span>", severity=_frsmap.get(fr, 'success'))
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
            _lsmap = {'HIGH': 'error', 'MEDIUM': 'warning'}
            _llabel = '&#129431; ' + (f"<b>{T('Locust Risk')}: {lr}</b> &#8212; {sw} {T('swarms')}" if lr in ('HIGH','MEDIUM') else f"<b>{T('No Locust Risk')}</b>")
            card(f"{_llabel}<br><span style='font-size:0.88rem;'>{loc_msg}</span>", severity=_lsmap.get(lr, 'success'))
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

        st.divider()
        st.markdown(f"#### 📤 {T('Send Field Alert to WhatsApp')}")

        _name    = st.session_state.get('farmer_name', '') or T('Farmer')
        _crop    = st.session_state.get('farmer_crop', '') or T('Crop')
        _village = st.session_state.get('farmer_village', '') or fw_city
        _ts      = datetime.datetime.now().strftime('%d %b %Y, %I:%M %p')
        _fire_s  = f"🔥 {T('Wildfire')}: {(fw.get('fire') or {}).get('risk','?')} ({(fw.get('fire') or {}).get('hotspots_nearby',0)} {T('hotspots')})"
        _flood_s = f"🌊 {T('Flood')}: {(fw.get('flood') or {}).get('flood_risk','?')} ({(fw.get('flood') or {}).get('rain_48h',0)}mm)"
        _loc_s   = f"🦗 {T('Locust')}: {(fw.get('locust') or {}).get('risk','?')} ({(fw.get('locust') or {}).get('swarms_nearby',0)} {T('swarms')})"

        wa_msg = (
            f"🛰️ *Field Watch Alert — KisanOS*\n\n"
            f"Farmer: *{_name}*\nCrop: {_crop}\nLocation: {_village}\nTime: {_ts}\n\n"
            f"*Overall Risk: {overall}*\n\n"
            f"{_fire_s}\n{_flood_s}\n{_loc_s}\n\n"
            f"Generated by KisanOS Field Watch · NASA FIRMS · FAO · OpenWeatherMap"
        )
        _encoded = urllib.parse.quote(wa_msg)

        _profile_phone = st.session_state.get('farmer_phone', '').strip()
        _extra = st.text_input(T("Additional number (with 91)"), placeholder="e.g. 919876543210", key="fw_extra_num")

        _numbers = [n for n in [_profile_phone, _extra.strip()] if n]
        if _numbers:
            for _num in _numbers:
                _wa_link = f"https://wa.me/{_num}?text={_encoded}"
                st.markdown(
                    f'<a href="{_wa_link}" target="_blank" style="display:inline-flex;align-items:center;gap:8px;'
                    f'background:#25D366;color:white;text-decoration:none;padding:10px 18px;border-radius:10px;'
                    f'font-weight:600;font-size:13px;margin:4px 0;width:100%;justify-content:center">'
                    f'📲 {T("Send Alert to")} {_num}</a>',
                    unsafe_allow_html=True
                )
        else:
            card(T("Add your WhatsApp number in the sidebar profile to send alerts."), severity="info")
