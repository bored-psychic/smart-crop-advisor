# Bee↔Beetle Boundary Gate — OODA verdict plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close (or formally null-result) the Bee→Beetle 12.3% test-fold confusion using the Phase B abstain-gate playbook, with kill-switches before each irreversible step.

**Architecture:** Hold the bundle weights fixed; layer a pure-precondition abstain rule on `PANNsBundle.predict()` analogous to `_is_cicada_topk_boundary`. Probe-first to verify the failure reproduces out-of-distribution, diagnose-second to test whether structure exists, gate-third only if structure supports it, NULL_RESULT-otherwise.

**Tech stack:** Python · `panns_inference` CNN14 · sklearn ensemble head · pytest · iNat audio (Apoidea/Coleoptera taxa), xc fallback (fam:apidae / fam:scarabaeidae) if iNat starves.

**Canonical home:** Once approved, this plan is also written to `docs/superpowers/plans/2026-05-26-c-bee-beetle-pivot.md`, replacing the existing stub.

---

## Context

Phase B closed cicada/orthoptera via abstain elevation at margin<0.20 plus a top-k tie-breaker for the conf-49 residual (commits `0fc84bc`, `46f5cb2`, `58c941d`). The diagnostic at `docs/superpowers/results/2026-05-26-monoculture-diagnostic/DIAGNOSTIC.md` (commit `89fc544`) then falsified the iNat-monoculture hypothesis: Cricket xc 14.0% (Wilson [6.6%, 27.3%]) ≈ Grasshopper E1 14.5%, even though Cricket is the only training class with built-in xc diversity (~11%).

Therefore the test-fold Bee→Beetle 12.3% (matrix row 0: `[53, 9, 1, 3, 2, 4, 0, 1]` → 9/73 → 12.3%) is the next-worst off-diagonal and is **not** monoculture-induced. It's either (a) a real acoustic-overlap problem amenable to a gate, or (b) confidently-wrong head behavior that no precondition rule can catch (the conf-90 cicada analogue as the *primary* failure mode rather than residual). Branch C decides between these.

Asymmetry matters: Beetle→Bee in the same matrix row 1 is `[1, 28, 1, 3, 2, 2, 0, 0]` → 1/37 → 2.7%. The confusion is heavily directional, so the gate (if any) should be asymmetric: when **top1 = Beetle and Bee is a contender**, not the symmetric Phase B framing.

## OODA verdict — godmode vs devil

**Godmode argument** (run plan as drafted in stub):
- Phase B playbook is proven, with one ship and one NULL_RESULT in the discipline.
- Pre-committed kill-switches contain blast radius (≤2 hr Task 1, ≤1 hr Task 2, kill at Task 3 if structure absent).
- Bee→Beetle is the largest off-diagonal cell; closing it lifts macro F1 directly (Beetle F1 0.69, lowest non-Wasp class).

**Devil argument** (three real concerns with the stub):
1. **iNat-supply risk.** Beetle (Coleoptera) is dominated by visual observations on iNat; Cerambycidae/Elateridae audio is sparser than Cicadidae. Probe may starve at <30 held-out per class — the stub doesn't pre-flight this.
2. **Symmetry mismatch.** Cicada/ortho gate is bidirectional. Bee↔Beetle is 12.3% vs 2.7% — asymmetric. Mirroring the Phase B gate verbatim would over-fire on Beetle-true clips and cost precision.
3. **Refactor risk.** The stub's Task 1 ("parameterize `probe_orthoptera_cicada.py`") touches a script that is now a frozen regression artifact for a shipped feature. DRY here is premature abstraction (YAGNI) — three near-identical group probes is fine; a parameterized one needs its own tests.

**Verdict (what changes vs the stub):**
1. **Adopt the gate-style approach.** Branch A is falsified; this is the only remaining lever short of #11/#13.
2. **Reject Task 1 refactor; copy-modify instead.** `scripts/probe_orthoptera_cicada.py` stays frozen. New file `scripts/probe_bee_beetle.py` clones the iNat-fetch+score pattern, parameterized inline, drops the synthetic mixed-overlay section (asymmetric confusion is measurable on held-out alone — overlays would change the question).
3. **Add iNat-supply pre-flight to Task 2.** Tighten kill-switch: if held-out yield <30/class on iNat after 6 pages, abort and switch to xc (fam:apidae / fam:scarabaeidae) before scoring.
4. **Reframe Task 4 as asymmetric.** Gate fires only when `top1 = Beetle AND Bee in top-k at non-trivial p`. Mirror `_is_cicada_topk_boundary` shape, not `_is_cicada_ortho_boundary` shape (the latter is bidirectional/margin-based; the former is asymmetric/contender-based).
5. **Pre-commit Task 3 STOP rule.** Explicit threshold: if ≥80% of Bee→Beetle errors have top1≥0.65 AND p_bee<0.15, halt and write `NULL_RESULT.md` — gate cannot help.

## File structure

| File | Role | Action |
|---|---|---|
| `scripts/probe_bee_beetle.py` | New held-out iNat (+ xc fallback) Bee/Beetle probe. | **Create** |
| `scripts/probe_orthoptera_cicada.py` | Frozen Phase B regression check. | **Do not touch** |
| `scripts/probe_cricket_distshift.py` | Frozen monoculture-falsification regression check. | **Do not touch** |
| `backend/ml/panns_model.py` | Gate constants + `_is_bee_beetle_topk_boundary` + call site in `predict()`. | **Modify** (lines 82–144 area for constants/helpers; ~349–360 area for the precondition call) |
| `tests/test_bee_beetle_boundary_abstain.py` | Unit tests mirroring `tests/test_cicada_ortho_boundary_abstain.py`. | **Create** |
| `backend/models/panns_baseline.json` | Re-baseline after head behavior unchanged but predict() abstain rate may shift. | **Modify** (only if Task 5 measurements warrant; otherwise leave) |
| `docs/superpowers/results/2026-05-26-bee-beetle-gate/` | Probe JSONs + decision doc (`GATE.md` or `NULL_RESULT.md` per Task 3 outcome). | **Create dir + 1–2 files** |
| `docs/superpowers/plans/2026-05-26-c-bee-beetle-pivot.md` | Replace the stub with this plan's content. | **Replace** (after plan approval) |

## Tasks

### Task 1: Create `scripts/probe_bee_beetle.py` (copy-modify, ~30 min)

**Files:**
- Create: `scripts/probe_bee_beetle.py`

- [ ] **Step 1: Copy `probe_orthoptera_cicada.py` as the skeleton, strip synthetic-mix section.**

  ```bash
  cp scripts/probe_orthoptera_cicada.py scripts/probe_bee_beetle.py
  ```
  Then edit the copy so it has only the iNat-fetch + score paths (no `mix_at_snr`, no `mixed/` subdir, no synthetic overlays — those answered a different question).

- [ ] **Step 2: Replace taxonomy constants (top of file).**

  ```python
  BEE = {"Bee"}
  BEETLE = {"Beetle"}

  PROBE_INAT_TAXA = {
      "Bee":    ["Apis", "Bombus", "Xylocopa", "Halictus", "Osmia",
                 "Megachile", "Anthophora", "Andrena"],
      "Beetle": ["Cerambycidae", "Elateridae", "Passalidae", "Lucanus",
                 "Dynastinae", "Scolytinae", "Dytiscidae", "Prionus"],
  }

  def bb_group(label: str) -> Optional[str]:
      if label in BEE:
          return "bee"
      if label in BEETLE:
          return "beetle"
      return None
  ```

- [ ] **Step 3: Replace `assemble_probe_dir` to drop synthetic mix; keep iNat fetch.**

  Subdirs become `{bee, beetle}` only. Target `max_per_species=60` (probe asks for 60, hard floor 30 in Step 5 below).

- [ ] **Step 4: Adapt `score_probe` for asymmetric reporting.**

  Report not just `cross_group` but **direction**:
  ```python
  stats = {"n": 0, "correct_group": 0,
           "bee_to_beetle": 0,    # true=Bee, pred=Beetle (target failure)
           "beetle_to_bee": 0,    # true=Beetle, pred=Bee
           "other": 0, "abstain": 0,
           "details": []}
  ```
  `details` must capture `top3` and `all_class_confidence` so Task 3 can inspect structure without re-running scoring.

- [ ] **Step 5: Add iNat-starvation kill-switch (replaces `>=30` total assert).**

  ```python
  bee_n = len(list((probe_dir / "bee").glob("*.wav")))
  beetle_n = len(list((probe_dir / "beetle").glob("*.wav")))
  if bee_n < 30 or beetle_n < 30:
      raise SystemExit(
          f"iNat starvation: bee={bee_n}, beetle={beetle_n} (need ≥30 each). "
          f"Rerun with --source xc to fall back to xeno-canto."
      )
  ```
  Defer the xc fallback to a follow-up if Step 9 confirms iNat is sufficient — YAGNI. (Stub-out `--source` arg as a CLI option that currently only accepts `inat`; raise NotImplementedError on `xc` so future work has a single point to extend.)

- [ ] **Step 6: Verify file is syntactically valid (no execution yet).**

  ```bash
  /Users/kiyo/smart-crop-advisor/venv/bin/python -m py_compile scripts/probe_bee_beetle.py
  ```
  Expected: silent exit 0.

- [ ] **Step 7: Commit.**

  ```bash
  git add scripts/probe_bee_beetle.py
  git commit -m "research(acoustic): bee/beetle held-out probe scaffold (no fetch yet)"
  ```

### Task 2: Fetch + score held-out iNat probe (~30 min fetch + ~10 min score)

**Files:**
- Read-only run of: `scripts/probe_bee_beetle.py`
- Output: `/tmp/bee_beetle_probe_results.json`
- Output: `docs/superpowers/results/2026-05-26-bee-beetle-gate/probe_results_v1.json` (committed copy)

- [ ] **Step 1: Pre-flight iNat supply check (manual, fast).**

  ```bash
  curl -s "https://api.inaturalist.org/v1/observations?taxon_name=Cerambycidae&sounds=true&per_page=1" | python -c "import json,sys; print(json.load(sys.stdin).get('total_results'))"
  curl -s "https://api.inaturalist.org/v1/observations?taxon_name=Apis&sounds=true&per_page=1" | python -c "import json,sys; print(json.load(sys.stdin).get('total_results'))"
  ```
  Expected: Apis ≥ a few hundred, Cerambycidae unknown. If Cerambycidae < 20, log to the probe doc and proceed (fetch tries 8 taxa; other Coleoptera families likely make up the difference).

- [ ] **Step 2: Run probe.**

  ```bash
  cd /Users/kiyo/smart-crop-advisor/.claude/worktrees/feat-orthoptera-cicada-gate
  /Users/kiyo/smart-crop-advisor/venv/bin/python scripts/probe_bee_beetle.py
  ```
  Expected: writes `/tmp/bee_beetle_probe_results.json` with per-source confusion stats. Either succeeds (≥30/class) or exits with iNat-starvation message.

- [ ] **Step 3: Apply pre-committed kill-switch.**

  Read `aggregate.bee_to_beetle / (n - abstain)` from the JSON.
  - **If < 5%**: Bee→Beetle was a test-fold artifact. STOP. Write `docs/superpowers/results/2026-05-26-bee-beetle-gate/NULL_RESULT.md` documenting the finding. Skip Tasks 3–5.
  - **If ≥ 5%**: continue to Task 3.

- [ ] **Step 4: Commit probe results.**

  ```bash
  mkdir -p docs/superpowers/results/2026-05-26-bee-beetle-gate
  cp /tmp/bee_beetle_probe_results.json docs/superpowers/results/2026-05-26-bee-beetle-gate/probe_results_v1.json
  git add docs/superpowers/results/2026-05-26-bee-beetle-gate/probe_results_v1.json
  git commit -m "diag(acoustic): held-out bee/beetle probe v1 — bee→beetle X.X%"
  ```

### Task 3: Diagnose failure mode (~1–2 hr, READ-ONLY analysis)

**Files:**
- Read: `docs/superpowers/results/2026-05-26-bee-beetle-gate/probe_results_v1.json`
- Create: `docs/superpowers/results/2026-05-26-bee-beetle-gate/DIAGNOSIS.md`

- [ ] **Step 1: Extract the failure distribution.**

  From `by_source.bee.details` (true=Bee, pred=Beetle entries), gather: `top1_p`, `top2_label`, `top2_p`, `p_bee_in_top3`, `confidence` for each. Build a table in `DIAGNOSIS.md`.

- [ ] **Step 2: Apply the pre-committed STOP rule.**

  Compute: of the Bee→Beetle errors, what fraction has `top1_p >= 0.65 AND p_bee < 0.15`?
  - **If ≥ 80%**: head is confidently wrong on most errors (analogue of conf-90 cicada residual as primary mode). Gate cannot reach them. STOP. Write `NULL_RESULT.md` referencing this rule. Skip Tasks 4–5.
  - **If < 80%**: at least 20% of errors live in a precondition-reachable region. Proceed to Task 4.

- [ ] **Step 3: If proceeding, characterize the structure.**

  In `DIAGNOSIS.md`, write the target precondition explicitly: "Bee→Beetle errors with top1=Beetle, p_top1 in [X, Y], p_bee >= Z at top-k position K." Pre-commit thresholds **before** Task 4 measures fire/false-abstain rates — otherwise Task 4 is post-hoc fitting.

- [ ] **Step 4: Commit diagnosis.**

  ```bash
  git add docs/superpowers/results/2026-05-26-bee-beetle-gate/DIAGNOSIS.md
  git commit -m "diag(acoustic): bee→beetle failure mode characterized — gate viable/NULL"
  ```

### Task 4: Asymmetric top-k abstain gate — TDD (~3 hr; conditional on Task 3 proceed)

**Files:**
- Modify: `backend/ml/panns_model.py`
- Create: `tests/test_bee_beetle_boundary_abstain.py`

- [ ] **Step 1: Write the failing test first.**

  Create `tests/test_bee_beetle_boundary_abstain.py`. Copy the fixture scaffolding (`_FakeLE`, `_FakeClf`, `_FakeTagger`, `_make_bundle`, `_pcm_2s`, `CLASSES`) from `tests/test_cicada_ortho_boundary_abstain.py:30-77` — this is a verbatim copy of test infrastructure, not the rule logic.

  First test, the failing one (use the thresholds chosen in Task 3 Step 3 — placeholders shown):
  ```python
  from backend.ml.panns_model import (
      PANNsAbstain, BEE_BEETLE_TOPK_TOP1_LABELS,
      BEE_BEETLE_TOPK_MIN_P_BEE, BEE_BEETLE_TOPK_MAX_TOP1_MINUS_PBEE,
  )

  def test_bee_beetle_topk_constants_match_design():
      assert BEE_BEETLE_TOPK_TOP1_LABELS == frozenset({"Beetle"})
      assert BEE_BEETLE_TOPK_MIN_P_BEE == 0.15  # placeholder — Task 3 sets
      assert BEE_BEETLE_TOPK_MAX_TOP1_MINUS_PBEE == 0.40  # placeholder

  def test_bee_beetle_topk_abstains_when_bee_contender_at_low_gap():
      # Real-world target: Bee→Beetle error at top1=Beetle 0.49, p_bee=0.19, gap 0.30.
      bundle = _make_bundle({"Beetle": 0.49, "Bee": 0.19,
                              "Cricket": 0.20, "Non-biological": 0.05,
                              "Cicada": 0.07})
      with pytest.raises(PANNsAbstain):
          bundle.predict(_pcm_2s(), 32000)
  ```

- [ ] **Step 2: Run the test — verify it fails with ImportError.**

  ```bash
  cd /Users/kiyo/smart-crop-advisor/.claude/worktrees/feat-orthoptera-cicada-gate
  /Users/kiyo/smart-crop-advisor/venv/bin/python -m pytest tests/test_bee_beetle_boundary_abstain.py -x -v 2>&1 | tail -20
  ```
  Expected: `ImportError: cannot import name 'BEE_BEETLE_TOPK_TOP1_LABELS' …`.

- [ ] **Step 3: Add constants + helper to `backend/ml/panns_model.py`.**

  Insert after the existing `CICADA_TOPK_*` block (around line 96):
  ```python
  # Bee↔Beetle boundary (2026-05-26, Branch C). Held-out probe found
  # Bee→Beetle confusion at top1=Beetle conf≈49, p_bee≈19 at top-k position K.
  # Asymmetric: Beetle→Bee was 2.7% on test fold and is not gated. Mirror shape
  # of _is_cicada_topk_boundary (contender-at-top-k), not the symmetric
  # margin-based _is_cicada_ortho_boundary, because the confusion is one-way.
  BEE_BEETLE_TOPK_TOP1_LABELS = frozenset({"Beetle"})
  BEE_BEETLE_TOPK_MIN_P_BEE = 0.15   # tuned in Task 3
  BEE_BEETLE_TOPK_MAX_TOP1_MINUS_PBEE = 0.40   # tuned in Task 3
  ```

  Insert helper after `_is_cicada_topk_boundary` (around line 145):
  ```python
  def _is_bee_beetle_topk_boundary(top1_lbl: str, probs: np.ndarray,
                                    ordered_classes: list[str],
                                    order: np.ndarray) -> bool:
      """True when top1=Beetle and Bee is a top-3 contender at narrow gap.

      Asymmetric counterpart of _is_cicada_topk_boundary, targeting the
      Bee→Beetle 12.3% test-fold confusion (matrix row 0). Beetle→Bee at 2.7%
      is not gated by this rule — the precondition top1=Beetle is one-way.
      """
      if top1_lbl not in BEE_BEETLE_TOPK_TOP1_LABELS:
          return False
      if "Bee" not in ordered_classes:
          return False
      top3 = [ordered_classes[i] for i in order[:3]]
      if "Bee" not in top3:
          return False
      bee_idx = ordered_classes.index("Bee")
      p_bee = float(probs[bee_idx])
      if p_bee < BEE_BEETLE_TOPK_MIN_P_BEE:
          return False
      top1_p = float(probs[order[0]])
      return (top1_p - p_bee) < BEE_BEETLE_TOPK_MAX_TOP1_MINUS_PBEE
  ```

- [ ] **Step 4: Wire the helper into `predict()`.**

  Add the call alongside the existing `_is_cicada_topk_boundary` block in `predict()` (currently at lines ~353–360):
  ```python
  if _is_bee_beetle_topk_boundary(
      ordered_classes[top1_idx], probs, ordered_classes, order
  ):
      bee_p = float(probs[ordered_classes.index("Bee")])
      raise PANNsAbstain(
          f"bee_beetle_topk_boundary top1={top1_p:.2f} "
          f"p_bee={bee_p:.2f} gap={top1_p - bee_p:.2f}"
      )
  ```

- [ ] **Step 5: Run the failing test — verify it now passes.**

  ```bash
  /Users/kiyo/smart-crop-advisor/venv/bin/python -m pytest tests/test_bee_beetle_boundary_abstain.py::test_bee_beetle_topk_abstains_when_bee_contender_at_low_gap -v
  ```
  Expected: PASSED.

- [ ] **Step 6: Add inert-case tests (mirror cicada-topk inert tests).**

  Mirror `tests/test_cicada_ortho_boundary_abstain.py::test_topk_inert_when_*` tests, swapping {Cicada → Bee} and {Grasshopper/Locust → Beetle}:
  - `test_topk_inert_when_bee_outside_top3`
  - `test_topk_inert_when_pbee_below_floor`
  - `test_topk_inert_when_gap_above_threshold`
  - `test_topk_inert_when_top1_is_bee` (Bee top1 — rule must not fire on Beetle→Bee direction)
  - `test_topk_inert_when_top1_is_grasshopper` (only Beetle qualifies)
  - `test_topk_inert_when_beetle_strongly_confident` (Beetle 0.85, Bee 0.05 → gap 0.80 ≥ 0.40)

- [ ] **Step 7: Run full new test file.**

  ```bash
  /Users/kiyo/smart-crop-advisor/venv/bin/python -m pytest tests/test_bee_beetle_boundary_abstain.py -v
  ```
  Expected: all pass.

- [ ] **Step 8: Regression-run the cicada/ortho gate tests.**

  ```bash
  /Users/kiyo/smart-crop-advisor/venv/bin/python -m pytest tests/test_cicada_ortho_boundary_abstain.py -v
  ```
  Expected: all 18+ existing tests still pass (new rule is structurally orthogonal — different top1 labels).

- [ ] **Step 9: Commit.**

  ```bash
  git add backend/ml/panns_model.py tests/test_bee_beetle_boundary_abstain.py
  git commit -m "feat(acoustic): asymmetric bee→beetle top-k abstain gate"
  ```

### Task 5: Re-score the probe + cicada regression + commit GATE.md (~1 hr)

**Files:**
- Read-only: `scripts/probe_bee_beetle.py`, `scripts/probe_orthoptera_cicada.py`, `scripts/probe_cricket_distshift.py`
- Output: `docs/superpowers/results/2026-05-26-bee-beetle-gate/probe_results_v2_with_gate.json`
- Output: `docs/superpowers/results/2026-05-26-bee-beetle-gate/GATE.md`
- Maybe modify: `backend/models/panns_baseline.json` (only if test-fold rerun warrants — see Step 4)

- [ ] **Step 1: Re-score Bee/Beetle probe with the new gate active.**

  ```bash
  /Users/kiyo/smart-crop-advisor/venv/bin/python scripts/probe_bee_beetle.py --score-only \
      --probe-dir /tmp/bee_beetle_probe \
      --output /tmp/bee_beetle_probe_results_v2.json
  ```
  Diff aggregate `bee_to_beetle` and `abstain` counts vs v1. Pre-committed acceptance: ≥30% reduction in `bee_to_beetle / (n - abstain)` AND `abstain` increase ≤ doubling.

- [ ] **Step 2: Cicada/ortho regression.**

  ```bash
  /Users/kiyo/smart-crop-advisor/venv/bin/python scripts/probe_orthoptera_cicada.py --score-only \
      --probe-dir /tmp/ortho_cicada_probe
  ```
  Diff aggregate cross-group + abstain rates vs the last committed result in `docs/superpowers/results/2026-05-25-orthoptera-cicada-gate/`. Acceptance: ≤ +0.5pp regression on cross-group, ≤ +2pp on abstain.

- [ ] **Step 3: Cricket monoculture regression.**

  ```bash
  XC_API_KEY=$XC_API_KEY /Users/kiyo/smart-crop-advisor/venv/bin/python scripts/probe_cricket_distshift.py
  ```
  (XC_API_KEY must be inline-exported — see handoff gotcha.) Acceptance: ≤ +2pp non-target rate vs the 14.0% recorded in DIAGNOSTIC.md (the new gate's top1=Beetle precondition cannot reach Cricket-true clips, so this is a sanity check).

- [ ] **Step 4: Decide on baseline update.**

  `eval_acoustic.py` bypasses `bundle.predict()` (per NULL_RESULT.md), so the test-fold confusion matrix is unchanged by this gate. Do **not** modify `backend/models/panns_baseline.json` unless you also re-run `scripts/train_panns_head.py` (which this plan does not). Leave the file untouched.

- [ ] **Step 5: Write `GATE.md`.**

  Mirror the structure of `docs/superpowers/results/2026-05-25-orthoptera-cicada-gate/NULL_RESULT.md` (which is the canonical template even though Phase B ultimately shipped). Required sections:
  - What was built
  - Pre-commit thresholds + Task 2/3 results
  - Probe v2 vs v1 deltas (per-source table)
  - Cicada/Cricket regression deltas
  - Acknowledged residuals (Beetle→Bee direction still ungated; any Bee→Beetle error with p_bee<0.15)
  - Next-cycle options if regressions show up

- [ ] **Step 6: Commit results doc + final feature commit.**

  ```bash
  cp /tmp/bee_beetle_probe_results_v2.json docs/superpowers/results/2026-05-26-bee-beetle-gate/probe_results_v2_with_gate.json
  git add docs/superpowers/results/2026-05-26-bee-beetle-gate/
  git commit -m "docs(acoustic): bee/beetle gate ship — bee→beetle X.X%→Y.Y%"
  ```

- [ ] **Step 7: Replace the stub plan with this plan content.**

  ```bash
  cp /Users/kiyo/.claude/plans/adaptive-munching-mitten.md docs/superpowers/plans/2026-05-26-c-bee-beetle-pivot.md
  git add docs/superpowers/plans/2026-05-26-c-bee-beetle-pivot.md
  git commit -m "docs(plans): bee/beetle pivot — replace stub with executed plan"
  ```

## Pre-committed decision rules (single table for at-a-glance review)

| Stage | Measurement | < threshold → action | ≥ threshold → action |
|---|---|---|---|
| Task 2 (held-out probe) | iNat supply per class | <30 → write supply-gap NULL_RESULT, optionally extend to xc later | ≥30 → score |
| Task 2 (held-out probe) | `bee_to_beetle / (n - abstain)` | <5% → STOP, NULL_RESULT (test-fold artifact) | ≥5% → diagnose |
| Task 3 (diagnose) | fraction of errors with top1≥0.65 AND p_bee<0.15 | <80% → gate viable, set thresholds, proceed | ≥80% → STOP, NULL_RESULT (head confidently wrong) |
| Task 5 (re-score) | reduction in `bee_to_beetle` rate | <30% reduction → revert gate (commit, then revert commit, keep tests as research artifact) | ≥30% reduction AND abstain≤2× → ship |
| Task 5 (regression) | cicada cross-group delta | > +0.5pp → revert (interference detected) | ≤ +0.5pp → ship |

## Verification (end-to-end)

After Task 5 ships (or NULL_RESULTs):
1. `/Users/kiyo/smart-crop-advisor/venv/bin/python -m pytest tests/test_bee_beetle_boundary_abstain.py tests/test_cicada_ortho_boundary_abstain.py -v` — all gate tests green.
2. `set -a; source /Users/kiyo/smart-crop-advisor/.env; set +a; /Users/kiyo/smart-crop-advisor/venv/bin/python -m pytest tests/ -k "panns or acoustic" -v` — broader PANNs/acoustic test suite green (env-load workaround per handoff gotcha).
3. Probe JSONs (v1, v2, ortho, cricket) all committed under `docs/superpowers/results/`.
4. `MEMORY.md` updated: add a line under `project_yamnet_roadmap.md` if the Bee F1 improvement affects #11 unblock framing; otherwise no MEMORY change (this is a self-contained acoustic ship, not a roadmap pivot).

## What this plan deliberately is NOT

- **Not a backbone swap** (#11 still data-blocked).
- **Not a data-source diversification** (Branch A — falsified).
- **Not labeling `data/feedback_clips/`** (#13 follow-on; independent).
- **Not a refactor of `probe_orthoptera_cicada.py`** (frozen regression artifact — copy-modify instead).
- **Not symmetric Beetle↔Bee gating** (asymmetric direction is the empirical signal — Beetle→Bee at 2.7% is not a problem worth gating).

## Effort estimate (revised)

| Task | Wall | vs stub |
|---|---|---|
| Task 1 (copy-modify probe) | 30 min | ↓ from 2 hr (no refactor) |
| Task 2 (probe + kill-switch) | 1 hr | ≈ same |
| Task 3 (diagnose + STOP rule) | 1–2 hr | ≈ same |
| Task 4 (gate, TDD, conditional) | 2–3 hr | ↓ slightly (asymmetric rule is simpler) |
| Task 5 (re-baseline + GATE.md) | 1 hr | ≈ same |
| **Total** | **5.5–7.5 hr** | **↓ from 8–10 hr** |
