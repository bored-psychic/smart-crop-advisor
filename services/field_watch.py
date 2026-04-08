import requests
import datetime

def fetch_field_watch(city, lat=None, lon=None):
    """
    Aggregates:
    1. OpenWeatherMap current + 5-day forecast
    2. NASA FIRMS wildfire hotspots (MODIS, 1-day) — free, no key
    3. Locust swarm data from FAO eLocust3 public feed
    4. Air Quality Index
    Returns a structured dict of all alerts.
    """
    import datetime
    OWM_KEY = "bd5e378503939ddaee76f12ad7a97608"
    alerts = {'weather': None, 'fire': None, 'locust': None, 'aqi': None,
              'flood': None, 'forecast': None, 'city': city}

    # 1. Current weather + 5-day forecast
    try:
        cur_url = f"http://api.openweathermap.org/data/2.5/weather?q={city},IN&appid={OWM_KEY}&units=metric"
        r = requests.get(cur_url, timeout=5)
        w = r.json()
        if w.get('cod') == 200:
            alerts['weather'] = {
                'temp': w['main']['temp'],
                'feels_like': w['main']['feels_like'],
                'humidity': w['main']['humidity'],
                'wind': round(w['wind']['speed'] * 3.6, 1),
                'desc': w['weather'][0]['description'].title(),
                'rain_1h': w.get('rain', {}).get('1h', 0),
                'lat': w['coord']['lat'],
                'lon': w['coord']['lon'],
            }
            lat = w['coord']['lat']
            lon = w['coord']['lon']

        # 5-day forecast for flood risk
        if lat and lon:
            fct_url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OWM_KEY}&units=metric&cnt=8"
            rf = requests.get(fct_url, timeout=5)
            fdata = rf.json()
            rain_next48 = sum(
                item.get('rain', {}).get('3h', 0)
                for item in fdata.get('list', [])
            )
            alerts['flood'] = {
                'rain_48h': round(rain_next48, 1),
                'flood_risk': 'HIGH' if rain_next48 > 50 else 'MEDIUM' if rain_next48 > 25 else 'LOW',
            }
    except Exception:
        pass

    # 2. NASA FIRMS wildfire hotspots — public CSV, no key needed for 1-day MODIS
    try:
        if lat and lon:
            # Check bounding box 2 degrees around location (~220km)
            firms_url = (
                f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/"
                f"6a8dded48b9e7f3f8fb71ac4c5a45e89/MODIS_NRT/IND/1"
            )
            rf = requests.get(firms_url, timeout=7)
            if rf.status_code == 200 and rf.text.strip():
                lines = rf.text.strip().split('\n')
                hotspots_nearby = 0
                for line in lines[1:]:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        try:
                            flat, flon = float(parts[0]), float(parts[1])
                            dist = ((flat-lat)**2 + (flon-lon)**2)**0.5
                            if dist < 2.0:  # ~220km radius
                                hotspots_nearby += 1
                        except:
                            pass
                alerts['fire'] = {
                    'hotspots_nearby': hotspots_nearby,
                    'risk': 'HIGH' if hotspots_nearby > 5 else 'MEDIUM' if hotspots_nearby > 0 else 'NONE',
                    'source': 'NASA FIRMS MODIS',
                }
    except Exception:
        alerts['fire'] = {'hotspots_nearby': 0, 'risk': 'UNKNOWN', 'source': 'NASA FIRMS (unavailable)'}

    # 3. FAO Desert Locust situation (public JSON)
    try:
        fao_url = "https://locust-hub-hqfao.hub.arcgis.com/datasets/fao::desert-locust-presence-1.geojson"
        rf = requests.get(fao_url, timeout=6)
        if rf.status_code == 200:
            gjson = rf.json()
            features = gjson.get('features', [])
            nearby_swarms = 0
            for feat in features[:200]:
                coords = feat.get('geometry', {}).get('coordinates', [])
                if coords and lat:
                    flon, flat = coords[0], coords[1]
                    dist = ((flat-lat)**2 + (flon-lon)**2)**0.5
                    if dist < 5.0:
                        nearby_swarms += 1
            alerts['locust'] = {
                'swarms_nearby': nearby_swarms,
                'risk': 'HIGH' if nearby_swarms > 2 else 'MEDIUM' if nearby_swarms > 0 else 'NONE',
                'source': 'FAO Desert Locust Hub',
            }
        else:
            alerts['locust'] = {'swarms_nearby': 0, 'risk': 'UNKNOWN', 'source': 'FAO Hub (unavailable)'}
    except Exception:
        alerts['locust'] = {'swarms_nearby': 0, 'risk': 'UNKNOWN', 'source': 'FAO Hub (unavailable)'}

    # 4. AQI via OpenWeatherMap
    try:
        if lat and lon:
            aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={OWM_KEY}"
            ra = requests.get(aqi_url, timeout=5)
            aq = ra.json()
            aqi_val = aq['list'][0]['main']['aqi']
            aqi_labels = {1:'Good',2:'Fair',3:'Moderate',4:'Poor',5:'Very Poor'}
            alerts['aqi'] = {'value': aqi_val, 'label': aqi_labels.get(aqi_val,'Unknown')}
    except Exception:
        pass

    return alerts



