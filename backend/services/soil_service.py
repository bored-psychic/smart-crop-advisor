"""
Soil Service — Soil type detection from nutrient + pH data.
Pure computation — no external API calls.
"""


def get_soil_type(N: float, P: float, K: float, ph: float) -> dict:
    """
    Classify soil type from nutrient levels and pH.
    Returns: {soil_type, advice, indicator}
    """
    if ph < 5.5:
        return {
            'soil_type': 'Acidic Soil',
            'advice': 'Add lime to increase pH. Most crops struggle below pH 5.5.',
            'indicator': '🔴',
        }
    elif ph > 7.5:
        return {
            'soil_type': 'Alkaline Soil',
            'advice': 'Add gypsum or sulfur to reduce pH. Iron deficiency common.',
            'indicator': '🟡',
        }
    elif K > 150 and ph >= 6.5:
        return {
            'soil_type': 'Black/Regur Soil',
            'advice': 'Excellent for cotton, sorghum, wheat. High water retention.',
            'indicator': '⚫',
        }
    elif N < 30 and P < 20:
        return {
            'soil_type': 'Red/Laterite Soil',
            'advice': 'Low fertility. Add organic matter and NPK fertilizers.',
            'indicator': '🔶',
        }
    elif N > 80 and 6.0 <= ph <= 7.5:
        return {
            'soil_type': 'Alluvial Soil',
            'advice': 'Highly fertile! Ideal for rice, wheat, sugarcane, vegetables.',
            'indicator': '🟢',
        }
    elif P > 80:
        return {
            'soil_type': 'Sandy Loam Soil',
            'advice': 'Good drainage. Suitable for groundnut, potato, vegetables.',
            'indicator': '🟤',
        }
    else:
        return {
            'soil_type': 'Loamy Soil',
            'advice': 'Well-balanced soil. Suitable for most crops.',
            'indicator': '🟢',
        }
