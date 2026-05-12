# Multilingual Web Frontend — Full i18n Coverage

**Date:** 2026-05-13  
**Scope:** `/web/` React/JSX frontend only  
**Goal:** Every user-visible string passes through `t()` and has translations in all 10 languages.

---

## Context

The web app already has a working i18n system (`/web/lib/i18n.js`, `/web/lib/bundles.json`) with 143 keys × 10 languages (en, hi, te, ta, kn, bn, mr, ml, gu, pa). The language switcher in the sidebar is live. However ~185 strings across 8 component files are still hardcoded and bypass translation. Five view components don't receive the `t` prop at all. This work completes the coverage so every word switches language when the user picks one.

---

## Architecture

No new files, no new libraries. Extend the existing pattern:

- `t = window.makeT(lang)` created in `app.jsx` via `useMemo`
- `t('English string as key')` — key equals the English value; fallback chain: current lang → en → raw key
- `t` passed as a prop to every view component

### Component wiring changes

| File | Change |
|------|--------|
| `app.jsx` | Add `t={t}` to ViewDisease, ViewMarket, ViewIrrigation, ViewAcoustic, ViewField calls |
| `ViewDisease.jsx` | Add `t` to function signature, wrap all strings |
| `ViewMarket.jsx` | Add `t` to function signature, wrap all strings |
| `ViewIrrigation.jsx` | Add `t` to function signature, wrap all strings |
| `ViewAcoustic.jsx` | Add `t` to function signature, wrap all strings |
| `ViewField.jsx` | Add `t` to function signature, wrap all strings |
| `ViewCrop.jsx` | Already receives `t`; wrap remaining hardcoded strings |
| `atoms.jsx` | Constants stay as plain JS objects; strings inside them translated at render time |

---

## String Wrapping Rules

### Standard strings
```jsx
// Before
<h3>Upload a recording</h3>
// After
<h3>{t('Upload a recording')}</h3>
```

### Strings with embedded HTML (page titles)
Keep HTML tags outside the key; translate the text content separately:
```jsx
// Before
<p>Hear the bugs <em>before they show.</em></p>
// After
<p>{t('Hear the bugs')} <em>{t('before they show.')}</em></p>
```

### Data constants in atoms.jsx (CALAMITY_TIPS, PEST_META, etc.)
Constants remain unchanged. Translate their string values at the render site:
```jsx
// CALAMITY_TIPS tips array — render site:
{tips.map(tip => <li key={tip}>{t(tip)}</li>)}

// PEST_META roleLabel — render site:
<span>{t(pest.roleLabel)}</span>

// GROWTH_STAGES — render site:
{GROWTH_STAGES.map(s => <option key={s}>{t(s)}</option>)}

// GOVT_HELPLINES name/description — render site:
<td>{t(line[0])}</td><td>{line[1]}</td><td>{t(line[2])}</td>

// ACOUSTIC_WARNING_LABELS — render site:
<p>{t(ACOUSTIC_WARNING_LABELS[code])}</p>
```

### Phone numbers, numeric values, emoji-only
Do NOT wrap in `t()` — these are language-neutral.

### Dynamic template strings
Split at the boundary between static and dynamic:
```jsx
// Before
<p>{count} mandis · state factor {factor}</p>
// After
<p>{count} {t('mandis')} · {t('state factor')} {factor}</p>
```

---

## Strings to Wrap — Complete Inventory

### atoms.jsx constants (translated at render sites, not in the constant itself)
- **CALAMITY_TIPS**: 8 weather types × 3 tips = 24 strings
- **PEST_META roleLabel**: 7 values (Pollinator, Pest, Ambient)
- **ACOUSTIC_WARNING_LABELS**: 5 values
- **GOVT_HELPLINES**: name + description for 6 helplines = 12 strings
- **GROWTH_STAGES**: 4 values (Initial, Development, Mid-season, Late season)

### ViewCrop.jsx (~25 new keys)
Page eyebrow/title/lede, slider labels (Nitrogen, Phosphorus, Potassium, Soil pH, Temperature, Humidity, Rainfall), slider hints (a little hungry, just right, plenty, acidic, sweet spot, a touch alkaline), loading text, error messages, result labels.

### ViewDisease.jsx (~20 new keys)
Page eyebrow/title/lede, card headings (Send a photo, What we see), drop zone text, loading/idle/error states, result labels (right now, treatment, prevention, top matches, via).

### ViewMarket.jsx (~28 new keys)
Page eyebrow/title/lede, slider label (Forecast horizon, days), button text, loading/error states, metric eyebrows (live mandi, best price, worst price, average price, our advice), table headers (Date, Price, Min, Max), status tags (LIVE, ESTIMATED), fallback messages.

### ViewIrrigation.jsx (~30 new keys)
Page eyebrow/title/lede, card headings (Your field, Get advice), slider labels (Field area, Recent rain, Temperature, Humidity, Wind speed) + units (ac, mm, °C, %, km/h), stage label, button text, loading/error states, metric tiles (Water needed, Net irrigation, Crop Kc factor), result labels (urgency, fertilizer, weather tips), FAO method text, table headers.

### ViewAcoustic.jsx (~33 new keys)
Page eyebrow/title/lede, card headings (Upload a recording, What we heard), drop zone text + file format help, placeholder (Crop type optional), tip text, button states (listening…, analyze, clear), loading/idle/error states, table headers (Icon, Name, Role, Severity, Freq range), section labels (band energy, top detections, Claude advice, quality notes, Reference library).

### ViewField.jsx (~38 new keys)
Page eyebrow/title/lede, button (Scan now), loading/error states, weather metric labels (Temperature, feels like, Humidity, Wind, surface wind, Rain 1h, last hour), alert card titles (Flood risk, Fire, Locust, Air Quality), risk labels (RISK), alert body text (Rain 48h, Hotspots nearby, Swarms nearby, source), card headings (Emergency helplines, Send to WhatsApp), button text (Copy, Open WhatsApp, Send to my number).

### app.jsx (~8 new keys)
CRUMB_MAP values (Crop Advisor, Leaf Doctor, Market Prices, Watering, Listen to Field, Field Watch), sidebar profile subtitle (farmer · since 2019), sidebar quote.

**Total new keys: ~185**  
**Total bundle entries to add: ~185 × 10 languages = ~1,850**

---

## bundles.json Changes

Add all ~185 new English keys to the `"en"` section first. Then add Claude-generated translations for hi, te, ta, kn, bn, mr, ml, gu, pa. Format matches existing entries exactly:

```json
{
  "en": {
    "Nitrogen": "Nitrogen",
    "a little hungry": "a little hungry",
    ...existing 143 keys...
  },
  "hi": {
    "Nitrogen": "नाइट्रोजन",
    "a little hungry": "थोड़ा भूखा",
    ...
  }
}
```

---

## Files Modified

| File | Type of change |
|------|---------------|
| `web/lib/bundles.json` | +~185 keys × 10 languages |
| `web/components/app.jsx` | Add `t={t}` to 5 view component calls |
| `web/components/atoms.jsx` | No change to constants; render-site callers change |
| `web/components/views/ViewCrop.jsx` | Wrap ~25 strings in t() |
| `web/components/views/ViewDisease.jsx` | Add t prop + wrap ~20 strings |
| `web/components/views/ViewMarket.jsx` | Add t prop + wrap ~28 strings |
| `web/components/views/ViewIrrigation.jsx` | Add t prop + wrap ~30 strings |
| `web/components/views/ViewAcoustic.jsx` | Add t prop + wrap ~33 strings |
| `web/components/views/ViewField.jsx` | Add t prop + wrap ~38 strings |

---

## Verification

1. **Switch language in sidebar** → every string in every tab changes (no English leaking through)
2. **Check all 6 tabs** in at least Hindi (hi) and Tamil (ta) — the most different scripts
3. **Check atoms.jsx render sites**: calamity tips, helpline names/descriptions, acoustic warnings, pest roles, growth stages all translate
4. **Fallback check**: temporarily pass an unknown lang code → UI still shows English
5. **No layout breaks**: translated strings may be longer — verify sliders, buttons, and metric tiles don't overflow in Hindi/Bengali
