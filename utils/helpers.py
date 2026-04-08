import numpy as np

CROP_EMOJI = {
    'rice': '🌾', 'maize': '🌽', 'chickpea': '🫘', 'kidneybeans': '🫘',
    'pigeonpeas': '🫘', 'mothbeans': '🫘', 'mungbean': '🫘', 'blackgram': '🫘',
    'lentil': '🫘', 'pomegranate': '🍎', 'banana': '🍌', 'mango': '🥭',
    'grapes': '🍇', 'watermelon': '🍉', 'muskmelon': '🍈', 'apple': '🍎',
    'orange': '🍊', 'papaya': '🫐', 'coconut': '🥥', 'cotton': '🌿',
    'jute': '🌿', 'coffee': '☕'
}

CROP_TIPS = {
    'rice':       'Best grown in waterlogged, clayey soil. Requires consistent irrigation.',
    'maize':      'Grows well in well-drained loamy soil. Needs moderate water.',
    'chickpea':   'Drought-tolerant. Thrives in cool, dry weather. Minimal irrigation needed.',
    'kidneybeans':'Needs well-drained soil and moderate rainfall. Avoid waterlogging.',
    'pigeonpeas': 'Highly drought resistant. Good for rain-fed areas.',
    'mothbeans':  'Extreme drought tolerance. Ideal for arid/semi-arid zones.',
    'mungbean':   'Short duration crop. Suitable for inter-cropping.',
    'blackgram':  'Prefers warm, humid climate. Good for mixed cropping.',
    'lentil':     'Cool season crop. Fixes nitrogen — great for soil health.',
    'pomegranate':'Thrives in hot, dry climate. Very water efficient.',
    'banana':     'Requires high humidity and warm temperatures year-round.',
    'mango':      'Requires a distinct dry season for flowering. Deep soil preferred.',
    'grapes':     'Needs well-drained sandy loam. Sensitive to waterlogging.',
    'watermelon': 'Grows best in sandy loam with warm temperatures.',
    'muskmelon':  'Warm-season crop. Needs dry climate during fruiting.',
    'apple':      'Requires cold winters for dormancy. Hilly terrain preferred.',
    'orange':     'Subtropical climate. Needs mild winters and warm summers.',
    'papaya':     'Grows year-round in tropical climates. Frost-sensitive.',
    'coconut':    'Thrives in coastal, humid regions with sandy soil.',
    'cotton':     'Requires long, frost-free season. Deep, well-drained soil.',
    'jute':       'Grows best in warm, humid climate with heavy rainfall.',
    'coffee':     'Needs high altitude, moderate temp, and well-distributed rainfall.'
}

CROP_KC = {
    'Rice':        {'Initial': 1.05, 'Development': 1.20, 'Mid-season': 1.20, 'Late season': 0.90}

FERTILIZER_SCHEDULE = {
    'Initial':     {'N': '30% of total N dose', 'tip': 'Apply basal dose of P and K fully at sowing.'}

def calculate_ET0(temp, humidity, wind_speed_kmh):
    wind_ms = wind_speed_kmh / 3.6
    es = 0.6108 * np.exp(17.27 * temp / (temp + 237.3))
    ea = es * humidity / 100
    vpd = max(es - ea, 0)
    ET0 = (0.408 * 0.0135 * (temp + 17.8) * (wind_ms + 1)) + (0.34 * vpd * wind_ms)
    return max(round(ET0, 2), 1.0)


