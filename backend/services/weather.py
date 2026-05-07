import requests
import asyncio


class WeatherService:
    @staticmethod
    async def get_weather(city: str):
        return await asyncio.get_event_loop().run_in_executor(None, get_weather, city)



def get_weather(city):
    try:
        from core.config import settings
        api_key = settings.WEATHER_API_KEY
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

