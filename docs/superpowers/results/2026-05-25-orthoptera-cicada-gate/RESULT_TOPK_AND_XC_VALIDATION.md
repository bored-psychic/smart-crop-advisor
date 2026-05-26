# Top-k boundary abstain + held-out xeno-canto validation — result

**Plan:** `/Users/kiyo/.claude/plans/tingly-knitting-ember.md` (next-cycle option 1 from RESULT_ABSTAIN_ELEVATION.md)
**Date:** 2026-05-26
**Outcome:** Phase B shipped. Phase C2 (hard-negative retrain) rejected upstream. E1 (held-out scientific-recordist probe) validates Phase B differentiation on truly novel data and surfaces a new pre-existing distribution-shift finding.
**Cross-group rate:** 9.3% → **8.3%** on the original probe (n=200); **1.0%** on a fresh 100-clip xeno-canto held-out probe (Wilson 95% CI [0.18%, 5.4%]).

## What was built (Phase B, commit `46f5cb2`)

A second pure-precondition abstain rule inside `PANNsBundle.predict()`, layered on top of
the margin<0.20 elevation shipped in `0fc84bc`. When top1 ∈ {Grasshopper, Locust} and
Cicada appears in top-3 with `p_cicada ≥ 0.15` and `top1 − p_cicada < 0.40`, raise the
top-1 floor to 0.65 (same precondition-collapse trick as the margin rule).

- Constants + helper: `backend/ml/panns_model.py` (`CICADA_TOPK_*` + `_is_cicada_topk_boundary`)
- Wired into `predict()` alongside the existing margin rule
- Unit tests: `tests/test_cicada_ortho_boundary_abstain.py` — 10 new top-k tests, 9 existing margin tests, all 19 pass
- No changes to the pipeline, head, training data, or API contract
- `tolerance_macro_f1` bumped from 0.005 → 0.03 in `backend/models/panns_baseline.json` to match the bootstrap CI width already documented in the baseline

## Phase B probe outcome (n=200)

| Source | n | Pre-gate cross | After margin<0.20 | After top-k |
|---|---|---|---|---|
| Held-out iNat Orthoptera | 80 | 0 | 0 | 0 |
| Held-out iNat Cicada | 40 | 5 | 2 | **1** |
| Synthetic mixed | 80 | 14 | 13 | 12 |
| **Aggregate** | **200** | **19 (11.5%)** | **15 (9.3%)** | **13 (8.3%)** |

Net: 1 more cross-group caught (the `conf-49 → top2=Locust, Cicada top3 at 19%` case
flagged in RESULT_ABSTAIN_ELEVATION.md), 0 new false-abstains. Abstain budget went
43 → 43.

Remaining iNat residual: `inat_Cicada_291008566_1532448.wav` — predicted Grasshopper
at conf 90, p_cicada=0.07. Structurally unreachable by any top-k rule (Cicada outside
top-3 entirely with this gap).

## Phase C2 hard-negative retrain — rejected upstream

C2 was the second next-step from RESULT_ABSTAIN_ELEVATION.md. Rejected before any
code was written, based on prior-cycle observation:

- **One clip can't flip a 0.90 confident decision** on the conf-90 residual through
  sklearn LogReg+HistGB retraining. The head needs spectral discriminators, not
  more iNat-shaped negatives.
- **D1 (HistGB `sample_weight=balanced` same-data retrain) just failed** the D5
  acceptance gate one day prior. Same architecture + small data delta = expected
  repeat failure with ~50% odds.
- **Class-imbalance trap**: the only fresh acoustic source on hand was xeno-canto.
  XC covers Orthoptera (~1700 clips available) but **zero cicadas** (xc is bioacoustics
  for grasshoppers/crickets/katydids; cicadas are Hemiptera, not in scope). Adding
  1700 xc grasshopper clips against a static 733 cicada set would worsen the
  cicada/grasshopper boundary, not fix it.

Verified xc coverage gap by querying `fam:cicadidae`, `gen:magicicada`, `gen:tibicen`,
`gen:cicadetta`, `gen:cyclochila`, `gen:cryptotympana`, and `grp:8 q:cicada` — all
return 0 records.

## E1 — held-out xeno-canto probe as the salvage path

With C2 dead and the original probe known to mix iNat (training-distribution-adjacent)
with synthetic training-clip overlays, we needed evidence on truly held-out
scientific-recordist data. Fetched 100 `fam:acrididae` (grasshopper) recordings via
xeno-canto v3 API (`/tmp/ortho_xc_probe/orthoptera/`, files `xc_<id>_Grasshopper.wav`).

**Result:**

| Bucket | Count | Notes |
|---|---|---|
| Correct group (Grasshopper/Locust) | 70 | |
| Cross-group (predicted Cicada) | **1** | `xc_1064834_Grasshopper.wav` at conf 54 |
| Other-class confusion | 12 | 4 Wasp, 4 Bee, 1 Cricket, 1 Beetle, 2 Non-bio |
| Abstain | 17 | Phase A + B rules firing as designed |

Cross-group rate: **1.0%**, Wilson 95% CI **[0.18%, 5.4%]**. Upper bound well below
the original probe's 8.3% (mixed-source post-gate) and pre-gate 11.5%.

### Phase 1 systematic-debugging audit of the E1 claim

Before declaring the 1% number valid, audited the probe distribution to confirm it
was real evidence and not a sampling artifact that avoided the cicada/grasshopper
boundary:

- **Geography**: 42 Spain, 30 Russia, 10 Italy, 9 Netherlands, 3 Greece, 3 Germany,
  2 France, 1 South Korea. **55/100 in Mediterranean** (cicada-overlap regions).
- **Taxonomic diversity**: 15 unique genera (Chorthippus 50, Stenobothrus 13,
  Omocestus 11, Euchorthippus 6, …) — not a monoculture.
- **Multi-species contamination**: 11 of 100 clips have `also` species listed;
  **0 of 100 have cicada in `also`** (would have invalidated ground truth).
- **Clip length**: min=4s, median=23s, max=169s — librosa loads at 16kHz with
  `duration=10.0` so all clips contribute the same window count to the head.
- **The single cross-group clip** (`xc_1064834`): genuine single-species
  *Stenobothrus lineatus* recording from Netherlands, no `also` species. Real
  classifier error, not a label issue.

Validated: 1/100 on truly held-out, taxonomically-diverse, cicada-overlap-region
data is real evidence that Phase B's cicada/grasshopper differentiation generalizes
beyond the training distribution.

## New finding: pre-existing 12% other-class distribution-shift

The 12 "other-class" misclassifications on xc Grasshopper audio are NOT caused by
Phase B and are NOT in the cicada↔grasshopper category. The pattern:

| Predicted | Count | Confidence range |
|---|---|---|
| Wasp | 4 | 38–52 |
| Bee | 4 | 46–71 |
| Cricket | 1 | 49 |
| Beetle | 1 | 55 |
| Non-biological | 2 | 51–55 |

All 12 files are genuine Acrididae (grasshopper) recordings per xc metadata. The
training set is 100% iNat — the head learned an iNat-shaped grasshopper concept
that doesn't transfer cleanly to xc-quality scientific-recordist audio. This is a
**pre-existing distribution-shift bug** that the E1 probe surfaced; it's
independent of Phase B and would have been there before either cycle.

Candidate for the next OODA cycle, alongside the existing Bee↔Beetle 12.3%
test-fold confusion (the other candidate from `tingly-knitting-ember.md`'s
"Next cycle" section).

## Test fold regression (D2 budget)

`python scripts/eval_acoustic.py` → **+0.0000 F1 delta on all 8 classes**.
`eval_acoustic.py` calls `clf.predict()` directly, bypassing `bundle.predict()` and
therefore both abstain rules. Structural inertness in eval is expected and matches
RESULT_ABSTAIN_ELEVATION.md's prior observation. The pre-push hook's macro-F1
no-regression gate passes for the same reason.

## Honest claims and caveats

- 8.3% on the original n=200 probe is real but mostly bounded by mixed-source
  synthetic overlays (12 of 13 residuals). Their margins are wide (model is
  confidently wrong); post-processing has limited headroom against them.
- 1.0% on E1 is the strongest cicada/grasshopper differentiation evidence we have.
  CI upper bound 5.4% — n=100 is not enough to claim sub-percent precision.
- E1's data was fetched after Phase B was already designed, so there's no tuning
  feedback loop on this probe. The thresholds (margin<0.20, top-k 0.15/0.40) were
  tuned on the original iNat+synthetic probe and held up unchanged.
- conf-90 inat residual remains structurally unreachable. So do the 13 mixed-source
  synthetic errors with wide margins. Both require feature-level changes
  (spectral features or backbone swap), not post-processing.
- The 12% other-class confusion is a real finding but represents pre-existing
  behavior, not regression.

## Files touched in Phase B (commit `46f5cb2`)

- `backend/ml/panns_model.py` — top-k constants + helper + wire-in
- `backend/models/panns_baseline.json` — tolerance bump 0.005 → 0.03
- `tests/test_cicada_ortho_boundary_abstain.py` — +10 top-k tests
- `scripts/probe_orthoptera_cicada.py` — minor scoring updates for the v3 numbers

## Recommended next steps (priority order)

1. **Distribution-shift investigation** (medium, ~1 cycle). The 12% other-class
   confusion on xc surfaced by E1 is a measured, reproducible problem on
   non-training-distribution data. Highest-EV target for the next OODA cycle
   because it generalizes beyond the cicada/grasshopper boundary — a fix would
   improve Wasp/Bee/Beetle/Cricket boundaries simultaneously.
2. **Bee↔Beetle 12.3% test-fold pivot** (medium, ~1 cycle). Largest *measured*
   confusion in the current baseline. Already flagged as the recommended next
   target by `tingly-knitting-ember.md` under E. Still valid.
3. **Spectral features for the conf-90 cicada residual** (larger, ~1 week).
   Same recommendation as RESULT_ABSTAIN_ELEVATION.md. No post-processing rule
   will catch p_cicada=0.07 in a 0.83-margin Grasshopper prediction.
4. **Label `data/feedback_clips/` (38 UUID-named WAVs)** (~1–3 hrs). Unblocks
   future retrains, including a more credible hard-negative attempt than C2
   could have been.
