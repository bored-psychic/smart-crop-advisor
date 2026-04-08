import numpy as np

DISEASE_META = {
    # Healthy
    'healthy': {
        'severity': 'None', 'treatment': 'No disease detected. Continue regular monitoring every 7 days.',
        'prevention': 'Apply neem oil spray monthly. Maintain field hygiene.',
        'action': 'No immediate action needed.'
    },
    # Tomato
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
    # Potato
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
    # Corn / Maize
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
    # Rice
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
    # Apple
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
    # Grape
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
    # Peach
    'peach bacterial spot': {
        'severity': 'Medium', 'treatment': 'Copper hydroxide @ 3g/L during dormancy and at bud break.',
        'prevention': 'Resistant varieties. Avoid overhead irrigation.',
        'action': 'Apply copper spray at petal fall.'
    },
    # Pepper
    'pepper bell bacterial spot': {
        'severity': 'Medium', 'treatment': 'Copper-based bactericide @ 3g/L every 7 days.',
        'prevention': 'Certified disease-free transplants. Avoid wet conditions.',
        'action': 'Stop overhead irrigation. Apply copper immediately.'
    },
    # Strawberry
    'strawberry leaf scorch': {
        'severity': 'Low', 'treatment': 'Captan 50% WP @ 2g/L.',
        'prevention': 'Remove infected leaves. Improve airflow.',
        'action': 'Low severity. Remove old foliage after harvest.'
    },
    # Squash
    'squash powdery mildew': {
        'severity': 'Low', 'treatment': 'Sulphur 80% WP @ 2g/L or potassium bicarbonate.',
        'prevention': 'Resistant varieties. Avoid dense planting.',
        'action': 'Apply sulphur spray at first white patches.'
    },
    # Cherry
    'cherry powdery mildew': {
        'severity': 'Low', 'treatment': 'Myclobutanil or Sulphur @ 2g/L.',
        'prevention': 'Prune for airflow. Avoid high nitrogen.',
        'action': 'Spray at first sign on young leaves.'
    },
    # Soybean
    'soybean rust': {
        'severity': 'High', 'treatment': 'Azoxystrobin + Propiconazole @ 1ml/L urgently.',
        'prevention': 'Monitor fields from flowering. Resistant varieties.',
        'action': '⚠️ Can destroy entire crop. Spray at first pustule.'
    },
    # Default fallback
    'default': {
        'severity': 'Medium', 'treatment': 'Apply broad-spectrum fungicide (Carbendazim 12% + Mancozeb 63% WP) @ 2g/L. Monitor for 3 days.',
        'prevention': 'Ensure good field drainage. Avoid overhead irrigation.',
        'action': 'Take a clearer close-up photo in daylight for better accuracy.'
    },
}


