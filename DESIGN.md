# Design

## Theme: Field Instrument

A paper-white editorial shell holding dark carbon instrument panels. Precision-hardware aesthetic (anchors: Nothing, SOHub): Swiss grid, visible hairline rules, oversized lowercase display type, monospace data, one engineered green. The app reads as a calm lab sheet; each tab's answer ignites inside a dark instrument.

## Color (OKLCH; never #000/#fff)

| Token | Value | Use |
|---|---|---|
| `--paper` | `oklch(97.5% 0.006 120)` | App background |
| `--paper-2` | `oklch(94.8% 0.008 120)` | Recessed wells, hover rows on paper |
| `--ink` | `oklch(21% 0.012 140)` | Primary text and rules on paper |
| `--ink-soft` | `color-mix(in oklab, var(--ink) 72%, transparent)` | Secondary text |
| `--ink-faint` | `color-mix(in oklab, var(--ink) 46%, transparent)` | Tertiary text, axis labels |
| `--carbon` | `oklch(17% 0.012 150)` | Instrument panel background |
| `--carbon-2` | `oklch(22% 0.014 150)` | Elevated areas inside instruments |
| `--signal` | `oklch(56% 0.155 150)` | Accent on paper (AA on `--paper`) |
| `--signal-bright` | `oklch(82% 0.21 150)` | Accent on carbon (traces, dot-matrix) |
| `--alarm` | `oklch(55% 0.19 30)` | Severity/error only, semantic, never decorative |
| `--caution` | `oklch(58% 0.125 80)` | Medium severity only |
| `--hairline` | ink @ 12% | Rules on paper |
| `--hairline-strong` | ink @ 26% | Emphasized rules, input underlines |

Inside `.instrument`, the ink scale re-declares to paper-on-carbon values so nested content inherits correct polarity.

Color strategy: Restrained. `--signal` covers at most 10% of any screen. The only second hue is `--alarm`/`--caution` for genuine severity.

## Typography

- Display: `Space Grotesk`, lowercase voice, tracking `-0.02em`. Per-language swaps: Noto Sans Devanagari / Tamil / Telugu / Bengali / Kannada / Malayalam / Gujarati / Gurmukhi (replacing the old Noto Serif set).
- Body/UI: `Inter`.
- Data and microcaps: `JetBrains Mono`, `font-variant-numeric: tabular-nums`. Microcaps style: 11px, `letter-spacing: 0.08em`, uppercase, `--ink-faint`.
- Scale (ratio ≥ 1.3): 12 / 14 / 15 / 19 / 25 / 33 / 44, hero `clamp(38px, 5.2vw, 76px)`.

## Components

- **Instrument panel** (`.instrument`): carbon, 20px radius, 1px inner hairline, holds the tab's answer. Powers on with a 420ms opacity/rise; content staggers in after.
- **Dot-matrix numeral** (`DotMatrix`): canvas 5×7 dot font for hero metrics (confidence %, prices, litres). Dots ignite with stagger; instant under reduced motion.
- **Linear gauge** (`LinearGauge`): hairline track, signal fill, mono value. Replaces all donuts.
- **Inputs**: borderless, 1px bottom hairline (`--hairline-strong`), focus underline animates to `--signal`. Selects match.
- **Buttons**: `.btn.primary` ink pill, paper text, lowercase, arrow suffix; hover lifts 1px. `.btn` ghost: hairline border.
- **Section headers**: `01 · field inputs` mono microcaps above a full-width hairline.
- **Ticker strip**: thin carbon band of mono stats, marquee scroll (paused under reduced motion).

## Motion

- Easing: `cubic-bezier(0.16, 1, 0.3, 1)` (expo-out). Durations 240 / 420 / 700ms. No bounce, no elastic, no animated layout properties (transform/opacity only).
- Boot sequence (login → app, ~900ms total): hairlines draw, rail labels rise in stagger, instrument ignites last.
- Tab transitions: exit 160ms fade/rise, enter 360ms stagger.
- Traces draw via `stroke-dashoffset`; numbers tick via rAF count-up into DotMatrix.
- `prefers-reduced-motion: reduce` disables all of the above (instant final states).

## Layout

- Sheet: content max-width 1140px. Tab pattern: hero question headline → numbered input section (form column) beside/above the instrument panel (desktop ~5/7 split, instrument sticky; mobile stacks, instrument directly under the run action).
- Visible hairline rules separate acts; vertical rhythm 56–96px between acts, 20–28px within.
- Bans: glassmorphism, photos, gradients, nested cards, side-stripe borders, gradient text, identical card grids, emoji as UI.
