# Bee↔Beetle gate — null result

**Plan:** `/Users/kiyo/.claude/plans/adaptive-munching-mitten.md` (Branch C)
**Date:** 2026-05-26
**Outcome:** Task 2 kill-switch fired. Gate **not built**. Hypothesis (test-fold Bee→Beetle reflects a real OOD acoustic-overlap problem) **falsified**.

## TL;DR

The 12.3% test-fold Bee→Beetle confusion did **not** reproduce on held-out iNat clips: held-out Bee→Beetle = **1.1%** (1 / 93 decided), well below the pre-committed 5% floor for proceeding to gate work. The test-fold and held-out 95% CIs **do not overlap**: test-fold [6.6%, 21.8%] vs held-out [0.2%, 5.8%] (Wilson, full table below). The original test-fold signal was a small-fold artifact: 9/73 has a Wilson CI wide enough that the point estimate is unreliable on small n. Held-out Beetle→Bee = 2.2% (2 / 93), close to the test-fold 2.7%, which validates that the test-fold *reverse* direction was real but already too small to gate.

Branch C is closed. The OODA verdict's three real concerns (iNat supply, asymmetry, refactor risk) were all relevant — supply held up (60 Bee, 49 Beetle), asymmetry held up (1.1% vs 2.2%, still directional), but the absolute rate fell so far that asymmetry no longer matters.

## What was built

- `scripts/probe_bee_beetle.py` (commit `29ef389`) — held-out iNat Bee/Beetle probe with asymmetric reporting (`bee_to_beetle`, `beetle_to_bee`), `--source xc` stubbed as NotImplementedError extension point, kill-switch at <30/class.
- `docs/superpowers/results/2026-05-26-bee-beetle-gate/probe_results_v1.json` — probe output (60 Bee + 49 Beetle held-out iNat clips, scored against current PANNs bundle).

No changes to `backend/ml/panns_model.py`. No gate code. No test files. The plan's Tasks 3–5 (diagnose, build gate, ship/regress) were **skipped** per the Task 2 Step 3 pre-committed STOP rule.

## Pre-committed kill-switches (single table)

| Stage | Measurement | Threshold | Result | Action |
|---|---|---|---|---|
| Task 2 pre-flight | iNat supply per class | ≥30 each | Bee 60, Beetle 49 | PASS → score |
| **Task 2 probe** | **`bee_to_beetle / (n - abstain)`** | **<5% → STOP** | **1.1%** | **STOP → NULL_RESULT** |
| Task 3 STOP | fraction with `top1_p≥0.65 AND p_bee<0.15` | ≥80% → STOP | N/A | (skipped) |
| Task 5 acceptance | reduction in `bee_to_beetle` rate | ≥30% → ship | N/A | (skipped) |

The first kill-switch fired. By plan, Tasks 3–5 do not run.

## Results — held-out iNat

| Source | n | correct | bee→beetle | beetle→bee | other | abstain |
|---|---|---|---|---|---|---|
| Bee (60 clips, 8 taxa: Apis, Bombus, …) | 60 | 43 | 1 | 0 | 7 | 9 |
| Beetle (49 clips, 8 taxa: Cerambycidae, …) | 49 | 38 | 0 | 2 | 2 | 7 |
| **Aggregate** | **109** | **81** | **1** | **2** | **9** | **16** |

Decided = 93 (109 − 16 abstain). Rates:
- bee→beetle = **1/93 = 1.08%** (aggregate); 1/(60−9) = 1.96% on Bee-true alone.
- beetle→bee = **2/93 = 2.15%** (aggregate); 2/(49−7) = 4.76% on Beetle-true alone.

For reference, test-fold (from `backend/models/panns_baseline.json`):
- bee→beetle = 9/73 = **12.3%** → held-out **1.1%**, Δ = **−11.2pp**.
- beetle→bee = 1/37 = **2.7%** → held-out **2.2%**, Δ = **−0.5pp** (≈ same).

## Why the test-fold was misleading

The Bee→Beetle drop (12.3% → 1.1%) is much larger than the Beetle→Bee drop (2.7% → 2.2%). Two non-exclusive reasons:

1. **Small-fold noise.** 9/73 has a Wilson 95% CI of [6.6%, 21.8%] (see CI table below). The point estimate is unreliable for any single off-diagonal cell. The reverse-direction estimate (2.7%) didn't move, but that doesn't mean any single cell is well-estimated — only that *this particular cell* happened to be artifact-high.
2. **Test-fold composition.** The training/test split for Bee may have selected an unrepresentative subset of Bee clips. The held-out iNat draw is from a different, larger pool with the same taxon list — a regression-to-the-mean would explain the drop. Beetle→Bee is small in both because the underlying pattern is genuinely rare.

The single held-out Bee→Beetle error (`inat_Bee_318582706_1657164.wav`, pred=Beetle@75%, top3=[Beetle 75, Wasp 15, Bee 7]) is **confidently wrong**: p_top1=0.75, p_bee=0.07. It would not have been catchable by the asymmetric top-k gate in the plan, which required p_bee ≥ 0.15. So even if we'd built the gate and the held-out rate had been ≥5%, this specific error was unreachable — exactly the conf-90 cicada analogue the OODA verdict's Task 3 STOP rule was designed to detect.

## Statistical confidence (Wilson 95% CI)

| Cell | n | x | rate | Wilson 95% CI |
|---|---|---|---|---|
| **Test-fold bee→beetle** | 73 | 9 | 12.3% | **[6.6%, 21.8%]** |
| **Held-out bee→beetle (aggregate)** | 93 | 1 | 1.1% | **[0.2%, 5.8%]** |
| Held-out bee→beetle (Bee-true only) | 51 | 1 | 2.0% | [0.3%, 10.3%] |
| Test-fold beetle→bee | 37 | 1 | 2.7% | [0.5%, 13.8%] |
| Held-out beetle→bee (aggregate) | 93 | 2 | 2.2% | [0.6%, 7.5%] |
| Held-out beetle→bee (Beetle-true only) | 42 | 2 | 4.8% | [1.3%, 15.8%] |

Forward-direction CIs (test-fold vs held-out aggregate) do **not** overlap — 0.8pp gap between upper held-out (5.8%) and lower test-fold (6.6%). The 11.2pp drop is not explainable by sampling noise alone.

Caveat: the Bee-true-only held-out CI upper bound (10.3%) does overlap test-fold lower (6.6%). The aggregate denominator (n=93) is the right one here — the planned gate fires on prediction=Beetle regardless of true class — but a skeptic could push on the per-source view. Both reverse-direction CIs overlap heavily; the test-fold 2.7% point estimate was already too noisy to draw conclusions from on its own.

## Held-out Bee error scatter (informational only)

Bee true → wrong prediction (n=8 errors out of 60, 9 abstained):

| pred | n | top1_p range |
|---|---|---|
| Cricket | 2 | 67, 73 |
| Locust | 2 | 39, 63 |
| Wasp | 2 | 68, 90 |
| Beetle | 1 | 75 |
| Grasshopper | 1 | 58 |

There is **no dominant error direction** for Bee-true held-out clips. The 12.3% test-fold cell was an oversample of one direction; the actual OOD-failure structure is scattered. This is consistent with Bee F1 being limited by *recall* across many off-diagonal cells, not by a single targetable acoustic-overlap problem.

## Held-out Beetle errors

| file | pred | top1_p | p_beetle | p_bee |
|---|---|---|---|---|
| inat_Beetle_197608400_896731 | Bee | 50 | 37 | 50 |
| inat_Beetle_236854140_1168715 | Bee | 59 | 38 | 59 |
| inat_Beetle_237040025_1176239 | Locust | 54 | 15 | 1 |
| inat_Beetle_55721712_128380 | Cricket | 64 | 10 | 2 |

The two Beetle→Bee errors are at relatively narrow margins (top1 50 / p_beetle 37; top1 59 / p_beetle 38) and would arguably be reachable by a **symmetric** gate — but Beetle→Bee at 4.76% on Beetle-true alone (or 2.15% aggregate) is below the threshold where adding a second gate is worth its precision cost. **Not pursued.**

## What was reverted

Nothing. The probe script and its commit are the only repo changes for Branch C.

## What was retained as research artifacts

- `scripts/probe_bee_beetle.py` — reusable held-out probe for any future Bee/Beetle diagnostic. Asymmetric reporting + `--source xc` stub are forward-compatible.
- `probe_results_v1.json` — the disconfirming dataset itself.
- This NULL_RESULT.md — load-bearing record that Branch C was investigated and falsified, preventing future me from re-running the same experiment.

## OODA-disciplined recommendation for the next cycle

With Branch A (monoculture, falsified by `2026-05-26-monoculture-diagnostic/DIAGNOSTIC.md`) and Branch C (Bee→Beetle gate, falsified here) both closed, the remaining levers are:

1. **#13 active-learning loop on `data/feedback_clips/`** (independent; already shipped per `project_yamnet_roadmap.md` 2026-05-16). Re-label and use as a held-out validation source — would let us re-check baseline test-fold confusion estimates against a *third* OOD distribution and potentially identify the next-worst cell with better statistics than the small training/test split.
2. **#11 backbone swap** (still data-blocked on labeled output from #13). Promotes Branch C from "asymmetric gate over a flawed estimate" to "head retrain on a better-estimated label distribution" — which is what the test-fold artifact above implies we actually need.
3. **Re-baseline `panns_baseline.json` on a held-out iNat fold** (small, ~1 day). If the test-fold confusion matrix is systematically misleading for off-diagonal cells, the *next-worst* cell we'd attack might also be artifactual. Re-baseline before picking the next gate target. Cheap and dispositive.

(3) is the smallest defensible next step. The Bee→Beetle outcome here implies that *small-fold off-diagonal cells carry high sampling noise* — a 73-clip Bee row and 37-clip Beetle row don't support reliable point estimates for individual cells. The selection criterion (largest test-fold off-diagonal) isn't necessarily wrong, but it must be paired with a Wilson CI check before committing to gate work.

## Notes for the next reader

- The probe required ~10 min wall-clock for fetch (60 + 49 iNat clips with held-out filtering against 732 + 369 training clips), ~1.5 min for scoring. iNat supply was tight on the Beetle side (49/60 target) — `--source xc` stub exists as the YAGNI extension point if a future probe needs more.
- The single `inat_Bee_318582706_1657164.wav` Beetle@75 prediction is worth a listen if anyone wants to confirm by ear whether it's a labeling issue at the iNat source vs a model error. Either way: 1 error doesn't move the gate decision.
- **Reproducibility caveat.** The held-out filter scans `data/audio_samples/inat_<class>_<obs_id>_<sound_id>.wav` to determine which iNat observations are training-set members. Both `data/_cache/` and `data/audio_samples/` are gitignored, so re-running on a fresh checkout will pull a *different* held-out draw — what's "held out" depends on training-set filesystem state at probe time. The `probe_results_v1.json` artifact in this directory is the canonical record of *this* run. To re-validate the falsification on a deterministic basis, derive the training-set sound-ID list from a checked-in source (e.g., the bundle's training manifest) rather than `data/audio_samples/` state.
