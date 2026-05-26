# Branch C — Bee↔Beetle pivot (next plan stub)

**Status:** stub. Detailed task breakdown to follow once stub is reviewed.
**Date:** 2026-05-26
**Source of decision:** `docs/superpowers/results/2026-05-26-monoculture-diagnostic/DIAGNOSTIC.md`
**Parent plan:** `/Users/kiyo/.claude/plans/tingly-knitting-ember.md`

## Why this branch

The Cricket xc distribution-shift probe came in at 14.0% non-target (Wilson CI [6.6%, 27.3%]) — statistically indistinguishable from the 14.5% Grasshopper baseline. Cricket is the only training class with built-in xc diversity (~11%). If diversity were load-bearing, Cricket should have moved measurably; it didn't.

The Bee→Beetle 12.3% test-fold confusion is therefore **not a monoculture artifact**. It's an acoustic-overlap problem (broadband wing-beat / flight noise). The right tool is a Phase B-style gate layered on `PANNsBundle.predict()`, not a data-source diversification.

## Strategy (high level — to be detailed)

Mirror the Phase B playbook that closed cicada/orthoptera:

1. **Probe first, gate second.** Measure the boundary on held-out iNat Bee+Beetle before designing the rule.
2. **Pure-precondition abstain rule** (no retraining). Look for top-k structure or margin patterns specific to the confusion direction (asymmetric: Bee→Beetle 12.3% vs Beetle→Bee 2.7% — the asymmetry is a signal).
3. **Unit tests around the rule.** Same approach as `tests/test_cicada_ortho_boundary_abstain.py`.
4. **Re-baseline.** Update `backend/models/panns_baseline.json`. Re-run all probes to confirm no regression on the cicada/orthoptera boundary.

## Task 1: Refactor probe to parameterize taxonomy

`scripts/probe_orthoptera_cicada.py` is currently hardcoded to the orthoptera↔cicada question. Bee↔Beetle reuses ~90% of the same scaffold (iNat held-out fetch, abstain handling, JSON output) — parameterize and reuse.

**Lines to change** (verified against current HEAD at start of plan):

| Line | Current | Generalize to |
|---|---|---|
| 42 | `ORTHOPTERA = {"Grasshopper", "Locust"}` | `GROUP_A` (parameterized) |
| 43 | `CICADA = {"Cicada"}` | `GROUP_B` (parameterized) |
| 58 | `def ortho_group(label: str)` | rename to `group_of(label: str)` over GROUP_A/B |
| 235 | hardcoded `true_label = "Grasshopper"` | derive from iNat taxonomy mapping |
| 238 | hardcoded `true_label = "Cicada"` | same |
| 276 | `parts[1] in ORTHOPTERA else "Grasshopper"` | use GROUP_A |
| 278 | hardcoded `true_label = "Cicada"` | use GROUP_B |

Add CLI flags `--group-a "Bee"` and `--group-b "Beetle"` (sets accept comma-separated, e.g. `"Grasshopper,Locust"`).

**Verification:** rerun the existing orthoptera-cicada probe via the parameterized path with `--group-a "Grasshopper,Locust" --group-b "Cicada"`; results must match the pre-refactor JSON byte-for-byte (or within abstain-tie noise). No regression on the Phase B baseline.

## Task 2: Held-out iNat Bee + Beetle probe

Fetch held-out iNat Bee and Beetle clips not in `data/audio_samples/{Bee,Beetle}/`. Score with the current bundle. Bucket: correct, cross-group (Bee↔Beetle), other, abstain.

**Target n:** 100 per class. **Hypothesis to test:** the test-fold Bee→Beetle 12.3% reproduces on fresh iNat data (= it's a real boundary problem, not test-set artifact). Pre-committed: if the held-out rate is <5%, this whole plan is moot — Bee↔Beetle was a test-fold artifact. Stop here, write a result doc, no gate needed.

## Task 3: Diagnose the failure mode before designing the gate

Look at the confused clips. Are they:
- **Top-k overlapping?** Bee top1 with Beetle top2 close (analogous to the cicada/orthoptera margin pattern that Phase B exploited).
- **Confidence-bimodal?** High-confidence Bee→Beetle errors that no abstain rule can catch (the conf-90 residual case from cicada/orthoptera — structurally unreachable).
- **Spectrally distinguishable by ear?** If yes, the head has signal it isn't using; if no, the physics may not allow this boundary.

This step gates whether Tasks 4–5 are worth doing. If the failures are mostly conf-90 unreachables, the right move is to STOP and write a NULL_RESULT instead of forcing a gate that doesn't generalize.

## Task 4: Design + ship the gate (conditional on Task 3)

Mirror `_is_cicada_topk_boundary` in `backend/ml/panns_model.py`. Pre-commit thresholds before measuring final acceptance rate (so the result interprets itself, same discipline as Phase B).

## Task 5: Re-baseline + commit

- Update `backend/models/panns_baseline.json`
- Confirm cicada/orthoptera Phase B numbers don't regress
- Commit + update `MEMORY.md` entry if the YAMNet roadmap is affected

## What this plan deliberately is NOT

- **Not a backbone swap** (#11 is still data-blocked; orthogonal).
- **Not a multi-source data lift** (Branch A — falsified by the diagnostic).
- **Not labeling `data/feedback_clips/`** (#13 follow-on; independent).
- **Not the Cricket-into-Locust finding** from the diagnostic — that's a separate research note worth filing under "open questions" but not load-bearing for the next ship.

## Effort estimate (rough)

| Task | Wall |
|---|---|
| Task 1 (refactor) | 2 hr |
| Task 2 (Bee+Beetle probe) | 1 hr code + ~30 min fetch + ~10 min score |
| Task 3 (diagnose) | 1–2 hr |
| Task 4 (gate, IF Task 3 supports it) | 3–4 hr |
| Task 5 (re-baseline) | 1 hr |
| **Total** | **8–10 hr** (one focused session, with Task 3 as a kill-switch) |
