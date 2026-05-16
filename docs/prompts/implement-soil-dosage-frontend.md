# Implement Frontend Views for Soil Health (#1) and Dosage Advisor (#2)

## Context

Both features have complete, working backends but zero frontend. The KisanOS SPA currently has 6 tabs. These two features need two new tabs added to the tab bar and two new view components built from scratch.

The SPA uses React 18 loaded via CDN (no bundler). JSX files are loaded as `<script type="text/babel">` tags in `web/index.html`. All components are global — no imports/exports.

---

## Exact Files to Touch

| Action | File |
|--------|------|
| Create | `web/components/views/ViewSoil.jsx` |
| Create | `web/components/views/ViewDosage.jsx` |
| Edit | `web/lib/api.js` — add 2 new methods |
| Edit | `web/components/atoms.jsx` — add 2 tabs to TabBar |
| Edit | `web/components/app.jsx` — add to VIEW_MAP and CRUMB_MAP |
| Edit | `web/index.html` — add 2 `<script>` tags |

---

## Step 1 — Add API methods to `web/lib/api.js`

Append inside the `window.api = { ... }` object (before the closing `}`):

```js
soilAnalyze: (body) => _req('/soil/analyze', { method: 'POST', body }),

dosageRecommend: (body) => _req('/dosage/recommend', { method: 'POST', body }),
```

The `_req` function prefixes `window.API_BASE` and injects `X-API-Key: window.API_KEY` automatically.

---

## Step 2 — Add tabs to TabBar in `web/components/atoms.jsx`

The `tabs` array in the `TabBar` function (around line 340) currently has 6 entries. Append two more:

```js
{ k:'soil',   label: t('Soil Health') },
{ k:'dosage', label: t('Dosage Advisor') },
```

---

## Step 3 — Register views in `web/components/app.jsx`

`VIEW_MAP` (line 4) and `CRUMB_MAP` (line 13) — add:

```js
// VIEW_MAP
soil:   ViewSoil,
dosage: ViewDosage,

// CRUMB_MAP
soil:   'Soil Health',
dosage: 'Dosage Advisor',
```

---

## Step 4 — Add script tags to `web/index.html`

After the `ViewField.jsx` script tag (line 627), add:

```html
<script type="text/babel" src="components/views/ViewSoil.jsx?v=1778576200"></script>
<script type="text/babel" src="components/views/ViewDosage.jsx?v=1778576200"></script>
```

---

## Step 5 — Create `web/components/views/ViewSoil.jsx`

### API contract

**POST `/api/soil/analyze`**

Request body:
```json
{
  "N": 90,
  "P": 42,
  "K": 43,
  "ph": 6.5,
  "organic_matter_pct": 1.2,
  "target_crop": "wheat",
  "area_acres": 2.0
}
```

Response:
```json
{
  "deficiencies": [
    {
      "nutrient": "N",
      "current_value": 90,
      "optimal_min": 100,
      "optimal_max": 140,
      "deficit": 10,
      "severity": "medium"
    }
  ],
  "amendments": [
    {
      "name": "Urea",
      "deficiency_target": "N",
      "dose_kg_per_acre": 25,
      "dose_kg_per_hectare": 62,
      "dose_tonnes_per_acre": null,
      "dose_tonnes_per_hectare": null,
      "time_to_effect_days": 14,
      "application_method": "Broadcast and incorporate",
      "notes": "Apply before rain or irrigate after"
    }
  ],
  "soil_type": "Loamy",
  "narrative": "Your soil is slightly low in nitrogen...",
  "compatible_crops": ["wheat", "maize", "sunflower"]
}
```

### Inputs (sliders — same Slider component used in ViewCrop)

| Field | Label | Min | Max | Step | Unit | Default |
|-------|-------|-----|-----|------|------|---------|
| N | Nitrogen | 0 | 140 | 1 | kg/ha | 90 |
| P | Phosphorus | 5 | 145 | 1 | kg/ha | 42 |
| K | Potassium | 5 | 205 | 1 | kg/ha | 43 |
| ph | Soil pH | 3.5 | 9.5 | 0.1 | — | 6.5 |
| organic_matter_pct | Organic Matter | 0 | 20 | 0.1 | % | 1.2 |

Text inputs (not sliders):
- `target_crop` — text input, pre-filled from `profile.crop` (passed as prop)
- `area_acres` — number input, default 1.0

### UI layout

Follow the exact same structure as `ViewCrop.jsx`:

```
page-header div
  page-eyebrow: "soil health"
  page-title: "What does your <em>soil need?</em>"
  page-lede: "Enter your soil test numbers. We'll find the gaps and tell you exactly what to apply."

card rise rise-1 — "Soil Parameters" (NPK + pH sliders)
card rise rise-2 — "Field Details" (organic matter + crop + area)

<button className="btn btn-full"> Analyse Soil </button>

[while loading] <Loading label="Analysing soil profile…" />
[on error]      <ErrorCard title="Could not analyse soil" detail={error.detail} onRetry={...} />

[on result]
  card rise — narrative text in italic, with soil_type badge (leaf-colored eyebrow)
  
  if deficiencies.length > 0:
    card rise — "Deficiencies" section
      for each deficiency:
        row with nutrient name, severity badge (berry=high, sun=medium, leaf=low),
        current value vs optimal range
  else:
    card rise — green "✓ Soil looks healthy" message

  if amendments.length > 0:
    card rise — "Amendments" section
      for each amendment:
        name (bold), dose (kg/acre or tonnes/acre), application_method, notes,
        "Effect in {time_to_effect_days} days"

  card rise — "Compatible Crops" — flex-wrap list of crop pills
    (same pill style as used in ViewDisease/ViewAcoustic for tags)
```

### Severity badge colors
- `high` → `var(--berry)` with bg `rgba(232,112,95,0.14)`
- `medium` → `var(--sun)` with bg `rgba(240,192,96,0.14)`  
- `low` → `var(--leaf)` with bg `rgba(127,217,140,0.14)`

### Props received
`function ViewSoil({ profile, t }) { ... }`

---

## Step 6 — Create `web/components/views/ViewDosage.jsx`

### API contract

**POST `/api/dosage/recommend`**

Request body:
```json
{
  "pest_id": "armyworm",
  "crop": "maize",
  "crop_stage_days": 45,
  "area_acres": 2.0,
  "state": "Maharashtra"
}
```

Response:
```json
{
  "chemical_name": "Chlorpyrifos",
  "formulation": "20EC",
  "total_quantity_ml": 1000,
  "water_litres": 400,
  "timing": "dawn or dusk",
  "reapply_after_days": 7,
  "total_cost_inr": 68,
  "roi_protected_inr": 12400,
  "narrative": "Farmer-friendly advisory text from Haiku...",
  "source": "db"
}
```

### Known pest_ids (show as datalist suggestions, not a hard dropdown)
`armyworm`, `aphids`, `stem_borer`, `whitefly`, `fusarium_wilt`, `blast`, `blight`, `leaf_curl`, `powdery_mildew`, `red_mite`

### Inputs

| Field | UI | Default |
|-------|-----|---------|
| pest_id | text input with `<datalist>` of known pest_ids | "" |
| crop | text input | `profile.crop` |
| crop_stage_days | number input (0–365) | 30 |
| area_acres | number input (0.1–100) step 0.1 | 1.0 |
| state | text input | `profile.state` |

### UI layout

```
page-header div
  page-eyebrow: "dosage advisor"
  page-title: "Right dose, <em>right time.</em>"
  page-lede: "Tell us the pest and your crop. We'll calculate the exact quantity and cost."

card rise rise-1 — "Pest & Crop" (pest_id input + crop input)
card rise rise-2 — "Field Details" (crop_stage_days + area_acres + state)

<button className="btn btn-full"> Get Dosage </button>

[while loading] <Loading label="Calculating dosage…" />
[on error]      <ErrorCard title="Could not calculate dosage" detail={error.detail} onRetry={...} />

[on result]
  card rise — hero result
    Large: "{chemical_name} {formulation}"
    Sub: narrative text (italic)
    if source === "llm_fallback": small amber badge "AI estimate — verify with agronomist"

  card rise — "Application" grid (2-col on wide, 1-col on narrow)
    📦 Quantity: {total_quantity_ml} ml
    💧 Water: {water_litres} L
    ⏰ Timing: {timing}
    🔄 Reapply after: {reapply_after_days} days

  card rise — "Cost & ROI"
    Total cost: ₹{total_cost_inr}
    if roi_protected_inr != null:
      Yield protected: ₹{roi_protected_inr}
      ROI: {(roi_protected_inr / total_cost_inr).toFixed(1)}× return
    else:
      "Market price unavailable for ROI calculation"
```

### Props received
`function ViewDosage({ profile, t }) { ... }`

---

## UI Patterns to Reuse (don't reinvent)

All of these are global (no import needed):

| Symbol | Where defined | What it does |
|--------|--------------|-------------|
| `Slider` | `atoms.jsx` | Labeled range slider with hint |
| `Loading` | `atoms.jsx` | Centered spinner card |
| `ErrorCard` | `atoms.jsx` | Error card with optional retry |
| `useToast` | `atoms.jsx` | `const { add } = useToast()` → `add("msg", "info"\|"warn"\|"error")` |
| `window.api.soilAnalyze` | `api.js` (added in Step 1) | POST /soil/analyze |
| `window.api.dosageRecommend` | `api.js` (added in Step 1) | POST /dosage/recommend |

CSS classes from `index.html`:
- `card rise` / `card rise rise-1` / `card rise rise-2` — glassmorphic cards with staggered entrance
- `btn` / `btn-full` — button styles
- `page-header`, `page-eyebrow`, `page-title`, `page-lede` — page header structure
- `meta` — small muted label (used in card headers)

CSS variables: `--leaf`, `--berry`, `--sun`, `--glass-bg`, `--glass-border`, `--ink`, `--ink-soft`

---

## State pattern (copy from ViewCrop or ViewMarket)

```jsx
const [loading, setLoading] = React.useState(false);
const [error, setError]     = React.useState(null);
const [result, setResult]   = React.useState(null);
const { add: toast }        = useToast();

async function handleSubmit() {
  setLoading(true);
  setError(null);
  setResult(null);
  try {
    const data = await window.api.soilAnalyze({ N, P, K, ph, organic_matter_pct, target_crop, area_acres });
    setResult(data);
  } catch (err) {
    setError(err);
    toast('Analysis failed', 'error');
  } finally {
    setLoading(false);
  }
}
```

---

## Verification checklist

1. Two new tabs appear in the tab bar: "Soil Health" and "Dosage Advisor"
2. Clicking Soil Health tab shows sliders for N/P/K/pH/OM + analyse button
3. Submitting soil form calls `POST /api/soil/analyze` (check Network tab) and renders deficiencies + amendments
4. Clicking Dosage Advisor tab shows pest + crop inputs + get dosage button
5. Submitting dosage form calls `POST /api/dosage/recommend` and renders chemical name, quantities, cost
6. Loading spinner appears during fetch; error card appears if backend is offline
7. `profile.crop` and `profile.state` pre-fill the dosage form inputs
