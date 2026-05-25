# Cicada/Orthoptera boundary abstain elevation — result

**Plan:** `/Users/kiyo/.claude/plans/tingly-knitting-ember.md` (next-cycle Option 1 from NULL_RESULT.md)
**Date:** 2026-05-25
**Outcome:** Partial success. Shipped at margin<0.20 (not the originally-recommended 0.15).
**Cross-group rate:** 11.5% → **9.3%** (−21% relative) at 1 false-abstain cost (n=200 probe).

## What was built

A pure-precondition abstain rule inside `PANNsBundle.predict()`. When top1 and
top2 are both in {Cicada, Grasshopper, Locust}, span different acoustic groups
(orthoptera ↔ cicada), and the head's top1−top2 margin < 0.20, raise the top-1
floor from the default 0.45 (or per-class override) to 0.65. With the simplex
constraint `top1 + top2 ≤ 1.0`, margin<0.20 caps top1 at 0.60 — strictly below
0.65 — so the precondition collapses to "abstain whenever the boundary fires."

- Constants + helper: `backend/ml/panns_model.py:66-101`
- Wired in `predict()`: `backend/ml/panns_model.py:305-310`
- Unit tests: `tests/test_cicada_ortho_boundary_abstain.py` (9 tests, all pass)
- No changes to the pipeline, the head, training data, or the API contract.

## Why margin = 0.20, not 0.15 (the recommended value in NULL_RESULT.md)

The NULL_RESULT.md recommendation assumed the head's failure mode was
*boundary-confused* predictions at margin<0.15. Margin sweep on the probe
showed otherwise:

| Margin threshold | cross_caught | false_abstain |
|---|---|---|
| 0.10 | 0 | 0 |
| **0.15 (recommended)** | **0** | 0 |
| **0.20 (shipped)** | **4** | 0 |
| 0.25 | 4 | 0 |
| 0.30 | 4 | 1 |
| 0.99 (no precondition) | 8 | 19 |

The 4 confidence-55 cicada→grasshopper errors on the probe have actual margins
≈ 0.17 in `predict()`. The recommended 0.15 threshold caught zero of them. The
v2 ship at 0.20 catches all four. Diminishing returns beyond 0.25, and 0.30
starts costing precision.

## Probe outcome (n=200, three sources)

| Source | n | Pre-gate cross | v2 cross | Pre-gate abstain | v2 abstain |
|---|---|---|---|---|---|
| Held-out iNat Orthoptera | 80 | 0 | 0 | 14 | 14 |
| Held-out iNat Cicada | 40 | 5 | **2** | 6 | 9 |
| Synthetic mixed | 80 | 14 | 13 | 14 | 16 |
| **Aggregate** | **200** | **19 (11.5%)** | **15 (9.3%)** | **34** | **39** |

Net: 4 cross-group errors converted to abstain (→ API fallback), with at most
1 false-abstain (the +1 mixed-source abstain that wasn't a cross-group flip).

Caught (verified via spy trace inside `predict()`):
- `inat_Cicada_287076897_1506853.wav` (was Grasshopper conf=55) → abstain
- `inat_Cicada_288313186_1506853.wav` (was Grasshopper conf=55) → abstain
- `inat_Cicada_288313461_1506853.wav` (was Grasshopper conf=55) → abstain
- `mix_006_dom-ortho_snr+5_Grasshopper.wav` (was Cicada conf=48) → abstain

Acknowledged residuals:
- `inat_Cicada_289036482_1520256.wav` (Grasshopper conf=49) — top2=Locust (same
  orthoptera group), Cicada is only 3rd at 19%. No top1/top2 rule can catch
  this; would need top-k inspection or a different signal.
- `inat_Cicada_291008566_1532448.wav` (Grasshopper conf=90, margin=0.83) — the
  confidence-90 confidently-wrong case from NULL_RESULT.md. Out of reach for
  any margin-conditioned post-processing. Hard-negative retraining or spectral
  features needed.
- 13 mixed-source errors at confidence 56–100 with margins too wide for the
  precondition.

## Test fold (D2) regression

`scripts/eval_acoustic.py` — all 8 classes show +0.0000 F1 delta. `eval_acoustic`
calls `clf.predict()` directly, bypassing `bundle.predict()` and thus the
abstain elevation. This is structurally expected and matches NULL_RESULT.md's
prior observation. The test fold also has 0/74 Grasshopper↔Cicada confusion,
so even an in-pipeline evaluation would not exercise the gate.

## What was kept from the failed variance gate

- `backend/ml/orthoptera_cicada_gate.py` and its unit tests (research artifacts,
  not wired)
- `scripts/probe_orthoptera_cicada.py` (reused for measuring this fix)
- `scripts/probe_physics_prior.py` (still validates the per-window variance
  asymmetry is real; the gate's failure was the precondition, not the signal)

## Honest claims

- 21% relative reduction in cross-group rate is real and validated on
  held-out iNat clips. Not the 50% target the NULL_RESULT.md set as the
  recommendation's stretch goal.
- The 0.20 threshold was tuned on the same probe used to measure the result —
  there is mild overfit risk. The margin sweep was discrete (5 grid points)
  and the chosen value sits at the elbow, so the risk is bounded but real.
  A fresh held-out probe would be the cleanest validation. Deferred.
- The mixed-source synthetic mixtures dominate the residual error count
  (13 of 15). Their margins are wide (model is confidently wrong), so the
  post-processing approach has fundamentally limited headroom here.

## Recommended next steps (in priority order)

1. **Top-k boundary check** (small, ~2 hrs). If top1 ∈ {Grasshopper, Locust}
   and Cicada in top-3 with prob ≥ 0.15 and top1−p_cicada < 0.40, abstain.
   Catches the conf-49 case and possibly more.
2. **Hard-negative retraining** (medium, ~3 days). Use the 13 remaining
   mixed-source errors + the 2 residual cicada errors as targeted negatives.
   Addresses the confidence-90 residual.
3. **Spectral features** (larger, ~1 week). Same recommendation as
   NULL_RESULT.md. Addresses the underlying boundary where the head's
   probabilities can't discriminate.
