# A1 Acoustic Pre-filter — Handoff

**Status:** Implementation complete, awaiting re-train + re-baseline + ship decision.
**Branch:** `feat-acoustic-prefilter` (worktree at `.claude/worktrees/feat-orthoptera-cicada-gate/`)
**Spec:** `/Users/kiyo/.claude/plans/merry-chasing-brooks.md`
**Date:** 2026-05-26

## What A1 is

Bandpass 1–15 kHz (Butterworth order 4, zero-phase `sosfiltfilt`) + per-channel energy normalization (RMS → 1, peak-aware scale-down to fit `[-1, 1]`, no hard clip). Applied identically in PANNs inference and training paths. Feature-flagged via `ENABLE_BANDPASS_FILTER` env var. Default **off**.

The flag is **not** a pydantic `Settings` field — it's read directly from `os.environ` by `backend.services.acoustic.dsp.bandpass_filter_enabled()` so the hot path and tests don't pay the cost of full `Settings` instantiation (which requires `API_KEY` / `JWT_SECRET` / etc.).

## Files modified (uncommitted on `feat-acoustic-prefilter`)

| File | Change |
|---|---|
| `backend/services/acoustic/dsp.py` | New: `bandpass_and_energy_normalize()`, `bandpass_filter_enabled()` |
| `backend/config.py` | Doc comment for the env var (no `Settings` field) |
| `backend/ml/panns_model.py` | Wired in `PANNsBundle.predict()` after `_resample_to_32k`, before CNN14 |
| `scripts/train_panns_head.py` | Wired in `cached_embed()` post-augmentation; `CACHE_VERSION` bumped to `v3-bandpass1-15k-norm-…` |
| `tests/test_acoustic_dsp_bandpass.py` | New: 12 unit tests (attenuation, in-band preservation, DC removal, RMS consistency, dtype, silence safety, flag reader) |

**Tests passing:** `pytest tests/test_acoustic*.py tests/test_panns_model.py tests/test_cicada_ortho_boundary_abstain.py` → 91 passed.

## Plan deviations to be aware of

1. **Env var name:** plan said `SCA_ENABLE_BANDPASS_FILTER`, shipped as `ENABLE_BANDPASS_FILTER` (matches project convention — no `SCA_` prefix used elsewhere).
2. **Settings field:** plan said `enable_bandpass_filter: bool = False` in `Settings`. Did not add it — instantiating `Settings` in tests/training fails without the full boot env. Doc comment only.
3. **Insertion point in inference:** plan said wire into `_decode_audio` after `_normalize_lufs()` in `pipeline.py`. Wired into `PANNsBundle.predict()` after `_resample_to_32k` instead. Reason: doing it in `_decode_audio` would have polluted the `MIN_RMS=1e-4` silence check (`pipeline.py:184`) and the `_band_energies` 50–200 Hz diagnostic (which intentionally measures the sub-1 kHz band the filter is meant to remove). The PANNs path is the only consumer that should see filtered audio.
4. **`eval_acoustic.py --bootstrap-ci`:** plan referenced this flag; it does not exist. The script computes Wilson CIs unconditionally and writes them via `--write-baseline`. See workflow below.

## What you need to run

All commands assume cwd = `/Users/kiyo/smart-crop-advisor/.claude/worktrees/feat-orthoptera-cicada-gate/` and your acoustic venv is active.

### Step 1 — Commit the implementation

So the lineage is clean (one commit = A1 implementation, separate from re-baseline and ship decision):

```bash
git add backend/services/acoustic/dsp.py backend/config.py backend/ml/panns_model.py \
        scripts/train_panns_head.py tests/test_acoustic_dsp_bandpass.py
git commit -m "feat(acoustic): A1 pre-filter — bandpass 1-15kHz + energy norm (flag off)"
```

### Step 2 — Back up the flag-off state (rollback safety)

Re-training overwrites `panns_head.joblib`. Save the current model + baseline:

```bash
cp backend/models/panns_head.joblib backend/models/panns_head.flag_off.joblib
cp backend/models/panns_baseline.json backend/models/panns_baseline.flag_off.json
```

### Step 3 — Re-train with flag on (~1h local, full cache rebuild)

`CACHE_VERSION` was bumped so the v2 cache is ignored; every embedding rebuilds with the pre-filter applied:

```bash
ENABLE_BANDPASS_FILTER=true python scripts/train_panns_head.py
```

### Step 4 — Capture the flag-on baseline

`eval_acoustic.py --write-baseline` overwrites `panns_baseline.json`. Run it under the flag, then move the file aside so the comparison has both:

```bash
ENABLE_BANDPASS_FILTER=true python scripts/eval_acoustic.py --write-baseline
mv backend/models/panns_baseline.json backend/models/panns_baseline_bandpass.json
cp backend/models/panns_baseline.flag_off.json backend/models/panns_baseline.json
```

Now `panns_baseline.json` holds the pre-A1 numbers (so existing tests/tolerance checks compare against the right thing) and `panns_baseline_bandpass.json` holds the A1 numbers.

### Step 5 — Write the comparison doc

`docs/superpowers/results/2026-05-26-acoustic-prefilter/A1_baseline_diff.md` should contain:

- Side-by-side macro-F1 (mean + 95% CI) from both JSONs
- Per-class F1 + 95% CI from both JSONs
- Macro-F1 delta (signed)
- For each class: does the A1 lower CI bound stay above `(flag_off_lower_bound − 1 × flag_off_half_width)`? (the regression guard)
- Held-out probe results — see Step 6

### Step 6 — Held-out probe (recommended, given the bee/beetle lesson)

The bee/beetle pivot (commit `134e8eb`, 2026-05-26) saw a 12.3% test-fold confusion cell collapse to 1.1% on held-out audio. Don't trust test-fold-only deltas. Re-run the relevant held-out probes from `data/_holdout_probes/` (if scaffolded) or pull a fresh 5/class held-out set from xeno-canto and re-score with both heads. Document in the comparison doc.

### Step 7 — Ship decision (hybrid rigor)

**Ship** (flip flag default to `True` in a follow-up commit) **only if all hold:**
- Macro-F1 mean improves (A1 > flag-off), AND
- No per-class F1 drops more than 1 CI half-width below the flag-off lower bound, AND
- Held-out probe does not contradict the test-fold trend.

**Revert** if macro-F1 regresses OR any per-class drops > 1 CI half-width OR held-out contradicts.

**Investigate** (borderline) before deciding: try variants (0.5–18 kHz, 2–12 kHz), or check confounder-gate interaction at `backend/ml/panns_model.py:238–320` — abstain gates were tuned against unfiltered embeddings and may behave differently.

### Step 8a — If shipping

```bash
# Flip default in code: add ENABLE_BANDPASS_FILTER=true to .env, or change the
# default branch in bandpass_filter_enabled() to True.
git add .env  # or whichever file you flipped
git commit -m "feat(acoustic): A1 pre-filter — flip default ON after baseline lift"

# Smoke test (5/clip-per-class harness from commit 32a41d6):
ENABLE_BANDPASS_FILTER=true make acoustic-smoke
```

Then update `backend/models/panns_baseline.json` to the A1 numbers so the eval-CI gate has a current reference:

```bash
cp backend/models/panns_baseline_bandpass.json backend/models/panns_baseline.json
git add backend/models/panns_baseline.json backend/models/panns_baseline_bandpass.json
git commit -m "baseline(acoustic): adopt A1 pre-filter baseline as primary"
```

### Step 8b — If reverting

```bash
cp backend/models/panns_head.flag_off.joblib backend/models/panns_head.joblib
# Leave the code in place (flag still defaults off — A1 is dormant).
# Write a NULL_RESULT.md next to A1_baseline_diff.md documenting what was tried.
```

## Open questions / known unknowns

- **LUFS interaction:** energy norm after LUFS partially undoes LUFS's loudness work for the PANNs path (LUFS still applies to other consumers via `_decode_audio`). If A1 underperforms, try dropping LUFS just on the PANNs path — was added for the older YAMNet pipeline.
- **Sample rate:** pre-filter runs at 32 kHz (CNN14 native), so the 15 kHz upper edge sits at ~94% of Nyquist — Butterworth roll-off is tight there. Tests assert > 20 dB relative attenuation at 15.5–16 kHz (looser than the > 40 dB sub-kHz bound for this reason).
- **A2 (Locust→Acrididae vocabulary collapse):** deferred — kept Locust separate per the deliberate prior decision at commit `10d2b5b` (`scripts/train_panns_head.py:94–100`); SWARM hotline routing differs from routine spray. Revisit only if post-A1 confusion matrix shows material Locust↔Grasshopper leak.
- **A3 (PANNs → BirdNET backbone swap):** still data-blocked per `project_yamnet_roadmap.md` — needs ≥100 labels/species from the #13 active-learning loop.
- **Gate retirement** (`CICADA_ORTHO_BOUNDARY_*`, Locust 0.35 abstain threshold): may become dead code after A1. Decide on post-A1 firing rates — retire if < 1%.

## Context for the next agent

The two previous abstain-gate experiments (`feat-orthoptera-cicada-gate` Branch A, `feat-bee-beetle-pivot` Branch C) were both falsified on held-out probes. The pattern: test-fold confusion cells were small-fold artifacts; gates tuned against them did nothing for real-world audio. A1 is the deliberate pivot from layer-4 polish (gates) to layer-1 (SNR / pre-processing). It has positive externality — lifts every class simultaneously rather than trading one class against another — and is a precondition for any future A3 backbone swap since it changes the input distribution.

Don't get clever. Run the steps above in order. Trust the held-out probe over the test-fold delta. If the comparison doc says revert, revert without negotiating.
