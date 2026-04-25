def get_soil_type(N, P, K, ph):
    if ph < 5.5:
        return "Acidic Soil", "Add lime to increase pH. Most crops struggle below pH 5.5.", "🔴"
    elif ph > 7.5:
        return "Alkaline Soil", "Add gypsum or sulfur to reduce pH. Iron deficiency common.", "🟡"
    elif K > 150 and ph >= 6.5:
        return "Black/Regur Soil", "Excellent for cotton, sorghum, wheat. High water retention.", "⚫"
    elif N < 30 and P < 20:
        return "Red/Laterite Soil", "Low fertility. Add organic matter and NPK fertilizers.", "🔶"
    elif N > 80 and 6.0 <= ph <= 7.5:
        return "Alluvial Soil", "Highly fertile! Ideal for rice, wheat, sugarcane, vegetables.", "🟢"
    elif P > 80:
        return "Sandy Loam Soil", "Good drainage. Suitable for groundnut, potato, vegetables.", "🟤"
    else:
        return "Loamy Soil", "Well-balanced soil. Suitable for most crops.", "🟢"


