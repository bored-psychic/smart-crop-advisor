import streamlit as st
import time
import numpy as np
from frontend.api_client import APIClient, run_async
from frontend.ui_helpers import card, page_hero
from core.language import T

CROP_KC = {
    'Rice':        {'Initial': 1.05, 'Development': 1.20, 'Mid-season': 1.20, 'Late season': 0.90},
    'Wheat':       {'Initial': 0.30, 'Development': 0.70, 'Mid-season': 1.15, 'Late season': 0.25},
    'Maize':       {'Initial': 0.30, 'Development': 0.70, 'Mid-season': 1.20, 'Late season': 0.35},
    'Chickpea':    {'Initial': 0.40, 'Development': 0.70, 'Mid-season': 1.00, 'Late season': 0.35},
    'Kidneybeans': {'Initial': 0.40, 'Development': 0.70, 'Mid-season': 1.15, 'Late season': 0.30},
    'Pigeonpeas':  {'Initial': 0.40, 'Development': 0.70, 'Mid-season': 1.05, 'Late season': 0.55},
    'Mothbeans':   {'Initial': 0.35, 'Development': 0.65, 'Mid-season': 1.00, 'Late season': 0.30},
    'Mungbean':    {'Initial': 0.40, 'Development': 0.70, 'Mid-season': 1.05, 'Late season': 0.35},
    'Blackgram':   {'Initial': 0.40, 'Development': 0.70, 'Mid-season': 1.05, 'Late season': 0.35},
    'Lentil':      {'Initial': 0.40, 'Development': 0.70, 'Mid-season': 1.10, 'Late season': 0.30},
    'Pomegranate': {'Initial': 0.40, 'Development': 0.70, 'Mid-season': 1.05, 'Late season': 0.75},
    'Banana':      {'Initial': 0.50, 'Development': 0.90, 'Mid-season': 1.20, 'Late season': 1.10},
    'Mango':       {'Initial': 0.40, 'Development': 0.70, 'Mid-season': 1.00, 'Late season': 0.85},
    'Grapes':      {'Initial': 0.30, 'Development': 0.70, 'Mid-season': 0.85, 'Late season': 0.45},
    'Watermelon':  {'Initial': 0.40, 'Development': 0.75, 'Mid-season': 1.00, 'Late season': 0.75},
    'Muskmelon':   {'Initial': 0.40, 'Development': 0.75, 'Mid-season': 1.00, 'Late season': 0.75},
    'Apple':       {'Initial': 0.45, 'Development': 0.75, 'Mid-season': 1.10, 'Late season': 0.85},
    'Orange':      {'Initial': 0.60, 'Development': 0.70, 'Mid-season': 0.75, 'Late season': 0.70},
    'Papaya':      {'Initial': 0.40, 'Development': 0.80, 'Mid-season': 1.05, 'Late season': 0.90},
    'Coconut':     {'Initial': 0.90, 'Development': 1.00, 'Mid-season': 1.00, 'Late season': 1.00},
    'Cotton':      {'Initial': 0.35, 'Development': 0.70, 'Mid-season': 1.20, 'Late season': 0.50},
    'Jute':        {'Initial': 0.40, 'Development': 0.70, 'Mid-season': 1.15, 'Late season': 0.50},
    'Coffee':      {'Initial': 0.90, 'Development': 0.95, 'Mid-season': 1.05, 'Late season': 1.05},
}

FERTILIZER_SCHEDULE = {
    'Initial':     {'N': '30% of total N dose', 'tip': 'Apply basal dose of P and K fully at sowing.'},
    'Development': {'N': '30% of total N dose', 'tip': 'Top-dress with urea. Monitor leaf color.'},
    'Mid-season':  {'N': '40% of total N dose', 'tip': 'Final N top-dress. Avoid excess — causes lodging.'},
    'Late season': {'N': 'No N needed',          'tip': 'Stop fertilizing. Focus on pest monitoring.'},
}

CALAMITY_TIPS = {
    'thunderstorm': ['⚡ Move livestock to shelter', '🚫 Stop all field work immediately', '💧 Clear drainage channels'],
    'rain':         ['🌱 Avoid fertilizer — will wash away', '🌊 Create bunds around fields', '📞 Contact agriculture office if flooding'],
    'drizzle':      ['💧 Good for germination', '🌱 Ideal time for transplanting', '✅ Reduce irrigation today'],
    'snow':         ['🌿 Cover sensitive crops with cloth', '🔥 Light irrigation before frost protects roots', '🌱 Avoid pruning until frost passes'],
    'mist':         ['🍄 Watch for fungal disease', '💊 Apply preventive fungicide', '🌬️ Improve air circulation'],
    'haze':         ['😷 Reduce outdoor work', '💧 Increase irrigation — heat stress likely', '🌿 Monitor crops for wilting'],
    'clear':        ['☀️ Good day for spraying pesticides', '🚜 Ideal for harvesting', '💧 Check soil moisture levels'],
    'clouds':       ['🌤️ Good day for transplanting', '💧 Moderate irrigation needed', '🌱 Apply fertilizers today'],
}

WEATHER_CACHE_TTL_SECONDS = 300


def calculate_ET0(temp, humidity, wind_speed_kmh):
    wind_ms = wind_speed_kmh / 3.6
    es  = 0.6108 * np.exp(17.27 * temp / (temp + 237.3))
    ea  = es * humidity / 100
    vpd = max(es - ea, 0)
    ET0 = (0.408 * 0.0135 * (temp + 17.8) * (wind_ms + 1)) + (0.34 * vpd * wind_ms)
    return max(round(ET0, 2), 1.0)


def render():
    page_hero("WATERING", "Just enough water,", "just in time.", "We do the FAO water math behind the scenes and tell you simply: how many litres today, and when to water next.")

    st.markdown(f"#### 🌤️ {T('Live Weather (Auto-fill)')}")
    city = st.text_input(T("Enter your city name"), placeholder=T("e.g. Bengaluru, Pune, Hyderabad"), key="irr_city")
    weather_data = None
    city_clean = city.strip()
    if city_clean:
        cached_city = st.session_state.get('irr_weather_city')
        cached_data = st.session_state.get('irr_weather_data')
        cached_ts = st.session_state.get('irr_weather_ts')
        now_ts = time.time()
        city_changed = city_clean != cached_city
        cache_expired = (
            cached_ts is None
            or (now_ts - float(cached_ts)) >= WEATHER_CACHE_TTL_SECONDS
        )

        if city_changed or cache_expired:
            fresh_weather = run_async(APIClient.get_weather(city_clean))
            if fresh_weather:
                weather_data = fresh_weather
                st.session_state['irr_weather_city'] = city_clean
                st.session_state['irr_weather_data'] = fresh_weather
                st.session_state['irr_weather_ts'] = now_ts
            else:
                if city_clean == cached_city and cached_data:
                    weather_data = cached_data
                    st.warning(T("Live weather refresh failed. Showing last known data."))
                else:
                    weather_data = None
        else:
            weather_data = cached_data
        if weather_data:
            wc1, wc2, wc3, wc4 = st.columns(4)
            wc1.metric("🌡️ " + T("Temp"), f"{weather_data['temp']}°C")
            wc2.metric("💧 " + T("Humidity"), f"{weather_data['humidity']}%")
            wc3.metric("💨 " + T("Wind"), f"{weather_data.get('wind_speed', 0):.1f} km/h")
            wc4.metric("🌧️ " + T("Rain"), f"{weather_data.get('rainfall', 0)} mm")
            card(f"&#128205; {T('Live weather for')} <b>{weather_data['city']}</b>: {weather_data['description']}", severity="success")
            st.session_state['irr_temp'] = min(max(float(weather_data['temp']), 10.0), 48.0)
            st.session_state['irr_hum']  = min(max(float(weather_data['humidity']), 10.0), 100.0)
            st.session_state['irr_wind'] = min(float(weather_data.get('wind_speed', 10.0)), 50.0)
            desc_lower = weather_data['description'].lower()
            for key, tips in CALAMITY_TIPS.items():
                if key in desc_lower:
                    st.warning(f"⚠️ **{T('Weather Advisory for Farmers')}:**")
                    for tip in tips:
                        st.markdown(f"- {T(tip)}")
                    break
        else:
            card(T("Live weather unavailable. You can still adjust today's weather manually below."), severity="warning")

    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**🌱 {T('Crop Details')}**")
        irr_crop     = st.selectbox(T("Crop"), sorted(list(CROP_KC.keys())), key="irr_crop")
        growth_stage = st.selectbox(T("Growth Stage"), ['Initial', 'Development', 'Mid-season', 'Late season'], key="irr_stage")
        field_area   = st.number_input(T("Field Area (acres)"), min_value=0.5, max_value=100.0, value=1.0, step=0.5, key="irr_area")
        last_rain    = st.slider(T("Rainfall in last 3 days (mm)"), 0, 100, 0, key="irr_rain")

    with col2:
        st.markdown(f"**🌡️ {T('Today Weather')}**")
        irr_temp     = st.slider(T("Temperature (°C)"), 10.0, 48.0, 30.0, step=0.5, key="irr_temp")
        irr_humidity = st.slider(T("Humidity (%)"), 10.0, 100.0, 60.0, step=1.0, key="irr_hum")
        wind_speed   = st.slider(T("Wind Speed (km/h)"), 0.0, 50.0, 10.0, step=1.0, key="irr_wind")

    st.divider()

    if st.button(f"💧 {T('Get Irrigation Advice')}", use_container_width=True, type="primary"):
        with st.spinner(T("Consulting the Swarm...")):
            res = run_async(APIClient.irrigation_advice({
                "crop": irr_crop,
                "growth_stage": growth_stage,
                "field_area": field_area,
                "last_rain_mm": last_rain,
                "temperature": irr_temp,
                "humidity": irr_humidity,
                "wind_speed": wind_speed,
            }))
        if res:
            st.session_state['tab4_result'] = res
        else:
            card(T("Irrigation API unavailable. Check backend connection."), severity="error")

    if 'tab4_result' in st.session_state:
        r              = st.session_state['tab4_result']
        ET0            = r['ET0']
        Kc             = r['Kc']
        ETc            = r['ETc']
        net_irrigation = r['net_irrigation_mm']
        total_litres   = r['total_litres']
        total_kl       = r['total_kl']
        field_area     = r['field_area']
        fert           = r['fertilizer']
        growth_stage   = fert['growth_stage']
        irr_crop       = r['crop']

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(f"💧 {T('Water Need')}", f"{ETc:.1f} mm/day")
        with c2:
            st.metric(f"🚿 {T('Net Irrigation')}", f"{net_irrigation:.1f} mm/day")
        with c3:
            st.metric(f"🪣 {T('Total Water')}", f"{total_kl:.1f} kL", f"{T('for')} {field_area} {T('acre(s)')}")

        st.divider()

        if net_irrigation < 1.0:
            card(f"&#9989; <b>{T('No irrigation needed today!')}</b> {T('Recent rainfall is sufficient.')}", severity="success", dark=True)
        elif net_irrigation < 3.0:
            card(f"&#128167; <b>{T('Light irrigation recommended')}:</b> {T('Apply')} {net_irrigation:.1f} mm ({total_kl:.1f} kL)", severity="warning", dark=True)
        else:
            card(f"&#128680; <b>{T('Irrigation urgently needed')}:</b> {T('Apply')} {net_irrigation:.1f} mm ({total_kl:.1f} kL)", severity="error", dark=True)

        card(f"""
        <b style='color:#166534;'>&#127807; {T('Fertilizer Recommendation')}</b><br>
        <span style='font-family:JetBrains Mono,monospace;font-size:0.8rem;color:#15803D;'>{T('Stage')}:</span>
        <span style='color:#1A2E1A;'> {T(growth_stage)}</span>&nbsp;&nbsp;
        <span style='font-family:JetBrains Mono,monospace;font-size:0.8rem;color:#15803D;'>N dose:</span>
        <span style='color:#1A2E1A;'> {T(fert['nitrogen'])}</span><br>
        <span style='font-size:0.88rem;color:#1A2E1A;'>{T(fert['tip'])}</span>
        """, severity="info", dark=True)

        with st.expander(f"🔬 {T('Calculation Details (FAO-56 Method)')}"):
            st.markdown(f"""
            | {T('Parameter')} | {T('Value')} |
            |---|---|
            | Reference ET₀ | {ET0:.2f} mm/day |
            | Crop Coefficient (Kc) | {Kc} |
            | Crop Water Need (ETc) | {ETc:.2f} mm/day |
            | {T('Net Irrigation Need')} | {net_irrigation:.2f} mm/day |
            | {T('Field Area')} | {field_area} {T('acres')} |
            | {T('Total Water Required')} | {total_kl:.2f} kL |

            *{T('Using FAO Penman-Monteith method (FAO-56 guidelines)')}*
            """)
