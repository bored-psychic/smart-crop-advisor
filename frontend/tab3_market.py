import streamlit as st
import pandas as pd
from frontend.api_client import APIClient, run_async
from frontend.ui_helpers import card, page_hero
from core.language import T

ALL_CROPS = [
    'Apple', 'Banana', 'Blackgram', 'Chickpea', 'Coconut', 'Coffee',
    'Cotton', 'Grapes', 'Jute', 'Kidneybeans', 'Lentil', 'Maize',
    'Mango', 'Mothbeans', 'Mungbean', 'Muskmelon', 'Onion', 'Orange',
    'Papaya', 'Pigeonpeas', 'Pomegranate', 'Potato', 'Rice', 'Tomato',
    'Watermelon', 'Wheat',
]


def render():
    page_hero("MARKET PRICES", "Know before you", "sell.", "Live mandi prices for your crop and district. Sell when the moment is right.")

    _default_city = st.session_state.get('farmer_village', '').split(',')[0].strip()
    city_input = st.text_input(
        f"🏙️ {T('Your City / District')}",
        value=_default_city,
        placeholder="e.g. Bellary, Nagpur, Warangal",
        key="mkt_city"
    )

    crop_choice = st.selectbox(f"🌾 {T('Crop')}", ALL_CROPS, key="mkt_crop")

    forecast_days = st.slider(T("Forecast horizon (days)"), 7, 60, 30, key="mkt_days")

    if st.button(f"📈 {T('Get Live Price + Forecast')}", use_container_width=True, type="primary"):
        if not city_input.strip():
            st.error(T("Please enter your city or district name."))
        else:
            with st.spinner(T("Resolving location and fetching live Agmarknet data...")):
                res = run_async(APIClient.get_market_price(city_input.strip(), crop_choice, forecast_days))
            if res:
                st.session_state['tab3_result'] = res
            else:
                card(T("Market API unavailable or city not recognised. Check the city name and backend connection."), severity="error")

    if 'tab3_result' in st.session_state:
        r3      = st.session_state['tab3_result']
        live    = r3.get('live_price')
        crop_r  = r3['crop']
        state_r = r3['state']
        city_r  = r3.get('city', '')
        factor  = r3['state_factor']
        location_label = f"{city_r}, {state_r}" if city_r else state_r

        # Derived state badge
        st.markdown(
            f'<div style="display:inline-block;background:rgba(34,197,94,0.12);border:1px solid '
            f'rgba(34,197,94,0.3);border-radius:20px;padding:4px 14px;font-size:12px;'
            f'color:#22C55E;font-weight:600;margin-bottom:12px">📍 {state_r}</div>',
            unsafe_allow_html=True,
        )

        if live and live.get('live'):
            tp = live['today_price']
            st.markdown(f"""
            <div style="background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.3);
                        border-radius:12px;padding:16px 20px;margin-bottom:16px">
              <div style="display:flex;align-items:center;gap:12px">
                <div>
                  <div style="font-size:11px;color:#6B8F6B;font-weight:600;text-transform:uppercase;letter-spacing:.08em">
                    LIVE · {live['source']} · {live['mandis_checked']} mandis
                  </div>
                  <div style="font-size:2rem;font-weight:700;color:#22C55E;font-family:monospace">
                    ₹{tp:,.0f}<span style="font-size:1rem;color:#6B8F6B"> /qtl</span>
                  </div>
                  <div style="font-size:12px;color:#6B8F6B">{crop_r} · {location_label}</div>
                </div>
                <div style="margin-left:auto;text-align:right">
                  <div style="font-size:11px;color:#6B8F6B">State adj. factor</div>
                  <div style="font-size:1.2rem;font-weight:600;color:#F59E0B">{factor:.2f}×</div>
                </div>
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            card(f"&#128161; {T('Agmarknet API unavailable — showing Prophet forecast calibrated for')} {location_label}. {T('Factor')}: {factor:.2f}&times;", severity="info")

        # Karnataka city-wise price chart
        city_prices = live.get('city_prices', []) if live else []
        if state_r.lower() == 'karnataka' and city_prices:
            st.markdown(f"#### {T('Karnataka — Price by District')} · {crop_r}")
            cp_df = pd.DataFrame(city_prices).set_index('city').rename(columns={'price': 'Price (₹/qtl)'})
            st.bar_chart(cp_df)
            state_avg = live['today_price'] if live else 0
            st.caption(f"📊 State average: ₹{state_avg:,.0f}/qtl · Source: Agmarknet Live")

        forecast_list = r3.get('forecast', [])
        if forecast_list:
            ff = pd.DataFrame(forecast_list)
            ff.rename(columns={'date': 'Date', 'price': 'Price', 'min_price': 'Min', 'max_price': 'Max'}, inplace=True)
            ff['Date'] = pd.to_datetime(ff['Date'])

            best_price  = r3['best_price']
            best_date   = r3['best_date']
            worst_price = r3['worst_price']
            worst_date  = r3['worst_date']
            avg_price   = r3['avg_price']

            c1, c2, c3 = st.columns(3)
            with c1:
                today_p = ff['Price'].iloc[0]
                delta = f"{((best_price - today_p) / today_p * 100):+.1f}%" if today_p else ""
                st.metric(f"💰 {T('Best Price')}", f"₹{best_price:,.0f}", f"{best_date} · {delta}")
            with c2:
                st.metric(f"📉 {T('Lowest Price')}", f"₹{worst_price:,.0f}", worst_date)
            with c3:
                st.metric(f"📊 {T('Avg / 30d')}", f"₹{avg_price:,.0f}")

            card(f"&#128640; <b>{T(r3['sell_advice'])}</b>", severity="success" if "Wait" in r3['sell_advice'] else "warning")

            st.markdown(f"#### {T('Price Forecast Chart')} — {crop_r} · {location_label}")
            chart_df = ff.set_index('Date')[['Price', 'Min', 'Max']]
            st.line_chart(chart_df)
            st.caption(f"📊 {T('State factor applied')}: {factor:.2f}× · Prophet trend decomposition")

            with st.expander(f"📋 {T('Full Forecast Table')}"):
                disp = ff.copy()
                disp['Date'] = disp['Date'].dt.strftime('%d %b %Y')
                st.dataframe(disp, use_container_width=True)
