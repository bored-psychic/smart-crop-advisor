# Acoustic Hardening Resume Plan — 2026-05-24

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish executing the 8-class PANNs acoustic hardening plan from the previous session. T1 retrain died mid-flight; resume from there and ship through reviewer + push.

**Architecture:** Continuation of the approved 6-decision plan (D1 HistGB rebalance / D2 per-class abstain / D3 bootstrap CIs / D4 multi-clip smoke / D5 acceptance gate / D6 no-field-fold). T1 code change and T2 are committed; T3 helper + tests and T4 script are written but uncommitted; retrain bundle and Makefile and smoke run are still pending.

**Tech Stack:** Python 3 / sklearn HistGradientBoostingClassifier / panns_inference CNN14 / FastAPI backend / pytest / joblib bundle on disk / `data/audio_samples/<class>/*.wav` corpus.

---

## Context

### Why this plan exists

The previous session's plan (`/Users/kiyo/.claude/plans/groovy-toasting-pond.md`) addresses three concerns surfaced in devil/godmode analysis of the just-shipped 8-class PANNs bundle (Bee, Beetle, Cicada, Cricket, Grasshopper, Locust, Non-biological, Wasp):

1. **Beetle F1 regressed −0.080** (0.771 → 0.691) because `scripts/train_panns_head.py` passed `class_weight="balanced"` to LogRegCV but not to HistGB. Fix: `compute_sample_weight("balanced", y_train)` at fit time.
2. **Locust/Wasp routing fragility** — Locust smoke came in at exactly `confidence=45`, on the `ABSTAIN_TOP1=0.45` cliff. Fix: per-class thresholds (Locust/Wasp = 0.35).
3. **Measurement noise** — Wasp F1=0.50 on n=13 has 95% CI ≈ [0.23, 0.77]. Fix: bootstrap CIs in eval + baseline file.

That session got 2 commits ahead of `origin/main`, kicked off the retrain in a background shell, hit a `/clear`, and the retrain process died before HistGB finished. Snapshot was already taken to `/tmp/panns_head_v8_unweighted.bak` for rollback. WIP for T3 and T4 is sitting uncommitted/untracked.

This plan picks up from that exact state and ships through reviewer + push.

### State entering this plan (verified 2026-05-24)

**Committed on local main (2 ahead of `origin/main`):**
- `5c660e4 feat(train): HistGB sample_weight=balanced for minority lift` — T1 code only (no new bundle)
- `a73da67 feat(acoustic): class-specific abstain thresholds (Locust/Wasp 0.35)` — T2 in panns + yamnet + unit tests

**Working tree:**
- Modified, uncommitted: `scripts/eval_acoustic.py` (bootstrap_ci helper wired into `evaluate()`, `compare_to_baseline()`, `write_baseline()`)
- Untracked: `scripts/smoke_acoustic.py` (T4 harness, never run), `tests/test_eval_bootstrap.py` (3 tests, all passing)
- Untracked (NOT this plan's scope, leave alone): `docs/superpowers/plans/2026-05-24-*.md`, `scripts/probe_tta.py`

**Filesystem:**
- `/tmp/panns_head_v8_unweighted.bak` (14 MB, 24 May 18:09) — rollback snapshot, IS the current `backend/models/panns_head.joblib` byte-for-byte (both are unweighted v8)
- `backend/models/panns_head.joblib` (24 May 16:08) — still the unweighted bundle (retrain never wrote it)
- `/tmp/retrain_v8_weighted.log` ends at `18:18:46,374 [INFO] Training HistGradientBoostingClassifier head …` then nothing — process was killed
- No `Makefile` exists at repo root

**Verified before writing this plan:**
- `pytest tests/test_eval_bootstrap.py -q` → 3 passed
- `tests/test_panns_model.py:121-145` contains `test_abstain_threshold_returns_lower_for_high_stakes_classes` and `test_yamnet_abstain_threshold_mirrors_panns`
- `train_panns_head.py:361-362` has `sw_train = compute_sample_weight(...)` + `hgb.fit(..., sample_weight=sw_train)`
- `panns_model.py` + `yamnet_model.py` both have `ABSTAIN_TOP1_DEFAULT`, `ABSTAIN_TOP1_PER_CLASS = {"Locust": 0.35, "Wasp": 0.35}`, and `_abstain_threshold()` used at the abstain decision point

### The D5 acceptance gate (decision point at Task 3)

After retraining, eval the new bundle and read the CI bounds:

- **PASS** iff Beetle F1 lower-CI ≥ 0.65 **AND** macro_f1 lower-CI ≥ 0.74 → atomic commit of bundle + baseline + eval + tests.
- **FAIL** → restore `/tmp/panns_head_v8_unweighted.bak`, ship D2 (already shipped) + D3 + D4 against the unweighted bundle, surface to user with the numbers.

## File map

| Path | Action | Why |
|---|---|---|
| `backend/models/panns_head.joblib` | Overwrite via retrain (Task 1) | D1 — weighted bundle |
| `backend/models/panns_baseline.json` | Overwrite via `--write-baseline` (Task 3) | D1 + D3 — new floor + CIs |
| `scripts/eval_acoustic.py` | Already-modified, commit at Task 3 | D3 — CIs persisted |
| `tests/test_eval_bootstrap.py` | Already-written, commit at Task 3 | D3 — guard helper |
| `scripts/smoke_acoustic.py` | Already-written, commit at Task 4 | D4 — multi-clip smoke |
| `Makefile` | Create at Task 4 | D4 — `make smoke-acoustic` |

---

## Task 0: Verify pickup state (read-only sanity)

**Files:** none modified

- [ ] **Step 1: Confirm git state matches the assumptions above.**

```bash
git status --short
git log --oneline origin/main..HEAD
```

Expected: `M scripts/eval_acoustic.py`, `?? scripts/smoke_acoustic.py`, `?? tests/test_eval_bootstrap.py` present in status. `log` returns exactly:
```
a73da67 feat(acoustic): class-specific abstain thresholds (Locust/Wasp 0.35)
5c660e4 feat(train): HistGB sample_weight=balanced for minority lift
```

If anything diverges (more commits, missing WIP), STOP and reconcile before proceeding — the D5 atomic-commit later assumes this exact starting set.

- [ ] **Step 2: Confirm rollback snapshot exists and matches the live bundle.**

```bash
ls -la /tmp/panns_head_v8_unweighted.bak backend/models/panns_head.joblib
shasum /tmp/panns_head_v8_unweighted.bak backend/models/panns_head.joblib
```

Expected: both files exist, sizes ~14 MB, sha sums identical (the .bak was taken before retrain and the retrain never wrote a new bundle, so they should still match byte-for-byte).

If sums differ → the live bundle is NOT the unweighted v8 and rollback would silently restore the wrong bundle. STOP and ask the user.

- [ ] **Step 3: Confirm no orphan retrain process is running.**

```bash
pgrep -fl "train_panns_head" || echo "no orphan procs"
```

Expected: `no orphan procs`. If a process is found, STOP and ask the user before killing — it may belong to another session.

- [ ] **Step 4: Confirm WIP tests still pass against committed code.**

```bash
venv/bin/python -m pytest tests/test_eval_bootstrap.py tests/test_panns_model.py -q
```

Expected: all pass (3 in `test_eval_bootstrap.py`, plus the existing `test_panns_model.py` suite including the two `_abstain_threshold` tests).

---

## Task 1: Resume the HistGB-weighted retrain (D1)

**Files:** `backend/models/panns_head.joblib` (overwrite)

The previous run's LogRegCV log line at `18:18:46 val_acc=0.742` is informational only — sklearn will redo LogRegCV from scratch. Embeddings ARE cached on disk (the previous run logged `train/clean — 3535 ok, 0 skipped` in ~2 s, which only happens against a warm cache), so the total retrain is bounded by LogRegCV (~9 min) + HistGB (a few min) ≈ 12–20 min wall.

- [ ] **Step 1: Re-snapshot the live bundle (idempotent, safety belt).**

```bash
cp backend/models/panns_head.joblib /tmp/panns_head_v8_unweighted.bak
shasum /tmp/panns_head_v8_unweighted.bak
```

This is a no-op if the live bundle is still the unweighted v8 (Task 0 Step 2 confirmed that). If somehow the bundle is now newer, this would *destroy* the rollback — DON'T run this step in that case; STOP and ask the user.

- [ ] **Step 2: Kick off retrain in background, capture log.**

```bash
nohup venv/bin/python scripts/train_panns_head.py \
  > /tmp/retrain_v8_weighted.log 2>&1 &
echo $! > /tmp/retrain.pid
```

Background it so the calling shell isn't blocked. PID file lets you tail or kill if it hangs.

- [ ] **Step 3: Watch the log until completion.**

```bash
tail -f /tmp/retrain_v8_weighted.log
```

Wait for the final `[INFO] Saved bundle → backend/models/panns_head.joblib` (or whatever the training script prints on success — the file mtime jumping is the unambiguous signal). Ctrl-C the tail when done.

If after 30 minutes there's no progress past `Training HistGradientBoostingClassifier head …`, the process may be stuck — `kill $(cat /tmp/retrain.pid)` and investigate (`top` for CPU, `vmmap` for memory).

- [ ] **Step 4: Confirm bundle was rewritten and HistGB log line is present.**

```bash
ls -la backend/models/panns_head.joblib
grep "HistGB trained with sample_weight=balanced" /tmp/retrain_v8_weighted.log
```

Expected: mtime is from the current run (newer than 16:08), and the grep returns one line showing the `sw min/max` values. If the grep returns nothing, the code path didn't fire — STOP and investigate before scoring against a bundle that may be unweighted.

---

## Task 2: Evaluate new bundle + apply D5 acceptance gate

**Files:** none modified

- [ ] **Step 1: Run eval with the bootstrap-CI-aware script.**

```bash
venv/bin/python scripts/eval_acoustic.py 2>&1 | tee /tmp/eval_v8_weighted.log
```

Eval reuses the deterministic 80/10/10 split + cached embeddings, so this is ~30 s on the test fold. The CI columns in the output table (added by the uncommitted `scripts/eval_acoustic.py` change) are the inputs to the D5 gate.

- [ ] **Step 2: Apply the D5 gate.**

Read `/tmp/eval_v8_weighted.log` for the `per-class F1` table. The CI bounds appear as `[lo, hi]` next to each row. Specifically:

- Find the `Beetle` row → record its `lo` (e.g. `Beetle  ... [0.652, 0.812]` → `lo=0.652`).
- Find the `macro_f1` row → record its `lo`.

Decision:

| Beetle lo | macro lo | Outcome |
|---|---|---|
| ≥ 0.65 | ≥ 0.74 | **PASS** → go to Task 3a |
| else | else | **FAIL** → go to Task 3b |

Surface the actual numbers to the user before proceeding — D5 is the only place we deliberately leave the rails for a model regression, and the user should see the numbers regardless of outcome.

---

## Task 3a: PASS branch — atomic commit of bundle + baseline + eval + tests

**Only run if Task 2 decided PASS. Skip to Task 3b otherwise.**

**Files:** `backend/models/panns_baseline.json` (overwrite), commits 4 paths.

- [ ] **Step 1: Write new baseline from the weighted-bundle eval run.**

```bash
venv/bin/python scripts/eval_acoustic.py --write-baseline
```

Expected: log line `Wrote baseline → backend/models/panns_baseline.json`. The new JSON has `macro_f1`, `macro_f1_ci95`, `per_class_f1`, `per_class_f1_ci95`, fresh `confusion_matrix`, fresh `trained_at`, fresh `dataset_fingerprint`.

- [ ] **Step 2: Sanity-spot-check the new baseline file.**

```bash
venv/bin/python -c "
import json
b = json.load(open('backend/models/panns_baseline.json'))
print('macro_f1', b['macro_f1'])
print('macro_f1_ci95', b['macro_f1_ci95'])
print('Beetle', b['per_class_f1']['Beetle'], 'CI', b['per_class_f1_ci95']['Beetle'])
print('Wasp', b['per_class_f1']['Wasp'], 'CI', b['per_class_f1_ci95']['Wasp'])
print('Locust', b['per_class_f1']['Locust'], 'CI', b['per_class_f1_ci95']['Locust'])
"
```

Confirm: 8 classes still present in `per_class_f1`, both `*_ci95` fields are populated (not null, not missing). If `macro_f1_ci95` is missing → `write_baseline()` change didn't fire → STOP.

- [ ] **Step 3: Re-run all relevant tests one final time.**

```bash
venv/bin/python -m pytest tests/test_eval_bootstrap.py tests/test_panns_model.py -q
```

Expected: all pass.

- [ ] **Step 4: Atomic commit (bundle + baseline + eval + tests in one commit).**

```bash
git add backend/models/panns_head.joblib \
        backend/models/panns_baseline.json \
        scripts/eval_acoustic.py \
        tests/test_eval_bootstrap.py
git status --short
```

Expected status before commit: 4 files staged (M for joblib + json + eval, A for new test), nothing else.

```bash
git commit -m "feat(acoustic): retrained bundle + bootstrap CIs in eval

D1 retrain with HistGB sample_weight=balanced, gated through
D5 (Beetle F1 lower-CI >= 0.65, macro_f1 lower-CI >= 0.74).
Replaces backend/models/panns_baseline.json with new floor
including per-class and macro F1 95% CIs."
```

- [ ] **Step 5: Skip Task 3b — jump to Task 4.**

---

## Task 3b: FAIL branch — rollback bundle, commit eval-only changes

**Only run if Task 2 decided FAIL. Skip if Task 3a ran.**

**Files:** `backend/models/panns_head.joblib` (restore), `backend/models/panns_baseline.json` (overwrite against unweighted bundle), commits 3 paths.

- [ ] **Step 1: Restore the unweighted bundle from snapshot.**

```bash
cp /tmp/panns_head_v8_unweighted.bak backend/models/panns_head.joblib
shasum /tmp/panns_head_v8_unweighted.bak backend/models/panns_head.joblib
```

Expected: sha sums match (sanity that the cp succeeded).

- [ ] **Step 2: Re-run eval against the restored unweighted bundle to confirm it's the prior state.**

```bash
venv/bin/python scripts/eval_acoustic.py 2>&1 | tail -30
```

Expected: macro_f1 ≈ 0.776 (the current committed baseline). If it differs by more than ±0.005, the rollback is wrong somehow — STOP.

- [ ] **Step 3: Re-write baseline so it now contains the CI fields for the unweighted bundle.**

```bash
venv/bin/python scripts/eval_acoustic.py --write-baseline
```

The point estimates should be ~identical to what's already in the file; the new fields `macro_f1_ci95` and `per_class_f1_ci95` are the only structural change.

- [ ] **Step 4: Tests one final time.**

```bash
venv/bin/python -m pytest tests/test_eval_bootstrap.py tests/test_panns_model.py -q
```

Expected: all pass.

- [ ] **Step 5: Revert the T1 training-script commit so the tree no longer claims weighted-HistGB-but-unweighted-bundle.**

```bash
git revert --no-edit 5c660e4
```

This creates a new commit that undoes the `sample_weight=balanced` line. Better than `git reset` because main is shared-history-clean — we add a revert commit on top instead of rewriting.

- [ ] **Step 6: Commit baseline + eval + tests (bundle is unchanged from origin/main now).**

```bash
git add backend/models/panns_baseline.json scripts/eval_acoustic.py tests/test_eval_bootstrap.py
git status --short
```

Expected: 3 files staged. NOT `backend/models/panns_head.joblib` (it's unchanged from origin/main now that we reverted T1).

```bash
git commit -m "feat(acoustic): bootstrap CIs in eval + baseline

D3 only — D1 retrain failed D5 acceptance gate and was rolled back
(see Task 3b commit body for the Beetle/macro CI numbers that
triggered the rollback). D2 (per-class abstain, a73da67) stays
shipped because it's independent of the bundle."
```

Replace the parenthetical with the actual Beetle lo + macro lo numbers from Task 2 Step 2 so the commit body is self-explanatory.

---

## Task 4: Multi-clip smoke harness — Makefile target + first run + commit

**Files:** `Makefile` (create), commits `Makefile` + `scripts/smoke_acoustic.py`.

`scripts/smoke_acoustic.py` is already written (verified: it imports `backend.auth.issue_token`, stratified-samples 5 clips/class with `random.seed(42)`, POSTs each via `requests`, scores top1/top3/conf_range, exits non-zero on top-3 floor).

- [ ] **Step 1: Create `Makefile` at repo root.**

```makefile
.PHONY: smoke-acoustic

smoke-acoustic:
	@venv/bin/uvicorn backend.main:app --port 8000 --log-level warning > /tmp/uvicorn-smoke.log 2>&1 & \
	echo $$! > /tmp/uvicorn-smoke.pid; \
	sleep 4; \
	venv/bin/python scripts/smoke_acoustic.py; rc=$$?; \
	kill $$(cat /tmp/uvicorn-smoke.pid) 2>/dev/null; \
	rm -f /tmp/uvicorn-smoke.pid; \
	exit $$rc
```

Tabs (not spaces) on the indented lines — Make will refuse the target otherwise.

- [ ] **Step 2: Run smoke once to seed the expectations log.**

```bash
make smoke-acoustic 2>&1 | tee /tmp/smoke_v8.log
```

Expected: per-class table prints 8 rows. Gate: `top3_hit >= 3/5` for every class (the script exits non-zero otherwise). Tabulate the actual hit-rates and confidence ranges; surface to user.

If smoke FAILS on a class that the eval thinks is healthy (e.g. eval Cricket F1 = 0.82 but smoke top3 = 1/5), that's a real bug → STOP and investigate (mismatch between eval test-fold and `data/audio_samples/<cls>/*.wav` random clips, or a routing-layer bug in `backend/services/acoustic/pipeline.py`).

If smoke FAILS on a class where the eval is also weak (e.g. Wasp), record the numbers and surface to user — they may want to accept the failure as a known limitation, or to drop the `--strict` floor.

- [ ] **Step 3: Commit smoke harness + Makefile.**

```bash
git add Makefile scripts/smoke_acoustic.py
git commit -m "feat(acoustic): multi-clip smoke harness (5/class)

scripts/smoke_acoustic.py POSTs 5 stratified clips per class to
/api/acoustic/analyze, reports top1/top3 hits + confidence range,
and exits non-zero on a top-3 floor (3/5 per class).
'make smoke-acoustic' starts uvicorn, runs the harness, tears down."
```

---

## Task 5: Reviewer subagent + push

- [ ] **Step 1: Dispatch a code-review subagent over the 3-4 new commits.**

Branch is now 4 (PASS) or 5 (FAIL, +revert) commits ahead of `origin/main`. Use whichever review template the prior plan's T7 used — or, if not memory-resident, dispatch a general-purpose agent with this prompt:

```
Review the commits between origin/main and HEAD on this repo. Focus
on (a) whether the D5 acceptance gate decision recorded in commit
messages aligns with the per-class numbers in
backend/models/panns_baseline.json, (b) whether the per-class
abstain helper is correctly used at the only decision point in both
panns_model.py and yamnet_model.py, (c) whether the bootstrap_ci
helper is deterministic across runs (a baseline rewrite flapping on
identical input would be a regression). Flag anything that needs
fixing before push. Under 300 words.
```

- [ ] **Step 2: Present the subagent's report to the user. WAIT for explicit "push" / "ship" / "yes" before continuing.**

If the reviewer flags issues, address them in new commits (not amends) and re-dispatch. Do not push without explicit go-ahead.

- [ ] **Step 3: Push.**

```bash
git push origin main
```

The pre-push hook gates on `scripts/eval_acoustic.py` → no macro regression. After T3a's `--write-baseline`, the baseline IS the new bundle's metrics so the hook should pass trivially. After T3b's rollback + revert, the bundle on disk matches the baseline file's prior-bundle metrics ± bootstrap noise, so it should also pass.

If the hook blocks the push, read the hook's diff output and decide with the user: was the regression real, or is the tolerance too tight given the new CIs? Don't `--no-verify`.

---

## Verification (end-to-end, after Task 5)

1. `git log origin/main..HEAD` → empty (push succeeded).
2. `venv/bin/python scripts/eval_acoustic.py` → `PASS — no regression beyond tolerance`; CIs printed for all 8 classes; baseline file contains both `macro_f1_ci95` and `per_class_f1_ci95`.
3. `venv/bin/python -m pytest tests/test_panns_model.py tests/test_eval_bootstrap.py -q` → all pass.
4. `make smoke-acoustic` → all 8 classes report `top3_hit ≥ 3/5`; backend cleaned up afterwards (`pgrep -f 'uvicorn backend.main:app'` returns nothing).
5. Per-class abstain probe (sanity, no model load):
   ```bash
   venv/bin/python -c "
   from backend.ml.panns_model import _abstain_threshold as p
   from backend.ml.yamnet_model import _abstain_threshold as y
   assert p('Locust') == p('Wasp') == y('Locust') == y('Wasp') == 0.35
   assert p('Bee') == y('Bee') == 0.45
   print('per-class abstain consistent across panns + yamnet')"
   ```

## Critical files

- `scripts/train_panns_head.py` (T1 already-committed code change, retrain target)
- `scripts/eval_acoustic.py` (T3, uncommitted modification)
- `scripts/smoke_acoustic.py` (T4, untracked)
- `tests/test_eval_bootstrap.py` (T3, untracked)
- `backend/models/panns_head.joblib` (T1 output, T3a or T3b)
- `backend/models/panns_baseline.json` (T3 output)
- `Makefile` (T4, create)
- `/tmp/panns_head_v8_unweighted.bak` (rollback snapshot — DO NOT delete until after push)

## Rollback procedure (if the new bundle breaks production post-push)

Only the bundle-touching commit (Task 3a or 3b) needs reverting — D2 (abstain) and D4 (smoke) are independent improvements and should stay.

```bash
# 1. Find the commit that wrote the new bundle:
git log --oneline -- backend/models/panns_head.joblib | head -3
# 2. Restore bundle from snapshot:
cp /tmp/panns_head_v8_unweighted.bak backend/models/panns_head.joblib
# 3. Re-baseline against the restored bundle:
venv/bin/python scripts/eval_acoustic.py --write-baseline
# 4. New commit (do NOT git revert the prior commit — the bundle file is
#    binary and reverts on binaries can produce confusing diffs; just
#    commit the new restored state forward):
git add backend/models/panns_head.joblib backend/models/panns_baseline.json
git commit -m "revert(acoustic): restore unweighted v8 bundle"
git push origin main
```

The `.bak` is the source of truth for "what was running before this plan touched anything." Do not delete it until production has been observed stable on the new bundle for at least a day.

## Honest risk register

| Risk | Probability | Mitigation in plan |
|---|---|---|
| Retrain dies again mid-flight | Med (it died once) | Background + pid file + explicit kill instructions in Task 1.3 |
| D5 FAILs (Beetle doesn't recover) | Med (~40%, per the original plan estimate) | Task 3b rollback path is fully spelled out |
| Pre-push hook blocks push | Low | After `--write-baseline` against new bundle, hook should pass; if it blocks, surface diff to user |
| Smoke fails on a class eval thought was healthy | Low-Med | Task 4.2 STOP-and-investigate clause |
| `make` not installed / wrong tab vs spaces in Makefile | Low | Task 4.1 calls out tabs; if `make` missing, the smoke can be run manually (2-step: start uvicorn, then `python scripts/smoke_acoustic.py`) |
| Orphan uvicorn from a previous smoke run | Low | Task 4.1 Makefile target writes pid file + kills on exit; if a stale one exists, `pkill -f 'uvicorn backend.main:app'` |

## Out of scope (intentionally deferred)

- New data collection (`docs/superpowers/plans/2026-05-24-phase-c-prime-data-lift.md`)
- Backbone replacement (issue #11, blocked on labeled field audio)
- Field-audio test fold from `data/feedback_clips/` (needs decrypt + label tooling)
- CI-aware no-regression gate (point-estimate `tolerance_macro_f1` stays this plan)
- k-fold cross-validation
- Touching the untracked `docs/superpowers/plans/2026-05-24-*.md` planning docs or `scripts/probe_tta.py` (prior-session artifacts; leave alone or commit in a separate session)
