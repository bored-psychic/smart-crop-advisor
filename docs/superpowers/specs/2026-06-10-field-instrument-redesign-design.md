# Field Instrument — Frontend Redesign Design Spec

**Date:** 2026-06-10
**Status:** Approved by user (interview + visual probes + theme board, this session)
**Companion docs:** `/PRODUCT.md` (strategy), `/DESIGN.md` (visual system)

## 1. Feature Summary

Full redesign of the KisanOS SPA — login, app shell, and all six tabs — replacing the photo-background + glassmorphism + serif look with "Field Instrument": a paper-white engineered-monochrome shell holding dark carbon instrument panels, one engineered-green accent, and rich but disciplined motion. Audience is demo-first (judges/recruiters on the public HF Space) while staying defensible as a real farmer tool.

## 2. Problem

User verdict on the current UI: feels AI-generic, weak hierarchy, lacks craft, "looks built by a kid with html commands." Wall-to-wall glass cards over stock photos is the signature AI-slop pattern. Anchor references supplied by user: **in.nothing.tech** and **sohub.digital** — both stark monochrome, oversized lowercase type, grid discipline, motion as choreography.

## 3. Primary User Action

Per tab: feed inputs, fire an analysis, read one unmistakable answer off an instrument. The demo viewer should read "real product company" within seconds.

## 4. Design Direction (locked with user)

- Theme: **light paper shell + dark instrument insets** (chosen over full-dark and full-light).
- Accent: **engineered green** (chosen over Nothing-red and amber), ≤10% of any screen; severity red/amber stay semantic-only.
- Color strategy: **Restrained** (tinted monochrome + one accent).
- Scene sentence: a judge opens the HF Space on a laptop in a bright room and must be impressed in ten seconds.
- Scope: **full sweep** — login + shell + all 6 tabs + shared atoms in one pass, production quality.
- Three AI-image direction probes + a theme board were generated and approved (crop sheet, login, acoustic instrument, theme board).

## 5. Layout Strategy

Each tab is an *instrument sheet*: oversized lowercase headline phrased as the field question, numbered mono-microcap sections (`01 · field inputs`), hairline-separated form column, and the tab's output inside a dark carbon instrument panel (sticky beside the form on desktop, stacked on mobile). Sidebar becomes a slim ink-on-paper rail carrying the nav; the pill TabBar becomes mobile-only. No uniform card grids, no nested containers.

Per-tab instruments:
- crop: recommendation readout igniting + DotMatrix confidence + ranked probability hairline bars
- disease: scan-sweep over the uploaded leaf photo, result readout with severity
- market: glowing price trace drawing on inside carbon, hairline stat row, mono table
- irrigation: water-need DotMatrix + linear gauges (donut deleted)
- acoustic: spectrogram-style level bars in carbon + species readout with role/severity
- field: overall-risk readout + hairline alert list + helplines/whatsapp restyled

## 6. Key States

Loading = scanline sweep + mono "analysing…"; empty = ghost numeral + one-line prompt; error = alarm hairline panel keeping existing friendly 422 copy; success = staggered instrument ignition. All states designed.

## 7. Interaction Model / Motion Inventory

Boot sequence (login → app): rules draw, labels rise, instruments ignite (~900ms). Choreographed tab transitions (existing phase machine, retimed). DotMatrix count-ups, SVG trace draw-on, magnetic-lite hover on primary buttons (desktop). Everything transform/opacity-only, expo-out easing, fully disabled under `prefers-reduced-motion`.

## 8. Content Requirements

Lowercase UI voice ("run analysis →"). New per-tab headline questions (which crop should i sow? / what's wrong with this leaf? / when should i sell? / how much water today? / what's singing in the field? / is my field safe today?). i18n: new keys added to the `en` bundle; `makeT` falls back en → key so untranslated languages degrade to English copy, with `scripts/translate_new_keys.py` available for follow-up translation. Emoji removed from UI chrome (kept only where data-semantic, e.g. severity dots become CSS).

## 9. Constraints

- Prod CSP: `script-src 'self'` — no CDN scripts; motion is CSS/WAAPI/canvas only (no new vendored libs needed). `style-src` allows inline; fonts only Google Fonts; images self+data.
- Classic-script React (no bundler); dev = in-browser Babel, prod = `scripts/build_frontend.py` precompile. File-scope `const` collisions forbidden (use `var` or unique names at top level).
- 9 Indic scripts must stay first-class (Noto Sans per-script display swaps).
- `kisanos.token` auth flow, hooks, and API wiring must not change behavior.

## 10. Out of Scope / Anti-goals

No backend changes; no new marketing/landing page; no Tailwind/bundler migration; no dark-mode toggle (theme is fixed); don't break the tweaks-panel script load.

## 11. Open Questions

None blocking. Bee/pollinator severity colors stay semantic (signal=good, alarm=pest-high).
