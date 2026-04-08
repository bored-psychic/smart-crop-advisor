import requests

def get_weather(city):
    try:
        api_key = "bd5e378503939ddaee76f12ad7a97608"
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city},IN&appid={api_key}&units=metric"
        r = requests.get(url, timeout=5)
        data = r.json()
        if data.get('cod') == 200:
            return {
                'temp': data['main']['temp'],
                'humidity': data['main']['humidity'],
                'description': data['weather'][0]['description'].title(),
                'wind_speed': data['wind']['speed'] * 3.6,
                'rainfall': data.get('rain', {}).get('1h', 0),
                'city': data['name']
            }
    except:
        pass
    return None

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


TAB2_SPEAK = {
    'en': "Upload a photo of your crop for instant AI disease diagnosis. Or select your crop and symptom below for text-based diagnosis.",
    'hi': "अपनी फसल की फोटो अपलोड करें — AI तुरंत बीमारी पहचानेगा। या नीचे अपनी फसल और लक्षण चुनें।",
    'te': "మీ పంట ఫోటో అప్లోడ్ చేయండి — AI వెంటనే వ్యాధిని గుర్తిస్తుంది. లేదా క్రింద పంట మరియు లక్షణం ఎంచుకోండి.",
    'ta': "உங்கள் பயிர் புகைப்படத்தை பதிவேற்றவும் — AI உடனடியாக நோயை கண்டறியும். அல்லது கீழே பயிர் மற்றும் அறிகுறி தேர்வு செய்யுங்கள்.",
    'kn': "ನಿಮ್ಮ ಬೆಳೆ ಫೋಟೋ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ — AI ತಕ್ಷಣ ರೋಗ ಗುರುತಿಸುತ್ತದೆ. ಅಥವಾ ಕೆಳಗೆ ಬೆಳೆ ಮತ್ತು ಲಕ್ಷಣ ಆಯ್ಕೆಮಾಡಿ.",
    'mr': "तुमच्या पिकाचा फोटो अपलोड करा — AI लगेच आजार ओळखेल. किंवा खाली पीक आणि लक्षण निवडा.",
    'bn': "আপনার ফসলের ছবি আপলোড করুন — AI তাৎক্ষণিক রোগ শনাক্ত করবে। অথবা নিচে ফসল ও লক্ষণ বেছে নিন।",
    'gu': "તમારા પાકનો ફોટો અપલોડ કરો — AI તરત રોગ ઓળખશે. અથવા નીચે પાક અને લક્ષણ પસંદ કરો.",
    'pa': "ਆਪਣੀ ਫ਼ਸਲ ਦੀ ਫ਼ੋਟੋ ਅਪਲੋਡ ਕਰੋ — AI ਤੁਰੰਤ ਬਿਮਾਰੀ ਪਛਾਣੇਗਾ। ਜਾਂ ਹੇਠਾਂ ਫ਼ਸਲ ਅਤੇ ਲੱਛਣ ਚੁਣੋ।",
}
TAB3_SPEAK = {
    'en': "Select your state and crop to get live mandi prices from Agmarknet, plus a 30-day forecast. The best sell date is highlighted automatically.",
    'hi': "लाइव मंडी भाव देखने के लिए अपना राज्य और फसल चुनें। 30 दिन का अनुमान और बेचने का सबसे अच्छा दिन अपने आप दिखेगा।",
    'te': "లైవ్ మండి ధరలు చూడటానికి మీ రాష్ట్రం మరియు పంట ఎంచుకోండి. 30 రోజుల అంచనా మరియు అమ్మడానికి మంచి రోజు స్వయంచాలకంగా చూపబడుతుంది.",
    'ta': "நேரடி மண்டி விலைகளுக்கு உங்கள் மாநிலம் மற்றும் பயிர் தேர்வு செய்யுங்கள். 30 நாள் கணிப்பு மற்றும் சிறந்த விற்பனை தேதி தானாகவே காட்டப்படும்.",
    'kn': "ಲೈವ್ ಮಂಡಿ ಬೆಲೆಗಳಿಗಾಗಿ ನಿಮ್ಮ ರಾಜ್ಯ ಮತ್ತು ಬೆಳೆ ಆಯ್ಕೆಮಾಡಿ. 30 ದಿನಗಳ ಮುನ್ಸೂಚನೆ ಮತ್ತು ಮಾರಾಟಕ್ಕೆ ಉತ್ತಮ ದಿನ ತಾನಾಗಿ ತೋರಿಸಲ್ಪಡುತ್ತದೆ.",
    'mr': "लाइव्ह मंडी भाव पाहण्यासाठी तुमचे राज्य आणि पीक निवडा. ३० दिवसांचा अंदाज आणि विकण्याचा सर्वोत्तम दिवस आपोआप दिसेल.",
    'bn': "লাইভ মান্ডি দাম দেখতে আপনার রাজ্য ও ফসল বেছে নিন। ৩০ দিনের পূর্বাভাস এবং সেরা বিক্রির দিন স্বয়ংক্রিয়ভাবে দেখাবে।",
    'gu': "લાઇવ મંડી ભાવ જોવા તમારું રાજ્ય અને પાક પસંદ કરો. ૩૦ દિવસનો અંદાજ અને વેચવા માટેનો શ્રેષ્ઠ દિવસ આપોઆપ બતાવાશે.",
    'pa': "ਲਾਈਵ ਮੰਡੀ ਭਾਅ ਦੇਖਣ ਲਈ ਆਪਣਾ ਰਾਜ ਅਤੇ ਫ਼ਸਲ ਚੁਣੋ। 30 ਦਿਨਾਂ ਦਾ ਅਨੁਮਾਨ ਅਤੇ ਵੇਚਣ ਦਾ ਸਭ ਤੋਂ ਵਧੀਆ ਦਿਨ ਆਪਣੇ ਆਪ ਦਿਖੇਗਾ।",
}
TAB5_SPEAK = {
    'en': "Record 4 seconds of audio near your crop leaves. The AI analyzes sound frequency to detect pests like aphids, whitefly, locust, stem borer, and fungal infection.",
    'hi': "अपनी फसल की पत्तियों के पास 4 सेकंड की आवाज रिकॉर्ड करें। AI आवाज की फ्रीक्वेंसी से एफिड, व्हाइटफ्लाई, टिड्डी, स्टेम बोरर और फंगस पकड़ता है।",
    'te': "మీ పంట ఆకుల దగ్గర 4 సెకన్లు రికార్డ్ చేయండి. AI శబ్ద తరంగ విశ్లేషణతో అఫిడ్, తెల్లదోమ, మిడత, కాండం తొలుచు పురుగు మరియు ఫంగస్ గుర్తిస్తుంది.",
    'ta': "உங்கள் பயிர் இலைகளுக்கு அருகில் 4 வினாடிகள் ஆடியோ பதிவு செய்யுங்கள். AI ஒலி அதிர்வெண் பகுப்பாய்வால் அஃபிட், வெள்ளை ஈ, வெட்டுக்கிளி மற்றும் பூஞ்சை கண்டறியும்.",
    'kn': "ನಿಮ್ಮ ಬೆಳೆ ಎಲೆಗಳ ಬಳಿ 4 ಸೆಕೆಂಡ್ ಆಡಿಯೋ ರೆಕಾರ್ಡ್ ಮಾಡಿ. AI ಶಬ್ದ ಆವರ್ತನ ವಿಶ್ಲೇಷಣೆಯಿಂದ ಅಫಿಡ್, ವೈಟ್‌ಫ್ಲೈ, ಮಿಡತ ಮತ್ತು ಶಿಲೀಂಧ್ರ ಗುರುತಿಸುತ್ತದೆ.",
    'mr': "तुमच्या पिकाच्या पानांजवळ 4 सेकंद ऑडिओ रेकॉर्ड करा. AI आवाजाच्या फ्रिक्वेन्सीने मावा, पांढरी माशी, टोळ, खोडकिडा आणि बुरशी ओळखतो.",
    'bn': "আপনার ফসলের পাতার কাছে ৪ সেকেন্ড অডিও রেকর্ড করুন। AI শব্দ কম্পাংক বিশ্লেষণে জাবমাছি, সাদামাছি, পঙ্গপাল ও ছত্রাক শনাক্ত করে।",
    'gu': "તમારા પાકના પાંદડા પાસે 4 સેકન્ડ ઓડિયો રેકોર્ડ કરો. AI ધ્વનિ આવૃત્તિ વિશ્લેષણ દ્વારા એફિડ, વ્હાઇટફ્લાય, તીડ અને ફૂગ શોધે છે.",
    'pa': "ਆਪਣੀ ਫ਼ਸਲ ਦੇ ਪੱਤਿਆਂ ਦੇ ਨੇੜੇ 4 ਸਕਿੰਟ ਆਡੀਓ ਰਿਕਾਰਡ ਕਰੋ। AI ਆਵਾਜ਼ ਦੀ ਬਾਰੰਬਾਰਤਾ ਨਾਲ ਮਾਹੂ, ਚਿੱਟੀ ਮੱਖੀ, ਟਿੱਡੀ ਅਤੇ ਫੰਗਸ ਪਛਾਣਦਾ ਹੈ।",
}
TAB6_SPEAK = {
    'en': "This is your Field Watch. It checks live satellite weather, wildfire alerts, flood warnings, and locust swarm data for your location. Updates every time you open this tab.",
    'hi': "यह आपका फील्ड वॉच है। यह आपकी जगह के लिए लाइव सैटेलाइट मौसम, जंगल की आग, बाढ़ की चेतावनी और टिड्डी दल की जानकारी देता है।",
    'te': "ఇది మీ ఫీల్డ్ వాచ్. ఇది మీ స్థానానికి లైవ్ శాటిలైట్ వాతావరణం, అటవీ అగ్ని, వరద హెచ్చరికలు మరియు మిడత మందల డేటాను తనిఖీ చేస్తుంది.",
    'ta': "இது உங்கள் ஃபீல்ட் வாட்ச். இது உங்கள் இடத்திற்கான நேரடி செயற்கைக்கோள் வானிலை, காட்டுத்தீ, வெள்ளம் மற்றும் வெட்டுக்கிளி மந்தை தரவை சரிபார்க்கிறது.",
    'kn': "ಇದು ನಿಮ್ಮ ಫೀಲ್ಡ್ ವಾಚ್. ಇದು ನಿಮ್ಮ ಸ್ಥಳಕ್ಕಾಗಿ ಲೈವ್ ಉಪಗ್ರಹ ಹವಾಮಾನ, ಕಾಳ್ಗಿಚ್ಚು, ಪ್ರವಾಹ ಎಚ್ಚರಿಕೆ ಮತ್ತು ಮಿಡತ ಗುಂಪಿನ ಡೇಟಾ ಪರಿಶೀಲಿಸುತ್ತದೆ.",
    'mr': "हे तुमचे फील्ड वॉच आहे. हे तुमच्या ठिकाणासाठी लाइव्ह सॅटेलाइट हवामान, वणवा, पूर इशारे आणि टोळधाड डेटा तपासते.",
    'bn': "এটি আপনার ফিল্ড ওয়াচ। এটি আপনার অবস্থানের জন্য লাইভ স্যাটেলাইট আবহাওয়া, দাবানল, বন্যা সতর্কতা এবং পঙ্গপাল তথ্য পরীক্ষা করে।",
    'gu': "આ તમારું ફીલ્ડ વૉચ છે. આ તમારા સ્થળ માટે લાઇવ સેટેલાઇટ હવામાન, જંગલની આગ, પૂર ચેતવણી અને તીડ ડેટા તપાસે છે.",
    'pa': "ਇਹ ਤੁਹਾਡਾ ਫੀਲਡ ਵਾਚ ਹੈ। ਇਹ ਤੁਹਾਡੀ ਜਗ੍ਹਾ ਲਈ ਲਾਈਵ ਸੈਟੇਲਾਈਟ ਮੌਸਮ, ਜੰਗਲੀ ਅੱਗ, ਹੜ੍ਹ ਚੇਤਾਵਨੀ ਅਤੇ ਟਿੱਡੀ ਦਲ ਡੇਟਾ ਜਾਂਚਦਾ ਹੈ।",
}

# Agmarknet state→mandi_code mapping + crop price calibration
INDIA_STATES = [
    "Andhra Pradesh","Assam","Bihar","Chhattisgarh","Gujarat","Haryana",
    "Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh",
    "Maharashtra","Odisha","Punjab","Rajasthan","Tamil Nadu","Telangana",
    "Uttar Pradesh","Uttarakhand","West Bengal",
]

# State-crop seasonal price adjustment factors (vs national baseline)
# Based on APMC seasonal patterns from Agmarknet historical data
STATE_PRICE_FACTORS = {
    "Punjab":          {"Wheat":1.08,"Rice":1.05,"Maize":0.98,"Cotton":1.02,"Potato":0.94},
    "Haryana":         {"Wheat":1.06,"Rice":1.03,"Maize":0.97,"Cotton":1.01,"Potato":0.95},
    "Uttar Pradesh":   {"Wheat":1.04,"Rice":1.02,"Maize":1.00,"Sugarcane":1.10,"Potato":1.12},
    "Maharashtra":     {"Cotton":1.15,"Onion":1.20,"Soybean":1.08,"Grape":1.25,"Orange":1.18},
    "Karnataka":       {"Coffee":1.22,"Cotton":1.10,"Maize":1.05,"Tomato":1.08,"Mango":1.15},
    "Andhra Pradesh":  {"Rice":1.06,"Cotton":1.08,"Chilli":1.30,"Maize":1.04,"Tomato":1.10},
    "Telangana":       {"Rice":1.04,"Cotton":1.09,"Maize":1.06,"Tomato":1.12,"Soybean":1.07},
    "Tamil Nadu":      {"Rice":1.07,"Banana":1.18,"Coconut":1.22,"Cotton":1.05,"Groundnut":1.15},
    "Gujarat":         {"Cotton":1.12,"Groundnut":1.18,"Cumin":1.35,"Castor":1.20,"Wheat":1.02},
    "Madhya Pradesh":  {"Soybean":1.14,"Wheat":1.05,"Chickpea":1.10,"Maize":1.02,"Tomato":0.98},
    "Rajasthan":       {"Wheat":1.03,"Mustard":1.15,"Cumin":1.28,"Barley":1.08,"Cotton":1.06},
    "West Bengal":     {"Rice":1.08,"Potato":1.15,"Jute":1.25,"Banana":1.10,"Mustard":1.12},
    "Bihar":           {"Rice":1.05,"Wheat":1.03,"Maize":1.08,"Potato":1.18,"Litchi":1.40},
    "Odisha":          {"Rice":1.06,"Potato":1.10,"Tomato":1.05,"Banana":1.08,"Jute":1.15},
    "Kerala":          {"Coconut":1.30,"Rubber":1.45,"Banana":1.20,"Pepper":1.50,"Cardamom":1.60},
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

