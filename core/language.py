import streamlit as st
from deep_translator import GoogleTranslator

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

def T(text):
    """
    Translate text to the selected language.
    Uses session-state cache — each unique string is translated only once per session.
    This prevents rate-limiting from repeated GoogleTranslator calls on every render.
    """
    lang = st.session_state.get('lang_code', 'en')
    if lang == 'en' or not text:
        return text
    cache_key = f'_tcache_{lang}'
    if cache_key not in st.session_state:
        st.session_state[cache_key] = {}
    cache = st.session_state[cache_key]
    text_str = str(text)
    if text_str in cache:
        return cache[text_str]
    try:
        from deep_translator import GoogleTranslator
        result = GoogleTranslator(source='en', target=lang).translate(text_str)
        cache[text_str] = result if result else text_str
        return cache[text_str]
    except Exception:
        cache[text_str] = text_str
        return text_str



def T_batch(strings: list, lang: str) -> dict:
    """
    Translate a list of strings in bulk, returning {original: translated}.
    Called once when the language changes to pre-populate the cache.
    """
    if lang == 'en':
        return {s: s for s in strings}
    cache_key = f'_tcache_{lang}'
    if cache_key not in st.session_state:
        st.session_state[cache_key] = {}
    cache = st.session_state[cache_key]
    # Only translate strings not yet in cache
    to_translate = [s for s in strings if str(s) not in cache]
    if to_translate:
        try:
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source='en', target=lang)
            for s in to_translate:
                try:
                    result = translator.translate(str(s))
                    cache[str(s)] = result if result else str(s)
                except Exception:
                    cache[str(s)] = str(s)
        except Exception:
            for s in to_translate:
                cache[str(s)] = str(s)
    return cache


# All static UI strings — pre-translated when language changes
UI_STRINGS = [
    "Crop Recommender", "Disease + Vision", "Market Prices", "Irrigation",
    "Acoustic", "Field Watch", "Find the best crop for your field",
    "Enter your soil and climate details below.", "Read Instructions Aloud",
    "Soil Nutrients", "Climate Conditions", "Nitrogen (N) — kg/ha",
    "Phosphorus (P) — kg/ha", "Potassium (K) — kg/ha", "Soil pH",
    "Temperature (°C)", "Humidity (%)", "Rainfall (mm)",
    "Get Crop Recommendation", "Best Crop", "confidence", "Tip",
    "Detected Soil Type", "Soil Advice", "Read Result Aloud", "Other Options",
    "Confidence Across Top 8 Crops", "Your Input Summary", "Parameter", "Value",
    "Crop Disease & Vision AI",
    "Upload a photo of your crop for instant AI diagnosis — or use the symptom checker below.",
    "Method 1 — Photo Diagnosis (Recommended)", "Method 2 — Symptom Checker",
    "Select Crop for Diagnosis", "Upload leaf / stem / fruit photo",
    "Diagnose from Photo", "AI Confidence", "Treatment", "Prevention",
    "Vision AI Detected", "Detected", "Share on WhatsApp",
    "Use this if you cannot take a photo or want to confirm a diagnosis.",
    "Crop", "Symptom observed", "Diagnose by Symptom",
    "Live Mandi Prices",
    "Real-time prices from Agmarknet. State-calibrated 30-day forecast powered by Prophet.",
    "Read Instructions", "Your State", "Forecast horizon (days)",
    "Get Live Price + Forecast", "Best Price", "Lowest Price", "Avg / 30d",
    "Wait to sell", "Sell now", "Read Market Advice", "Price Forecast Chart",
    "Full Forecast Table", "Smart Irrigation & Fertilizer Advisor",
    "Get precise water and fertilizer recommendations based on your crop and weather.",
    "Live Weather (Auto-fill)", "Enter your city name", "Temp", "Humidity",
    "Wind", "Rain 1h", "Crop Details", "Growth Stage", "Field Area (acres)",
    "Rainfall in last 3 days (mm)", "Today Weather", "Get Irrigation Advice",
    "Water Need", "Net Irrigation", "Total Water", "for", "acre(s)",
    "No irrigation needed today!", "Recent rainfall is sufficient.",
    "Light irrigation recommended", "Apply", "Irrigation urgently needed",
    "Fertilizer Recommendation", "Acoustic Pest Detector",
    "Which crop did you record?", "Upload field audio recording",
    "Analyze for Pests", "Detection Confidence", "Dominant Frequency",
    "Signal Energy", "Spectral Pattern", "Risk Level", "Recommended Action",
    "Share Pest Alert on WhatsApp", "Read Result Aloud",
    "Field Watch — Satellite Intelligence",
    "Live satellite weather, wildfire alerts, flood warnings, locust swarm data, and air quality — all in one place.",
    "Your City / Nearest Town", "WhatsApp numbers to notify (one per line, with 91)",
    "Farmer Name", "Your Crop", "Scan My Field Now", "Overall Field Risk",
    "Current Weather", "Flood Risk (Next 48 hours)", "Wildfire / Field Fire Alert",
    "Desert Locust Alert", "Air Quality", "Read Field Alert Summary",
    "Send Field Alert to Contacts", "Emergency Helplines",
]


UI_STRINGS = [
    "Crop Recommender", "Disease + Vision", "Market Prices", "Irrigation",
    "Acoustic", "Field Watch", "Find the best crop for your field",
    "Enter your soil and climate details below.", "Read Instructions Aloud",
    "Soil Nutrients", "Climate Conditions", "Nitrogen (N) — kg/ha",
    "Phosphorus (P) — kg/ha", "Potassium (K) — kg/ha", "Soil pH",
    "Temperature (°C)", "Humidity (%)", "Rainfall (mm)",
    "Get Crop Recommendation", "Best Crop", "confidence", "Tip",
    "Detected Soil Type", "Soil Advice", "Read Result Aloud", "Other Options",
    "Confidence Across Top 8 Crops", "Your Input Summary", "Parameter", "Value",
    "Crop Disease & Vision AI",
    "Upload a photo of your crop for instant AI diagnosis — or use the symptom checker below.",
    "Method 1 — Photo Diagnosis (Recommended)", "Method 2 — Symptom Checker",
    "Select Crop for Diagnosis", "Upload leaf / stem / fruit photo",
    "Diagnose from Photo", "AI Confidence", "Treatment", "Prevention",
    "Vision AI Detected", "Detected", "Share on WhatsApp",
    "Use this if you cannot take a photo or want to confirm a diagnosis.",
    "Crop", "Symptom observed", "Diagnose by Symptom",
    "Live Mandi Prices",
    "Real-time prices from Agmarknet. State-calibrated 30-day forecast powered by Prophet.",
    "Read Instructions", "Your State", "Forecast horizon (days)",
    "Get Live Price + Forecast", "Best Price", "Lowest Price", "Avg / 30d",
    "Wait to sell", "Sell now", "Read Market Advice", "Price Forecast Chart",
    "Full Forecast Table", "Smart Irrigation & Fertilizer Advisor",
    "Get precise water and fertilizer recommendations based on your crop and weather.",
    "Live Weather (Auto-fill)", "Enter your city name", "Temp", "Humidity",
    "Wind", "Rain 1h", "Crop Details", "Growth Stage", "Field Area (acres)",
    "Rainfall in last 3 days (mm)", "Today Weather", "Get Irrigation Advice",
    "Water Need", "Net Irrigation", "Total Water", "for", "acre(s)",
    "No irrigation needed today!", "Recent rainfall is sufficient.",
    "Light irrigation recommended", "Apply", "Irrigation urgently needed",
    "Fertilizer Recommendation", "Acoustic Pest Detector",
    "Which crop did you record?", "Upload field audio recording",
    "Analyze for Pests", "Detection Confidence", "Dominant Frequency",
    "Signal Energy", "Spectral Pattern", "Risk Level", "Recommended Action",
    "Share Pest Alert on WhatsApp", "Read Result Aloud",
    "Field Watch — Satellite Intelligence",
    "Live satellite weather, wildfire alerts, flood warnings, locust swarm data, and air quality — all in one place.",
    "Your City / Nearest Town", "WhatsApp numbers to notify (one per line, with 91)",
    "Farmer Name", "Your Crop", "Scan My Field Now", "Overall Field Risk",
    "Current Weather", "Flood Risk (Next 48 hours)", "Wildfire / Field Fire Alert",
    "Desert Locust Alert", "Air Quality", "Read Field Alert Summary",
    "Send Field Alert to Contacts", "Emergency Helplines",
]

TAB1_INSTRUCTIONS = {
    'en': "Tell us about your soil and weather. Enter Nitrogen, Phosphorus, Potassium, pH, Temperature, Humidity, and Rainfall. Then tap Get Crop Recommendation.",
    'hi': "अपनी मिट्टी और मौसम की जानकारी भरें। नाइट्रोजन, फॉस्फोरस, पोटैशियम, पीएच, तापमान, नमी और बारिश डालें। फिर फसल सुझाव पाएं बटन दबाएं।",
    'te': "మీ నేల మరియు వాతావరణ వివరాలు నమోదు చేయండి. నత్రజని, భాస్వరం, పొటాషియం, pH, ఉష్ణోగ్రత, తేమ మరియు వర్షపాతం నమోదు చేయండి. తర్వాత పంట సూచన పొందండి బటన్ నొక్కండి.",
    'ta': "உங்கள் மண் மற்றும் வானிலை விவரங்களை உள்ளிடுங்கள். நைட்ரஜன், பாஸ்பரஸ், பொட்டாசியம், pH, வெப்பநிலை, ஈரப்பதம் மற்றும் மழையளவு உள்ளிடவும். பின்னர் பயிர் பரிந்துரை பெறுங்கள்.",
    'kn': "ನಿಮ್ಮ ಮಣ್ಣು ಮತ್ತು ಹವಾಮಾನ ವಿವರಗಳನ್ನು ನಮೂದಿಸಿ. ಸಾರಜನಕ, ರಂಜಕ, ಪೊಟ್ಯಾಸಿಯಂ, pH, ತಾಪಮಾನ, ತೇವಾಂಶ ಮತ್ತು ಮಳೆ ನಮೂದಿಸಿ. ನಂತರ ಬೆಳೆ ಶಿಫಾರಸು ಪಡೆಯಿರಿ.",
    'mr': "तुमच्या मातीची आणि हवामानाची माहिती भरा. नायट्रोजन, फॉस्फरस, पोटॅशियम, pH, तापमान, आर्द्रता आणि पाऊस टाका. मग पीक शिफारस मिळवा बटण दाबा.",
    'bn': "আপনার মাটি ও আবহাওয়ার তথ্য দিন। নাইট্রোজেন, ফসফরাস, পটাসিয়াম, pH, তাপমাত্রা, আর্দ্রতা ও বৃষ্টিপাত লিখুন। তারপর ফসলের পরামর্শ পান বোতামটি চাপুন।",
    'gu': "તમારી જમીન અને હવામાનની માહિતી ભરો. નાઇટ્રોજન, ફોસ્ફરસ, પોટેશિયમ, pH, તાપમાન, ભેજ અને વરસાદ દાખલ કરો. પછી પાક ભલામણ મેળવો બટન દબાવો.",
    'pa': "ਆਪਣੀ ਮਿੱਟੀ ਅਤੇ ਮੌਸਮ ਦੀ ਜਾਣਕਾਰੀ ਭਰੋ। ਨਾਈਟ੍ਰੋਜਨ, ਫਾਸਫੋਰਸ, ਪੋਟਾਸ਼ੀਅਮ, pH, ਤਾਪਮਾਨ, ਨਮੀ ਅਤੇ ਬਾਰਸ਼ ਦਰਜ ਕਰੋ। ਫਿਰ ਫ਼ਸਲ ਸਿਫ਼ਾਰਸ਼ ਲਓ ਬਟਨ ਦਬਾਓ।",
}

TAB2_INSTRUCTIONS = {
    'en': "Select your crop from the list. Then pick the symptom you see on your plant. Tap Diagnose to know the disease, how serious it is, and how to treat it.",
    'hi': "अपनी फसल चुनें। फिर अपने पौधे पर जो लक्षण दिख रहा है वो चुनें। बीमारी पहचानें बटन दबाएं और इलाज जानें।",
    'te': "మీ పంటను ఎంచుకోండి. మీ మొక్కపై కనిపించే లక్షణాన్ని ఎంచుకోండి. వ్యాధి నిర్ధారణ బటన్ నొక్కి చికిత్స తెలుసుకోండి.",
    'ta': "உங்கள் பயிரை தேர்ந்தெடுங்கள். உங்கள் தாவரத்தில் தெரியும் அறிகுறியை தேர்வு செய்யுங்கள். நோய் கண்டறி பொத்தானை அழுத்தி சிகிச்சை தெரிந்துகொள்ளுங்கள்.",
    'kn': "ನಿಮ್ಮ ಬೆಳೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ. ನಿಮ್ಮ ಗಿಡದಲ್ಲಿ ಕಾಣುವ ಲಕ್ಷಣವನ್ನು ಆರಿಸಿ. ರೋಗ ಪತ್ತೆ ಮಾಡಿ ಬಟನ್ ಒತ್ತಿ ಚಿಕಿತ್ಸೆ ತಿಳಿಯಿರಿ.",
    'mr': "तुमचे पीक निवडा. तुमच्या झाडावर दिसणारे लक्षण निवडा. आजार ओळखा बटण दाबा आणि उपाय जाणून घ्या.",
    'bn': "আপনার ফসল বেছে নিন। গাছে যে লক্ষণ দেখছেন তা নির্বাচন করুন। রোগ নির্ণয় বোতামটি চাপুন এবং চিকিৎসা জানুন।",
    'gu': "તમારો પાક પસંદ કરો. તમારા છોડ પર દેખાતા લક્ષણ પસંદ કરો. રોગ ઓળખો બટન દબાવો અને ઉપચાર જાણો.",
    'pa': "ਆਪਣੀ ਫ਼ਸਲ ਚੁਣੋ। ਆਪਣੇ ਪੌਦੇ 'ਤੇ ਦਿਖਾਈ ਦੇ ਰਹੇ ਲੱਛਣ ਦੀ ਚੋਣ ਕਰੋ। ਬਿਮਾਰੀ ਪਛਾਣੋ ਬਟਨ ਦਬਾਓ ਅਤੇ ਇਲਾਜ ਜਾਣੋ।",
}

TAB3_INSTRUCTIONS = {
    'en': "Choose your crop and how many days ahead you want to see prices. Tap Forecast Price to know the best day to sell at the highest price.",
    'hi': "अपनी फसल चुनें और कितने दिन आगे का भाव देखना है वो चुनें। भाव अनुमान लगाएं बटन दबाएं और जानें कब बेचना फायदेमंद है।",
    'te': "మీ పంట మరియు ఎన్ని రోజుల ముందు ధరలు చూడాలో ఎంచుకోండి. ధర అంచనా వేయండి బటన్ నొక్కి అమ్మడానికి మంచి రోజు తెలుసుకోండి.",
    'ta': "உங்கள் பயிர் மற்றும் எத்தனை நாட்கள் முன்னோக்கி விலை பார்க்கணும் என்று தேர்வு செய்யுங்கள். விலை கணிக்க பொத்தானை அழுத்தி எந்த நாளில் விற்பது லாபகரம் என்று தெரிந்துகொள்ளுங்கள்.",
    'kn': "ನಿಮ್ಮ ಬೆಳೆ ಮತ್ತು ಎಷ್ಟು ದಿನ ಮುಂದಿನ ಬೆಲೆ ನೋಡಬೇಕು ಎಂದು ಆಯ್ಕೆಮಾಡಿ. ಬೆಲೆ ಅಂದಾಜು ಬಟನ್ ಒತ್ತಿ ಯಾವ ದಿನ ಮಾರಾಟ ಮಾಡುವುದು ಲಾಭದಾಯಕ ಎಂದು ತಿಳಿಯಿರಿ.",
    'mr': "तुमचे पीक आणि किती दिवसांचा भाव बघायचा ते निवडा. भाव अंदाज लावा बटण दाबा आणि कधी विकणे फायदेशीर आहे ते जाणून घ्या.",
    'bn': "আপনার ফসল এবং কত দিন এগিয়ে দাম দেখতে চান তা বেছে নিন। দাম পূর্বাভাস বোতামটি চাপুন এবং কোন দিন বিক্রি করা লাভজনক তা জানুন।",
    'gu': "તમારો પાક અને કેટલા દિવસ આગળનો ભાવ જોવો છે તે પસંદ કરો. ભાવ અંદાજ લગાવો બટન દબાવો અને ક્યારે વેચવું ફાયદાકારક છે તે જાણો.",
    'pa': "ਆਪਣੀ ਫ਼ਸਲ ਅਤੇ ਕਿੰਨੇ ਦਿਨ ਅੱਗੇ ਦਾ ਭਾਅ ਦੇਖਣਾ ਹੈ ਉਹ ਚੁਣੋ। ਭਾਅ ਅੰਦਾਜ਼ਾ ਲਗਾਓ ਬਟਨ ਦਬਾਓ ਅਤੇ ਕਦੋਂ ਵੇਚਣਾ ਫਾਇਦੇਮੰਦ ਹੈ ਜਾਣੋ।",
}

TAB4_INSTRUCTIONS = {
    'en': "Enter your city to get live weather. Then select your crop, growth stage, and field size. Tell us how much rain fell in the last 3 days. Tap Get Irrigation Advice to know exactly how much water your field needs today.",
    'hi': "अपना शहर डालें ताकि मौसम अपने आप भर जाए। अपनी फसल, विकास का चरण और खेत का आकार चुनें। पिछले 3 दिनों की बारिश बताएं। पानी की सलाह लें बटन दबाएं।",
    'te': "లైవ్ వాతావరణం కోసం మీ నగరం నమోదు చేయండి. మీ పంట, పెరుగుదల దశ మరియు పొలం పరిమాణం ఎంచుకోండి. చివరి 3 రోజుల వర్షపాతం చెప్పండి. నీటిపారుదల సలహా పొందండి బటన్ నొక్కండి.",
    'ta': "நேரடி வானிலைக்கு உங்கள் நகரம் உள்ளிடுங்கள். உங்கள் பயிர், வளர்ச்சி நிலை மற்றும் வயல் அளவு தேர்வு செய்யுங்கள். கடந்த 3 நாட்கள் மழை அளவு சொல்லுங்கள். நீர்ப்பாசன ஆலோசனை பெற பொத்தானை அழுத்துங்கள்.",
    'kn': "ನೇರ ಹವಾಮಾನಕ್ಕಾಗಿ ನಿಮ್ಮ ನಗರ ನಮೂದಿಸಿ. ನಿಮ್ಮ ಬೆಳೆ, ಬೆಳವಣಿಗೆ ಹಂತ ಮತ್ತು ಜಮೀನಿನ ಗಾತ್ರ ಆಯ್ಕೆಮಾಡಿ. ಕಳೆದ 3 ದಿನಗಳ ಮಳೆ ಹೇಳಿ. ನೀರಾವರಿ ಸಲಹೆ ಪಡೆಯಿರಿ ಬಟನ್ ಒತ್ತಿ.",
    'mr': "लाइव्ह हवामानासाठी तुमचे शहर टाका. तुमचे पीक, वाढीचा टप्पा आणि शेताचा आकार निवडा. गेल्या 3 दिवसांचा पाऊस सांगा. पाणी सल्ला मिळवा बटण दाबा.",
    'bn': "সরাসরি আবহাওয়ার জন্য আপনার শহর লিখুন। আপনার ফসল, বৃদ্ধির পর্যায় এবং জমির আকার বেছে নিন। গত ৩ দিনের বৃষ্টি বলুন। সেচ পরামর্শ পান বোতামটি চাপুন।",
    'gu': "લાઇવ હવામાન માટે તમારું શહેર દાખલ કરો. તમારો પાક, વૃદ્ધિ તબક્કો અને ખેતરનું કદ પસંદ કરો. છેલ્લા 3 દિવસનો વરસાદ જણાવો. સિંચાઈ સલાહ મેળવો બટન દબાવો.",
    'pa': "ਲਾਈਵ ਮੌਸਮ ਲਈ ਆਪਣਾ ਸ਼ਹਿਰ ਦਰਜ ਕਰੋ। ਆਪਣੀ ਫ਼ਸਲ, ਵਿਕਾਸ ਪੜਾਅ ਅਤੇ ਖੇਤ ਦਾ ਆਕਾਰ ਚੁਣੋ। ਪਿਛਲੇ 3 ਦਿਨਾਂ ਦੀ ਬਾਰਸ਼ ਦੱਸੋ। ਪਾਣੀ ਦੀ ਸਲਾਹ ਲਓ ਬਟਨ ਦਬਾਓ।",
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

