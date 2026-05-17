# GENERATED FILE — do not edit by hand. Source: scripts/i18n/langs.yaml
from typing import Dict

LANGS: Dict[str, dict] = {'en': {'code': 'en', 'bcp47': 'en-IN', 'english_name': 'English', 'native_name': 'English'}, 'hi': {'code': 'hi', 'bcp47': 'hi-IN', 'english_name': 'Hindi', 'native_name': 'हिन्दी'}, 'te': {'code': 'te', 'bcp47': 'te-IN', 'english_name': 'Telugu', 'native_name': 'తెలుగు'}, 'ta': {'code': 'ta', 'bcp47': 'ta-IN', 'english_name': 'Tamil', 'native_name': 'தமிழ்'}, 'kn': {'code': 'kn', 'bcp47': 'kn-IN', 'english_name': 'Kannada', 'native_name': 'ಕನ್ನಡ'}, 'mr': {'code': 'mr', 'bcp47': 'mr-IN', 'english_name': 'Marathi', 'native_name': 'मराठी'}, 'bn': {'code': 'bn', 'bcp47': 'bn-IN', 'english_name': 'Bengali', 'native_name': 'বাংলা'}, 'gu': {'code': 'gu', 'bcp47': 'gu-IN', 'english_name': 'Gujarati', 'native_name': 'ગુજરાતી'}, 'pa': {'code': 'pa', 'bcp47': 'pa-IN', 'english_name': 'Punjabi', 'native_name': 'ਪੰਜਾਬੀ'}, 'ml': {'code': 'ml', 'bcp47': 'ml-IN', 'english_name': 'Malayalam', 'native_name': 'മലയാളം'}}

def is_supported(code: str) -> bool:
    return code in LANGS

def bcp47(code: str) -> str:
    return LANGS.get(code, LANGS['en'])['bcp47']
