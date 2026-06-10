# Field Instrument Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the photo+glassmorphism KisanOS SPA with the approved "Field Instrument" design (paper shell, carbon instruments, engineered green, choreographed motion) across login, shell, and all six tabs.

**Architecture:** The whole app shares one stylesheet (`web/index.html <style>`) and one set of shared classes (`card`, `btn`, `input`, `page-title`…), so the redesign lands as: (1) a wholesale token/CSS rewrite that redefines those classes and aliases the legacy tokens (`--leaf`, `--glass-*`…) so every screen instantly switches theme without breaking; (2) new primitives in `atoms.jsx` (DotMatrix, LinearGauge, Ticker); (3) per-view JSX passes that restructure each tab into a "sheet + instrument" layout and remove glass-era inline styles. Logic, hooks, and API calls are untouched.

**Tech Stack:** Classic-script React 18 (no bundler; dev = in-browser Babel, prod = `scripts/build_frontend.py` precompile), CSS custom properties + keyframes + WAAPI-free animation, canvas 2D for DotMatrix, Google Fonts (Space Grotesk / Inter / JetBrains Mono / Noto Sans Indic set). No new dependencies (prod CSP is `script-src 'self'`).

**Reference docs:** `/PRODUCT.md`, `/DESIGN.md`, `docs/superpowers/specs/2026-06-10-field-instrument-redesign-design.md`

**Verification model:** There is no JS test infra. Each task verifies in the browser against `python run_api.py` (serves SPA+API on :8000) and must keep `pytest tests/` green (serve/CSP/security-header tests). Visual checks use the chrome-devtools MCP or a manual browser. JSX files MUST keep the classic-script rules: top-level `var` (never file-scope `const` that collides across files), components exported via `window.X = X`.

**Important global rules for every task:**
- Never introduce `border-left`/`border-right` accent stripes, gradient text, glass blur, or emoji-as-UI.
- All new animation: transform/opacity only, easing `var(--ease)`, and silenced by the global `prefers-reduced-motion` block (Task 2).
- New user-facing strings go through `t('...')` with the English string as key (the `makeT` fallback chain en → key makes English render everywhere until translated).

---

### Task 0: Branch

- [ ] **Step 0.1:** Create the working branch (or worktree via superpowers:using-git-worktrees):

```bash
git checkout -b redesign/field-instrument
```

---

### Task 1: Fonts + design tokens + base styles

**Files:**
- Modify: `web/index.html:7-9` (font links), `web/index.html:10-59` (token block)

- [ ] **Step 1.1: Replace the Google Fonts link** (drop Cormorant Garamond + all Noto *Serif*; add Space Grotesk, JetBrains Mono, Noto *Sans* equivalents; keep Inter):

```html
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500;600&family=Noto+Sans+Devanagari:wght@400;500;600;700&family=Noto+Sans+Tamil:wght@400;500;600;700&family=Noto+Sans+Telugu:wght@400;500;600;700&family=Noto+Sans+Bengali:wght@400;500;600;700&family=Noto+Sans+Kannada:wght@400;500;600;700&family=Noto+Sans+Malayalam:wght@400;500;600;700&family=Noto+Sans+Gujarati:wght@400;500;600;700&family=Noto+Sans+Gurmukhi:wght@400;500;600;700&display=swap" rel="stylesheet">
```

- [ ] **Step 1.2: Replace the `:root` token block and per-language overrides** (`web/index.html` lines 10-59). The legacy aliases keep every untouched inline style rendering sanely until its per-view task lands:

```css
:root{
  /* Field Instrument tokens */
  --paper:    oklch(97.5% 0.006 120);
  --paper-2:  oklch(94.8% 0.008 120);
  --ink:      oklch(21% 0.012 140);
  --ink-soft:  color-mix(in oklab, oklch(21% 0.012 140) 72%, transparent);
  --ink-faint: color-mix(in oklab, oklch(21% 0.012 140) 46%, transparent);
  --carbon:   oklch(17% 0.012 150);
  --carbon-2: oklch(22% 0.014 150);
  --signal:        oklch(56% 0.155 150);
  --signal-bright: oklch(82% 0.21 150);
  --signal-dim:    color-mix(in oklab, oklch(56% 0.155 150) 12%, transparent);
  --alarm:    oklch(55% 0.19 30);
  --alarm-dim: color-mix(in oklab, oklch(55% 0.19 30) 10%, transparent);
  --caution:  oklch(58% 0.125 80);
  --caution-dim: color-mix(in oklab, oklch(58% 0.125 80) 12%, transparent);
  --hairline:        color-mix(in oklab, oklch(21% 0.012 140) 12%, transparent);
  --hairline-strong: color-mix(in oklab, oklch(21% 0.012 140) 26%, transparent);

  --display: 'Space Grotesk', 'Inter', system-ui, sans-serif;
  --body:    'Inter', system-ui, sans-serif;
  --mono:    'JetBrains Mono', ui-monospace, 'SF Mono', monospace;

  --ease: cubic-bezier(0.16, 1, 0.3, 1);
  --rail-w: 248px;

  /* Legacy aliases — old code keeps working; per-view tasks remove usages */
  --leaf: var(--signal); --leaf-2: var(--signal); --leaf-soft: var(--signal-dim);
  --berry: var(--alarm); --sun: var(--caution);
  --line: var(--hairline); --line-2: var(--hairline-strong);
  --glass-bg: var(--paper-2); --glass-bg-hover: var(--paper-2);
  --glass-bg-strong: var(--paper); --glass-bg-subtle: var(--paper-2);
  --glass-border: var(--hairline); --glass-border-strong: var(--hairline-strong);
  --glass-blur: 0px; --glass-blur-sm: 0px; --glass-glow: none;
  --spring: var(--ease); --spring-gentle: var(--ease);
  --sb-w: var(--rail-w);
}

/* Carbon instrument scope — re-declares ink polarity so nested content
   (including legacy inline var(--ink) styles) renders light-on-dark. */
.instrument{
  --ink:      oklch(95% 0.008 120);
  --ink-soft:  color-mix(in oklab, oklch(95% 0.008 120) 72%, transparent);
  --ink-faint: color-mix(in oklab, oklch(95% 0.008 120) 48%, transparent);
  --line:      color-mix(in oklab, oklch(95% 0.008 120) 14%, transparent);
  --line-2:    color-mix(in oklab, oklch(95% 0.008 120) 26%, transparent);
  --hairline: var(--line); --hairline-strong: var(--line-2);
  --signal: var(--signal-bright); --leaf: var(--signal-bright);
  --paper-2: var(--carbon-2);
  --glass-bg: var(--carbon-2); --glass-bg-subtle: var(--carbon-2);
  --glass-border: var(--line); --glass-border-strong: var(--line-2);
}

/* Per-language display font (Indic scripts) — Sans set */
[lang="hi"], [lang="mr"] { --display: 'Noto Sans Devanagari', sans-serif; }
[lang="ta"]              { --display: 'Noto Sans Tamil', sans-serif; }
[lang="te"]              { --display: 'Noto Sans Telugu', sans-serif; }
[lang="bn"]              { --display: 'Noto Sans Bengali', sans-serif; }
[lang="kn"]              { --display: 'Noto Sans Kannada', sans-serif; }
[lang="ml"]              { --display: 'Noto Sans Malayalam', sans-serif; }
[lang="gu"]              { --display: 'Noto Sans Gujarati', sans-serif; }
[lang="pa"]              { --display: 'Noto Sans Gurmukhi', sans-serif; }
```

- [ ] **Step 1.3: Update `html,body` base** (replaces the dark background at `web/index.html:60-66`):

```css
*{box-sizing:border-box}
html,body{margin:0;padding:0;font-family:var(--body);min-height:100vh;font-size:15px;line-height:1.6}
body{ background:var(--paper); color:var(--ink); -webkit-font-smoothing:antialiased }
a{ color:var(--signal) }
::selection{ background:var(--signal); color:var(--paper) }
```

- [ ] **Step 1.4: Verify** — `python run_api.py`, open http://localhost:8000. Expect: light background, dark text, old layout still functional (ugly mid-migration is fine; broken is not). No console errors.

- [ ] **Step 1.5: Commit**

```bash
git add web/index.html
git commit -m "feat(redesign): Field Instrument tokens, fonts, ink-polarity instrument scope"
```

---

### Task 2: Full component stylesheet rewrite

**Files:**
- Modify: `web/index.html` — everything between the base styles and `</style>` (old lines ~68-598: bg-stack, auth, layout, sidebar, tabbar, cards, forms, donut, responsive)

This is the soul of the redesign. Replace the remaining CSS wholesale with the blocks below (order matters; keep class names used by JSX). Delete: all `.bg-stack/.bg-photo/.bg-overlay` rules, all glass/backdrop-filter rules, the `@supports not (backdrop-filter…)` fallback, old keyframes.

- [ ] **Step 2.1: Typography & sheet structure**

```css
/* ===== Type ===== */
h2,h3,h4{ font-family:var(--display); color:var(--ink); margin:0 0 6px; font-weight:600; letter-spacing:-0.01em }
h2{font-size:25px} h3{font-size:19px} h4{font-size:15px}
.page-head{ margin:8px 0 34px }
.page-eyebrow{
  font-family:var(--mono); font-size:11px; font-weight:500;
  letter-spacing:0.08em; text-transform:uppercase; color:var(--ink-faint);
}
.page-title{
  font-family:var(--display); font-weight:600; text-transform:lowercase;
  font-size:clamp(34px, 4.6vw, 64px); line-height:1.04; letter-spacing:-0.025em;
  color:var(--ink); margin:10px 0 14px;
}
.page-title em{ font-style:normal; color:var(--signal) }
.page-lede{ max-width:62ch; color:var(--ink-soft); font-size:15px; margin:0 }
.muted{ color:var(--ink-soft) } .small{ font-size:12px }
.mono{ font-family:var(--mono); font-variant-numeric:tabular-nums }

/* numbered section header: <div class="sec-h"><span>01</span> field inputs</div> */
.sec-h{
  display:flex; align-items:baseline; gap:10px; margin:34px 0 18px;
  padding-top:14px; border-top:1px solid var(--hairline);
  font-family:var(--mono); font-size:11px; letter-spacing:0.08em;
  text-transform:uppercase; color:var(--ink-soft);
}
.sec-h span{ color:var(--signal); font-weight:600 }
.bignum{ font-family:var(--display); font-weight:600; font-size:44px; letter-spacing:-0.02em; color:var(--ink); line-height:1 }
.bignum em{ font-style:normal }
.bignum .unit{ font-family:var(--mono); font-size:13px; color:var(--ink-faint); margin-left:4px }
```

- [ ] **Step 2.2: Shell — layout, rail (sidebar), topbar, mobile tabbar**

```css
/* ===== Layout ===== */
.layout{ display:grid; grid-template-columns:var(--rail-w) 1fr; min-height:100vh }
.layout.collapsed{ grid-template-columns:0 1fr }
.main{ padding:26px clamp(20px, 4vw, 56px) 80px; max-width:1240px; width:100% }

/* ===== Rail ===== */
.sidebar{
  position:sticky; top:0; height:100vh; overflow:hidden;
  border-right:1px solid var(--hairline); background:var(--paper);
  display:flex; flex-direction:column;
}
.layout.collapsed .sidebar{ border-right:none }
.sb-content{ display:flex; flex-direction:column; height:100%; padding:22px 18px; overflow-y:auto }
.sb-brand{ display:flex; align-items:baseline; gap:6px; margin-bottom:26px }
.brand-name{
  font-family:var(--display); font-weight:600; font-size:19px;
  letter-spacing:-0.02em; text-transform:lowercase; color:var(--ink);
}
.brand-name em{ font-style:normal }
.brand-dot{ width:7px; height:7px; background:var(--signal); display:inline-block }
.brand-tag{ font-family:var(--mono); font-size:10px; letter-spacing:0.08em; text-transform:uppercase; color:var(--ink-faint) }

.rail-nav{ display:flex; flex-direction:column; margin:0 -18px 18px }
.rail-item{
  display:flex; align-items:center; justify-content:space-between;
  padding:11px 18px; border:0; border-top:1px solid var(--hairline);
  background:none; cursor:pointer; text-align:left; width:100%;
  font-family:var(--display); font-size:14px; font-weight:500;
  text-transform:lowercase; letter-spacing:-0.01em; color:var(--ink-soft);
  transition:color .18s var(--ease), background .18s var(--ease);
}
.rail-item:last-child{ border-bottom:1px solid var(--hairline) }
.rail-item:hover{ color:var(--ink); background:var(--paper-2) }
.rail-item.active{ color:var(--ink) }
.rail-item .idx{ font-family:var(--mono); font-size:10px; color:var(--ink-faint); letter-spacing:0.06em }
.rail-item.active .idx{ color:var(--signal) }
.rail-item .tick{ width:6px; height:6px; background:var(--signal); opacity:0; transform:scale(0.4); transition:all .25s var(--ease) }
.rail-item.active .tick{ opacity:1; transform:scale(1) }

.profile-card{ border-top:1px solid var(--hairline); padding-top:14px; margin-bottom:16px }
.profile-row{ display:flex; gap:10px; align-items:center; margin-bottom:10px }
.avatar{
  width:34px; height:34px; display:flex; align-items:center; justify-content:center;
  background:var(--ink); color:var(--paper); font-family:var(--mono); font-size:12px; font-weight:600;
}
.profile-name-input{
  width:100%; border:0; background:none; color:var(--ink);
  font-family:var(--display); font-size:15px; font-weight:600; padding:0;
}
.profile-name-input:focus{ outline:none }
.profile-field{ display:flex; align-items:center; gap:8px; padding:7px 0; border-bottom:1px solid var(--hairline) }
.profile-field .ic{ font-family:var(--mono); font-size:10px; letter-spacing:0.06em; color:var(--ink-faint); text-transform:uppercase; min-width:38px }
.profile-field input{ flex:1; border:0; background:none; color:var(--ink-soft); font-size:13px; font-family:var(--body) }
.profile-field input:focus{ outline:none; color:var(--ink) }

.lang-pill{
  display:flex; align-items:center; gap:8px; width:100%;
  background:none; border:1px solid var(--hairline-strong); border-radius:0;
  padding:9px 12px; cursor:pointer; color:var(--ink); font-family:var(--mono); font-size:12px;
}
.lang-menu{
  position:absolute; bottom:calc(100% + 6px); left:0; right:0; z-index:30;
  background:var(--paper); border:1px solid var(--hairline-strong);
  max-height:280px; overflow-y:auto;
}
.lang-menu button{
  display:block; width:100%; text-align:left; padding:9px 12px; border:0;
  border-top:1px solid var(--hairline); background:none; cursor:pointer;
  font-size:13px; color:var(--ink-soft); font-family:var(--body);
}
.lang-menu button:hover{ background:var(--paper-2); color:var(--ink) }
.lang-menu button.active{ color:var(--signal) }

.sb-actions{ margin-top:auto; padding-top:14px; border-top:1px solid var(--hairline) }
.sb-action{
  display:flex; align-items:center; gap:8px; background:none; border:0; cursor:pointer;
  font-family:var(--mono); font-size:11px; letter-spacing:0.08em; text-transform:uppercase;
  color:var(--ink-faint); padding:6px 0;
}
.sb-action:hover{ color:var(--alarm) }

/* collapse FAB */
.sb-fab{
  position:fixed; z-index:60; top:18px; left:18px; width:34px; height:34px;
  display:flex; flex-direction:column; gap:4px; align-items:center; justify-content:center;
  background:var(--paper); border:1px solid var(--hairline-strong); cursor:pointer;
}
.sb-fab-bar{ width:14px; height:1.5px; background:var(--ink); transition:transform .25s var(--ease) }
.sb-fab.is-open{ left:calc(var(--rail-w) - 17px) }
.sb-toggle-host,.sb-collapsed-icon{ display:none }

/* ===== Topbar ===== */
.topbar{
  display:flex; justify-content:space-between; align-items:center;
  padding:0 0 14px; margin-bottom:6px; border-bottom:1px solid var(--hairline);
}
.crumb{ font-family:var(--mono); font-size:11px; letter-spacing:0.08em; text-transform:uppercase; color:var(--ink-faint) }
.live{ display:flex; align-items:center; gap:7px; font-family:var(--mono); font-size:11px; color:var(--ink-soft) }
.live .dot{ animation:pulse 2.4s var(--ease) infinite }
@keyframes pulse{ 0%,100%{opacity:1} 50%{opacity:0.3} }

/* ===== Tabbar (mobile only) ===== */
.tabbar-wrap{ display:none }
```

- [ ] **Step 2.3: Sheet blocks, forms, buttons, instrument, states**

```css
/* ===== Blocks (old .card → open paper section) ===== */
.card{ background:none; border:0; border-top:1px solid var(--hairline); border-radius:0; padding:18px 0 22px; margin-bottom:4px }
.card-h{ display:flex; justify-content:space-between; align-items:baseline; gap:12px; margin-bottom:14px }
.card-h .meta{ font-family:var(--mono); font-size:11px; letter-spacing:0.08em; text-transform:uppercase; color:var(--ink-faint) }
.grid-2{ display:grid; grid-template-columns:1fr 1fr; gap:0 44px }
.grid-3{ display:grid; grid-template-columns:repeat(3,1fr); gap:0 32px }
.grid-4{ display:grid; grid-template-columns:repeat(4,1fr); gap:0 32px }

/* ===== Instrument panel ===== */
.instrument{
  background:var(--carbon); color:var(--ink);
  border-radius:18px; padding:26px 28px; position:relative; overflow:hidden;
  box-shadow:inset 0 0 0 1px color-mix(in oklab, oklch(95% 0.008 120) 8%, transparent);
}
.instrument.ignite{ animation:ignite .6s var(--ease) both }
@keyframes ignite{ from{ opacity:0; transform:translateY(14px) scale(0.985) } to{ opacity:1; transform:none } }
.inst-label{
  font-family:var(--mono); font-size:10px; letter-spacing:0.12em; text-transform:uppercase;
  color:var(--ink-faint); display:flex; justify-content:space-between; margin-bottom:14px;
}
.inst-sticky{ position:sticky; top:24px; align-self:start }

/* ===== Forms ===== */
.input, select.input, textarea.input{
  background:none; border:0; border-bottom:1px solid var(--hairline-strong); border-radius:0;
  color:var(--ink); font-family:var(--body); font-size:14px; padding:9px 2px;
  transition:border-color .2s var(--ease);
}
.input:focus{ outline:none; border-bottom-color:var(--signal) }
select.input{ cursor:pointer }
.field{ margin-bottom:16px }
.field-label{ display:flex; justify-content:space-between; align-items:baseline; margin-bottom:7px }
.field-label .name{ font-size:13px; color:var(--ink-soft) }
.field-label .val{ font-family:var(--mono); font-size:14px; font-weight:600; color:var(--ink); font-variant-numeric:tabular-nums }
input[type=range]{ -webkit-appearance:none; appearance:none; width:100%; height:20px; background:none; cursor:pointer; --p:50% }
input[type=range]::-webkit-slider-runnable-track{ height:2px; background:linear-gradient(to right, var(--ink) var(--p), var(--hairline) var(--p)) }
input[type=range]::-webkit-slider-thumb{
  -webkit-appearance:none; width:13px; height:13px; margin-top:-5.5px;
  background:var(--paper); border:2px solid var(--ink); border-radius:0; transform:rotate(45deg);
}
input[type=range]::-moz-range-track{ height:2px; background:var(--hairline) }
input[type=range]::-moz-range-progress{ height:2px; background:var(--ink) }
input[type=range]::-moz-range-thumb{ width:11px; height:11px; background:var(--paper); border:2px solid var(--ink); border-radius:0; transform:rotate(45deg) }

.locbar{ display:flex; gap:18px; align-items:flex-end; padding:0 0 18px; flex-wrap:wrap }
.locbar .pin{ font-family:var(--mono); font-size:10px; letter-spacing:0.08em; text-transform:uppercase; color:var(--ink-faint) }
.locbar .input{ min-width:180px }

.drop{
  border:1px dashed var(--hairline-strong); border-radius:0; padding:34px 18px;
  text-align:center; cursor:pointer; transition:border-color .2s var(--ease), background .2s var(--ease);
}
.drop:hover{ border-color:var(--ink); background:var(--paper-2) }

/* ===== Buttons & tags ===== */
.btn{
  display:inline-flex; align-items:center; gap:8px;
  background:none; border:1px solid var(--hairline-strong); border-radius:999px;
  color:var(--ink); font-family:var(--display); font-weight:500; font-size:14px;
  text-transform:lowercase; letter-spacing:0; padding:10px 20px; cursor:pointer;
  transition:transform .18s var(--ease), background .18s var(--ease), color .18s var(--ease), border-color .18s var(--ease);
}
.btn:hover{ border-color:var(--ink); transform:translateY(-1px) }
.btn:active{ transform:translateY(0) }
.btn.primary{ background:var(--ink); border-color:var(--ink); color:var(--paper) }
.btn.primary:hover{ background:var(--carbon-2) }
.btn.primary:disabled{ opacity:0.5; cursor:default; transform:none }
.btn.ghost{ border-color:transparent; color:var(--ink-soft) }
.btn.ghost:hover{ color:var(--ink); border-color:var(--hairline-strong) }
.instrument .btn.primary{ background:var(--signal-bright); border-color:var(--signal-bright); color:var(--carbon) }
.tag{
  display:inline-flex; align-items:center; gap:6px;
  font-family:var(--mono); font-size:10px; letter-spacing:0.08em; text-transform:uppercase;
  border:1px solid var(--hairline-strong); border-radius:999px; padding:4px 10px; color:var(--ink-soft);
}
.tag.alert{ border-color:var(--alarm); color:var(--alarm) }
.tag.warn{ border-color:var(--caution); color:var(--caution) }
.tile{
  display:inline-flex; align-items:center; border:1px solid var(--hairline-strong);
  background:none; border-radius:0; padding:10px 14px; cursor:pointer; color:var(--ink-soft);
  font-family:var(--body); font-size:13px; transition:all .18s var(--ease);
}
.tile:hover{ border-color:var(--ink); color:var(--ink) }
.tile.active{ background:var(--ink); border-color:var(--ink); color:var(--paper) }

/* ===== States ===== */
.state-loading{ position:relative; overflow:hidden; padding:34px 0; text-align:center;
  font-family:var(--mono); font-size:12px; letter-spacing:0.08em; text-transform:uppercase; color:var(--ink-faint) }
.state-loading::after{
  content:''; position:absolute; inset:0;
  background:linear-gradient(100deg, transparent 30%, color-mix(in oklab, var(--ink) 5%, transparent) 50%, transparent 70%);
  animation:scan 1.4s linear infinite;
}
@keyframes scan{ from{ transform:translateX(-100%) } to{ transform:translateX(100%) } }
.state-empty{ padding:30px 0; text-align:center; color:var(--ink-faint); font-size:13px }
.state-empty .ghost{ font-family:var(--display); font-weight:600; font-size:54px; line-height:1; color:transparent;
  -webkit-text-stroke:1px var(--hairline-strong); display:block; margin-bottom:8px }
.error-panel{ border-top:1px solid var(--alarm); padding:16px 0 }
.error-panel .et{ font-family:var(--mono); font-size:11px; letter-spacing:0.08em; text-transform:uppercase; color:var(--alarm); margin-bottom:6px }

/* hairline stat row: <div class="stat-row"><div class="stat">…</div>… */
.stat-row{ display:flex }
.stat-row .stat{ flex:1; padding:14px 18px 14px 0; border-top:1px solid var(--hairline) }
.stat-row .stat + .stat{ padding-left:18px; border-left:1px solid var(--hairline) }
.stat .s-label{ font-family:var(--mono); font-size:10px; letter-spacing:0.1em; text-transform:uppercase; color:var(--ink-faint); margin-bottom:6px }

/* progress hairline bars (replaces rounded prob bars) */
.hbar{ height:3px; background:var(--hairline); position:relative; overflow:hidden }
.hbar > i{ position:absolute; inset:0 auto 0 0; background:var(--signal); display:block; transition:width .8s var(--ease) }
```

- [ ] **Step 2.4: Auth screen, ticker, toast, motion system, responsive** (auth markup is rewritten in Task 6; these classes serve it)

```css
/* ===== Auth ===== */
.auth-screen{ min-height:100vh; display:flex; flex-direction:column; justify-content:center; padding:40px clamp(20px,6vw,80px); position:relative }
.auth-card{ width:100%; max-width:560px; background:none; border:0; padding:0; box-shadow:none; animation:none }
.auth-wordmark{
  font-family:var(--display); font-weight:600; text-transform:lowercase; letter-spacing:-0.04em;
  font-size:clamp(54px, 11vw, 128px); line-height:0.95; color:var(--ink); margin:0 0 8px;
}
.auth-wordmark .dot{ display:inline-block; width:0.14em; height:0.14em; background:var(--signal); margin-left:0.06em }
.auth-sub{ font-family:var(--mono); font-size:12px; letter-spacing:0.08em; text-transform:uppercase; color:var(--ink-faint); margin:0 0 40px }
.auth-field{ margin-bottom:22px }
.auth-field label{ display:block; font-family:var(--mono); font-size:10px; letter-spacing:0.1em; text-transform:uppercase; color:var(--ink-faint); margin-bottom:8px }
.auth-input{
  width:100%; background:none; border:0; border-bottom:1px solid var(--hairline-strong);
  font-family:var(--mono); font-size:22px; color:var(--ink); padding:8px 2px; letter-spacing:0.04em;
  transition:border-color .2s var(--ease);
}
.auth-input:focus{ outline:none; border-bottom-color:var(--signal) }
.auth-submit{
  margin-top:6px; background:var(--ink); color:var(--paper); border:1px solid var(--ink); border-radius:999px;
  font-family:var(--display); font-weight:500; font-size:15px; text-transform:lowercase;
  padding:12px 26px; cursor:pointer; transition:transform .18s var(--ease), background .18s var(--ease);
}
.auth-submit:hover{ transform:translateY(-1px); background:var(--carbon-2) }
.auth-submit:disabled{ opacity:0.5; transform:none }
.auth-error{ color:var(--alarm); font-size:13px; margin:10px 0 }
.auth-info{ color:var(--ink-soft); font-size:13px; margin:10px 0 }
.auth-row{ display:flex; gap:22px; margin-top:18px }
.auth-link{ font-family:var(--mono); font-size:11px; letter-spacing:0.06em; text-transform:uppercase; color:var(--ink-soft); text-decoration:none; border-bottom:1px solid var(--hairline-strong) }
.auth-link:hover{ color:var(--ink); border-color:var(--ink) }
.auth-foot{ font-size:12px; color:var(--ink-faint); margin-top:34px }
.demo-chip{ display:flex; align-items:center; justify-content:space-between; gap:12px; border:1px solid var(--hairline-strong); padding:10px 14px; margin:0 0 18px }
.demo-chip .code{ font-family:var(--mono); font-size:22px; letter-spacing:0.22em; color:var(--signal); background:none; border:0; cursor:pointer; padding:0 }

/* ===== Ticker strip ===== */
.ticker{ position:absolute; left:0; right:0; bottom:0; background:var(--carbon); overflow:hidden; padding:12px 0 }
.ticker-track{ display:flex; gap:48px; width:max-content; animation:tick 26s linear infinite }
@keyframes tick{ from{ transform:translateX(0) } to{ transform:translateX(-50%) } }
.ticker .ti{ display:flex; gap:10px; align-items:baseline; font-family:var(--mono); font-size:12px; white-space:nowrap }
.ticker .ti b{ color:var(--signal-bright); font-weight:600 }
.ticker .ti span{ color:color-mix(in oklab, oklch(95% 0.008 120) 50%, transparent); letter-spacing:0.08em; text-transform:uppercase; font-size:10px }

/* ===== Toast ===== */
.toast{ background:var(--ink); color:var(--paper); border-radius:0; padding:9px 16px;
  font-family:var(--mono); font-size:12px; animation:rise .3s var(--ease) both }

/* ===== Motion system ===== */
@keyframes rise{ from{ opacity:0; transform:translateY(12px) } to{ opacity:1; transform:none } }
.rise{ animation:rise .5s var(--ease) both }
.rise-1{ animation-delay:.05s } .rise-2{ animation-delay:.12s } .rise-3{ animation-delay:.19s }
.rise-4{ animation-delay:.26s } .rise-5{ animation-delay:.33s }
.view-fade{ animation:rise .4s var(--ease) both }

/* tab switch phases (driven by app.jsx state machine) */
.tab-content.leaving{ opacity:0; transform:translateY(-8px); transition:opacity .16s ease-in, transform .16s ease-in }
.tab-content.entering{ animation:rise .42s var(--ease) both }

/* boot sequence: body[data-boot="1"] set for ~1.1s after sign-in */
body[data-boot="1"] .rail-item{ opacity:0; animation:rise .5s var(--ease) forwards }
body[data-boot="1"] .rail-item:nth-child(1){ animation-delay:.10s }
body[data-boot="1"] .rail-item:nth-child(2){ animation-delay:.16s }
body[data-boot="1"] .rail-item:nth-child(3){ animation-delay:.22s }
body[data-boot="1"] .rail-item:nth-child(4){ animation-delay:.28s }
body[data-boot="1"] .rail-item:nth-child(5){ animation-delay:.34s }
body[data-boot="1"] .rail-item:nth-child(6){ animation-delay:.40s }
body[data-boot="1"] .topbar{ opacity:0; animation:rise .5s var(--ease) .05s forwards }
body[data-boot="1"] .tab-content{ opacity:0; animation:rise .6s var(--ease) .35s forwards }

/* ===== Reduced motion: kill everything ===== */
@media (prefers-reduced-motion: reduce){
  *, *::before, *::after{ animation-duration:0.01ms !important; animation-delay:0ms !important; transition-duration:0.01ms !important }
  .ticker-track{ animation:none }
}

/* ===== Responsive ===== */
@media(max-width:880px){
  .grid-2,.grid-3{ grid-template-columns:1fr } .grid-4{ grid-template-columns:repeat(2,1fr) }
  .inst-sticky{ position:static }
}
@media(max-width:640px){
  .layout{ grid-template-columns:1fr } .sidebar{ display:none } .sb-fab{ display:none }
  .main{ padding:18px 18px 110px }
  .page-title{ font-size:34px }
  .tabbar-wrap{ display:block; position:fixed; left:0; right:0; bottom:0; z-index:50;
    background:var(--paper); border-top:1px solid var(--hairline-strong); overflow-x:auto }
  .tabbar{ display:flex }
  .tab-pill{ flex:1; min-width:max-content; padding:13px 14px; background:none; border:0; cursor:pointer;
    font-family:var(--mono); font-size:10px; letter-spacing:0.06em; text-transform:uppercase; color:var(--ink-faint);
    border-top:2px solid transparent }
  .tab-pill.active{ color:var(--ink); border-top-color:var(--signal) }
  .stat-row{ flex-direction:column } .stat-row .stat + .stat{ border-left:0; padding-left:0 }
}
```

- [ ] **Step 2.5: Verify** — reload :8000. Shell shows paper rail + hairlines; tabs render light; mobile width (devtools 390px) shows bottom tabbar. Note: emoji and some white-on-white inline bars remain — fixed per-view later.

- [ ] **Step 2.6: Commit** — `git add web/index.html && git commit -m "feat(redesign): full Field Instrument stylesheet (shell, sheet, instrument, forms, motion)"`

---

### Task 3: Remove photo/glass era assets and markup

**Files:**
- Modify: `web/index.html:601-615` (body opening), Delete: `web/assets/bg-*.jpg` (7 files)

- [ ] **Step 3.1:** In `web/index.html`, replace the body opening (the `.bg-stack` div with 8 `.bg-photo` children and the `.bg-overlay` div) with just:

```html
<body data-auth="login">

<div id="root"></div>
```

- [ ] **Step 3.2:** Delete assets and confirm nothing references them (sw.js was checked: no refs):

```bash
git rm web/assets/bg-acoustic.jpg web/assets/bg-crop.jpg web/assets/bg-disease.jpg web/assets/bg-field.jpg web/assets/bg-irrigation.jpg web/assets/bg-login.jpg web/assets/bg-market.jpg
grep -rn "bg-" web/sw.js web/lib/ || true   # expect: no asset hits
```

- [ ] **Step 3.3: Verify** — reload; no 404s in network tab; login renders on plain paper.
- [ ] **Step 3.4: Commit** — `git commit -am "feat(redesign): remove photo backgrounds and glass markup"`

---

### Task 4: New primitives in atoms.jsx — DotMatrix, LinearGauge, Ticker; restyle shared helpers

**Files:**
- Modify: `web/components/atoms.jsx` (Slider hint line, Donut → keep + add new, LocationBar pin, Loading, ErrorCard, ToastContainer, window exports)

- [ ] **Step 4.1: Add DotMatrix** (canvas 5×7 dot numerals; place above `Slider`). Complete component:

```jsx
/* DotMatrix — 5x7 dot-grid numeral renderer (the instrument signature).
   props: value (string|number), height (px, default 56), color (css color string,
   default signal-bright), align ('left'|'center'). Re-animates on value change;
   instant under prefers-reduced-motion. */
const DM_FONT = {
  '0':['01110','10001','10011','10101','11001','10001','01110'],
  '1':['00100','01100','00100','00100','00100','00100','01110'],
  '2':['01110','10001','00001','00010','00100','01000','11111'],
  '3':['11111','00010','00100','00010','00001','10001','01110'],
  '4':['00010','00110','01010','10010','11111','00010','00010'],
  '5':['11111','10000','11110','00001','00001','10001','01110'],
  '6':['00110','01000','10000','11110','10001','10001','01110'],
  '7':['11111','00001','00010','00100','01000','01000','01000'],
  '8':['01110','10001','10001','01110','10001','10001','01110'],
  '9':['01110','10001','10001','01111','00001','00010','01100'],
  '.':['00000','00000','00000','00000','00000','01100','01100'],
  ',':['00000','00000','00000','00000','01100','00100','01000'],
  '%':['11000','11001','00010','00100','01000','10011','00011'],
  '-':['00000','00000','00000','01110','00000','00000','00000'],
  '₹':['11111','00100','11111','01000','01110','01001','01000'],
  '/':['00001','00010','00100','00100','00100','01000','10000'],
  ' ':['00000','00000','00000','00000','00000','00000','00000'],
};
function DotMatrix({ value, height = 56, color, align = 'left' }) {
  const canvasRef = useRef(null);
  const rafRef = useRef(0);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const chars = String(value).split('').filter(c => DM_FONT[c]);
    const dot = height / 9;                 // 7 rows + breathing room
    const gap = dot * 0.45;
    const chW = 5 * dot + 4 * gap, chGap = dot * 1.6;
    const W = Math.max(1, chars.length * chW + Math.max(0, chars.length - 1) * chGap);
    const dpr = window.devicePixelRatio || 1;
    canvas.width = W * dpr; canvas.height = height * dpr;
    canvas.style.width = W + 'px'; canvas.style.height = height + 'px';
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    const fill = color ||
      getComputedStyle(canvas).getPropertyValue('--signal-bright').trim() || '#7fd98c';
    const dots = [];
    chars.forEach((ch, ci) => {
      DM_FONT[ch].forEach((row, r) => {
        row.split('').forEach((bit, c) => {
          if (bit === '1') dots.push({
            x: ci * (chW + chGap) + c * (dot + gap) + dot / 2,
            y: r * (dot + gap) + dot / 2,
            order: Math.random(),
          });
        });
      });
    });
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const D = reduced ? 0 : 480;
    const t0 = performance.now();
    cancelAnimationFrame(rafRef.current);
    function frame(now) {
      const p = D === 0 ? 1 : Math.min(1, (now - t0) / D);
      ctx.clearRect(0, 0, W, height);
      ctx.fillStyle = fill;
      dots.forEach(d => {
        if (d.order <= p) {
          ctx.beginPath();
          ctx.arc(d.x, d.y, dot / 2, 0, Math.PI * 2);
          ctx.fill();
        }
      });
      if (p < 1) rafRef.current = requestAnimationFrame(frame);
    }
    rafRef.current = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(rafRef.current);
  }, [value, height, color]);
  return <canvas ref={canvasRef} style={{ display: 'block', margin: align === 'center' ? '0 auto' : 0 }} aria-label={String(value)} role="img" />;
}
```

- [ ] **Step 4.2: Add LinearGauge and Ticker** (below DotMatrix):

```jsx
/* LinearGauge — hairline track + signal fill. props: value, max, label, unit */
function LinearGauge({ value, max = 100, label, unit }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div style={{ margin: '12px 0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 7 }}>
        <span className="s-label" style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-faint)' }}>{label}</span>
        <span className="mono" style={{ fontSize: 13, fontWeight: 600 }}>{value}{unit && <span style={{ color: 'var(--ink-faint)', fontWeight: 400 }}> {unit}</span>}</span>
      </div>
      <div className="hbar"><i style={{ width: pct + '%' }} /></div>
    </div>
  );
}

/* Ticker — carbon marquee strip. props: items = [[label, value], ...] */
function Ticker({ items }) {
  const doubled = [...items, ...items];
  return (
    <div className="ticker" aria-hidden="true">
      <div className="ticker-track">
        {doubled.map(([label, val], i) => (
          <span className="ti" key={i}><span>{label}</span><b>{val}</b></span>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4.3: Restyle helpers in place** — exact replacements:
  - `Slider` hint div (line ~38): drop `fontStyle:'italic'`, use `fontFamily:'var(--mono)', fontSize:10, letterSpacing:'0.06em', textTransform:'uppercase'`.
  - `Donut` (lines 43-60): leave the component (compat) but change `stroke="rgba(255,255,255,0.10)"` → `stroke="var(--line)"`; ViewCrop stops using it in Task 8.
  - `LocationBar` (line ~128-136): replace `<span className="pin">📍</span>` with `<span className="pin">loc</span>`.
  - `Loading` (lines 317-324): replace the whole body with the scanline state:

```jsx
function Loading({ label }) {
  return <div className="state-loading rise">{label || 'analysing…'}</div>;
}
```

  - `ErrorCard` (lines 326-334): replace with:

```jsx
function ErrorCard({ title, detail, onRetry, t }) {
  return (
    <div className="error-panel rise">
      <div className="et">{title}</div>
      {detail && <div style={{ color: 'var(--ink-soft)', fontSize: 14, marginBottom: 12 }}>{typeof detail === 'string' ? detail : JSON.stringify(detail)}</div>}
      {onRetry && <button className="btn" onClick={onRetry}>{t ? t('try again') : 'try again'}</button>}
    </div>
  );
}
```

  - `ToastContainer` (lines 348-366): replace each toast's inline glass style with `className="toast"` and a 2px top border in the kind color: `style={{ borderTop: \`2px solid ${kindColor[t.kind] || kindColor.info}\` }}` where `kindColor = { info: 'var(--signal)', warn: 'var(--caution)', error: 'var(--alarm)' }`.

- [ ] **Step 4.4: Export the new primitives** — extend the `Object.assign(window, {...})` at the bottom: add `DotMatrix, LinearGauge, Ticker`.

- [ ] **Step 4.5: Verify** — reload; every tab still renders; loading states show scanline; no console errors.
- [ ] **Step 4.6: Commit** — `git commit -am "feat(redesign): DotMatrix, LinearGauge, Ticker primitives; instrument-styled shared states"`

---

### Task 5: Rail Sidebar (with nav), mobile TabBar, Topbar

**Files:**
- Modify: `web/components/atoms.jsx` — `Sidebar` (lines 156-277), `TabBar` (280-302), `Topbar` (305-314)

- [ ] **Step 5.1: Replace `Sidebar` entirely** (keeps all props/behavior: profile edit, language select with outside-click close, logout; adds the nav; removes leaf SVGs, flags, quote, glass snippet):

```jsx
const NAV_ITEMS = [
  { k: 'crop',       idx: '01' },
  { k: 'disease',    idx: '02' },
  { k: 'market',     idx: '03' },
  { k: 'irrigation', idx: '04' },
  { k: 'acoustic',   idx: '05' },
  { k: 'field',      idx: '06' },
];

function Sidebar({ collapsed, setCollapsed, profile, setProfile, lang, setLang, active, setActive, t, onLogout }){
  const [langOpen, setLangOpen] = useState(false);
  const langRef = useRef(null);
  useEffect(()=>{
    function close(e){ if(langRef.current && !langRef.current.contains(e.target)) setLangOpen(false); }
    document.addEventListener('click', close); return ()=>document.removeEventListener('click', close);
  },[]);
  const langObj = LANGS.find(l=>l.code===lang) || LANGS[0];
  const initials = (profile.name||'?').split(' ').map(s=>s[0]).slice(0,2).join('').toUpperCase();
  const NAV_LABELS = {
    crop: t('crop'), disease: t('leaf'), market: t('market'),
    irrigation: t('water'), acoustic: t('listen'), field: t('field watch'),
  };

  return (
    <aside className="sidebar">
      <div className="sb-content">
        <div className="sb-brand">
          <span className="brand-name">kisan<em>os</em></span>
          <span className="brand-dot" aria-hidden="true" />
        </div>
        <div className="brand-tag" style={{marginBottom:22}}>{t('field instrument')}</div>

        <nav className="rail-nav" aria-label={t('sections')}>
          {NAV_ITEMS.map(item => (
            <button key={item.k}
              className={`rail-item ${active === item.k ? 'active' : ''}`}
              onClick={() => setActive(item.k)}>
              <span>{NAV_LABELS[item.k]}</span>
              <span style={{display:'flex',alignItems:'center',gap:8}}>
                <span className="tick" /><span className="idx">{item.idx}</span>
              </span>
            </button>
          ))}
        </nav>

        <div className="profile-card">
          <div className="profile-row">
            <div className="avatar">{initials}</div>
            <input className="profile-name-input" value={profile.name}
              onChange={e=>setProfile({...profile,name:e.target.value})} placeholder={t('your name')}/>
          </div>
          <div className="profile-field"><span className="ic">loc</span>
            <input value={profile.village} onChange={e=>setProfile({...profile,village:e.target.value})} placeholder={t('village')}/></div>
          <div className="profile-field"><span className="ic">tel</span>
            <input value={profile.phone} onChange={e=>setProfile({...profile,phone:e.target.value})} placeholder={t('phone')}/></div>
          <div className="profile-field"><span className="ic">crop</span>
            <input value={profile.crop} onChange={e=>setProfile({...profile,crop:e.target.value})} placeholder={t('primary crop')}/></div>
        </div>

        <div ref={langRef} style={{position:'relative', marginTop:16}}>
          <button className={`lang-pill ${langOpen?'open':''}`} onClick={(e)=>{e.stopPropagation();setLangOpen(!langOpen)}}>
            <span style={{color:'var(--ink-faint)',letterSpacing:'0.08em'}}>{lang}</span>
            <span>{langObj.label}</span>
          </button>
          {langOpen && (
            <div className="lang-menu">
              {LANGS.map(l=>(
                <button key={l.code} className={l.code===lang?'active':''}
                  onClick={()=>{setLang(l.code);setLangOpen(false)}}>
                  <span className="mono" style={{fontSize:10,marginRight:8,color:'var(--ink-faint)'}}>{l.code}</span>{l.label}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="sb-actions">
          <button className="sb-action" onClick={onLogout}>{t('sign out')} →</button>
        </div>
      </div>
    </aside>
  );
}
```

- [ ] **Step 5.2: Slim `TabBar`** (mobile-only now; same API):

```jsx
function TabBar({ active, setActive, t }){
  const tabs = [
    { k:'crop', label:t('crop') }, { k:'disease', label:t('leaf') },
    { k:'market', label:t('market') }, { k:'irrigation', label:t('water') },
    { k:'acoustic', label:t('listen') }, { k:'field', label:t('field') },
  ];
  return (
    <div className="tabbar-wrap">
      <div className="tabbar" role="tablist">
        {tabs.map(tab=>(
          <button key={tab.k} role="tab" aria-selected={active===tab.k}
            className={`tab-pill ${active===tab.k?'active':''}`}
            onClick={()=>setActive(tab.k)}>
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5.3: Topbar** — keep structure, change the crumb text to lowercase mono (CSS already does it) and the live dot markup:

```jsx
function Topbar({ crumb }){
  const [t, setT] = useState(()=>new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}));
  useEffect(()=>{ const id=setInterval(()=>setT(new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})),30000); return ()=>clearInterval(id); },[]);
  return (
    <div className="topbar">
      <div className="crumb">kisan os · {crumb}</div>
      <div className="live"><span className="dot" style={{width:6,height:6,background:'var(--signal)'}}></span> live · {t}</div>
    </div>
  );
}
```

- [ ] **Step 5.4: Verify** — rail shows numbered lowercase nav, tab switching works from the rail, language menu opens/closes, mobile shows bottom bar. Sidebar collapse FAB still toggles.
- [ ] **Step 5.5: Commit** — `git commit -am "feat(redesign): rail sidebar with numbered nav, mobile tabbar, mono topbar"`

---

### Task 6: Login rewrite

**Files:**
- Modify: `web/components/Login.jsx` (JSX return only, lines 94-212 — all state/handlers stay identical)

- [ ] **Step 6.1: Replace the `return` block** of `Login`:

```jsx
  return (
    <div className="auth-screen">
      <form className="auth-card" onSubmit={step === 'phone' ? submitPhone : submitOtp} noValidate>
        <div className="auth-sub">{tr('field instrument · sign in')}</div>
        <h1 className="auth-wordmark">kisan os<span className="dot" aria-hidden="true" /></h1>
        <p style={{ color: 'var(--ink-soft)', fontSize: 14, margin: '0 0 36px', maxWidth: '42ch' }}>
          {step === 'phone'
            ? tr('Your phone number is your KisanOS identity.')
            : tr('Enter the code we sent to your phone.')}
        </p>

        {step === 'phone' ? (
          <div className="auth-field">
            <label htmlFor="auth-id">{tr('mobile number')}</label>
            <input id="auth-id" className="auth-input" type="tel" inputMode="tel"
                   autoComplete="tel" placeholder="+91 ·····  ·····"
                   value={phone} onChange={(e) => setPhone(e.target.value)} />
          </div>
        ) : (
          <>
            <div className="auth-field">
              <label htmlFor="auth-id">{tr('mobile number')}</label>
              <input id="auth-id" className="auth-input" type="tel" value={normalisedPhone} readOnly />
            </div>
            {demoOtp && (
              <div className="demo-chip" role="status">
                <span style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-faint)' }}>
                  {tr('demo mode · your code')}
                </span>
                <button type="button" className="code" onClick={() => setOtp(demoOtp)} title={tr('tap to fill')}>
                  {demoOtp}
                </button>
              </div>
            )}
            <div className="auth-field">
              <label htmlFor="auth-otp">{tr('verification code')}</label>
              <input id="auth-otp" className="auth-input" type="text" inputMode="numeric"
                     autoComplete="one-time-code" pattern="\d*" maxLength={8}
                     placeholder="······" value={otp} onChange={(e) => setOtp(e.target.value)} />
            </div>
          </>
        )}

        {error && <div className="auth-error" role="alert">{error}</div>}
        {!error && info && <div className="auth-info" role="status">{info}</div>}

        <button type="submit" className="auth-submit" disabled={busy}>
          {busy
            ? (step === 'phone' ? tr('sending…') : tr('verifying…'))
            : (step === 'phone' ? tr('send code →') : tr('sign in →'))}
        </button>

        {step === 'otp' && (
          <div className="auth-row">
            <a className="auth-link" href="#" onClick={(e) => { e.preventDefault(); backToPhone(); }}>{tr('change number')}</a>
            <a className="auth-link" href="#" onClick={(e) => { e.preventDefault(); resend(); }}>{tr('resend code')}</a>
          </div>
        )}
      </form>

      <Ticker items={[
        ['mandi · wheat', '₹2,140/q'], ['soil ph', '6.5'], ['bees', '87%'],
        ['rain 48h', '12 mm'], ['fire risk', 'low'], ['et₀ today', '4.2 mm'],
      ]} />
    </div>
  );
```

(The old `auth-divider`/`auth-foot` block is removed; the ticker replaces it as the proof-of-life moment.)

- [ ] **Step 6.2: Verify** — logged-out screen shows giant wordmark, underlined input, scrolling carbon ticker; full OTP flow works with DEMO_PHONE (code chip fills on tap); errors render in alarm color.
- [ ] **Step 6.3: Commit** — `git commit -am "feat(redesign): instrument login — wordmark, underlined fields, live ticker"`

---

### Task 7: Boot sequence + retimed tab choreography in app.jsx

**Files:**
- Modify: `web/components/app.jsx:102-112` (switchTab timing), `122-129` (handleSignIn), add boot effect near line 60

- [ ] **Step 7.1:** Add the boot flag effect after the `document.body.dataset.tab` effect (line 60):

```jsx
  // Boot choreography: brief data-boot attr after sign-in drives staggered CSS reveals.
  useEffect(() => {
    if (!authed) return;
    document.body.dataset.boot = '1';
    const id = setTimeout(() => { delete document.body.dataset.boot; }, 1200);
    return () => { clearTimeout(id); delete document.body.dataset.boot; };
  }, [authed]);
```

- [ ] **Step 7.2:** Retime `switchTab` (165→160, 340→420ms to match the new CSS):

```jsx
  function switchTab(next) {
    if (next === displayTab) return;
    if (phase !== 'idle') return;
    setPhase('leaving');
    setTimeout(() => {
      setDisplayTab(next);
      setPhase('entering');
      setTimeout(() => setPhase('idle'), 420);
    }, 160);
    setActive(next);
  }
```

- [ ] **Step 7.3: Verify** — sign out, sign in: rail items cascade in, content rises last. Tab switches feel like exit→enter choreography. With macOS "Reduce Motion" on, everything is instant.
- [ ] **Step 7.4: Commit** — `git commit -am "feat(redesign): boot sequence + retimed tab choreography"`

---

### Task 8: ViewCrop — flagship instrument sheet

**Files:**
- Modify: `web/components/views/ViewCrop.jsx` (all JSX; hook usage unchanged)

Target structure: head question → `01 · field inputs` two-column form (open paper, no boxes) → run row → instrument with DotMatrix confidence + crop readout + alternatives + prob hairline bars; soil report as paper section below.

- [ ] **Step 8.1: Replace head + form sections** (lines 33-74):

```jsx
  return (
    <div className="view-fade">
      <Topbar crumb={t('crop advisor')} />
      <div className="page-head">
        <div className="page-eyebrow">01 · {t('crop advisor')}</div>
        <h1 className="page-title">{t('which crop should i sow?')}</h1>
        <p className="page-lede">{t('We compare 26 crops against your soil and weather, and surface the one your land will support best.')}</p>
      </div>

      <LocationBar
        t={t}
        village={profile.village} setVillage={v => setProfile({ ...profile, village: v })}
        state={profile.state} setState={s => setProfile({ ...profile, state: s })}
        extra={<span className="tag">{t('kharif season')}</span>}
      />

      <div className="grid-2">
        <div className="rise rise-1">
          <div className="sec-h"><span>01</span>{t('soil')}</div>
          <Slider label={t('Nitrogen')} unit="kg/ha" min={0} max={140} value={N} onChange={setN}
            hint={N < 40 ? t('a little hungry') : N < 90 ? t('just right') : t('plenty')} />
          <Slider label={t('Phosphorus')} unit="kg/ha" min={5} max={145} value={P} onChange={setP} />
          <Slider label={t('Potassium')} unit="kg/ha" min={5} max={205} value={K} onChange={setK} />
          <Slider label={t('Soil pH')} unit="" min={3.5} max={9.5} step={0.1} value={ph} onChange={setPh}
            hint={ph < 5.5 ? t('acidic') : ph < 7.5 ? t('sweet spot') : t('a touch alkaline')} />
          <Slider label={t('Area')} unit="acres" min={0.5} max={50} step={0.5} value={areaAcres} onChange={setAreaAcres} />
        </div>
        <div className="rise rise-2">
          <div className="sec-h"><span>02</span>{t('weather')}{wxLoading ? ' · '+t('fetching live…') : ''}</div>
          {wxNote && <div className="mono" style={{ fontSize: 11, color: 'var(--ink-faint)', marginBottom: 10 }}>{wxNote}</div>}
          <Slider label={t('Temperature')} unit="°C" min={8} max={45} step={0.5} value={temperature} onChange={setTemp} />
          <Slider label={t('Humidity')} unit="%" min={14} max={100} value={humidity} onChange={setHum} />
          <Slider label={t('Rainfall')} unit="mm" min={20} max={300} step={5} value={rainfall} onChange={setRain} />
          <div style={{ display: 'flex', gap: 10, marginTop: 22 }}>
            <button className="btn primary" onClick={handleSubmit} disabled={loading}>
              {loading ? t('analysing…') : t('run analysis →')}
            </button>
            <button className="btn ghost" onClick={handleReset}>{t('reset')}</button>
          </div>
        </div>
      </div>
```

- [ ] **Step 8.2: Replace the result block** (old Donut card, lines 89-121) with the instrument:

```jsx
      {loading && <Loading label={t('analysing soil and climate…')} />}

      {error && !loading && (
        <ErrorCard t={t}
          title={error.status === 401 || error.status === 403
            ? t('API key misconfigured. Open web/config.js and verify the dev key.')
            : t('could not analyse soil')}
          detail={!error.status && error.message ? t('No connection — check your network and try again.') : error.detail}
          onRetry={handleSubmit} />
      )}

      {result && !loading && (
        <div className="instrument ignite" style={{ marginTop: 28 }}>
          <div className="inst-label"><span>{t('recommendation')}</span><span>{t('confidence')}</span></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 28, flexWrap: 'wrap' }}>
            <div style={{ fontFamily: 'var(--display)', fontWeight: 600, textTransform: 'lowercase', fontSize: 'clamp(40px, 5vw, 72px)', lineHeight: 1, letterSpacing: '-0.03em', color: 'var(--ink)' }}>
              {result.top_crop.crop}
            </div>
            <div style={{ textAlign: 'right' }}>
              <DotMatrix value={`${Number(result.top_crop.confidence).toFixed(1)}%`} height={52} />
            </div>
          </div>
          {result.tip && <p style={{ color: 'var(--ink-soft)', maxWidth: '60ch', marginTop: 18, fontSize: 14 }}>{result.tip}</p>}
          {result.soil && (
            <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px solid var(--line)' }}>
              <div className="inst-label"><span>{t('soil')} · {result.soil.soil_type}</span></div>
              <div style={{ fontSize: 14 }}>{result.soil.advice}</div>
            </div>
          )}
          <div style={{ marginTop: 18, paddingTop: 14, borderTop: '1px solid var(--line)' }}>
            <div className="inst-label"><span>{t('also viable')}</span></div>
            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
              {result.alternatives.slice(0, 3).map(c => (
                <div key={c.crop} style={{ display: 'flex', gap: 8, alignItems: 'baseline' }}>
                  <span style={{ textTransform: 'lowercase', fontFamily: 'var(--display)', fontWeight: 500 }}>{c.crop}</span>
                  <span className="mono" style={{ color: 'var(--ink-faint)', fontSize: 12 }}>{Number(c.confidence).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
          {result.all_probabilities && <ProbBars probs={result.all_probabilities} t={t} />}
        </div>
      )}
```

- [ ] **Step 8.3: Restyle `ProbBars`** (lines 4-21) to hairline bars (it now renders inside the instrument, so tokens flip automatically):

```jsx
function ProbBars({ probs, t }) {
  const sorted = Object.entries(probs).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const max = sorted[0]?.[1] || 1;
  return (
    <div style={{ marginTop: 20, paddingTop: 14, borderTop: '1px solid var(--line)' }}>
      <div className="inst-label"><span>{t('all crops')}</span></div>
      {sorted.map(([crop, prob]) => (
        <div key={crop} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 7 }}>
          <div className="mono" style={{ width: 96, fontSize: 11, color: 'var(--ink-soft)', textAlign: 'right', textTransform: 'lowercase' }}>{crop}</div>
          <div className="hbar" style={{ flex: 1 }}><i style={{ width: `${(prob / max) * 100}%` }} /></div>
          <div className="mono" style={{ width: 44, fontSize: 11, color: 'var(--ink-faint)' }}>{Number(prob).toFixed(2)}%</div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 8.4: Soil deficiencies section** (lines 123-163): keep structure but swap container classes — outer div `className="rise"` with a `sec-h` (`<div className="sec-h"><span>03</span>{t('soil report')} · {soilResult.soil_type}</div>`), severity pill colors → `var(--alarm)` / `var(--caution)` / `var(--signal)` with their `-dim` backgrounds, healthy state becomes `<div className="rise" style={{borderTop:'1px solid var(--signal)', paddingTop:14}}>` with a signal check line. Remove all `rgba(...)` literals.

- [ ] **Step 8.5: Verify** — run an analysis on the crop tab: instrument ignites, DotMatrix counts the confidence in, prob bars draw. Empty/error/loading all styled. Hindi (`hi`) renders the headline in Noto Sans Devanagari.
- [ ] **Step 8.6: Commit** — `git commit -am "feat(redesign): crop tab instrument sheet with dot-matrix confidence"`

---

### Task 9: ViewMarket — price trace instrument

**Files:**
- Modify: `web/components/views/ViewMarket.jsx`

- [ ] **Step 9.1: Head** — same pattern as Task 8: eyebrow `03 · {t('market')}`, title `{t('when should i sell?')}`, lede `{t('Live mandi prices plus a Prophet forecast, condensed into one clear sell signal.')}`. Run button text → `{t('get forecast →')}`.

- [ ] **Step 9.2: ForecastChart** (lines 5-55) — carbon-ready with draw-on animation; replace the SVG internals:

```jsx
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 200, display: 'block' }}>
      {gridYs.map((gy, i) => (
        <line key={i} x1={pad} y1={gy} x2={W - pad} y2={gy} stroke="var(--line)" strokeWidth="1" />
      ))}
      <path d={bandPath} fill="var(--signal-bright)" opacity="0.10" />
      <path d={mainLine} fill="none" stroke="var(--signal-bright)" strokeWidth="2" strokeLinecap="round"
        pathLength="1" strokeDasharray="1" strokeDashoffset="1"
        style={{ animation: 'drawline 1.1s var(--ease) .15s forwards' }} />
      {dateLabels.map(({ i, date }) => (
        <text key={i} x={xp(i)} y={H - 4} textAnchor="middle"
          style={{ fontSize: 9, fill: 'var(--ink-faint)', fontFamily: 'var(--mono)' }}>
          {(date ?? '').slice(5)}
        </text>
      ))}
    </svg>
  );
```

Add to the Task 2 stylesheet if missed: `@keyframes drawline{ to{ stroke-dashoffset:0 } }` (place near the other keyframes).

- [ ] **Step 9.3: Result blocks** (lines 155-229) — restructure to: one `.instrument ignite` containing the live price as `DotMatrix value={'₹' + (result.live_price?.today_price?.toFixed(0) ?? '—') }`, LIVE/ESTIMATED as `.tag` (signal/caution border), then the ForecastChart, then below the instrument a paper `.stat-row` with best/worst/average (mono `.s-label` + `.bignum` at 28px), the advice as a `sec-h`-headed paragraph (no amber box: `<div className="sec-h"><span>★</span>{t('our advice')}</div><p style={{maxWidth:'60ch'}}>{result.sell_advice}</p>`), and the `details` table with: header row `borderBottom:'1px solid var(--hairline-strong)'`, all cells `fontFamily:'var(--mono)', fontSize:12`, zebra backgrounds removed, row borders `1px solid var(--hairline)`.

- [ ] **Step 9.4: Verify** — forecast run: trace draws inside carbon, price ticks in dot-matrix, stat row is hairline-separated, table reads as a mono ledger.
- [ ] **Step 9.5: Commit** — `git commit -am "feat(redesign): market tab — drawing price trace instrument + mono ledger"`

---

### Task 10: ViewAcoustic — spectrogram instrument

**Files:**
- Modify: `web/components/views/ViewAcoustic.jsx`, `web/components/views/hooks/useAcousticDisplayHelpers.js`

- [ ] **Step 10.1: Head** — eyebrow `05 · {t('listen')}`, title `{t("what's singing in the field?")}`, lede unchanged in meaning, button `{loading ? t('listening…') : t('analyse →')}`. Upload column gets `<div className="sec-h"><span>01</span>{t('recording')}</div>`; drop-zone emoji (🎵/🎙) → mono glyphs `{file ? '▮▯▮' : 'rec'}` styled `fontFamily:'var(--mono)', fontSize:22, letterSpacing:'0.2em', color:'var(--ink-faint)'`; drag styles → `borderColor: drag ? 'var(--signal)' : undefined, background: drag ? 'var(--signal-dim)' : undefined`. Warning/error boxes → `border:'1px solid var(--caution)'` / `.error-panel` styles, no fills.

- [ ] **Step 10.2: Result column becomes the instrument.** Replace the right card (lines 95-123):

```jsx
        <div className="instrument inst-sticky rise rise-2">
          <div className="inst-label">
            <span>{t('what we heard')}</span>
            {result && <span style={{ color: result.severity === 'high' ? 'var(--alarm)' : 'var(--ink-faint)' }}>{result.severity}</span>}
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2, height: 110, padding: '8px 0 14px', borderBottom: '1px solid var(--line)' }}>
            {bars.map((b, i) => (
              <div key={i} style={{
                flex: 1, height: `${Math.max(6, b * 100)}%`,
                background: 'var(--signal-bright)',
                opacity: loading ? 0.95 : result ? 0.55 : 0.18,
                transition: 'height .12s ease',
              }} />
            ))}
          </div>
          {loading && <Loading label={t('listening…')} />}
          {error && !loading && <ErrorCard t={t} title={t('analysis failed')} detail={error.message} onRetry={analyze} />}
          {!result && !loading && !error && (
            <div className="state-empty"><span className="ghost">??</span>{t('drop a recording to begin')}</div>
          )}
          {result && !loading && <AcousticRichResult r={result} t={t} />}
        </div>
```

- [ ] **Step 10.3: Display helpers** (`useAcousticDisplayHelpers.js`): `roleColor` → pest:`var(--alarm)`, pollinator:`var(--signal)`, vector:`var(--caution)`, else `var(--ink-faint)`. `AcousticMethodBadge` → outline tag (border in color, transparent bg, color text, no white-on-fill). In `AcousticTopBars`/`AcousticBandChart`: every `rgba(255,255,255,0.10)` → `var(--line)`, bar fills `var(--signal-bright)` → these render inside the instrument now. In the RichResult (rest of file): species name becomes the hero — wrap in `<DotMatrix value={Math.round(confidencePct) + '%'} height={40}/>` next to a lowercase display-font species name; keep PEST_META role labels as mono text, drop emoji icons.

- [ ] **Step 10.4: Verify** — upload a clip (tests/fixtures or any wav): bars pulse while loading, result shows species + dot-matrix confidence + hairline band chart, severity colors correct.
- [ ] **Step 10.5: Commit** — `git commit -am "feat(redesign): acoustic tab — carbon spectrogram instrument + species readout"`

---

### Task 11: ViewIrrigation — gauge instrument

**Files:**
- Modify: `web/components/views/ViewIrrigation.jsx`

- [ ] **Step 11.1: Head** — eyebrow `04 · {t('water')}`, title `{t('how much water today?')}`, button `{t('calculate →')}`. Form column: `sec-h` `01 · {t('your field')}`; growth-stage tiles keep `.tile`/`.tile.active` (already restyled); remove the inline `background:'var(--leaf-soft)'` override on active (the class handles it).

- [ ] **Step 11.2: Results** (lines 168-220) → single instrument + paper rows:

```jsx
      {result && (
        <div className="instrument ignite" style={{ marginTop: 28 }}>
          <div className="inst-label"><span>{t('water needed today')}</span><span>{result.crop} · {stage}</span></div>
          <DotMatrix value={result.total_litres.toLocaleString('en-IN')} height={58} />
          <div className="mono" style={{ marginTop: 8, fontSize: 12, color: 'var(--ink-faint)' }}>
            {t('litres')} · {result.total_kl} kL · {fieldArea} {t('acres')}
          </div>
          <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid var(--line)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 32px' }}>
            <LinearGauge label={t('net irrigation')} value={result.net_irrigation_mm} max={20} unit={t('mm/day')} />
            <LinearGauge label={t('crop kc factor')} value={result.Kc} max={1.4} unit="" />
          </div>
          <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px solid var(--line)' }}>
            <div className="inst-label">
              <span>{t('urgency')} · {result.urgency}</span>
            </div>
            <div style={{ fontSize: 14, lineHeight: 1.6, color: result.urgency === 'urgent' ? 'var(--alarm)' : 'var(--ink)' }}>{result.advice}</div>
          </div>
        </div>
      )}

      {result && (
        <div className="rise" style={{ marginTop: 8 }}>
          <div className="sec-h"><span>02</span>{t('fertilizer')} · {result.fertilizer.growth_stage}</div>
          <div style={{ fontSize: 14 }}><strong>{t('Nitrogen:')}</strong> {result.fertilizer.nitrogen}</div>
          <div style={{ fontSize: 13, color: 'var(--ink-soft)', marginTop: 4 }}>{result.fertilizer.tip}</div>
        </div>
      )}
```

- [ ] **Step 11.3: Calamity tips** (lines 223-236) → paper section, caution accent without fills: `sec-h` (`<span>!</span>{t('weather tips')} · {calamityKey}`), `<ul>` unchanged but strip the emoji prefixes from `CALAMITY_TIPS` strings in `atoms.jsx:81-90` (e.g. `'⚡ Move livestock to shelter'` → `'Move livestock to shelter'` — 24 strings; note these strings are also i18n keys, so update the `en` bundle keys in Task 14 to match).
- [ ] **Step 11.4: Verify** — set a city (autofill fires), calculate: litres tick in dot-matrix, gauges fill, urgency reads correctly in urgent (alarm) vs normal.
- [ ] **Step 11.5: Commit** — `git commit -am "feat(redesign): irrigation tab — water gauge instrument, donut retired"`

---

### Task 12: ViewDisease — scan instrument

**Files:**
- Modify: `web/components/views/ViewDisease.jsx`

- [ ] **Step 12.1: Head** — eyebrow `02 · {t('leaf doctor')}`, title `{t("what's wrong with this leaf?")}`. `SevTag` (lines 4-13): colors → High `var(--alarm)`, Medium `var(--caution)`, else `var(--signal)`; replace the hex-alpha tricks with `style={{ color, borderColor: color }}` on `.tag`.
- [ ] **Step 12.2: PhotoPanel** — left column open paper with `sec-h` `01 · {t('photo')}`; drop zone: 🍃 → `img` mono glyph (same style as Task 10); drag colors → signal as in Task 10. Right column becomes `.instrument inst-sticky` with `inst-label` `{t('diagnosis')}`; empty state `<div className="state-empty"><span className="ghost">·_·</span>{t('send a photo to begin')}</div>`.
- [ ] **Step 12.3: PhotoResult** (lines 34-81) — inside the instrument: disease name in lowercase display font 32px; `right now` / `treatment` / `prevention` boxes → stacked hairline sections (`borderTop:'1px solid var(--line)', paddingTop:14, marginTop:14`) each headed by an `inst-label` (action label in `var(--caution)` when urgent); cost estimate keeps its numbers in `.mono`; `Top3Bars` → same hairline-bar treatment as ProbBars (Task 8.3 pattern, `var(--line)` track + `var(--signal-bright)` fill).
- [ ] **Step 12.4: Verify** — upload a leaf photo; diagnosis renders inside carbon with severity tag, treatment sections hairline-stacked, top-3 bars draw.
- [ ] **Step 12.5: Commit** — `git commit -am "feat(redesign): disease tab — diagnosis instrument"`

---

### Task 13: ViewField — risk instrument + ledger sections

**Files:**
- Modify: `web/components/views/ViewField.jsx`

- [ ] **Step 13.1: Head** — eyebrow `06 · {t('field watch')}`, title `{t('is my field safe today?')}`, scan button `{t('scan now →')}`.
- [ ] **Step 13.2: riskStyle + AlertCard** (lines 6-24) — replace with hairline list (kills the identical-card grid):

```jsx
function riskColor(risk) {
  if (risk === 'HIGH')   return 'var(--alarm)';
  if (risk === 'MEDIUM') return 'var(--caution)';
  return 'var(--signal)';
}

function AlertRow({ title, risk, children }) {
  const c = riskColor(risk);
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 16, padding: '13px 0', borderTop: '1px solid var(--hairline)' }}>
      <span style={{ width: 8, height: 8, background: c, flex: 'none', alignSelf: 'center' }} aria-hidden="true" />
      <span style={{ fontFamily: 'var(--display)', fontWeight: 500, fontSize: 15, textTransform: 'lowercase', minWidth: 110 }}>{title}</span>
      <span style={{ flex: 1, color: 'var(--ink-soft)', fontSize: 13 }}>{children}</span>
      <span className="mono" style={{ fontSize: 10, letterSpacing: '0.1em', color: c }}>{risk}</span>
    </div>
  );
}
```

- [ ] **Step 13.3: Result layout** — overall risk becomes the instrument: `.instrument ignite` with `inst-label` `{t('overall risk')} · {result.city}`, a `DotMatrix value={result.overall_risk} …` — DotMatrix is digits-only, so instead render the risk word in display font 56px lowercase colored `riskColor(result.overall_risk)`, with the four weather numbers as a mono grid inside the instrument (temp/humidity/wind/rain, each `.s-label` + 24px `.mono` value). The old `grid-4` weather cards are removed. Alert section: `sec-h` `01 · {t('alerts')}` + `AlertRow`s (flood/fire/locust/aqi with their existing fields; AQI value inline mono). Helplines: `sec-h` `02 · {t('emergency helplines')}`, table rows → `borderTop:'1px solid var(--hairline)'`, no zebra, numbers `.mono` linked in `var(--signal)`. WhatsApp: `sec-h` `03 · {t('send to whatsapp')}`, textarea `.input` mono full-width, buttons `{t('copy')}` / `{t('open whatsapp →')}` (emoji dropped).
- [ ] **Step 13.4: Verify** — scan a city: risk word ignites in correct color, alert rows hairline-stacked with status dots, helplines ledger, copy button toasts.
- [ ] **Step 13.5: Commit** — `git commit -am "feat(redesign): field watch — risk instrument + hairline alert ledger"`

---

### Task 14: i18n keys + copy sweep

**Files:**
- Modify: `web/lib/bundles.json` (en section), possibly run `scripts/translate_new_keys.py`

- [ ] **Step 14.1:** Collect every new `t('…')` key introduced in Tasks 5-13 (grep the diff: `git diff main -- web/components | grep -o "t('[^']*')" | sort -u`). Add each to the `en` bundle as identity entries (`"which crop should i sow?": "which crop should i sow?"` or proper-cased text where the key is a slug). `makeT` falls back en → key, so missing translations harmlessly render English.
- [ ] **Step 14.2:** Update the 24 `CALAMITY_TIPS` strings in the `en` bundle to their emoji-less forms (Task 11.3) so existing translations re-key. If `python scripts/translate_new_keys.py` runs without missing credentials, run it to fill the 9 languages; otherwise leave English fallback and note it in the commit message.
- [ ] **Step 14.3: Verify** — switch to hi and ta: headlines render in Noto Sans scripts, no raw key leakage worse than English text.
- [ ] **Step 14.4: Commit** — `git commit -am "feat(redesign): i18n keys for instrument copy"`

---

### Task 15: A11y, reduced-motion, mobile, contrast audit

- [ ] **Step 15.1:** Keyboard pass: rail nav, language menu, forms, drop zones (Enter triggers file dialog via click handler — add `onKeyDown={e => e.key === 'Enter' && inputRef.current?.click()} tabIndex={0} role="button"` to both drop zones if missing).
- [ ] **Step 15.2:** Contrast: spot-check `--ink-faint` on `--paper` (target ≥ 4.5:1 for body-size text; bump the mix percentage if below), `--signal` on paper, `--signal-bright` on carbon, `--caution` on paper. Adjust token lightness, not per-use overrides.
- [ ] **Step 15.3:** Reduced motion: with emulation on, confirm no ticker scroll, no dot-matrix stagger, instant tab switches.
- [ ] **Step 15.4:** 390px viewport: every tab usable, bottom tabbar reachable, instruments full-width, no horizontal scroll.
- [ ] **Step 15.5: Commit** — `git commit -am "fix(redesign): a11y/contrast/mobile audit fixes"`

---

### Task 16: Build + tests + full verification matrix

- [ ] **Step 16.1:** `pytest tests/ -q` — expect green (security headers, serve, API suites unaffected).
- [ ] **Step 16.2:** Prod build: `python scripts/build_frontend.py` (JSX precompile + vendor pins). Serve the built output the way `docs/csp-deploy-handoff-2026-06-08.md` describes and confirm the SPA boots with strict CSP (no console CSP violations — canvas, fonts, and CSS animations are all `self`-safe).
- [ ] **Step 16.3:** Browser matrix on :8000 — for each of the 7 screens (login + 6 tabs): default, loading, result, error (kill network for one), empty. Screenshot each for the record.
- [ ] **Step 16.4:** The AI-slop test from `/DESIGN.md`: no glass, no photos, no gradient text, no side-stripes, no identical card grids, no emoji chrome, accent ≤10% per screen. Fix anything that fails before declaring done.
- [ ] **Step 16.5:** Final commit + handoff per superpowers:finishing-a-development-branch (merge vs PR decision is the user's).

---

## Self-Review Notes

- Spec coverage: theme/tokens (T1), shell+motion (T2, T5, T7), photo/glass removal (T3), primitives (T4), login+ticker (T6), six tabs (T8-T13), copy/i18n (T14), a11y/reduced-motion (T15), CSP/build/verification (T16). Boot sequence T7; dot-matrix T4+T8/10/11; trace draw T9.
- Donut: retired from use in T8/T11; component kept window-exported for compat (only ViewCrop used it — verified by read).
- Type consistency: `DotMatrix({value,height,color,align})`, `LinearGauge({value,max,label,unit})`, `Ticker({items})` used exactly with those props in T6, T8, T10, T11. Class names introduced in T2 (`sec-h`, `instrument`, `inst-label`, `inst-sticky`, `stat-row`, `s-label`, `hbar`, `state-loading`, `state-empty`, `error-panel`, `ghost`, `rail-*`, `ticker*`, `demo-chip`, `auth-wordmark`) are the ones consumed in T5-T13.
- Known mid-migration states are explicitly tolerated and cleaned by later tasks (legacy aliases strategy).
