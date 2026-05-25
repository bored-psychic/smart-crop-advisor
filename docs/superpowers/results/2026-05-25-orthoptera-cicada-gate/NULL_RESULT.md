# Orthoptera-vs-Cicada gate — null result

**Plan:** `/Users/kiyo/.claude/plans/tingly-knitting-ember.md` (Path A)
**Date:** 2026-05-25
**Outcome:** Devil wins. Gate not shipped. Research artifacts retained.

## What was built

A pure-function tie-breaker gate that nudges (max 0.05) between Cicada and the
top-Orthoptera class when (a) {top1, top2} ⊂ {Grasshopper, Locust, Cicada}, (b)
top1 and top2 span groups, and (c) margin < 0.15. Signal: per-window probability
variance from the trained head + onset density per second.

- Module: `backend/ml/orthoptera_cicada_gate.py` (pure functions, no I/O)
- Unit tests: `tests/test_orthoptera_cicada_gate.py` (11 tests, all pass)
- Probe: `scripts/probe_orthoptera_cicada.py` (held-out iNat fetch + SNR+5/+10 dB
  synthetic mixtures, score-only mode supported)
- Probe tests: `tests/test_probe_orthoptera_cicada.py` (3 tests)
- Physics-prior validator: `scripts/probe_physics_prior.py` (Fix A3 hardgate)

## What passed before the gate's go/no-go

| Layer | Result |
|---|---|
| Fix A3 physics-prior hardgate | PASS — Cicada median delta -0.00034, Grasshopper +0.03356 |
| Task 2 kill-switch (pre-gate ≥5%) | PASS — 11.5% aggregate cross-group on probe |
| Task 4 unit tests | PASS — 11/11 |
| Task 5 integration tests | PASS — 4/4 (gate wired into `predict()` correctly) |
| Task 6 D2 regression (≤0.01 F1 drop) | PASS — 0.0000 deltas (eval_acoustic.py bypasses bundle.predict, so test fold doesn't exercise the gate; gate is also structurally inert on classes outside its target set) |

## What failed

**Task 7 Field probe** — required ≥50% reduction in cross-group rate.

| Source | Pre-gate cross-group | Post-gate cross-group | Δ |
|---|---|---|---|
| Held-out iNat Orthoptera (n=66 decided) | 0 | 0 | 0 |
| Held-out iNat Cicada (n=34 decided) | 5 | 5 | 0 |
| Synthetic mixed (n=65→66 decided) | 14 | 15 | +1 |
| **Aggregate (n=165→166 decided)** | **19 (11.5%)** | **20 (12.0%)** | **+1, +0.5pp** |

## Why the gate didn't help (firing tally across 200 probe clips)

| Gate decision | Count |
|---|---|
| top2_outside_targets (e.g. top2=Cricket/Bee) | 72 |
| margin_above_floor (head confident enough; gate inert) | 48 |
| same_group (top1+top2 both Orthoptera, gate inert) | 39 |
| abstain (head's calibrated confidence below floor) | 34 |
| top1_outside_targets_fast_path | 6 |
| **fired** | **1** |

The gate's activation precondition (margin<0.15 AND spans groups) is
**structurally too narrow** for the actual failure mode. The held-out Cicada
clips that misclassify as Grasshopper do so at confidences 49, 55, 55, 55, **90**
— the head is *confidently wrong*, not boundary-confused. A tie-breaker is the
wrong tool. The only firing on 200 clips flipped a borderline mixed clip
(mix_006_dom-ortho_snr+5) from abstain → Cicada (wrong direction: truth was
Grasshopper). Net: -1 abstain, +1 cross-group error.

## What was reverted

- `backend/ml/panns_model.py` — gate import, `_per_window_head_probs` helper,
  Fix A4 fast-path call, `onset_density_per_sec` kwarg, telemetry field
- `backend/services/acoustic/pipeline.py` — `onset_density_per_sec` thread
- `tests/test_panns_predict_gate.py` — integration tests for wiring (deleted,
  no longer applicable)

## What was retained as research artifacts

- The gate module + its unit tests (importable, testable, but not wired into
  `predict()`)
- The probe scripts (reusable for future cicada/orthoptera analyses)
- The physics-prior validator (the per-window variance asymmetry is real on
  clean clips; the gate failed because the *failure mode* isn't boundary
  confusion, not because the signal is wrong)
- These probe result JSONs (pre/post)

## OODA-disciplined recommendation for the next cycle

The probe surfaces a real, recurring failure (Cicada→Grasshopper at confidence
55–90 on held-out iNat). Three candidate fixes, in increasing blast radius:

1. **Abstain elevation on the cicada/orthoptera boundary** *(surgical, ~1 day)*.
   When top1+top2 ∈ {Cicada, Grasshopper, Locust} with margin<0.15, raise the
   top1 floor from 0.45 → 0.65. Converts the 3-of-5 cicada cross-group errors
   at confidence 55 into abstains (→ API fallback). Structurally safe (only
   abstain, no flipped predictions; passes D6). Estimated effect on probe:
   cross-group ~11.5% → ~5%.

2. **Hard-negative re-training** *(medium, ~3 days)*. Use the held-out Cicada
   clips the model confidently misreads as Grasshopper as targeted negatives
   for a head retrain. Addresses root cause.

3. **Spectral features** *(larger, ~1 week)*. Cicada tonal carriers (3–15 kHz)
   ≠ orthoptera stridulation pulses. Adding spectral flatness/centroid as
   features (or as a parallel discriminator) addresses the boundary where
   probability variance failed.

The probe + physics validator built here are reusable for evaluating all three.
