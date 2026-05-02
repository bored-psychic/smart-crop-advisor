"""
State-level price adjustment factors and India state list.
Based on APMC seasonal patterns from Agmarknet historical data.
"""

INDIA_STATES = [
    "Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh",
    "Maharashtra", "Odisha", "Punjab", "Rajasthan", "Tamil Nadu", "Telangana",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
]

STATE_PRICE_FACTORS: dict[str, dict[str, float]] = {
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
