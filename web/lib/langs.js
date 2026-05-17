// GENERATED FILE — do not edit by hand. Source: scripts/i18n/langs.yaml
window.LANGS = [
  {
    "code": "en",
    "bcp47": "en-IN",
    "english_name": "English",
    "native_name": "English"
  },
  {
    "code": "hi",
    "bcp47": "hi-IN",
    "english_name": "Hindi",
    "native_name": "हिन्दी"
  },
  {
    "code": "te",
    "bcp47": "te-IN",
    "english_name": "Telugu",
    "native_name": "తెలుగు"
  },
  {
    "code": "ta",
    "bcp47": "ta-IN",
    "english_name": "Tamil",
    "native_name": "தமிழ்"
  },
  {
    "code": "kn",
    "bcp47": "kn-IN",
    "english_name": "Kannada",
    "native_name": "ಕನ್ನಡ"
  },
  {
    "code": "mr",
    "bcp47": "mr-IN",
    "english_name": "Marathi",
    "native_name": "मराठी"
  },
  {
    "code": "bn",
    "bcp47": "bn-IN",
    "english_name": "Bengali",
    "native_name": "বাংলা"
  },
  {
    "code": "gu",
    "bcp47": "gu-IN",
    "english_name": "Gujarati",
    "native_name": "ગુજરાતી"
  },
  {
    "code": "pa",
    "bcp47": "pa-IN",
    "english_name": "Punjabi",
    "native_name": "ਪੰਜਾਬੀ"
  },
  {
    "code": "ml",
    "bcp47": "ml-IN",
    "english_name": "Malayalam",
    "native_name": "മലയാളം"
  }
];
window.LANGS_BY_CODE = Object.fromEntries(window.LANGS.map(l => [l.code, l]));
window.bcp47 = function(code){ return (window.LANGS_BY_CODE[code]||window.LANGS_BY_CODE['en']).bcp47; };
window.isSupportedLang = function(code){ return !!window.LANGS_BY_CODE[code]; };
