# Monoculture diagnostic — diversity hypothesis falsified, Branch C chosen

**Plan:** `/Users/kiyo/.claude/plans/tingly-knitting-ember.md`
**Date:** 2026-05-26
**Outcome:** Diversity is NOT the load-bearing fix. Branch C (Bee↔Beetle pivot) selected.

## The question

Phase B closed cicada/grasshopper differentiation, then E1 surfaced a second 12% finding: xc-grasshopper-other = 12/100 (Wasp 4, Bee 4, Cricket 1, Beetle 1, Non-bio 2). Same surface number as the in-distribution Bee→Beetle 12.3% from the test fold. User's hunch: shared root cause (iNat monoculture). Cricket is the only training class with built-in xc diversity (93/867 = ~11% xc) — natural control. If diversity is load-bearing, Cricket should be measurably more robust than 100%-iNat Grasshopper on the same xc-style probe.

## The probe

`scripts/probe_cricket_distshift.py`: fetch 50 xc Cricket clips not already in training (`fam:gryllidae`), score with `PANNsBundle.predict()`, bucket into correct / cross-orthoptera / other / abstain. Same metric as the xc-grasshopper E1: `non_target_rate = (other + cross) / (n - abstain)`.

## Result

| | Grasshopper E1 (100% iNat) | Cricket (this probe, ~11% xc) |
|---|---|---|
| n | 100 | 50 |
| abstain | 17 | 7 |
| n_scored | 83 | 43 |
| non_target | 12 | 6 |
| **rate** | **14.5%** | **14.0%** |
| Wilson 95% CI | — | [6.6%, 27.3%] |

**Cricket rate (14.0%) is statistically indistinguishable from Grasshopper rate (14.5%) despite Cricket having ~11% non-iNat training coverage.** Wilson CI lower bound (6.6%) is above the 5% threshold for Branch A. Per the pre-committed decision rule, ≥10% → **Branch C: diversity falsified**.

## Surprising qualitative finding

The *composition* of errors differs sharply from Grasshopper E1, even though the *rate* matches.

| | Grasshopper E1 misroutes | Cricket misroutes |
|---|---|---|
| In-orthoptera (sister taxa) | 1 (Cricket) | **6** (Locust 5, Grasshopper 1) |
| Out-of-orthoptera (broad) | 11 (Wasp 4, Bee 4, Beetle 1, Non-bio 2) | **0** |

Cricket's failure mode is "confused with stridulating neighbors only." Grasshopper's was "confused broadly into unrelated classes." Same overall rate; different routing structure.

This is consistent with the falsification but adds nuance: Cricket's partial diversity may have constrained errors to *acoustically-adjacent* classes (Locust shares the high-frequency stridulation signature), while still failing at the same overall rate. The fix isn't "more training source variety" — it's "discriminate within acoustically-similar pairs," which is closer to the Phase B gate playbook than the data-lift playbook.

## Decision rule application

| Rate | Verdict | Branch | This run |
|---|---|---|---|
| < 5% | Diversity confirmed | A | — |
| 5–9% | Weakened | B | — |
| **≥ 10%** | **Falsified** | **C** | **14.0% ✓** |

## Implications for Bee↔Beetle (the original A candidate)

The Bee→Beetle 12.3% test-fold finding is now *unlikely* to be a monoculture artifact. If iNat monoculture were the root cause, Cricket (the partial control) should have shown measurable improvement vs Grasshopper. It didn't. Therefore Bee↔Beetle confusion is more likely a species-acoustic-overlap problem (broadband wing-beat ~100–300 Hz vs broadband flight) than a recordist-distribution problem.

This makes the next plan a **Bee↔Beetle pivot with a gate-style approach analogous to Phase B**, not a data-source diversification.

## Files committed

- `docs/superpowers/results/2026-05-26-monoculture-diagnostic/probe_results_cricket_xc.json` — raw probe output
- `docs/superpowers/results/2026-05-26-monoculture-diagnostic/DIAGNOSTIC.md` — this file
- `scripts/probe_cricket_distshift.py` — kept as a re-runnable regression check for head retrains
- `docs/superpowers/plans/2026-05-26-c-bee-beetle-pivot.md` — next plan stub

## Caveats

- **n_scored = 43 (small).** Wilson CI is wide [6.6%, 27.3%]. Cricket rate is still firmly above the 5% Branch A threshold, but the *exact* equivalence to Grasshopper (14.0% vs 14.5%) is within noise. The conclusion that "diversity isn't load-bearing" is robust; the conclusion that "Cricket and Grasshopper behave identically" needs a larger n to assert strongly.
- **Cricket has only ~11% xc training coverage** (93/867). A 100%-xc class would be a cleaner control. None exists in current training. This caveat doesn't change the verdict — partial diversity should have moved the needle measurably if diversity mattered, and it didn't.
- **Non-target metric pools abstains out of denominator.** Same as xc-grasshopper E1 — abstains are pipeline-routed safely, not classification errors. Comparison is apples-to-apples.
