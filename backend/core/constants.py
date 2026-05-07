"""
KisanOS Constants — All static data extracted from the monolithic app.py.
Single source of truth for crop metadata, disease metadata, pest metadata,
irrigation coefficients, and fertilizer schedules.
"""

# ── Language support ──────────────────────────────────────────────────────────
LANGUAGES = {
    'English': 'en',
    'हिंदी (Hindi)': 'hi',
    'తెలుగు (Telugu)': 'te',
    'தமிழ் (Tamil)': 'ta',
    'ಕನ್ನಡ (Kannada)': 'kn',
    'मराठी (Marathi)': 'mr',
    'বাংলা (Bengali)': 'bn',
    'ગુજરાતી (Gujarati)': 'gu',
    'ਪੰਜਾਬੀ (Punjabi)': 'pa',
}

# ── Crop Emoji Map ────────────────────────────────────────────────────────────
CROP_EMOJI = {
    'rice': '🌾', 'maize': '🌽', 'chickpea': '🫘', 'kidneybeans': '🫘',
    'pigeonpeas': '🫘', 'mothbeans': '🫘', 'mungbean': '🫘', 'blackgram': '🫘',
    'lentil': '🫘', 'pomegranate': '🍎', 'banana': '🍌', 'mango': '🥭',
    'grapes': '🍇', 'watermelon': '🍉', 'muskmelon': '🍈', 'apple': '🍎',
    'orange': '🍊', 'papaya': '🫐', 'coconut': '🥥', 'cotton': '🌿',
    'jute': '🌿', 'coffee': '☕'
}

# ── Crop Tips ─────────────────────────────────────────────────────────────────
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

# ── Crop Coefficients (FAO-56) ────────────────────────────────────────────────
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

# ── Fertilizer Schedule ──────────────────────────────────────────────────────
FERTILIZER_SCHEDULE = {
    'Initial':     {'N': '30% of total N dose', 'tip': 'Apply basal dose of P and K fully at sowing.'},
    'Development': {'N': '30% of total N dose', 'tip': 'Top-dress with urea. Monitor leaf color.'},
    'Mid-season':  {'N': '40% of total N dose', 'tip': 'Final N top-dress. Avoid excess — causes lodging.'},
    'Late season': {'N': 'No N needed',          'tip': 'Stop fertilizing. Focus on pest monitoring.'},
}

# ── Weather Calamity Tips ─────────────────────────────────────────────────────
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

# ── Disease Metadata ──────────────────────────────────────────────────────────
DISEASE_META = {
    'healthy': {
        'severity': 'None', 'treatment': 'No disease detected. Continue regular monitoring every 7 days.',
        'prevention': 'Apply neem oil spray monthly. Maintain field hygiene.',
        'action': 'No immediate action needed.'
    },
    'tomato early blight': {
        'severity': 'Medium', 'treatment': 'Mancozeb 75% WP @ 2g/L. Remove infected leaves. Repeat after 10 days.',
        'prevention': 'Crop rotation every 2 years. Use resistant varieties.',
        'action': 'Manageable with prompt treatment. Monitor daily.'
    },
    'tomato late blight': {
        'severity': 'High', 'treatment': 'Metalaxyl + Mancozeb @ 2g/L immediately. Destroy infected plants.',
        'prevention': 'Avoid overhead irrigation. Certified disease-free seeds only.',
        'action': '⚠️ Act within 24 hours. Spreads to 80% of field in 72 hours.'
    },
    'tomato leaf mold': {
        'severity': 'Medium', 'treatment': 'Mancozeb or Chlorothalonil @ 2g/L. Improve ventilation.',
        'prevention': 'Reduce humidity. Stake plants for airflow.',
        'action': 'Spray immediately. Remove heavily infected leaves.'
    },
    'tomato septoria leaf spot': {
        'severity': 'Medium', 'treatment': 'Chlorothalonil 75% WP @ 2g/L every 10 days.',
        'prevention': 'Avoid wetting foliage. Remove plant debris after harvest.',
        'action': 'Prevent spread to upper leaves.'
    },
    'tomato spider mites': {
        'severity': 'Medium', 'treatment': 'Abamectin 1.8% EC @ 0.5ml/L. Spray leaf undersides.',
        'prevention': 'Increase humidity. Avoid water stress.',
        'action': 'Check undersides of leaves. Act fast — mites multiply quickly.'
    },
    'tomato target spot': {
        'severity': 'Medium', 'treatment': 'Azoxystrobin or Difenoconazole @ 1ml/L.',
        'prevention': 'Crop rotation. Remove infected debris.',
        'action': 'Apply fungicide at first sign.'
    },
    'tomato yellow leaf curl virus': {
        'severity': 'High', 'treatment': 'No chemical cure. Remove infected plants immediately.',
        'prevention': 'Control whitefly with Imidacloprid. Silver reflective mulch.',
        'action': 'Destroy infected plants. Prevent whitefly spread.'
    },
    'tomato mosaic virus': {
        'severity': 'High', 'treatment': 'No cure. Remove and destroy infected plants.',
        'prevention': 'Use virus-free seeds. Disinfect tools with bleach.',
        'action': 'Remove immediately. Wash hands after handling.'
    },
    'tomato bacterial spot': {
        'severity': 'Medium', 'treatment': 'Copper hydroxide @ 3g/L every 7 days.',
        'prevention': 'Disease-free transplants. Avoid working in wet fields.',
        'action': 'Start copper spray early. Avoid overhead irrigation.'
    },
    'potato early blight': {
        'severity': 'Medium', 'treatment': 'Chlorothalonil @ 2g/L. Repeat every 10 days.',
        'prevention': 'Certified seed tubers. Crop rotation.',
        'action': 'Apply at first symptom. Remove infected leaves.'
    },
    'potato late blight': {
        'severity': 'High', 'treatment': 'Cymoxanil + Mancozeb urgently. Destroy infected haulms.',
        'prevention': 'Well-drained soil. Monitor weather for humid conditions.',
        'action': '⚠️ Emergency — destroy affected plants and spray immediately.'
    },
    'corn cercospora leaf spot': {
        'severity': 'Medium', 'treatment': 'Azoxystrobin or Propiconazole @ 1ml/L.',
        'prevention': 'Resistant hybrids. Crop rotation.',
        'action': 'Apply fungicide before tasseling for best results.'
    },
    'corn common rust': {
        'severity': 'Medium', 'treatment': 'Mancozeb or Azoxystrobin @ 1ml/L.',
        'prevention': 'Rust-resistant hybrids. Early planting.',
        'action': 'Spray at first pustule appearance.'
    },
    'corn northern leaf blight': {
        'severity': 'Medium', 'treatment': 'Propiconazole 25% EC @ 1ml/L at early stage.',
        'prevention': 'Resistant varieties. Crop rotation.',
        'action': 'Fungicide most effective before lesions reach upper canopy.'
    },
    'rice leaf blast': {
        'severity': 'High', 'treatment': 'Tricyclazole 75% WP @ 0.6g/L at booting stage.',
        'prevention': 'Blast-resistant varieties. Avoid excess nitrogen.',
        'action': 'Critical to spray at booting. Yield loss severe if untreated.'
    },
    'rice brown spot': {
        'severity': 'Medium', 'treatment': 'Mancozeb or Iprodione fungicide @ 2g/L.',
        'prevention': 'Balanced potassium nutrition. Healthy certified seed.',
        'action': 'Apply at tillering stage for prevention.'
    },
    'rice neck blast': {
        'severity': 'High', 'treatment': 'Tricyclazole @ 0.6g/L. Spray at heading.',
        'prevention': 'Resistant varieties. Balanced fertilization.',
        'action': '⚠️ Most destructive rice disease. Act immediately at heading.'
    },
    'apple scab': {
        'severity': 'Medium', 'treatment': 'Captan 50% WP @ 2g/L or Myclobutanil.',
        'prevention': 'Resistant varieties. Remove fallen leaves.',
        'action': 'Spray before and after rain events.'
    },
    'apple black rot': {
        'severity': 'High', 'treatment': 'Captan or Thiophanate-methyl @ 2g/L.',
        'prevention': 'Prune infected branches. Remove mummified fruit.',
        'action': 'Remove all infected fruit and wood immediately.'
    },
    'apple cedar rust': {
        'severity': 'Medium', 'treatment': 'Myclobutanil or Propiconazole @ 1ml/L.',
        'prevention': 'Remove nearby juniper / cedar trees if possible.',
        'action': 'Spray at pink bud stage for best control.'
    },
    'grape black rot': {
        'severity': 'High', 'treatment': 'Mancozeb or Myclobutanil @ 2g/L. Apply at bud break.',
        'prevention': 'Remove infected mummies. Prune for airflow.',
        'action': 'Most critical to spray pre-bloom through fruit set.'
    },
    'grape esca': {
        'severity': 'High', 'treatment': 'No effective chemical cure. Remove infected wood.',
        'prevention': 'Protect pruning wounds. Avoid water stress.',
        'action': 'Remove and burn infected canes. Protect cuts with wound paste.'
    },
    'grape leaf blight': {
        'severity': 'Medium', 'treatment': 'Copper oxychloride @ 3g/L.',
        'prevention': 'Improve canopy airflow. Avoid leaf wetness.',
        'action': 'Spray after rain. Reduce overhead irrigation.'
    },
    'peach bacterial spot': {
        'severity': 'Medium', 'treatment': 'Copper hydroxide @ 3g/L during dormancy and at bud break.',
        'prevention': 'Resistant varieties. Avoid overhead irrigation.',
        'action': 'Apply copper spray at petal fall.'
    },
    'pepper bell bacterial spot': {
        'severity': 'Medium', 'treatment': 'Copper-based bactericide @ 3g/L every 7 days.',
        'prevention': 'Certified disease-free transplants. Avoid wet conditions.',
        'action': 'Stop overhead irrigation. Apply copper immediately.'
    },
    'strawberry leaf scorch': {
        'severity': 'Low', 'treatment': 'Captan 50% WP @ 2g/L.',
        'prevention': 'Remove infected leaves. Improve airflow.',
        'action': 'Low severity. Remove old foliage after harvest.'
    },
    'squash powdery mildew': {
        'severity': 'Low', 'treatment': 'Sulphur 80% WP @ 2g/L or potassium bicarbonate.',
        'prevention': 'Resistant varieties. Avoid dense planting.',
        'action': 'Apply sulphur spray at first white patches.'
    },
    'cherry powdery mildew': {
        'severity': 'Low', 'treatment': 'Myclobutanil or Sulphur @ 2g/L.',
        'prevention': 'Prune for airflow. Avoid high nitrogen.',
        'action': 'Spray at first sign on young leaves.'
    },
    'soybean rust': {
        'severity': 'High', 'treatment': 'Azoxystrobin + Propiconazole @ 1ml/L urgently.',
        'prevention': 'Monitor fields from flowering. Resistant varieties.',
        'action': '⚠️ Can destroy entire crop. Spray at first pustule.'
    },
    'default': {
        'severity': 'Medium', 'treatment': 'Apply broad-spectrum fungicide (Carbendazim 12% + Mancozeb 63% WP) @ 2g/L. Monitor for 3 days.',
        'prevention': 'Ensure good field drainage. Avoid overhead irrigation.',
        'action': 'Take a clearer close-up photo in daylight for better accuracy.'
    },
}

# ── Pest Metadata (Acoustic) ─────────────────────────────────────────────────
PEST_META = {
    'Healthy Plant': {
        'severity': 'low', 'freq_range': '<100 Hz (flat)', 'pattern': 'Flat noise floor',
        'energy_level': 'Background',
        'action': 'No pest detected. Continue monitoring every 7 days. Apply neem oil spray monthly as a preventive measure.',
        'icon': '✅'
    },
    'Aphid Colony': {
        'severity': 'medium', 'freq_range': '200–400 Hz', 'pattern': 'Clustered mid-freq bursts',
        'energy_level': 'Moderate',
        'action': 'Apply Imidacloprid 17.8% SL @ 0.5ml/L in the evening. Repeat after 7 days. Check for ant colonies protecting aphids — destroy ant trails.',
        'icon': '🟡'
    },
    'Whitefly Infestation': {
        'severity': 'medium', 'freq_range': '400–700 Hz', 'pattern': 'Wing-beat harmonic series',
        'energy_level': 'Low-moderate',
        'action': 'Install yellow sticky traps immediately. Spray Spiromesifen 22.9% SC @ 0.5ml/L or Thiamethoxam 25% WG @ 0.3g/L. Use silver reflective mulch to repel adults.',
        'icon': '🟡'
    },
    'Locust Activity': {
        'severity': 'high', 'freq_range': '50–200 Hz', 'pattern': 'High-amplitude low-freq pulses',
        'energy_level': 'Very High',
        'action': '🚨 LOCUST SWARM — Act immediately. Contact State Agriculture Department: 1800-180-1551. Spray Chlorpyrifos 50% EC @ 2ml/L or Malathion 96% ULV aerial spray if available. Protect stored grain.',
        'icon': '🔴'
    },
    'Stem Borer': {
        'severity': 'high', 'freq_range': '50–150 Hz', 'pattern': 'Low-freq gnawing rhythm',
        'energy_level': 'High',
        'action': 'Apply Cartap hydrochloride 50% SP @ 1g/L at stem base. Check for dead heart (central shoot dying). Use pheromone traps. Coragen (Chlorantraniliprole) @ 0.4ml/L for severe infestation.',
        'icon': '🔴'
    },
    'Early Fungal Infection': {
        'severity': 'high', 'freq_range': '800–1200 Hz', 'pattern': 'High-freq crackling',
        'energy_level': 'Elevated',
        'action': 'Apply Mancozeb 75% WP @ 2.5g/L within 48 hours. Improve field drainage. Reduce overhead irrigation. Repeat after 10 days. Check for lesion spread.',
        'icon': '🔴'
    },
    'Spider Mite': {
        'severity': 'medium', 'freq_range': '1200–4000 Hz', 'pattern': 'Ultra-high freq scratching',
        'energy_level': 'Moderate-high',
        'action': 'Apply Abamectin 1.8% EC @ 0.5ml/L or Spiromesifen 22.9% SC @ 1ml/L. Spray underside of leaves — mites live there. Increase humidity if possible. Avoid broad-spectrum insecticides that kill predators.',
        'icon': '🟡'
    },
    'Thrips Infestation': {
        'severity': 'medium', 'freq_range': '350–500 Hz', 'pattern': 'Rapid mid-freq staccato',
        'energy_level': 'Low-moderate',
        'action': 'Apply Spinosad 45% SC @ 0.3ml/L or Fipronil 5% SC @ 1.5ml/L. Use blue sticky traps. Remove infested growing tips. Check for silvering on leaves.',
        'icon': '🟡'
    },
}

# ── Government Helplines ──────────────────────────────────────────────────────
GOVT_HELPLINES = [
    ("Kisan Call Centre", "18001801551", "Free · 24/7 · All Indian languages"),
    ("PM Kisan Helpline", "155261", "PM Kisan scheme queries"),
    ("NDRF Emergency", "1078", "Flood, earthquake, disaster"),
    ("Ambulance", "108", "Medical emergency"),
    ("Police", "100", "Security / theft"),
    ("State Agriculture Dept", "18004252", "Disease outbreak reporting"),
]
