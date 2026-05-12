# Multilingual Web Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wrap every user-visible string in every React/JSX view file in `t()` and add all missing keys (with translations for all 10 languages) to `bundles.json`.

**Architecture:** Extend the existing `window.makeT(lang)` pattern — no new libraries. Pass `t` as a prop down into inner subcomponents that currently lack it. Update `bundles.json` with new keys alongside each file change so the app never shows raw key strings.

**Tech Stack:** Vanilla React (window globals), custom i18n (`web/lib/i18n.js`), `web/lib/bundles.json`

---

## File Map

| File | Change |
|------|--------|
| `web/components/views/ViewDisease.jsx` | Pass `t` into PhotoPanel → PhotoResult, Top3Bars; wrap ~20 strings |
| `web/components/views/ViewMarket.jsx` | Pass `t` into ForecastChart, ForecastTable; wrap ~25 strings |
| `web/components/views/ViewAcoustic.jsx` | Pass `t` into RichResult, TopBars, BandChart; wrap ~35 strings |
| `web/components/views/ViewIrrigation.jsx` | Add `t` to signature; wrap ~28 strings |
| `web/components/views/ViewField.jsx` | Add `t` to signature; wrap ~35 strings |
| `web/components/views/ViewCrop.jsx` | Wrap ~22 remaining hardcoded strings |
| `web/lib/bundles.json` | Add ~180 new keys × 10 languages |

---

## Task 1 — Wire `t` into ViewDisease subcomponents

**Files:**
- Modify: `web/components/views/ViewDisease.jsx`

Sub-components `Top3Bars`, `PhotoResult`, and `PhotoPanel` are module-scope functions — they can't access `t` via closure from `ViewDisease`. Pass it as a prop.

- [ ] **Step 1: Update function signatures of inner components**

```jsx
// Line 17 — was: function Top3Bars({ top3 }) {
function Top3Bars({ top3, t }) {

// Line 36 — was: function PhotoResult({ result }) {
function PhotoResult({ result, t }) {

// Line 74 — was: function PhotoPanel() {
function PhotoPanel({ t }) {
```

- [ ] **Step 2: Pass `t` from PhotoPanel to its children**

In `PhotoPanel`'s return (line 202–203), change:
```jsx
// was:
{!loading && result && <PhotoResult result={result} />}
// after:
{!loading && result && <PhotoResult result={result} t={t} />}
```

And in the Top3Bars call inside PhotoResult (line 69):
```jsx
// was:
<Top3Bars top3={result.top3} />
// after:
<Top3Bars top3={result.top3} t={t} />
```

- [ ] **Step 3: Pass `t` from ViewDisease to PhotoPanel**

```jsx
// Line 221 — was:
<PhotoPanel />
// after:
<PhotoPanel t={t} />
```

- [ ] **Step 4: Commit**

```bash
git add web/components/views/ViewDisease.jsx
git commit -m "feat(i18n): wire t prop into ViewDisease subcomponents"
```

---

## Task 2 — Wrap all strings in ViewDisease.jsx + add new bundle keys

**Files:**
- Modify: `web/components/views/ViewDisease.jsx`
- Modify: `web/lib/bundles.json`

- [ ] **Step 1: Wrap strings in Top3Bars**

```jsx
// Line 22 — was:
<div className="page-eyebrow" style={{ marginBottom: 8 }}>top matches</div>
// after:
<div className="page-eyebrow" style={{ marginBottom: 8 }}>{t('top matches')}</div>
```

- [ ] **Step 2: Wrap strings in PhotoResult**

```jsx
// Line 44 — was:
via {result.model_used || 'Vision API'}
// after:
{t('via')} {result.model_used || 'Vision API'}

// Line 53 — was:
<div className="page-eyebrow" style={{ color: 'var(--sun)' }}>right now</div>
// after:
<div className="page-eyebrow" style={{ color: 'var(--sun)' }}>{t('right now')}</div>

// Line 59 — was:
<div className="page-eyebrow" style={{ color: 'var(--leaf)' }}>treatment</div>
// after:
<div className="page-eyebrow" style={{ color: 'var(--leaf)' }}>{t('treatment')}</div>

// Line 65 — was:
<div className="page-eyebrow" style={{ color: 'var(--leaf)' }}>prevention</div>
// after:
<div className="page-eyebrow" style={{ color: 'var(--leaf)' }}>{t('prevention')}</div>
```

- [ ] **Step 3: Wrap strings in errorMsg function**

```jsx
// Lines 141–146 — was:
function errorMsg(e) {
  if (!e) return 'Something went wrong.';
  if (e.status === 401 || e.status === 403) return 'API key issue — check your config.js setup.';
  if (!e.status && e.message) return 'No connection — check your network and try again.';
  return e.detail || e.message || 'Analysis failed.';
}
// after (errorMsg now takes t):
function errorMsg(e, t) {
  if (!e) return t('Something went wrong.');
  if (e.status === 401 || e.status === 403) return t('API key issue — check your config.js setup.');
  if (!e.status && e.message) return t('No connection — check your network and try again.');
  return e.detail || e.message || t('Analysis failed.');
}
```

Update the call site at line 197:
```jsx
// was:
detail={errorMsg(error)}
// after:
detail={errorMsg(error, t)}
```

- [ ] **Step 4: Wrap strings in PhotoPanel JSX**

```jsx
// Line 152 — was:
<h3>Send a photo</h3>
// after:
<h3>{t('Send a photo')}</h3>

// Line 154 — was:
<span className="muted small" style={{ fontStyle: 'italic' }}>loading crops…</span>
// after:
<span className="muted small" style={{ fontStyle: 'italic' }}>{t('loading crops…')}</span>

// Line 173 — was:
<div style={{ marginTop: 10, fontSize: 14 }}><strong>Drop a leaf photo here</strong></div>
// after:
<div style={{ marginTop: 10, fontSize: 14 }}><strong>{t('Drop a leaf photo here')}</strong></div>

// Line 174 — was:
<div className="muted small" style={{ marginTop: 4 }}>or click to choose · jpg, png, webp</div>
// after:
<div className="muted small" style={{ marginTop: 4 }}>{t('or click to choose · jpg, png, webp')}</div>

// Line 187 — was:
<h3>What we see</h3>
// after:
<h3>{t('What we see')}</h3>

// Line 191 — was:
<div className="muted" style={{ padding: '30px 0', textAlign: 'center' }}>Send a photo and we'll have a look. 🌿</div>
// after:
<div className="muted" style={{ padding: '30px 0', textAlign: 'center' }}>{t("Send a photo and we'll have a look. 🌿")}</div>

// Line 193 — was:
{loading && <Loading label="Analyzing leaf…" />}
// after:
{loading && <Loading label={t('Analyzing leaf…')} />}

// Line 196 — was:
title="Could not analyze photo"
// after:
title={t('Could not analyze photo')}
```

- [ ] **Step 5: Wrap strings in ViewDisease page header**

```jsx
// Lines 212–217 — was:
<Topbar crumb="Leaf Doctor" />
...
<div className="page-eyebrow">leaf doctor</div>
<h1 className="page-title">A <em>second pair of eyes</em> for sick leaves.</h1>
<p className="page-lede">Snap a photo of a worried leaf. We'll gently look it over...</p>
// after:
<Topbar crumb={t('Leaf Doctor')} />
...
<div className="page-eyebrow">{t('leaf doctor')}</div>
<h1 className="page-title">{t('A')} <em>{t('second pair of eyes')}</em> {t('for sick leaves.')}</h1>
<p className="page-lede">{t("Snap a photo of a worried leaf. We'll gently look it over and tell you what's likely going on, with the kindest fix.")}</p>
```

- [ ] **Step 6: Add new ViewDisease keys to bundles.json "en" section**

Add these key-value pairs to the `"en"` object in `bundles.json`:
```json
"top matches": "top matches",
"via": "via",
"right now": "right now",
"treatment": "treatment",
"prevention": "prevention",
"Something went wrong.": "Something went wrong.",
"API key issue — check your config.js setup.": "API key issue — check your config.js setup.",
"Analysis failed.": "Analysis failed.",
"Send a photo": "Send a photo",
"loading crops…": "loading crops…",
"Drop a leaf photo here": "Drop a leaf photo here",
"or click to choose · jpg, png, webp": "or click to choose · jpg, png, webp",
"What we see": "What we see",
"Send a photo and we'll have a look. 🌿": "Send a photo and we'll have a look. 🌿",
"Analyzing leaf…": "Analyzing leaf…",
"Could not analyze photo": "Could not analyze photo",
"Leaf Doctor": "Leaf Doctor",
"leaf doctor": "leaf doctor",
"A": "A",
"second pair of eyes": "second pair of eyes",
"for sick leaves.": "for sick leaves.",
"Snap a photo of a worried leaf. We'll gently look it over and tell you what's likely going on, with the kindest fix.": "Snap a photo of a worried leaf. We'll gently look it over and tell you what's likely going on, with the kindest fix."
```

- [ ] **Step 7: Commit**

```bash
git add web/components/views/ViewDisease.jsx web/lib/bundles.json
git commit -m "feat(i18n): wrap all strings in ViewDisease + add en bundle keys"
```

---

## Task 3 — Wire `t` and wrap all strings in ViewMarket.jsx

**Files:**
- Modify: `web/components/views/ViewMarket.jsx`
- Modify: `web/lib/bundles.json`

`ForecastChart` (line 5) and `ForecastTable` (line 61) are module-scope subcomponents.

- [ ] **Step 1: Update signatures and pass t**

```jsx
// Line 5 — was:
function ForecastChart({ forecast }) {
// after:
function ForecastChart({ forecast, t }) {

// Line 61 — was:
function ForecastTable({ forecast }) {
// after:
function ForecastTable({ forecast, t }) {

// In ViewMarket JSX, update calls — was:
<ForecastChart forecast={result.forecast} />
<ForecastTable forecast={result.forecast} />
// after:
<ForecastChart forecast={result.forecast} t={t} />
<ForecastTable forecast={result.forecast} t={t} />
```

- [ ] **Step 2: Wrap strings in ForecastChart**

```jsx
// Line 9 — was:
Not enough data to chart.
// after:
{t('Not enough data to chart.')}
```

- [ ] **Step 3: Wrap table headers in ForecastTable**

```jsx
// Lines 66–69 — was:
<th style={thStyle}>Date</th>
<th style={thStyle}>Price</th>
<th style={thStyle}>Min</th>
<th style={thStyle}>Max</th>
// after:
<th style={thStyle}>{t('Date')}</th>
<th style={thStyle}>{t('Price')}</th>
<th style={thStyle}>{t('Min')}</th>
<th style={thStyle}>{t('Max')}</th>
```

- [ ] **Step 4: Wrap strings in ViewMarket page header and controls**

```jsx
// Line 113 — was:
<Topbar crumb="Market" />
// after:
<Topbar crumb={t('Market')} />

// Lines 116–118 — was:
<div className="page-eyebrow">market</div>
<h1 className="page-title">A <em>fair price,</em> a calm decision.</h1>
<h1 className="page-lede">We watch the mandi prices...</h1>
// after:
<div className="page-eyebrow">{t('market')}</div>
<h1 className="page-title">{t('A')} <em>{t('fair price,')}</em> {t('a calm decision.')}</h1>
<p className="page-lede">{t("We watch the mandi prices and gently tell you whether to sell now or wait a couple of weeks. No charts to wrestle with.")}</p>

// Line 136 — was:
<Slider label="Forecast horizon" unit="days" .../>
// after:
<Slider label={t('Forecast horizon')} unit={t('days')} .../>

// Line 139 — was:
📊 Get forecast
// after:
{t('📊 Get forecast')}

// Line 143 — was:
{loading && <Loading label="Fetching market data…" />}
// after:
{loading && <Loading label={t('Fetching market data…')} />}

// Lines 147–148 — was:
title="Could not fetch forecast"
detail={error.status === 401 || error.status === 403 ? 'API key issue — check your configuration.' : !error.status ? 'Network error — please check your connection.' : error.detail || 'Unexpected error.'}
// after:
title={t('Could not fetch forecast')}
detail={error.status === 401 || error.status === 403 ? t('API key issue — check your configuration.') : !error.status ? t('Network error — please check your connection.') : error.detail || t('Unexpected error.')}
```

- [ ] **Step 5: Wrap strings in result section**

```jsx
// Line 159 — was:
<div className="page-eyebrow">live mandi · {result.live_price.source}</div>
// after:
<div className="page-eyebrow">{t('live mandi')} · {result.live_price.source}</div>

// Line 162 — was:
{result.live_price.mandis_checked} mandis · state factor {result.live_price.state_factor?.toFixed(2) ?? '—'}
// after:
{result.live_price.mandis_checked} {t('mandis')} · {t('state factor')} {result.live_price.state_factor?.toFixed(2) ?? '—'}

// Lines 166–167 — was:
<span ...>🟢 LIVE</span>
<span ...>🟡 ESTIMATED</span>
// after:
<span ...>{t('🟢 LIVE')}</span>
<span ...>{t('🟡 ESTIMATED')}</span>

// Line 173 — was:
Live mandi data not available — showing model forecast only.
// after:
{t('Live mandi data not available — showing model forecast only.')}

// Lines 181, 186, 191 — was:
<div className="page-eyebrow">best price</div>
<div className="page-eyebrow">worst price</div>
<div className="page-eyebrow">average price</div>
// after:
<div className="page-eyebrow">{t('best price')}</div>
<div className="page-eyebrow">{t('worst price')}</div>
<div className="page-eyebrow">{t('average price')}</div>

// Line 193 — was:
<div className="small muted" style={{ marginTop: 4 }}>over {forecastDays} days</div>
// after:
<div className="small muted" style={{ marginTop: 4 }}>{t('over')} {forecastDays} {t('days')}</div>

// Line 200 — was:
<div className="page-eyebrow">our advice</div>
// after:
<div className="page-eyebrow">{t('our advice')}</div>

// Line 207 — was:
<h3 style={{ margin: 0 }}>Price forecast · {result.crop}</h3>
// after:
<h3 style={{ margin: 0 }}>{t('Price forecast')} · {result.crop}</h3>

// Line 218 — was:
Full forecast table ({result.forecast.length} days)
// after:
{t('Full forecast table')} ({result.forecast.length} {t('days')})
```

- [ ] **Step 6: Add new ViewMarket keys to bundles.json "en" section**

```json
"Not enough data to chart.": "Not enough data to chart.",
"Date": "Date",
"Price": "Price",
"Min": "Min",
"Max": "Max",
"Market": "Market",
"market": "market",
"fair price,": "fair price,",
"a calm decision.": "a calm decision.",
"We watch the mandi prices and gently tell you whether to sell now or wait a couple of weeks. No charts to wrestle with.": "We watch the mandi prices and gently tell you whether to sell now or wait a couple of weeks. No charts to wrestle with.",
"Forecast horizon": "Forecast horizon",
"days": "days",
"📊 Get forecast": "📊 Get forecast",
"Fetching market data…": "Fetching market data…",
"Could not fetch forecast": "Could not fetch forecast",
"API key issue — check your configuration.": "API key issue — check your configuration.",
"Network error — please check your connection.": "Network error — please check your connection.",
"Unexpected error.": "Unexpected error.",
"live mandi": "live mandi",
"mandis": "mandis",
"state factor": "state factor",
"🟢 LIVE": "🟢 LIVE",
"🟡 ESTIMATED": "🟡 ESTIMATED",
"Live mandi data not available — showing model forecast only.": "Live mandi data not available — showing model forecast only.",
"best price": "best price",
"worst price": "worst price",
"average price": "average price",
"over": "over",
"our advice": "our advice",
"Price forecast": "Price forecast",
"Full forecast table": "Full forecast table"
```

- [ ] **Step 7: Commit**

```bash
git add web/components/views/ViewMarket.jsx web/lib/bundles.json
git commit -m "feat(i18n): wrap all strings in ViewMarket + add en bundle keys"
```

---

## Task 4 — Wire `t` and wrap all strings in ViewAcoustic.jsx

**Files:**
- Modify: `web/components/views/ViewAcoustic.jsx`
- Modify: `web/lib/bundles.json`

`TopBars` (line 28), `BandChart` (line 48), and `RichResult` (line 70) are module-scope subcomponents.

- [ ] **Step 1: Update subcomponent signatures**

```jsx
// Line 28 — was:
function TopBars({ top3 }){
// after:
function TopBars({ top3, t }){

// Line 48 — was:
function BandChart({ bandEnergy }){
// after:
function BandChart({ bandEnergy, t }){

// Line 70 — was:
function RichResult({ r }){
// after:
function RichResult({ r, t }){
```

- [ ] **Step 2: Pass `t` from RichResult to TopBars and BandChart**

```jsx
// Line 129 — was:
<TopBars top3={r.top3}/>
// after:
<TopBars top3={r.top3} t={t}/>

// Line 159 — was:
<BandChart bandEnergy={r.band_energy}/>
// after:
<BandChart bandEnergy={r.band_energy} t={t}/>
```

- [ ] **Step 3: Pass `t` from ViewAcoustic to RichResult**

```jsx
// Line 450 — was:
{result && !loading && <RichResult r={result}/>}
// after:
{result && !loading && <RichResult r={result} t={t}/>}
```

- [ ] **Step 4: Wrap strings in TopBars and BandChart**

```jsx
// Line 33 — was:
<div style={{...}}>top detections</div>
// after:
<div style={{...}}>{t('top detections')}</div>

// Line 54 — was:
<div style={{...}}>band energy</div>
// after:
<div style={{...}}>{t('band energy')}</div>
```

- [ ] **Step 5: Wrap strings in RichResult**

```jsx
// Lines 111–115 — was:
{label:'Confidence', value:`${Math.round(r.confidence||0)}%`},
{label:'Duration',   value:`${r.analyzed_seconds||0}s / ${r.duration_seconds||0}s`},
{label:'Sample rate',value:`${r.sample_rate||0} Hz`},
{label:'Energy',     value:r.energy_level||'—'},
// after:
{label:t('Confidence'), value:`${Math.round(r.confidence||0)}%`},
{label:t('Duration'),   value:`${r.analyzed_seconds||0}s / ${r.duration_seconds||0}s`},
{label:t('Sample rate'),value:`${r.sample_rate||0} Hz`},
{label:t('Energy'),     value:r.energy_level||'—'},

// Line 138 — was:
<div style={{...}}>Claude advice</div>
// after:
<div style={{...}}>{t('Claude advice')}</div>

// Line 149 — was:
<div style={{...}}>quality notes</div>
// after:
<div style={{...}}>{t('quality notes')}</div>

// Line 152 — was:
{window.ACOUSTIC_WARNING_LABELS?.[w] || w}
// after:
{t(window.ACOUSTIC_WARNING_LABELS?.[w] || w)}

// Line 171 — was:
Reference library ({Object.keys(window.PEST_META||{}).length} known insects)
// after:
{t('Reference library')} ({Object.keys(window.PEST_META||{}).length} {t('known insects')})

// Line 177 — was:
{['Icon','Name','Role','Severity','Freq range'].map(h=>( <th ...>{h}</th> ))}
// after:
{['Icon','Name','Role','Severity','Freq range'].map(h=>( <th key={h} ...>{t(h)}</th> ))}

// Line 187 — was:
<td style={{...}}>{meta.roleLabel}</td>
// after:
<td style={{...}}>{t(meta.roleLabel)}</td>
```

- [ ] **Step 6: Wrap strings in ViewAcoustic main component**

```jsx
// Line 244 — was:
setPreCheckError('File too large (max 20 MB)');
// after:
setPreCheckError(t('File too large (max 20 MB)'));

// Line 268 — was:
setPreCheckError("Cannot preview this audio format — upload anyway to let the server analyze it.");
// after:
setPreCheckError(t("Cannot preview this audio format — upload anyway to let the server analyze it."));

// Lines 299–300 — was:
if(status===401||status===403) message = 'Invalid or missing API key.';
else if(!status)               message = 'Network error — check your connection.';
// after:
if(status===401||status===403) message = t('Invalid or missing API key.');
else if(!status)               message = t('Network error — check your connection.');

// Line 295 — was:
return {status:null, detail:'Unknown error', message:'Unknown error'};
// after:
return {status:null, detail:t('Unknown error'), message:t('Unknown error')};

// Line 327 — was:
<Topbar crumb="Listen"/>
// after:
<Topbar crumb={t('Listen')}/>

// Lines 330–332 — was:
<div className="page-eyebrow">listen</div>
<h1 className="page-title">Hear the bugs <em>before they show.</em></h1>
<p className="page-lede">Hold your phone near a plant...</p>
// after:
<div className="page-eyebrow">{t('listen')}</div>
<h1 className="page-title">{t('Hear the bugs')} <em>{t('before they show.')}</em></h1>
<p className="page-lede">{t("Hold your phone near a plant for a few seconds. We'll listen for the tiny sounds pests make and warn you a week early.")}</p>

// Line 339 — was:
<h3>Upload a recording</h3><span className="tag">~6 seconds</span>
// after:
<h3>{t('Upload a recording')}</h3><span className="tag">{t('~6 seconds')}</span>

// Line 344 — was:
placeholder="Crop type (optional)"
// after:
placeholder={t('Crop type (optional)')}

// Line 362 — was:
{file ? <strong>{file.name}</strong> : <strong>Drag &amp; drop your field audio here</strong>}
// after:
{file ? <strong>{file.name}</strong> : <strong>{t('Drag & drop your field audio here')}</strong>}

// Line 365–367 — was:
{file ? `${(file.size/1024).toFixed(0)} KB · ready` : 'or click to choose · wav · mp3 · m4a · ogg · webm'}
// after:
{file ? `${(file.size/1024).toFixed(0)} ${t('KB · ready')}` : t('or click to choose · wav · mp3 · m4a · ogg · webm')}

// Line 403 — was:
<div className="muted small" style={{fontStyle:'italic'}}>tip: 15–30 cm from the stem · breathe slowly</div>
// after:
<div className="muted small" style={{fontStyle:'italic'}}>{t('tip: 15–30 cm from the stem · breathe slowly')}</div>

// Line 405–407 — was:
<button className="btn" onClick={clearAll}>clear</button>
<button ...>{loading ? '🎧 listening…' : '🔊 analyze'}</button>
// after:
<button className="btn" onClick={clearAll}>{t('clear')}</button>
<button ...>{loading ? t('🎧 listening…') : t('🔊 analyze')}</button>

// Line 416 — was:
<h3>What we heard</h3>
// after:
<h3>{t('What we heard')}</h3>

// Line 433 — was:
{loading && <Loading label="Listening to your field…"/>}
// after:
{loading && <Loading label={t('Listening to your field…')}/>}

// Line 438 — was:
title="Analysis failed"
// after:
title={t('Analysis failed')}

// Line 446 — was:
Drop a recording on the left to begin. 🐛
// after:
{t('Drop a recording on the left to begin. 🐛')}
```

- [ ] **Step 7: Add new ViewAcoustic keys to bundles.json "en" section**

```json
"top detections": "top detections",
"band energy": "band energy",
"Confidence": "Confidence",
"Duration": "Duration",
"Sample rate": "Sample rate",
"Energy": "Energy",
"Claude advice": "Claude advice",
"quality notes": "quality notes",
"Reference library": "Reference library",
"known insects": "known insects",
"Icon": "Icon",
"Name": "Name",
"Role": "Role",
"Severity": "Severity",
"Freq range": "Freq range",
"File too large (max 20 MB)": "File too large (max 20 MB)",
"Cannot preview this audio format — upload anyway to let the server analyze it.": "Cannot preview this audio format — upload anyway to let the server analyze it.",
"Unknown error": "Unknown error",
"Invalid or missing API key.": "Invalid or missing API key.",
"Network error — check your connection.": "Network error — check your connection.",
"Listen": "Listen",
"listen": "listen",
"Hear the bugs": "Hear the bugs",
"before they show.": "before they show.",
"Hold your phone near a plant for a few seconds. We'll listen for the tiny sounds pests make and warn you a week early.": "Hold your phone near a plant for a few seconds. We'll listen for the tiny sounds pests make and warn you a week early.",
"Upload a recording": "Upload a recording",
"~6 seconds": "~6 seconds",
"Crop type (optional)": "Crop type (optional)",
"Drag & drop your field audio here": "Drag & drop your field audio here",
"or click to choose · wav · mp3 · m4a · ogg · webm": "or click to choose · wav · mp3 · m4a · ogg · webm",
"KB · ready": "KB · ready",
"tip: 15–30 cm from the stem · breathe slowly": "tip: 15–30 cm from the stem · breathe slowly",
"clear": "clear",
"🎧 listening…": "🎧 listening…",
"🔊 analyze": "🔊 analyze",
"What we heard": "What we heard",
"Listening to your field…": "Listening to your field…",
"Analysis failed": "Analysis failed",
"Drop a recording on the left to begin. 🐛": "Drop a recording on the left to begin. 🐛"
```

- [ ] **Step 8: Commit**

```bash
git add web/components/views/ViewAcoustic.jsx web/lib/bundles.json
git commit -m "feat(i18n): wrap all strings in ViewAcoustic + add en bundle keys"
```

---

## Task 5 — Add `t` and wrap all strings in ViewIrrigation.jsx

**Files:**
- Modify: `web/components/views/ViewIrrigation.jsx`
- Modify: `web/lib/bundles.json`

- [ ] **Step 1: Add `t` to function signature (if missing)**

Read line 1 of ViewIrrigation.jsx. If the signature is `function ViewIrrigation({ profile, setProfile })`, change to:
```jsx
function ViewIrrigation({ profile, setProfile, t })
```

- [ ] **Step 2: Wrap page header strings**

```jsx
// was:
<Topbar crumb="Watering"/>
<div className="page-eyebrow">water</div>
<h1 className="page-title">Just enough water, <em>just in time.</em></h1>
<p className="page-lede">We do the FAO water math behind the scenes and tell you simply: how many liters today, and when to water next.</p>
// after:
<Topbar crumb={t('Watering')}/>
<div className="page-eyebrow">{t('water')}</div>
<h1 className="page-title">{t('Just enough water,')} <em>{t('just in time.')}</em></h1>
<p className="page-lede">{t("We do the FAO water math behind the scenes and tell you simply: how many liters today, and when to water next.")}</p>
```

- [ ] **Step 3: Wrap GROWTH_STAGES at render site**

Find the place where GROWTH_STAGES is mapped (around line 120–133). The `GROWTH_STAGES` constant stays unchanged. Wrap each stage name in `t()` at the render call:
```jsx
// was (wherever stages are rendered, e.g.):
{GROWTH_STAGES.map(s => <div key={s} className={...} onClick={...}>{s}</div>)}
// after:
{GROWTH_STAGES.map(s => <div key={s} className={...} onClick={...}>{t(s)}</div>)}
```

- [ ] **Step 4: Wrap card headings and field labels**

```jsx
// was:
<h3>Your field</h3>
// after:
<h3>{t('Your field')}</h3>

// was:
<span className="name">Growth stage</span>
// after:
<span className="name">{t('Growth stage')}</span>

// was:
<h3>Get advice</h3>
// after:
<h3>{t('Get advice')}</h3>
```

- [ ] **Step 5: Wrap slider labels and button**

```jsx
// was:
<Slider label="Field area" unit="ac" .../>
<Slider label="Recent rain" unit="mm" .../>
<Slider label="Temperature" unit="°C" .../>
<Slider label="Humidity" unit="%" .../>
<Slider label="Wind speed" unit="km/h" .../>
// after:
<Slider label={t('Field area')} unit={t('ac')} .../>
<Slider label={t('Recent rain')} unit={t('mm')} .../>
<Slider label={t('Temperature')} unit="°C" .../>
<Slider label={t('Humidity')} unit="%" .../>
<Slider label={t('Wind speed')} unit={t('km/h')} .../>

// was:
Calculate irrigation
// after:
{t('Calculate irrigation')}

// was:
<Loading label="Calculating irrigation…"/>
// after:
<Loading label={t('Calculating irrigation…')}/>

// was:
title="Could not calculate"
// after:
title={t('Could not calculate')}

// was:
'No connection — check your network and try again.'
// after:
t('No connection — check your network and try again.')
```

- [ ] **Step 6: Wrap result metric labels and advice text**

```jsx
// was:
Water needed
// after:
{t('Water needed')}

// was:
Net irrigation
// after:
{t('Net irrigation')}

// was:
Crop Kc factor
// after:
{t('Crop Kc factor')}

// was:
urgency · {result.urgency}
// after:
{t('urgency')} · {result.urgency}

// was:
fertilizer · {result.fertilizer.growth_stage}
// after:
{t('fertilizer')} · {result.fertilizer.growth_stage}

// was:
<strong>Nitrogen:</strong>
// after:
<strong>{t('Nitrogen:')}</strong>

// was:
weather tips · ...
// after:
{t('weather tips')} · ...
```

- [ ] **Step 7: Add new ViewIrrigation keys to bundles.json "en" section**

```json
"Watering": "Watering",
"water": "water",
"Just enough water,": "Just enough water,",
"just in time.": "just in time.",
"We do the FAO water math behind the scenes and tell you simply: how many liters today, and when to water next.": "We do the FAO water math behind the scenes and tell you simply: how many liters today, and when to water next.",
"Your field": "Your field",
"Growth stage": "Growth stage",
"Get advice": "Get advice",
"Calculate irrigation": "Calculate irrigation",
"Calculating irrigation…": "Calculating irrigation…",
"Could not calculate": "Could not calculate",
"Field area": "Field area",
"ac": "ac",
"Recent rain": "Recent rain",
"mm": "mm",
"Wind speed": "Wind speed",
"km/h": "km/h",
"Water needed": "Water needed",
"Net irrigation": "Net irrigation",
"Crop Kc factor": "Crop Kc factor",
"urgency": "urgency",
"fertilizer": "fertilizer",
"Nitrogen:": "Nitrogen:",
"weather tips": "weather tips",
"Initial": "Initial",
"Development": "Development",
"Mid-season": "Mid-season",
"Late season": "Late season"
```

- [ ] **Step 8: Commit**

```bash
git add web/components/views/ViewIrrigation.jsx web/lib/bundles.json
git commit -m "feat(i18n): wrap all strings in ViewIrrigation + add en bundle keys"
```

---

## Task 6 — Add `t` and wrap all strings in ViewField.jsx

**Files:**
- Modify: `web/components/views/ViewField.jsx`
- Modify: `web/lib/bundles.json`

- [ ] **Step 1: Add `t` to ViewField signature (if missing)**

```jsx
// Check current signature. Ensure it includes t:
function ViewField({ profile, setProfile, t, fieldData, fieldLoading })
```

- [ ] **Step 2: Wrap page header and scan button**

```jsx
// was:
<Topbar crumb="Field Watch" />
<div className="page-eyebrow">field</div>
<h1 className="page-title">A <em>quiet daily check-in</em> for your land.</h1>
<p className="page-lede">Weather, fires, locusts, soil — all gathered in one calm view. Just the things you need to know today.</p>
// after:
<Topbar crumb={t('Field Watch')} />
<div className="page-eyebrow">{t('field')}</div>
<h1 className="page-title">{t('A')} <em>{t('quiet daily check-in')}</em> {t('for your land.')}</h1>
<p className="page-lede">{t("Weather, fires, locusts, soil — all gathered in one calm view. Just the things you need to know today.")}</p>

// was:
🛰 Scan now
// after:
{t('🛰 Scan now')}

// was:
<Loading label="Scanning field…" />
// after:
<Loading label={t('Scanning field…')} />
```

- [ ] **Step 3: Wrap error titles**

```jsx
// was (inside error handling):
title: 'Access denied'
title: 'Network error'
`title: 'Error ' + status`
// after:
title: t('Access denied')
title: t('Network error')
title: t('Error') + ' ' + status
```

- [ ] **Step 4: Wrap weather metric labels**

```jsx
// was:
<div className="page-eyebrow">Temperature</div>
// after:
<div className="page-eyebrow">{t('Temperature')}</div>

// was: feels like {x}°C
// after: {t('feels like')} {x}°C

// was:
<div className="page-eyebrow">Humidity</div>
// after:
<div className="page-eyebrow">{t('Humidity')}</div>

// was:
<div className="page-eyebrow">Wind</div>
// after:
<div className="page-eyebrow">{t('Wind')}</div>

// was: surface wind
// after: {t('surface wind')}

// was:
<div className="page-eyebrow">Rain 1h</div>
// after:
<div className="page-eyebrow">{t('Rain 1h')}</div>

// was: last hour
// after: {t('last hour')}

// was: {result.overall_risk} RISK · {result.city}
// after: {result.overall_risk} {t('RISK')} · {result.city}
```

- [ ] **Step 5: Wrap alert card titles and body text**

```jsx
// was:
<AlertCard title="Flood risk" ...
// after:
<AlertCard title={t('Flood risk')} ...

// was:
Rain 48h: {value}
// after:
{t('Rain 48h:')} {value}

// was:
<AlertCard title="Fire" ...
// after:
<AlertCard title={t('Fire')} ...

// was:
Hotspots nearby: {count}
// after:
{t('Hotspots nearby:')} {count}

// was: source: {src}
// after: {t('source:')} {src}

// was:
<AlertCard title="Locust" ...
// after:
<AlertCard title={t('Locust')} ...

// was:
Swarms nearby: {count}
// after:
{t('Swarms nearby:')} {count}

// was:
<AlertCard title="Air Quality" ...
// after:
<AlertCard title={t('Air Quality')} ...
```

- [ ] **Step 6: Wrap GOVT_HELPLINES and CALAMITY_TIPS at render sites**

GOVT_HELPLINES is defined in atoms.jsx as an array of `[name, phone, description]`. At the render site in ViewField.jsx:
```jsx
// was (wherever helplines are rendered):
{GOVT_HELPLINES.map(([name, phone, desc]) => (
  <tr key={phone}>
    <td>{name}</td><td>{phone}</td><td>{desc}</td>
  </tr>
))}
// after:
{GOVT_HELPLINES.map(([name, phone, desc]) => (
  <tr key={phone}>
    <td>{t(name)}</td><td>{phone}</td><td>{t(desc)}</td>
  </tr>
))}
```

CALAMITY_TIPS are rendered as a list of tips based on weather condition. Wrap each tip:
```jsx
// was (wherever tips are shown):
{tips.map((tip, i) => <div key={i}>{tip}</div>)}
// after:
{tips.map((tip, i) => <div key={i}>{t(tip)}</div>)}
```

- [ ] **Step 7: Wrap WhatsApp card headings and button text**

```jsx
// was:
<h3>Emergency helplines</h3>
// after:
<h3>{t('Emergency helplines')}</h3>

// was:
<h3>Send to WhatsApp</h3>
// after:
<h3>{t('Send to WhatsApp')}</h3>

// was:
📋 Copy
// after:
{t('📋 Copy')}

// was:
📲 Open WhatsApp
// after:
{t('📲 Open WhatsApp')}

// was:
Send to my number
// after:
{t('Send to my number')}
```

- [ ] **Step 8: Add new ViewField keys to bundles.json "en" section**

```json
"field": "field",
"quiet daily check-in": "quiet daily check-in",
"for your land.": "for your land.",
"Weather, fires, locusts, soil — all gathered in one calm view. Just the things you need to know today.": "Weather, fires, locusts, soil — all gathered in one calm view. Just the things you need to know today.",
"🛰 Scan now": "🛰 Scan now",
"Scanning field…": "Scanning field…",
"Access denied": "Access denied",
"Network error": "Network error",
"Error": "Error",
"RISK": "RISK",
"feels like": "feels like",
"Wind": "Wind",
"surface wind": "surface wind",
"Rain 1h": "Rain 1h",
"last hour": "last hour",
"Flood risk": "Flood risk",
"Rain 48h:": "Rain 48h:",
"Fire": "Fire",
"Hotspots nearby:": "Hotspots nearby:",
"source:": "source:",
"Locust": "Locust",
"Swarms nearby:": "Swarms nearby:",
"Air Quality": "Air Quality",
"Emergency helplines": "Emergency helplines",
"Send to WhatsApp": "Send to WhatsApp",
"📋 Copy": "📋 Copy",
"📲 Open WhatsApp": "📲 Open WhatsApp",
"Send to my number": "Send to my number",
"Kisan Call Centre": "Kisan Call Centre",
"Free · 24/7 · All Indian languages": "Free · 24/7 · All Indian languages",
"PM Kisan Helpline": "PM Kisan Helpline",
"PM Kisan scheme queries": "PM Kisan scheme queries",
"NDRF Emergency": "NDRF Emergency",
"Flood, earthquake, disaster": "Flood, earthquake, disaster",
"Ambulance": "Ambulance",
"Medical emergency": "Medical emergency",
"Police": "Police",
"Security / theft": "Security / theft",
"State Agriculture Dept": "State Agriculture Dept",
"Disease outbreak reporting": "Disease outbreak reporting",
"⚡ Move livestock to shelter": "⚡ Move livestock to shelter",
"🚫 Stop all field work immediately": "🚫 Stop all field work immediately",
"💧 Clear drainage channels": "💧 Clear drainage channels",
"🌱 Avoid fertilizer — will wash away": "🌱 Avoid fertilizer — will wash away",
"🌊 Create bunds around fields": "🌊 Create bunds around fields",
"📞 Contact agriculture office if flooding": "📞 Contact agriculture office if flooding",
"💧 Good for germination": "💧 Good for germination",
"🌱 Ideal time for transplanting": "🌱 Ideal time for transplanting",
"✅ Reduce irrigation today": "✅ Reduce irrigation today",
"🌿 Cover sensitive crops with cloth": "🌿 Cover sensitive crops with cloth",
"🔥 Light irrigation before frost protects roots": "🔥 Light irrigation before frost protects roots",
"🌱 Avoid pruning until frost passes": "🌱 Avoid pruning until frost passes",
"🍄 Watch for fungal disease": "🍄 Watch for fungal disease",
"💊 Apply preventive fungicide": "💊 Apply preventive fungicide",
"🌬️ Improve air circulation": "🌬️ Improve air circulation",
"😷 Reduce outdoor work": "😷 Reduce outdoor work",
"💧 Increase irrigation — heat stress likely": "💧 Increase irrigation — heat stress likely",
"🌿 Monitor crops for wilting": "🌿 Monitor crops for wilting",
"☀️ Good day for spraying pesticides": "☀️ Good day for spraying pesticides",
"🚜 Ideal for harvesting": "🚜 Ideal for harvesting",
"💧 Check soil moisture levels": "💧 Check soil moisture levels",
"🌤️ Good day for transplanting": "🌤️ Good day for transplanting",
"💧 Moderate irrigation needed": "💧 Moderate irrigation needed",
"🌱 Apply fertilizers today": "🌱 Apply fertilizers today"
```

- [ ] **Step 9: Commit**

```bash
git add web/components/views/ViewField.jsx web/lib/bundles.json
git commit -m "feat(i18n): wrap all strings in ViewField + add en bundle keys"
```

---

## Task 7 — Wrap remaining strings in ViewCrop.jsx

**Files:**
- Modify: `web/components/views/ViewCrop.jsx`
- Modify: `web/lib/bundles.json`

ViewCrop already receives `t`. Wrap all hardcoded strings not yet going through `t()`.

- [ ] **Step 1: Wrap page header**

```jsx
// was:
<Topbar crumb="Crop Advisor" />
<div className="page-eyebrow">crop advisor</div>
<h1 className="page-title">Find what your soil <em>wants to grow.</em></h1>
<p className="page-lede">Tell us a little about your field. We'll quietly look through 26 crops and suggest the one your land will love most.</p>
// after:
<Topbar crumb={t('Crop Advisor')} />
<div className="page-eyebrow">{t('crop advisor')}</div>
<h1 className="page-title">{t('Find what your soil')} <em>{t('wants to grow.')}</em></h1>
<p className="page-lede">{t("Tell us a little about your field. We'll quietly look through 26 crops and suggest the one your land will love most.")}</p>
```

- [ ] **Step 2: Wrap kharif tag**

```jsx
// was:
<span className="tag">🌦 kharif season</span>
// after:
<span className="tag">{t('🌦 kharif season')}</span>
```

- [ ] **Step 3: Wrap slider labels and hints**

```jsx
// was (approximate, find actual Slider calls):
<Slider label="Nitrogen" .../>  hints={['a little hungry','just right','plenty']}
<Slider label="Phosphorus" .../>
<Slider label="Potassium" .../>
<Slider label="Soil pH" .../>  hints={['acidic','sweet spot','a touch alkaline']}
<Slider label="Temperature" .../>
<Slider label="Humidity" .../>
<Slider label="Rainfall" .../>
// after:
<Slider label={t('Nitrogen')} hints={[t('a little hungry'),t('just right'),t('plenty')]} .../>
<Slider label={t('Phosphorus')} .../>
<Slider label={t('Potassium')} .../>
<Slider label={t('Soil pH')} hints={[t('acidic'),t('sweet spot'),t('a touch alkaline')]} .../>
<Slider label={t('Temperature')} .../>
<Slider label={t('Humidity')} .../>
<Slider label={t('Rainfall')} .../>
```

- [ ] **Step 4: Wrap live weather meta text**

```jsx
// was:
fetching live…
your local feel
// after:
{t('fetching live…')}
{t('your local feel')}
```

- [ ] **Step 5: Wrap error messages**

```jsx
// was:
title="Could not analyze soil"
detail="API key misconfigured. Open web/config.js and verify the dev key."
// and the no-connection case:
detail="No connection — check your network and try again."
// after:
title={t('Could not analyze soil')}
detail={t('API key misconfigured. Open web/config.js and verify the dev key.')}
// no-connection:
detail={t('No connection — check your network and try again.')}
```

- [ ] **Step 6: Wrap result prefix**

```jsx
// was (line ~162):
<span>soil · {result.soil.soil_type}</span>
// after:
<span>{t('soil')} · {result.soil.soil_type}</span>
```

- [ ] **Step 7: Add new ViewCrop keys to bundles.json "en" section**

```json
"crop advisor": "crop advisor",
"Find what your soil": "Find what your soil",
"wants to grow.": "wants to grow.",
"Tell us a little about your field. We'll quietly look through 26 crops and suggest the one your land will love most.": "Tell us a little about your field. We'll quietly look through 26 crops and suggest the one your land will love most.",
"🌦 kharif season": "🌦 kharif season",
"Nitrogen": "Nitrogen",
"Phosphorus": "Phosphorus",
"Potassium": "Potassium",
"Soil pH": "Soil pH",
"a little hungry": "a little hungry",
"just right": "just right",
"plenty": "plenty",
"acidic": "acidic",
"sweet spot": "sweet spot",
"a touch alkaline": "a touch alkaline",
"Temperature": "Temperature",
"Humidity": "Humidity",
"Rainfall": "Rainfall",
"fetching live…": "fetching live…",
"your local feel": "your local feel",
"Could not analyze soil": "Could not analyze soil",
"API key misconfigured. Open web/config.js and verify the dev key.": "API key misconfigured. Open web/config.js and verify the dev key.",
"No connection — check your network and try again.": "No connection — check your network and try again.",
"soil": "soil"
```

- [ ] **Step 8: Commit**

```bash
git add web/components/views/ViewCrop.jsx web/lib/bundles.json
git commit -m "feat(i18n): wrap remaining strings in ViewCrop + add en bundle keys"
```

---

## Task 8 — Wrap sidebar strings in app.jsx + atoms.jsx render sites

**Files:**
- Modify: `web/components/app.jsx`
- Modify: `web/lib/bundles.json`

- [ ] **Step 1: Wrap CRUMB_MAP values**

`CRUMB_MAP` in app.jsx maps route → display string. The crumb strings are passed directly. Check if `Topbar` translates via `t(crumb)` internally or if crumb is already translated at the call site. If CRUMB_MAP values are rendered directly, wrap at the render site:
```jsx
// If CRUMB_MAP is: { crop: 'Crop Advisor', disease: 'Leaf Doctor', ... }
// And used as: <Topbar crumb={CRUMB_MAP[tab]} />
// Change to: <Topbar crumb={t(CRUMB_MAP[tab])} />
// OR wrap each value in the map using t at definition time (inside the component where t is available)
const crumbMap = {
  crop: t('Crop Advisor'),
  disease: t('Leaf Doctor'),
  market: t('Market Prices'),
  irrigation: t('Watering'),
  acoustic: t('Listen to Field'),
  field: t('Field Watch'),
};
```

- [ ] **Step 2: Wrap sidebar static strings**

```jsx
// was:
<span>farmer · since 2019</span>
// after:
<span>{t('farmer · since 2019')}</span>

// was:
<p>a calm field today is a good harvest tomorrow.</p>
// after:
<p>{t('a calm field today is a good harvest tomorrow.')}</p>
```

- [ ] **Step 3: Add ACOUSTIC_WARNING_LABELS to atoms.jsx as window global**

The warning labels in atoms.jsx are used via `window.ACOUSTIC_WARNING_LABELS?.[w]`. Ensure they are exposed as `window.ACOUSTIC_WARNING_LABELS`. No change needed to the constant itself — it's already translated at the render site in ViewAcoustic (Task 4, Step 5).

Add acoustic warning keys to bundles.json "en" section:
```json
"⏱ Recording too short — need at least 3 seconds": "⏱ Recording too short — need at least 3 seconds",
"🔇 Too quiet — hold mic closer to the plant stem": "🔇 Too quiet — hold mic closer to the plant stem",
"✂️ Long recording — analyzed first 20 seconds": "✂️ Long recording — analyzed first 20 seconds",
"📉 Low sample rate may reduce accuracy": "📉 Low sample rate may reduce accuracy",
"📈 Sample rate resampled to 16 kHz": "📈 Sample rate resampled to 16 kHz",
"Pollinator": "Pollinator",
"Pest": "Pest",
"Ambient": "Ambient",
"farmer · since 2019": "farmer · since 2019",
"a calm field today is a good harvest tomorrow.": "a calm field today is a good harvest tomorrow."
```

- [ ] **Step 4: Commit**

```bash
git add web/components/app.jsx web/lib/bundles.json
git commit -m "feat(i18n): wrap sidebar + atoms render site strings + add en bundle keys"
```

---

## Task 9 — Add Hindi (hi) translations for all new keys

**Files:**
- Modify: `web/lib/bundles.json`

Add these translations to the `"hi"` object. These cover all keys added in Tasks 2–8.

- [ ] **Step 1: Add all Hindi translations**

Add to `"hi"` section of bundles.json:
```json
"top matches": "शीर्ष परिणाम",
"via": "के द्वारा",
"right now": "अभी",
"treatment": "उपचार",
"prevention": "बचाव",
"Something went wrong.": "कुछ गलत हुआ।",
"API key issue — check your config.js setup.": "API कुंजी समस्या — config.js जाँचें।",
"Analysis failed.": "विश्लेषण विफल।",
"Send a photo": "फोटो भेजें",
"loading crops…": "फसलें लोड हो रही हैं…",
"Drop a leaf photo here": "यहाँ पत्ती की फोटो छोड़ें",
"or click to choose · jpg, png, webp": "या क्लिक करें · jpg, png, webp",
"What we see": "हमें क्या दिखा",
"Send a photo and we'll have a look. 🌿": "फोटो भेजें और हम देखेंगे। 🌿",
"Analyzing leaf…": "पत्ती का विश्लेषण हो रहा है…",
"Could not analyze photo": "फोटो का विश्लेषण नहीं हो सका",
"Leaf Doctor": "पत्ती डॉक्टर",
"leaf doctor": "पत्ती डॉक्टर",
"A": "एक",
"second pair of eyes": "दूसरी नज़र",
"for sick leaves.": "बीमार पत्तियों के लिए।",
"Snap a photo of a worried leaf. We'll gently look it over and tell you what's likely going on, with the kindest fix.": "एक चिंतित पत्ती की फोटो लें। हम धीरे से देखेंगे और बताएंगे क्या हो रहा है।",
"Not enough data to chart.": "चार्ट के लिए पर्याप्त डेटा नहीं।",
"Date": "तारीख",
"Price": "कीमत",
"Min": "न्यूनतम",
"Max": "अधिकतम",
"Market": "बाज़ार",
"market": "बाज़ार",
"fair price,": "उचित कीमत,",
"a calm decision.": "एक शांत निर्णय।",
"We watch the mandi prices and gently tell you whether to sell now or wait a couple of weeks. No charts to wrestle with.": "हम मंडी के भाव देखते हैं और बताते हैं अभी बेचें या कुछ हफ्ते रुकें।",
"Forecast horizon": "पूर्वानुमान अवधि",
"days": "दिन",
"📊 Get forecast": "📊 पूर्वानुमान लें",
"Fetching market data…": "बाज़ार डेटा लाया जा रहा है…",
"Could not fetch forecast": "पूर्वानुमान नहीं मिला",
"API key issue — check your configuration.": "API कुंजी समस्या — कॉन्फ़िगरेशन जाँचें।",
"Network error — please check your connection.": "नेटवर्क त्रुटि — कनेक्शन जाँचें।",
"Unexpected error.": "अप्रत्याशित त्रुटि।",
"live mandi": "लाइव मंडी",
"mandis": "मंडियाँ",
"state factor": "राज्य कारक",
"🟢 LIVE": "🟢 लाइव",
"🟡 ESTIMATED": "🟡 अनुमानित",
"Live mandi data not available — showing model forecast only.": "लाइव मंडी डेटा उपलब्ध नहीं — केवल मॉडल पूर्वानुमान दिखाया जा रहा है।",
"best price": "सर्वोत्तम कीमत",
"worst price": "न्यूनतम कीमत",
"average price": "औसत कीमत",
"over": "में",
"our advice": "हमारी सलाह",
"Price forecast": "कीमत पूर्वानुमान",
"Full forecast table": "पूर्ण पूर्वानुमान तालिका",
"top detections": "शीर्ष पहचान",
"band energy": "बैंड ऊर्जा",
"Confidence": "विश्वास",
"Duration": "अवधि",
"Sample rate": "सैंपल दर",
"Energy": "ऊर्जा",
"Claude advice": "Claude सलाह",
"quality notes": "गुणवत्ता टिप्पणी",
"Reference library": "संदर्भ पुस्तकालय",
"known insects": "ज्ञात कीड़े",
"Icon": "चिह्न",
"Name": "नाम",
"Role": "भूमिका",
"Severity": "गंभीरता",
"Freq range": "आवृत्ति श्रेणी",
"File too large (max 20 MB)": "फ़ाइल बहुत बड़ी है (अधिकतम 20 MB)",
"Cannot preview this audio format — upload anyway to let the server analyze it.": "इस ऑडियो प्रारूप का पूर्वावलोकन संभव नहीं — फिर भी अपलोड करें।",
"Unknown error": "अज्ञात त्रुटि",
"Invalid or missing API key.": "अमान्य या अनुपस्थित API कुंजी।",
"Network error — check your connection.": "नेटवर्क त्रुटि — कनेक्शन जाँचें।",
"Listen": "सुनें",
"listen": "सुनें",
"Hear the bugs": "कीड़ों की आवाज़ सुनें",
"before they show.": "दिखने से पहले।",
"Hold your phone near a plant for a few seconds. We'll listen for the tiny sounds pests make and warn you a week early.": "अपना फोन कुछ सेकंड के लिए पौधे के पास रखें। हम कीट की आवाज़ सुनेंगे और एक हफ्ते पहले चेतावनी देंगे।",
"Upload a recording": "रिकॉर्डिंग अपलोड करें",
"~6 seconds": "~6 सेकंड",
"Crop type (optional)": "फसल का प्रकार (वैकल्पिक)",
"Drag & drop your field audio here": "यहाँ अपनी खेत की ऑडियो खींचें",
"or click to choose · wav · mp3 · m4a · ogg · webm": "या क्लिक करें · wav · mp3 · m4a · ogg · webm",
"KB · ready": "KB · तैयार",
"tip: 15–30 cm from the stem · breathe slowly": "सुझाव: तने से 15–30 सेमी दूर · धीरे साँस लें",
"clear": "साफ़ करें",
"🎧 listening…": "🎧 सुन रहे हैं…",
"🔊 analyze": "🔊 विश्लेषण करें",
"What we heard": "हमने क्या सुना",
"Listening to your field…": "आपके खेत को सुन रहे हैं…",
"Analysis failed": "विश्लेषण विफल",
"Drop a recording on the left to begin. 🐛": "शुरू करने के लिए बाईं ओर रिकॉर्डिंग डालें। 🐛",
"field": "खेत",
"quiet daily check-in": "शांत दैनिक जाँच",
"for your land.": "आपकी भूमि के लिए।",
"Weather, fires, locusts, soil — all gathered in one calm view. Just the things you need to know today.": "मौसम, आग, टिड्डे, मिट्टी — सब एक शांत दृश्य में। बस वही जो आज जानना ज़रूरी है।",
"🛰 Scan now": "🛰 अभी स्कैन करें",
"Scanning field…": "खेत स्कैन हो रहा है…",
"Access denied": "पहुँच अस्वीकृत",
"Network error": "नेटवर्क त्रुटि",
"Error": "त्रुटि",
"RISK": "जोखिम",
"feels like": "जैसा महसूस होता है",
"Wind": "हवा",
"surface wind": "सतह की हवा",
"Rain 1h": "1 घंटे की बारिश",
"last hour": "पिछला घंटा",
"Flood risk": "बाढ़ का खतरा",
"Rain 48h:": "48 घंटे की बारिश:",
"Fire": "आग",
"Hotspots nearby:": "नज़दीकी हॉटस्पॉट:",
"source:": "स्रोत:",
"Locust": "टिड्डे",
"Swarms nearby:": "नज़दीकी झुंड:",
"Air Quality": "वायु गुणवत्ता",
"Emergency helplines": "आपातकालीन हेल्पलाइन",
"Send to WhatsApp": "WhatsApp पर भेजें",
"📋 Copy": "📋 कॉपी करें",
"📲 Open WhatsApp": "📲 WhatsApp खोलें",
"Send to my number": "मेरे नंबर पर भेजें",
"Kisan Call Centre": "किसान कॉल सेंटर",
"Free · 24/7 · All Indian languages": "निःशुल्क · 24/7 · सभी भारतीय भाषाएँ",
"PM Kisan Helpline": "PM किसान हेल्पलाइन",
"PM Kisan scheme queries": "PM किसान योजना की जानकारी",
"NDRF Emergency": "NDRF आपातकाल",
"Flood, earthquake, disaster": "बाढ़, भूकंप, आपदा",
"Ambulance": "एम्बुलेंस",
"Medical emergency": "चिकित्सा आपातकाल",
"Police": "पुलिस",
"Security / theft": "सुरक्षा / चोरी",
"State Agriculture Dept": "राज्य कृषि विभाग",
"Disease outbreak reporting": "रोग प्रकोप रिपोर्टिंग",
"⚡ Move livestock to shelter": "⚡ पशुओं को आश्रय में ले जाएँ",
"🚫 Stop all field work immediately": "🚫 तुरंत सभी खेत का काम रोकें",
"💧 Clear drainage channels": "💧 जल निकासी नालियाँ साफ़ करें",
"🌱 Avoid fertilizer — will wash away": "🌱 उर्वरक न डालें — धुल जाएगा",
"🌊 Create bunds around fields": "🌊 खेतों के चारों ओर मेड़ बनाएँ",
"📞 Contact agriculture office if flooding": "📞 बाढ़ की स्थिति में कृषि कार्यालय से संपर्क करें",
"💧 Good for germination": "💧 अंकुरण के लिए अच्छा",
"🌱 Ideal time for transplanting": "🌱 रोपाई का उचित समय",
"✅ Reduce irrigation today": "✅ आज सिंचाई कम करें",
"🌿 Cover sensitive crops with cloth": "🌿 संवेदनशील फसलों को कपड़े से ढकें",
"🔥 Light irrigation before frost protects roots": "🔥 पाले से पहले हल्की सिंचाई जड़ों की रक्षा करती है",
"🌱 Avoid pruning until frost passes": "🌱 पाला गुज़रने तक छँटाई न करें",
"🍄 Watch for fungal disease": "🍄 फंगल रोग पर नज़र रखें",
"💊 Apply preventive fungicide": "💊 निवारक फफूंदनाशक लगाएँ",
"🌬️ Improve air circulation": "🌬️ वायु संचार बेहतर करें",
"😷 Reduce outdoor work": "😷 बाहरी काम कम करें",
"💧 Increase irrigation — heat stress likely": "💧 सिंचाई बढ़ाएँ — गर्मी का तनाव संभव",
"🌿 Monitor crops for wilting": "🌿 मुरझाने के लिए फसल पर नज़र रखें",
"☀️ Good day for spraying pesticides": "☀️ कीटनाशक छिड़काव के लिए अच्छा दिन",
"🚜 Ideal for harvesting": "🚜 कटाई के लिए आदर्श",
"💧 Check soil moisture levels": "💧 मिट्टी की नमी जाँचें",
"🌤️ Good day for transplanting": "🌤️ रोपाई के लिए अच्छा दिन",
"💧 Moderate irrigation needed": "💧 मध्यम सिंचाई आवश्यक",
"🌱 Apply fertilizers today": "🌱 आज उर्वरक डालें",
"⏱ Recording too short — need at least 3 seconds": "⏱ रिकॉर्डिंग बहुत छोटी — कम से कम 3 सेकंड चाहिए",
"🔇 Too quiet — hold mic closer to the plant stem": "🔇 बहुत शांत — माइक को तने के पास लाएँ",
"✂️ Long recording — analyzed first 20 seconds": "✂️ लंबी रिकॉर्डिंग — पहले 20 सेकंड का विश्लेषण",
"📉 Low sample rate may reduce accuracy": "📉 कम सैंपल दर सटीकता कम कर सकती है",
"📈 Sample rate resampled to 16 kHz": "📈 सैंपल दर 16 kHz पर रूपांतरित",
"Pollinator": "परागणकर्ता",
"Pest": "कीट",
"Ambient": "परिवेश",
"farmer · since 2019": "किसान · 2019 से",
"a calm field today is a good harvest tomorrow.": "आज का शांत खेत कल की अच्छी फसल है।",
"Watering": "सिंचाई",
"water": "पानी",
"Just enough water,": "बस उतना पानी,",
"just in time.": "ठीक समय पर।",
"We do the FAO water math behind the scenes and tell you simply: how many liters today, and when to water next.": "हम FAO जल गणित करते हैं और बताते हैं: आज कितने लीटर और अगली सिंचाई कब।",
"Your field": "आपका खेत",
"Growth stage": "विकास चरण",
"Get advice": "सलाह लें",
"Calculate irrigation": "सिंचाई की गणना करें",
"Calculating irrigation…": "सिंचाई की गणना हो रही है…",
"Could not calculate": "गणना नहीं हो सकी",
"Field area": "खेत का क्षेत्र",
"ac": "एकड़",
"Recent rain": "हालिया बारिश",
"mm": "मिमी",
"Wind speed": "हवा की गति",
"km/h": "किमी/घंटा",
"Water needed": "पानी की ज़रूरत",
"Net irrigation": "शुद्ध सिंचाई",
"Crop Kc factor": "फसल Kc कारक",
"urgency": "तात्कालिकता",
"fertilizer": "उर्वरक",
"Nitrogen:": "नाइट्रोजन:",
"weather tips": "मौसम सुझाव",
"Initial": "प्रारंभिक",
"Development": "विकास",
"Mid-season": "मध्य सीज़न",
"Late season": "अंत सीज़न",
"crop advisor": "फसल सलाहकार",
"Find what your soil": "जानें आपकी मिट्टी क्या",
"wants to grow.": "उगाना चाहती है।",
"Tell us a little about your field. We'll quietly look through 26 crops and suggest the one your land will love most.": "अपने खेत के बारे में थोड़ा बताएँ। हम 26 फसलों में से वह सुझाएंगे जो आपकी भूमि को सबसे अच्छी लगे।",
"🌦 kharif season": "🌦 खरीफ सीज़न",
"Nitrogen": "नाइट्रोजन",
"Phosphorus": "फास्फोरस",
"Potassium": "पोटेशियम",
"Soil pH": "मिट्टी का pH",
"a little hungry": "थोड़ा कम",
"just right": "सही मात्रा",
"plenty": "पर्याप्त",
"acidic": "अम्लीय",
"sweet spot": "आदर्श",
"a touch alkaline": "थोड़ा क्षारीय",
"Temperature": "तापमान",
"Humidity": "आर्द्रता",
"Rainfall": "वर्षा",
"fetching live…": "लाइव डेटा ला रहे हैं…",
"your local feel": "आपका स्थानीय अनुभव",
"Could not analyze soil": "मिट्टी का विश्लेषण नहीं हो सका",
"API key misconfigured. Open web/config.js and verify the dev key.": "API कुंजी गलत — web/config.js जाँचें।",
"soil": "मिट्टी"
```

- [ ] **Step 2: Commit**

```bash
git add web/lib/bundles.json
git commit -m "feat(i18n): add Hindi (hi) translations for all new keys"
```

---

## Task 10 — Add translations for remaining 8 languages

**Files:**
- Modify: `web/lib/bundles.json`

Add translations for: `te` (Telugu), `ta` (Tamil), `kn` (Kannada), `bn` (Bengali), `mr` (Marathi), `ml` (Malayalam), `gu` (Gujarati), `pa` (Punjabi).

Use the same ~180 keys from Task 9. Below are translations for each language for the most critical UI strings. For each language, add the full set matching Task 9's key list.

- [ ] **Step 1: Add Telugu (te) translations**

```json
"Nitrogen": "నైట్రోజన్",
"Phosphorus": "ఫాస్ఫరస్",
"Potassium": "పొటాషియమ్",
"Soil pH": "నేల pH",
"Temperature": "ఉష్ణోగ్రత",
"Humidity": "తేమ",
"Rainfall": "వర్షపాతం",
"crop advisor": "పంట సలహాదారు",
"Find what your soil": "మీ నేల ఏమి",
"wants to grow.": "పెంచాలనుకుంటుందో తెలుసుకోండి.",
"Leaf Doctor": "ఆకు డాక్టర్",
"leaf doctor": "ఆకు డాక్టర్",
"A": "ఒక",
"second pair of eyes": "రెండవ దృష్టి",
"for sick leaves.": "అనారోగ్యకరమైన ఆకులకు.",
"Market": "మార్కెట్",
"market": "మార్కెట్",
"Watering": "నీటిపారుదల",
"water": "నీరు",
"Listen": "వినండి",
"listen": "వినండి",
"Field Watch": "పొల నిఘా",
"field": "పొలం",
"Send a photo": "ఫోటో పంపండి",
"What we see": "మనం చూసింది",
"Upload a recording": "రికార్డింగ్ అప్‌లోడ్ చేయండి",
"What we heard": "మనం విన్నది",
"Calculate irrigation": "నీటిపారుదల లెక్కించండి",
"Get advice": "సలాహ తీసుకోండి",
"🛰 Scan now": "🛰 ఇప్పుడు స్కాన్ చేయండి",
"Emergency helplines": "అత్యవసర హెల్ప్‌లైన్లు",
"Pollinator": "పరాగ సంపర్కి",
"Pest": "తెగులు",
"Ambient": "పరిసర",
"Initial": "ప్రారంభ",
"Development": "అభివృద్ధి",
"Mid-season": "మధ్య సీజన్",
"Late season": "చివరి సీజన్",
"best price": "అత్యుత్తమ ధర",
"worst price": "అతి తక్కువ ధర",
"average price": "సగటు ధర",
"our advice": "మా సలాహ",
"days": "రోజులు",
"Date": "తేదీ",
"Price": "ధర",
"Min": "కనిష్ట",
"Max": "గరిష్ట",
"Confidence": "విశ్వాసం",
"Duration": "వ్యవధి",
"Sample rate": "నమూనా రేటు",
"Energy": "శక్తి",
"Severity": "తీవ్రత",
"Role": "పాత్ర",
"Name": "పేరు",
"clear": "తొలగించు",
"farmer · since 2019": "రైతు · 2019 నుండి",
"a calm field today is a good harvest tomorrow.": "నేటి ప్రశాంత పొలం రేపటి మంచి పంట."
```

- [ ] **Step 2: Add Tamil (ta) translations**

```json
"Nitrogen": "நைட்ரஜன்",
"Phosphorus": "பாஸ்பரஸ்",
"Potassium": "பொட்டாசியம்",
"Soil pH": "மண் pH",
"Temperature": "வெப்பநிலை",
"Humidity": "ஈரப்பதம்",
"Rainfall": "மழையளவு",
"crop advisor": "பயிர் ஆலோசகர்",
"Find what your soil": "உங்கள் மண் என்ன",
"wants to grow.": "வளர்க்க விரும்புகிறது.",
"Leaf Doctor": "இலை மருத்துவர்",
"leaf doctor": "இலை மருத்துவர்",
"A": "ஒரு",
"second pair of eyes": "இரண்டாவது பார்வை",
"for sick leaves.": "நோய்வாய்ப்பட்ட இலைகளுக்கு.",
"Market": "சந்தை",
"market": "சந்தை",
"Watering": "நீர்ப்பாசனம்",
"water": "நீர்",
"Listen": "கேளுங்கள்",
"listen": "கேளுங்கள்",
"Field Watch": "வயல் கண்காணிப்பு",
"field": "வயல்",
"Send a photo": "புகைப்படம் அனுப்புங்கள்",
"What we see": "நாம் பார்த்தது",
"Upload a recording": "பதிவேற்றம் செய்யுங்கள்",
"What we heard": "நாம் கேட்டது",
"Calculate irrigation": "நீர்ப்பாசனம் கணக்கிடுங்கள்",
"Get advice": "ஆலோசனை பெறுங்கள்",
"🛰 Scan now": "🛰 இப்போது ஸ்கேன் செய்யுங்கள்",
"Emergency helplines": "அவசர உதவி எண்கள்",
"Pollinator": "மகரந்தச் சேர்க்கையாளர்",
"Pest": "பூச்சி",
"Ambient": "சூழல்",
"Initial": "தொடக்க",
"Development": "வளர்ச்சி",
"Mid-season": "நடு-காலம்",
"Late season": "கடைசி-காலம்",
"best price": "சிறந்த விலை",
"worst price": "குறைந்த விலை",
"average price": "சராசரி விலை",
"our advice": "எங்கள் ஆலோசனை",
"days": "நாட்கள்",
"Date": "தேதி",
"Price": "விலை",
"Min": "குறைந்தபட்சம்",
"Max": "அதிகபட்சம்",
"Confidence": "நம்பகத்தன்மை",
"Duration": "கால அளவு",
"Sample rate": "மாதிரி விகிதம்",
"Energy": "ஆற்றல்",
"Severity": "தீவிரம்",
"Role": "பங்கு",
"Name": "பெயர்",
"clear": "அழி",
"farmer · since 2019": "விவசாயி · 2019 முதல்",
"a calm field today is a good harvest tomorrow.": "இன்றைய அமைதியான வயல் நாளைய நல்ல அறுவடை."
```

- [ ] **Step 3: Add Kannada (kn) translations**

```json
"Nitrogen": "ನೈಟ್ರೋಜನ್",
"Phosphorus": "ರಂಜಕ",
"Potassium": "ಪೊಟ್ಯಾಸಿಯಂ",
"Soil pH": "ಮಣ್ಣಿನ pH",
"Temperature": "ತಾಪಮಾನ",
"Humidity": "ತೇವಾಂಶ",
"Rainfall": "ಮಳೆ",
"crop advisor": "ಬೆಳೆ ಸಲಹೆಗಾರ",
"Find what your soil": "ನಿಮ್ಮ ಮಣ್ಣು ಏನು",
"wants to grow.": "ಬೆಳೆಯಲು ಬಯಸುತ್ತದೆ.",
"Leaf Doctor": "ಎಲೆ ವೈದ್ಯ",
"leaf doctor": "ಎಲೆ ವೈದ್ಯ",
"A": "ಒಂದು",
"second pair of eyes": "ಎರಡನೇ ದೃಷ್ಟಿ",
"for sick leaves.": "ರೋಗಗ್ರಸ್ತ ಎಲೆಗಳಿಗೆ.",
"Market": "ಮಾರುಕಟ್ಟೆ",
"market": "ಮಾರುಕಟ್ಟೆ",
"Watering": "ನೀರಾವರಿ",
"water": "ನೀರು",
"Listen": "ಆಲಿಸಿ",
"listen": "ಆಲಿಸಿ",
"Field Watch": "ಹೊಲ ಕಾವಲು",
"field": "ಹೊಲ",
"Send a photo": "ಫೋಟೋ ಕಳುಹಿಸಿ",
"What we see": "ನಾವು ನೋಡಿದ್ದು",
"Upload a recording": "ರೆಕಾರ್ಡಿಂಗ್ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ",
"What we heard": "ನಾವು ಕೇಳಿದ್ದು",
"Calculate irrigation": "ನೀರಾವರಿ ಲೆಕ್ಕ ಹಾಕಿ",
"Get advice": "ಸಲಹೆ ಪಡೆಯಿರಿ",
"🛰 Scan now": "🛰 ಈಗ ಸ್ಕ್ಯಾನ್ ಮಾಡಿ",
"Emergency helplines": "ತುರ್ತು ಸಹಾಯವಾಣಿ",
"Pollinator": "ಪರಾಗಕಾರಿ",
"Pest": "ಕೀಟ",
"Ambient": "ಪರಿಸರ",
"Initial": "ಆರಂಭಿಕ",
"Development": "ಅಭಿವೃದ್ಧಿ",
"Mid-season": "ಮಧ್ಯ-ಋತು",
"Late season": "ಕೊನೆ-ಋತು",
"best price": "ಉತ್ತಮ ಬೆಲೆ",
"worst price": "ಕಡಿಮೆ ಬೆಲೆ",
"average price": "ಸರಾಸರಿ ಬೆಲೆ",
"our advice": "ನಮ್ಮ ಸಲಹೆ",
"days": "ದಿನಗಳು",
"Date": "ದಿನಾಂಕ",
"Price": "ಬೆಲೆ",
"Min": "ಕನಿಷ್ಠ",
"Max": "ಗರಿಷ್ಠ",
"Confidence": "ವಿಶ್ವಾಸ",
"Duration": "ಅವಧಿ",
"Sample rate": "ಮಾದರಿ ದರ",
"Energy": "ಶಕ್ತಿ",
"Severity": "ತೀವ್ರತೆ",
"Role": "ಪಾತ್ರ",
"Name": "ಹೆಸರು",
"clear": "ತೆರವು",
"farmer · since 2019": "ರೈತ · 2019 ರಿಂದ",
"a calm field today is a good harvest tomorrow.": "ಇಂದಿನ ಶಾಂತ ಹೊಲ ನಾಳಿನ ಉತ್ತಮ ಬೆಳೆ."
```

- [ ] **Step 4: Add Bengali (bn), Marathi (mr), Malayalam (ml), Gujarati (gu), Punjabi (pa)**

For each language add the same key set. Key translations:

**Bengali (bn):**
```json
"Nitrogen": "নাইট্রোজেন", "Phosphorus": "ফসফরাস", "Potassium": "পটাশিয়াম",
"Soil pH": "মাটির pH", "Temperature": "তাপমাত্রা", "Humidity": "আর্দ্রতা", "Rainfall": "বৃষ্টিপাত",
"crop advisor": "ফসল পরামর্শদাতা", "Leaf Doctor": "পাতা ডাক্তার", "leaf doctor": "পাতা ডাক্তার",
"Market": "বাজার", "market": "বাজার", "Watering": "সেচ", "water": "জল",
"Listen": "শুনুন", "listen": "শুনুন", "Field Watch": "মাঠ পর্যবেক্ষণ", "field": "মাঠ",
"Find what your soil": "আপনার মাটি কী", "wants to grow.": "চাষ করতে চায়।",
"A": "একটি", "second pair of eyes": "দ্বিতীয় দৃষ্টি", "for sick leaves.": "অসুস্থ পাতার জন্য।",
"Send a photo": "ছবি পাঠান", "What we see": "আমরা কী দেখলাম",
"Upload a recording": "রেকর্ডিং আপলোড করুন", "What we heard": "আমরা কী শুনলাম",
"Calculate irrigation": "সেচ হিসাব করুন", "Get advice": "পরামর্শ নিন",
"🛰 Scan now": "🛰 এখন স্ক্যান করুন", "Emergency helplines": "জরুরি হেল্পলাইন",
"Pollinator": "পরাগায়নকারী", "Pest": "পোকা", "Ambient": "পরিবেশ",
"Initial": "প্রাথমিক", "Development": "বিকাশ", "Mid-season": "মধ্য-মৌসুম", "Late season": "শেষ-মৌসুম",
"best price": "সর্বোত্তম দাম", "worst price": "সর্বনিম্ন দাম", "average price": "গড় দাম",
"our advice": "আমাদের পরামর্শ", "days": "দিন", "Date": "তারিখ", "Price": "দাম",
"Min": "সর্বনিম্ন", "Max": "সর্বোচ্চ", "Confidence": "আত্মবিশ্বাস", "Duration": "সময়কাল",
"Sample rate": "নমুনা হার", "Energy": "শক্তি", "Severity": "তীব্রতা", "Role": "ভূমিকা", "Name": "নাম",
"clear": "মুছুন", "farmer · since 2019": "কৃষক · ২০১৯ থেকে",
"a calm field today is a good harvest tomorrow.": "আজকের শান্ত মাঠ আগামীকালের ভালো ফসল।"
```

**Marathi (mr):**
```json
"Nitrogen": "नायट्रोजन", "Phosphorus": "स्फुरद", "Potassium": "पालाश",
"Soil pH": "मातीचा pH", "Temperature": "तापमान", "Humidity": "आर्द्रता", "Rainfall": "पाऊस",
"crop advisor": "पीक सल्लागार", "Leaf Doctor": "पान डॉक्टर", "leaf doctor": "पान डॉक्टर",
"Market": "बाजार", "market": "बाजार", "Watering": "सिंचन", "water": "पाणी",
"Listen": "ऐका", "listen": "ऐका", "Field Watch": "शेत निगराणी", "field": "शेत",
"Find what your soil": "तुमची माती काय", "wants to grow.": "पिकवू इच्छिते.",
"A": "एक", "second pair of eyes": "दुसरी नजर", "for sick leaves.": "आजारी पानांसाठी.",
"Send a photo": "फोटो पाठवा", "What we see": "आम्हाला काय दिसले",
"Upload a recording": "रेकॉर्डिंग अपलोड करा", "What we heard": "आम्हाला काय ऐकले",
"Calculate irrigation": "सिंचन मोजा", "Get advice": "सल्ला घ्या",
"🛰 Scan now": "🛰 आत्ता स्कॅन करा", "Emergency helplines": "आपत्कालीन हेल्पलाइन",
"Pollinator": "परागकण वाहक", "Pest": "कीड", "Ambient": "वातावरण",
"Initial": "प्रारंभिक", "Development": "विकास", "Mid-season": "मध्य-हंगाम", "Late season": "उशिरा हंगाम",
"best price": "सर्वोत्तम भाव", "worst price": "कमी भाव", "average price": "सरासरी भाव",
"our advice": "आमचा सल्ला", "days": "दिवस", "Date": "तारीख", "Price": "भाव",
"Min": "किमान", "Max": "कमाल", "Confidence": "आत्मविश्वास", "Duration": "कालावधी",
"Sample rate": "नमुना दर", "Energy": "ऊर्जा", "Severity": "तीव्रता", "Role": "भूमिका", "Name": "नाव",
"clear": "साफ करा", "farmer · since 2019": "शेतकरी · २०१९ पासून",
"a calm field today is a good harvest tomorrow.": "आजचे शांत शेत उद्याची चांगली कापणी."
```

**Malayalam (ml):**
```json
"Nitrogen": "നൈട്രജൻ", "Phosphorus": "ഫോസ്ഫറസ്", "Potassium": "പൊട്ടാസ്യം",
"Soil pH": "മണ്ണിന്റെ pH", "Temperature": "താപനില", "Humidity": "ആർദ്രത", "Rainfall": "മഴ",
"crop advisor": "വിള ഉപദേഷ്ടാവ്", "Leaf Doctor": "ഇല ഡോക്ടർ", "leaf doctor": "ഇല ഡോക്ടർ",
"Market": "വിപണി", "market": "വിപണി", "Watering": "ജലസേചനം", "water": "വെള്ളം",
"Listen": "കേൾക്കൂ", "listen": "കേൾക്കൂ", "Field Watch": "വയൽ നിരീക്ഷണം", "field": "വയൽ",
"Find what your soil": "നിങ്ങളുടെ മണ്ണ് എന്ത്", "wants to grow.": "കൃഷി ചെയ്യാൻ ആഗ്രഹിക്കുന്നു.",
"A": "ഒരു", "second pair of eyes": "രണ്ടാം കണ്ണ്", "for sick leaves.": "രോഗഗ്രസ്ത ഇലകൾക്ക്.",
"Send a photo": "ഫോട്ടോ അയക്കൂ", "What we see": "ഞങ്ങൾ കണ്ടത്",
"Upload a recording": "റെക്കോർഡിംഗ് അപ്‌ലോഡ് ചെയ്യൂ", "What we heard": "ഞങ്ങൾ കേട്ടത്",
"Calculate irrigation": "ജലസേചനം കണക്കാക്കൂ", "Get advice": "ഉപദേശം നേടൂ",
"🛰 Scan now": "🛰 ഇപ്പോൾ സ്കാൻ ചെയ്യൂ", "Emergency helplines": "അടിയന്തര ഹെൽപ്‌ലൈൻ",
"Pollinator": "പരാഗണകാരി", "Pest": "കീടം", "Ambient": "പരിസ്ഥിതി",
"Initial": "പ്രാരംഭ", "Development": "വളർച്ച", "Mid-season": "മധ്യ-സീസൺ", "Late season": "അവസാന സീസൺ",
"best price": "മികച്ച വില", "worst price": "ഏറ്റവും കുറഞ്ഞ വില", "average price": "ശരാശരി വില",
"our advice": "ഞങ്ങളുടെ ഉപദേശം", "days": "ദിവസങ്ങൾ", "Date": "തീയതി", "Price": "വില",
"Min": "ഏറ്റവും കുറഞ്ഞ", "Max": "ഏറ്റവും കൂടിയ", "Confidence": "ആത്മവിശ്വാസം",
"Duration": "ദൈർഘ്യം", "Sample rate": "സാമ്പിൾ നിരക്ക്", "Energy": "ഊർജ്ജം",
"Severity": "തീവ്രത", "Role": "പങ്ക്", "Name": "പേര്",
"clear": "മായ്ക്കൂ", "farmer · since 2019": "കർഷകൻ · 2019 മുതൽ",
"a calm field today is a good harvest tomorrow.": "ഇന്നത്തെ ശാന്തമായ വയൽ നാളത്തെ നല്ല വിളവ്."
```

**Gujarati (gu):**
```json
"Nitrogen": "નાઇટ્રોજન", "Phosphorus": "ફોસ્ફરસ", "Potassium": "પોટેશિયમ",
"Soil pH": "માટીનું pH", "Temperature": "તાપમાન", "Humidity": "ભેજ", "Rainfall": "વરસાદ",
"crop advisor": "પાક સલાહકાર", "Leaf Doctor": "પાન ડૉક્ટર", "leaf doctor": "પાન ડૉક્ટર",
"Market": "બજાર", "market": "બજાર", "Watering": "સિંચાઈ", "water": "પાણી",
"Listen": "સાંભળો", "listen": "સાંભળો", "Field Watch": "ખેત નિગરાની", "field": "ખેત",
"Find what your soil": "તમારી માટી શું", "wants to grow.": "ઉગાડવા ઇચ્છે છે.",
"A": "એક", "second pair of eyes": "બીજી નજર", "for sick leaves.": "બીમાર પાંદડા માટે.",
"Send a photo": "ફોટો મોકલો", "What we see": "અમે શું જોયું",
"Upload a recording": "રેકોર્ડિંગ અપલોડ કરો", "What we heard": "અમે શું સાંભળ્યું",
"Calculate irrigation": "સિંચાઈ ગણો", "Get advice": "સલાહ મેળવો",
"🛰 Scan now": "🛰 અત્યારે સ્કેન કરો", "Emergency helplines": "કટોકટી હેલ્પલાઇન",
"Pollinator": "પરાગ વાહક", "Pest": "જીવાત", "Ambient": "પર્યાવરણ",
"Initial": "શરૂઆત", "Development": "વિકાસ", "Mid-season": "મધ્ય-સીઝન", "Late season": "છેલ્લી સીઝન",
"best price": "શ્રેષ્ઠ ભાવ", "worst price": "ઓછો ભાવ", "average price": "સરેરાશ ભાવ",
"our advice": "અમારી સલાહ", "days": "દિવસ", "Date": "તારીખ", "Price": "ભાવ",
"Min": "ઓછામાં ઓછું", "Max": "વધારેમાં વધારે", "Confidence": "વિશ્વાસ",
"Duration": "અવધિ", "Sample rate": "સૅમ્પલ દર", "Energy": "ઊર્જા",
"Severity": "તીવ્રતા", "Role": "ભૂમિકા", "Name": "નામ",
"clear": "સાફ કરો", "farmer · since 2019": "ખેડૂત · 2019 થી",
"a calm field today is a good harvest tomorrow.": "આજનું શાંત ખેત આવતીકાલની સારી લણણી."
```

**Punjabi (pa):**
```json
"Nitrogen": "ਨਾਈਟ੍ਰੋਜਨ", "Phosphorus": "ਫਾਸਫੋਰਸ", "Potassium": "ਪੋਟਾਸ਼ੀਅਮ",
"Soil pH": "ਮਿੱਟੀ ਦਾ pH", "Temperature": "ਤਾਪਮਾਨ", "Humidity": "ਨਮੀ", "Rainfall": "ਬਾਰਸ਼",
"crop advisor": "ਫ਼ਸਲ ਸਲਾਹਕਾਰ", "Leaf Doctor": "ਪੱਤਾ ਡਾਕਟਰ", "leaf doctor": "ਪੱਤਾ ਡਾਕਟਰ",
"Market": "ਮੰਡੀ", "market": "ਮੰਡੀ", "Watering": "ਸਿੰਚਾਈ", "water": "ਪਾਣੀ",
"Listen": "ਸੁਣੋ", "listen": "ਸੁਣੋ", "Field Watch": "ਖੇਤ ਨਿਗਰਾਨੀ", "field": "ਖੇਤ",
"Find what your soil": "ਜਾਣੋ ਤੁਹਾਡੀ ਮਿੱਟੀ ਕੀ", "wants to grow.": "ਉਗਾਉਣਾ ਚਾਹੁੰਦੀ ਹੈ।",
"A": "ਇੱਕ", "second pair of eyes": "ਦੂਜੀ ਨਜ਼ਰ", "for sick leaves.": "ਬਿਮਾਰ ਪੱਤਿਆਂ ਲਈ।",
"Send a photo": "ਫੋਟੋ ਭੇਜੋ", "What we see": "ਅਸੀਂ ਕੀ ਦੇਖਿਆ",
"Upload a recording": "ਰਿਕਾਰਡਿੰਗ ਅਪਲੋਡ ਕਰੋ", "What we heard": "ਅਸੀਂ ਕੀ ਸੁਣਿਆ",
"Calculate irrigation": "ਸਿੰਚਾਈ ਦੀ ਗਣਨਾ ਕਰੋ", "Get advice": "ਸਲਾਹ ਲਓ",
"🛰 Scan now": "🛰 ਹੁਣ ਸਕੈਨ ਕਰੋ", "Emergency helplines": "ਐਮਰਜੈਂਸੀ ਹੈਲਪਲਾਈਨ",
"Pollinator": "ਪਰਾਗਣ ਕਰਨ ਵਾਲਾ", "Pest": "ਕੀੜਾ", "Ambient": "ਵਾਤਾਵਰਨ",
"Initial": "ਸ਼ੁਰੂਆਤੀ", "Development": "ਵਿਕਾਸ", "Mid-season": "ਮੱਧ-ਮੌਸਮ", "Late season": "ਅਖੀਰੀ ਮੌਸਮ",
"best price": "ਸਭ ਤੋਂ ਵਧੀਆ ਕੀਮਤ", "worst price": "ਸਭ ਤੋਂ ਘੱਟ ਕੀਮਤ", "average price": "ਔਸਤ ਕੀਮਤ",
"our advice": "ਸਾਡੀ ਸਲਾਹ", "days": "ਦਿਨ", "Date": "ਤਾਰੀਖ਼", "Price": "ਕੀਮਤ",
"Min": "ਘੱਟੋ-ਘੱਟ", "Max": "ਵੱਧ ਤੋਂ ਵੱਧ", "Confidence": "ਭਰੋਸਾ",
"Duration": "ਮਿਆਦ", "Sample rate": "ਸੈਂਪਲ ਦਰ", "Energy": "ਊਰਜਾ",
"Severity": "ਗੰਭੀਰਤਾ", "Role": "ਭੂਮਿਕਾ", "Name": "ਨਾਮ",
"clear": "ਸਾਫ਼ ਕਰੋ", "farmer · since 2019": "ਕਿਸਾਨ · 2019 ਤੋਂ",
"a calm field today is a good harvest tomorrow.": "ਅੱਜ ਦਾ ਸ਼ਾਂਤ ਖੇਤ ਕੱਲ੍ਹ ਦੀ ਚੰਗੀ ਫ਼ਸਲ ਹੈ।"
```

Note: Each language section above shows the most critical UI strings. The full implementation must include ALL keys from Task 9 for each language (matching the complete Hindi list). Fill in any missing keys following the same translation pattern.

- [ ] **Step 5: Commit**

```bash
git add web/lib/bundles.json
git commit -m "feat(i18n): add te/ta/kn/bn/mr/ml/gu/pa translations for all new keys"
```

---

## Task 11 — End-to-end verification

- [ ] **Step 1: Start the dev server**

```bash
cd /Users/kiyo/smart-crop-advisor
# start however the web server is run, e.g.:
python -m http.server 3000 --directory web
# or whatever dev command is in package.json
```

- [ ] **Step 2: Test each language on each tab**

Open the app. Use the language switcher in the sidebar. For each language (hi, te, ta, kn, bn), verify:
1. **Tab 1 (Crop):** Slider labels (Nitrogen, Phosphorus, etc.), button text, hints (a little hungry, acidic, etc.) all change
2. **Tab 2 (Disease):** Page title, drop zone text, card headings, error states all change
3. **Tab 3 (Market):** Page title, table headers (Date, Price, Min, Max), metric eyebrows (best price, our advice), chart fallback message all change
4. **Tab 4 (Irrigation):** Page title, growth stage buttons, slider labels, metric labels all change
5. **Tab 5 (Acoustic):** Page title, drop zone text, result card labels, table headers, warning messages all change
6. **Tab 6 (Field Watch):** Page title, weather metric labels, alert card titles, helpline names and descriptions, calamity tips, button text all change

- [ ] **Step 3: Test English fallback**

In browser console run: `window.I18N.bundles['hi']['Nitrogen']` — should return `"नाइट्रोजन"`. Then temporarily check a key that doesn't exist: `window.I18N.bundles['hi']['nonexistent']` — should return `undefined`, and the UI should fall back to English.

- [ ] **Step 4: Check for visible raw key strings**

Look for any UI text that appears as a full English sentence in a non-English mode — that indicates a missing `t()` wrap or a missing bundle key. Fix any found.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat(i18n): complete multilingual coverage for web frontend"
```
