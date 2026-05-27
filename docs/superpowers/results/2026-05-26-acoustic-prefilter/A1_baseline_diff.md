# A1 Pre-filter — Baseline Diff

**Date:** 2026-05-26
**Branch:** `feat-acoustic-prefilter` (worktree `feat-orthoptera-cicada-gate`)
**Implementation commit:** `a4bfba5` — feat(acoustic): A1 pre-filter — bandpass 1-15kHz + energy norm (flag off)
**Decision:** **REVERT** (see [Decision](#decision) below)

## What was compared

Both heads scored on the **same** 442-clip test fold (dataset fingerprint `208de4d1…`), so test-fold metrics are apples-to-apples.

- **flag-off** (`panns_head.flag_off.joblib`, trained 2026-05-24T10:38:51Z, `panns_baseline.flag_off.json`)
- **flag-on / A1** (`panns_head.flag_on.joblib`, trained 2026-05-26T16:53:29Z, `panns_baseline_bandpass.json`)

CIs are 95% bootstrap (n=1000, seed=42) per `scripts/eval_acoustic.py:bootstrap_ci`.

## Macro-F1

| Head | accuracy | macro-F1 | macro-F1 95% CI |
|---|---|---|---|
| flag-off | 0.7964 | **0.7761** | [0.7248, 0.8208] |
| flag-on (A1) | 0.7738 | **0.7183** | [0.6646, 0.7642] |
| **Δ** | −0.0226 | **−0.0578** | — |

flag-on macro-F1 lower bound (0.665) sits **0.060 below** flag-off lower bound (0.725). The 95% CIs overlap marginally (overlap region [0.725, 0.764]) but the **flag-on upper bound (0.764) sits below the flag-off mean (0.776)** — i.e., the most-optimistic A1 estimate is worse than the central flag-off estimate. This is a real regression beyond bootstrap noise, not a near-miss within overlapping CIs.

## Per-class F1 + regression guard

Guard: pass if `flag_on_lo ≥ flag_off_lo − 1 × flag_off_half_width`.

| Class | flag-off F1 [CI] | flag-on F1 [CI] | Δ | guard threshold | guard |
|---|---|---|---|---|---|
| Bee | 0.746 [0.662, 0.820] | 0.776 [0.694, 0.845] | +0.029 | 0.583 | ✓ pass |
| Beetle | 0.691 [0.571, 0.795] | 0.701 [0.571, 0.800] | +0.010 | 0.459 | ✓ pass |
| Cicada | 0.944 [0.904, 0.980] | 0.937 [0.893, 0.974] | −0.007 | 0.865 | ✓ pass |
| Cricket | 0.821 [0.754, 0.880] | 0.840 [0.780, 0.899] | +0.019 | 0.691 | ✓ pass |
| Grasshopper | 0.781 [0.701, 0.850] | 0.748 [0.672, 0.824] | −0.032 | 0.627 | ✓ pass |
| **Locust** | 0.765 [0.677, 0.834] | **0.671 [0.581, 0.752]** | **−0.094** | 0.599 | **✗ FAIL** (0.581 < 0.599) |
| **Non-biological** | 0.960 [0.857, 1.000] | **0.800 [0.583, 0.957]** | **−0.160** | 0.786 | **✗ FAIL** (0.583 < 0.786) |
| Wasp | 0.500 [0.211, 0.733] | 0.273 [0.000, 0.500] | −0.227 | -0.051 | ✓ pass (vacuous — threshold negative because CI half-width is 0.26 on n=13) |

Two real failures: **Locust** (n=73) and **Non-biological** (n=12).

## Confusion-matrix shifts (test fold, same 442 clips)

Largest off-diagonal changes (flag-off → flag-on):

| true | pred | flag-off | flag-on | Δ |
|---|---|---|---|---|
| Bee | Beetle | 9 | 4 | **−5** (A1 reduces Bee→Beetle leak) |
| Bee | Grasshopper | 2 | 4 | +2 |
| Bee | Wasp | 1 | 2 | +1 |
| Beetle | Locust | 2 | 4 | +2 |
| Cricket | Locust | 4 | 6 | +2 |
| **Locust** | **Grasshopper** | 5 | **12** | **+7** (Locust→Grasshopper more than doubled) |
| Non-biological | Bee | 0 | 1 | +1 |
| Non-biological | Beetle | 0 | 1 | +1 |
| Wasp | Locust | 0 | 4 | +4 |

The dominant pattern: **Locust→Grasshopper leak grew from 5 to 12** (5/73 = 6.8% → 12/73 = 16.4%). This is the inverse of what the existing `CICADA_ORTHO_BOUNDARY_*` guard was tuned to prevent. A1's energy normalization plausibly destroyed amplitude/loudness cues that distinguished the two species.

The Bee→Beetle leak shrank (9 → 4) — A1 *did* help the bee/beetle pair (which the held-out 1.1% had already shown was a small-fold artifact, so this is welcome but not load-bearing).

## Held-out probe

**Skipped per Step 7 decision matrix** ("macro-F1 regresses" routes to REVERT regardless of held-out, marking held-out as "n/a"). The single criterion of macro-F1 regression −5.8 pp is sufficient on its own.

We do **not** claim "held-out would have agreed" — the bee/beetle precedent (commit `134e8eb`, 2026-05-26) showed test-fold confusion cells can swing dramatically on held-out data (12.3% → 1.1%). The relevant claim is narrower: **held-out cannot save A1 from a macro-F1 regression of this magnitude under the plan's matrix**, because per Step 7 macro-F1 regression triggers REVERT independent of held-out.

Time cost saved: ~30–60 min. The skip is defensible under the plan's rules; it does not validate skipping held-out in other contexts. **Future re-runs of any A1 variant must include held-out** — the test-fold-only path is only available when test-fold itself already triggers REVERT.

## Decision

**REVERT.**

Triggering conditions (per plan Step 7):
- ✗ Macro-F1 regresses (−5.8 pp)
- ✗ Per-class guard fails (Locust, Non-biological)
- (Held-out skipped per matrix — macro-F1 regression alone routes to REVERT; no claim is made about what held-out *would have* shown)

Any one of these is sufficient for REVERT per the matrix. Two of three fire here.

## Guard firing-rate analysis (Step 8c)

On REVERT path the criteria in plan Step 8c (retire/loosen/keep) do **not apply** — we are not adopting A1 embeddings, so the abstain gates continue to operate on the flag-off feature distribution against which they were tuned.

The diagnostic interest remains: *did A1 change Locust↔Grasshopper boundary firing on the test fold?* The confusion matrix shift above (Locust→Grasshopper 5 → 12) suggests the boundary guard would have fired *more* on A1 embeddings, not less — which weakens the "Gate retirement" case rather than strengthening it. **Recorded as future-work note in the open questions file rather than executed**, because the A1 head is being discarded.

## Revisit candidates (prioritized)

If A1 is reattempted in a future cycle, the implementation wiring stays in place — only the failure-mode hypothesis changes. Ranked by hypothesis strength given current evidence:

**1. LUFS-on-PANNs-path bypass (prime candidate).** The inference path runs `_decode_audio (LUFS at source rate) → resample 32k → A1 (energy norm)`; training runs `librosa.load (no LUFS) → augment → A1 (energy norm)`. A1's RMS normalization already collapses the loudness degree of freedom in *both* paths — but inference collapses loudness *twice* (LUFS then RMS) while training collapses once (RMS only). This compounds the existing train/inference asymmetry rather than fixing it. The Locust→Grasshopper leak doubling (5→12) and the Non-biological −16 pp drop are consistent with a train/inference distribution gap that A1 introduced. **Next experiment:** drop LUFS just on the PANNs path (LUFS still applies to other consumers via `_decode_audio` so `_band_energies` diagnostics stay intact), retrain, re-baseline. ~1h compute. Held-out probe required this time.

**2. 2–12 kHz narrower passband.** May preserve Locust↔Grasshopper discriminative features that 1–15 kHz washed out. Only worth attempting *after* LUFS-bypass clears, because if (1) is the real cause then any passband variant will see the same regression.

**3. Energy-norm-only (no bandpass).** Falsifies whether the bandpass itself contributes anything beyond the RMS collapse. Cheapest diagnostic.

## Reusable artifacts retained

- `backend/models/panns_head.flag_on.joblib` — the A1-trained head, kept for any future re-evaluation
- `backend/models/panns_baseline_bandpass.json` — the A1 baseline numbers (this doc)
- `backend/models/panns_head.flag_off.joblib` — the recovery copy used by Step 8b

The implementation code (commit `a4bfba5`) stays in the codebase; flag defaults off, so A1 is dormant.
