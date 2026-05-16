# Soil Health Analysis API

Comprehensive soil analysis endpoint that detects nutrient deficiencies, recommends amendments, and provides farmer-friendly advisory narrative.

## Endpoint

```
POST /api/soil/analyze
```

## Request Schema

```json
{
  "N": 20,                          // Nitrogen (kg/ha), range 0-140
  "P": 10,                          // Phosphorus (kg/ha), range 5-145
  "K": 150,                         // Potassium (kg/ha), range 5-205
  "ph": 5.0,                        // Soil pH, range 3.5-9.5
  "organic_matter_pct": 1.0,        // Organic matter (%), range 0-20
  "target_crop": "rice",            // Optional: crop for crop-specific recommendations
  "area_acres": 2.5                 // Optional: farm area for dose calculations
}
```

## Response Schema

```json
{
  "deficiencies": [
    {
      "nutrient": "N",
      "current_value": 20.0,
      "optimal_min": 40.0,
      "optimal_max": 100.0,
      "deficit": 20.0,
      "severity": "high"              // high | medium | low
    }
  ],
  "amendments": [
    {
      "name": "Urea (46% N)",
      "deficiency_target": "N",
      "dose_kg_per_acre": 100.0,
      "dose_kg_per_hectare": 250.0,
      "dose_tonnes_per_acre": null,
      "dose_tonnes_per_hectare": null,
      "time_to_effect_days": 7,
      "application_method": "Dissolve in water and apply at V4-V6...",
      "notes": "Fast N source. Cheap. Apply with water..."
    }
  ],
  "soil_type": "Acidic Soil",       // Classified soil type
  "narrative": "Your soil narrative in farmer-friendly language...",
  "compatible_crops": ["rice", "wheat", "maize", ...]
}
```

## Examples

### Example 1: Deficient Soil (Acidic, Low Nutrients)

**Request:**
```bash
curl -X POST http://localhost:8000/api/soil/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: kisanos-dev-key-change-in-production" \
  -d '{
    "N": 20,
    "P": 10,
    "K": 150,
    "ph": 5.0,
    "organic_matter_pct": 1.0,
    "target_crop": "rice",
    "area_acres": 2.5
  }'
```

**Response:**
- Detects: N deficiency (high), P deficiency (high), pH acidic (high), organic matter (high)
- Recommends: Urea for N, SSP for P, Agricultural Lime for pH, FYM for organic matter
- Narrative: Hindi/English farmer-friendly advisory on amendments and timing
- Compatible crops: Rice, wheat, maize, cotton, chickpea, groundnut, sugarcane

---

### Example 2: Optimal Soil (Well-Balanced)

**Request:**
```bash
curl -X POST http://localhost:8000/api/soil/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: kisanos-dev-key-change-in-production" \
  -d '{
    "N": 85,
    "P": 35,
    "K": 180,
    "ph": 6.8,
    "organic_matter_pct": 3.5,
    "target_crop": "wheat",
    "area_acres": 5.0
  }'
```

**Response:**
- Deficiencies: Empty (no issues detected)
- Amendments: Empty
- Soil Type: Black/Regur Soil (excellent for cotton, wheat)
- Narrative: Positive feedback on soil health, maintenance recommendations
- Compatible crops: All crops (soil is well-suited)

---

## Features

1. **Nutrient Deficiency Detection**
   - Compares N, P, K, pH, and organic matter against ICAR optimal ranges
   - Severity classification (high/medium/low)
   - Calculates deficit amounts

2. **Amendment Recommendations**
   - ICAR-based amendment lookup (24+ different products)
   - Dose calculations per acre and per hectare
   - Application methods and timing
   - Time-to-effect estimates (7–60 days)

3. **Farmer-Friendly Narrative**
   - Generated via Claude Haiku 4.5
   - Hindi/English mix suitable for Indian farmers
   - Focuses on most urgent actions
   - Fallback narrative if API unavailable

4. **Crop Compatibility**
   - Matches crop soil requirements to current profile
   - Prioritizes crops that thrive in detected soil type
   - Based on ICAR agronomic guidelines

5. **Caching**
   - 1-hour TTL per soil fingerprint
   - Redis-backed with in-memory fallback
   - Fast responses for repeated queries

## Amendment Database

The system includes 24+ amendments across categories:

- **pH Correction**: Agricultural Lime, Hydrated Lime, Gypsum, Elemental Sulfur
- **Nitrogen**: Urea, DAP, FYM
- **Phosphorus**: Single Super Phosphate, DAP, Bone Meal
- **Potassium**: Muriate of Potash, Potassium Sulfate, Wood Ash
- **Organic Matter**: FYM, Compost, Green Manure

Each amendment includes:
- Recommended dose (kg/acre, kg/hectare, tonnes/acre, tonnes/hectare)
- Application method
- Time to effect
- Agronomic notes

## Error Handling

- **Missing API key**: Returns 403 Unauthorized
- **Invalid soil values**: Returns 422 Unprocessable Entity with field errors
- **No amendments found**: Returns empty amendments array (cache hit)
- **Haiku API failure**: Falls back to template-based narrative

## Caching

All responses are cached based on soil fingerprint (MD5 hash of N, P, K, pH, OM).

Same soil profile = cached response (< 20ms)

Cache TTL: 3600 seconds (1 hour)

Backend: Redis (falls back to in-memory LRU if Redis unavailable)

## Soil Type Classification

The endpoint returns one of 7 soil types:

1. **Acidic Soil** (pH < 5.5) — Needs lime, most crops struggle
2. **Alkaline Soil** (pH > 7.5) — Needs gypsum/sulfur, iron deficiency risk
3. **Black/Regur Soil** (K > 150, pH 6.0-7.5) — Excellent for cotton, sorghum, wheat
4. **Red/Laterite Soil** (N < 30, P < 20) — Low fertility, needs organic matter
5. **Alluvial Soil** (N > 80, pH 6.0-7.5) — Highly fertile, ideal for rice/wheat/vegetables
6. **Sandy Loam Soil** (P > 80) — Good drainage, suitable for groundnut/potato
7. **Loamy Soil** (default) — Well-balanced, suitable for most crops

---

## Deployment Notes

### Required Environment Variables

```
ANTHROPIC_API_KEY=sk-...          # For Haiku narrative generation
REDIS_HOST=localhost              # Redis server (optional, defaults to localhost)
REDIS_PORT=6379                   # Redis port
REDIS_DB=0                        # Redis database
REDIS_PASSWORD=                   # Redis password (optional)
```

### Dependencies

```
fastapi
uvicorn
anthropic
redis
pydantic
```

### Data Files

```
data/soil_amendments.json          # Amendment lookup table (24+ products)
```

---

## Use Cases

1. **Soil Testing Integration**: Farm testing labs return NPK + pH → call /api/soil/analyze → get amendments + narrative
2. **Mobile App**: Farmer inputs soil test results → real-time amendment recommendations
3. **Extension Services**: Batch analyze soil samples, export recommendations as PDF
4. **Farm Audits**: Track soil health over seasons, compare amendments effectiveness
5. **Crop Planning**: Analyze soil → compatible crops → plan next season

---

## Performance

- **Cold start** (first request): ~2–3 seconds (Haiku API call)
- **Cached response**: ~10–20 ms
- **Cache hit ratio**: High (farmer often reanalyzes same field)

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Haiku not responding | ANTHROPIC_API_KEY not set | Set API key in .env |
| 500 error on request | Server crash / missing import | Check logs, restart server |
| No amendments returned | Soil in optimal range | Expected behavior (no amendments needed) |
| Slow responses | Redis unavailable | Check Redis connection, falls back to in-memory |
| Cache not working | Redis failed silently | Check REDIS_HOST/PORT in config |

---

## Future Enhancements

1. **Seasonal amendment timing** — Recommend when to apply based on crop calendar
2. **Cost estimation** — Link amendments to market prices
3. **Graphical soil health dashboard** — Visualize nutrient trends over time
4. **Multi-field batch analysis** — Analyze 100+ soil samples in one request
5. **Soil health scorecarding** — Track soil quality index over seasons
