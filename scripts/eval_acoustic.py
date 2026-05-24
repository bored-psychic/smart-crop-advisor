"""
Phase B — held-out eval harness for the PANNs acoustic head.

Reproduces the deterministic 80/10/10 stratified split from
``scripts/train_panns_head.py`` and re-scores the saved
``backend/models/panns_head.joblib`` on the **test fold only**. Compares
against ``backend/models/panns_baseline.json`` and exits non-zero if
macro-F1 drops more than the recorded tolerance.

USAGE
-----
    # First-time seeding (after a deliberate model update):
    SSL_CERT_FILE=$(python -c "import certifi; print(certifi.where())") \\
        python scripts/eval_acoustic.py --write-baseline

    # No-regression check (CI default):
    SSL_CERT_FILE=$(python -c "import certifi; print(certifi.where())") \\
        python scripts/eval_acoustic.py

Wire into CI as a gate on PRs touching:
    - backend/models/panns_head.joblib
    - backend/ml/panns_model.py
    - backend/services/acoustic/*
    - scripts/train_panns_head.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix, f1_score,
)
from sklearn.model_selection import train_test_split

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Reuse training-time constants + cache loader so the eval reads the exact
# same features the head was trained on. Importing from the training script
# is the source-of-truth pattern — if WINDOW_SECONDS / CACHE_VERSION ever
# change, the eval automatically tracks.
from scripts.train_panns_head import (  # noqa: E402
    LABEL_REMAP, cached_embed, collect_clip_paths, load_panns,
)

MODEL_PATH = REPO_ROOT / "backend" / "models" / "panns_head.joblib"
BASELINE_PATH = REPO_ROOT / "backend" / "models" / "panns_baseline.json"

# 0.5 percentage-point macro-F1 regression bar. Tight enough to catch real
# regressions, loose enough to absorb LogisticRegression's non-determinism
# across BLAS implementations.
DEFAULT_TOL = 0.005

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("eval_acoustic")


def reproduce_test_indices(n_clips: int, y_enc: np.ndarray) -> np.ndarray:
    """Return the test-fold indices from train_panns_head's 80/10/10 split.

    The training script first peels off 10% as test (random_state=42,
    stratified), then splits the remaining 90% into train/val with
    test_size=0.111. We only need the first split here.
    """
    idx_all = np.arange(n_clips)
    _, idx_test = train_test_split(
        idx_all, test_size=0.10, random_state=42, stratify=y_enc,
    )
    return idx_test


def dataset_fingerprint(paths) -> str:
    """SHA-256 of sorted (species_dir_name, clip_stem) pairs.

    If clips are added/removed/renamed, the deterministic split shifts and
    the test fold is no longer the one the head was trained against. The
    fingerprint lets the eval *detect* that drift instead of silently
    scoring on a different test set.
    """
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(f"{p.parent.name}/{p.stem}".encode())
    return h.hexdigest()


def evaluate(bundle, paths, idx_test, tagger):
    """Score the saved head on the test fold and return a metrics dict."""
    clf = bundle["clf"]
    le = bundle["label_encoder"]
    classes = list(bundle["classes"])

    # Re-encode labels with the *saved* encoder so class indices match the
    # ones the head learned. Skip any clip whose class is not in the head
    # (e.g. dataset gained a new species since training).
    X_rows, y_rows = [], []
    n_skip_class = n_skip_embed = 0
    for i in idx_test:
        path = paths[i]
        label = path.parent.name
        # Apply the same pooling the training script applies. Source of
        # truth is LABEL_REMAP in scripts/train_panns_head.py — if it goes
        # back to {} (unpool), Wasp/Locust stay distinct in y_test and the
        # head is scored on the 8-class label space it was actually trained
        # on. Hardcoding the old {Wasp→Bee, Locust→Grasshopper} dict here
        # caused a silent 6-class scoring bug.
        pooled = LABEL_REMAP.get(label, label)
        if pooled not in classes:
            n_skip_class += 1
            continue
        v = cached_embed(tagger, path, aug_id="clean")
        if v is None:
            n_skip_embed += 1
            continue
        X_rows.append(v)
        y_rows.append(int(le.transform([pooled])[0]))

    if n_skip_class:
        log.warning("Skipped %d test clips: class not in saved head", n_skip_class)
    if n_skip_embed:
        log.warning("Skipped %d test clips: embedding failed", n_skip_embed)

    X_test = np.vstack(X_rows)
    y_test = np.array(y_rows)
    y_pred = clf.predict(X_test)

    present = np.unique(y_test)
    per_class_f1 = f1_score(y_test, y_pred, average=None, labels=present)
    per_class_named = {
        classes[int(c)]: float(s) for c, s in zip(present, per_class_f1)
    }
    return {
        "n_test": int(len(y_test)),
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "macro_f1": float(f1_score(y_test, y_pred, average="macro", labels=present)),
        "per_class_f1": per_class_named,
        "confusion_matrix": confusion_matrix(y_test, y_pred, labels=present).tolist(),
        "labels_in_test": [classes[int(c)] for c in present],
        "report": classification_report(
            y_test, y_pred,
            labels=present,
            target_names=[classes[int(c)] for c in present],
            zero_division=0,
        ),
    }


def compare_to_baseline(metrics: dict, baseline: dict, tol: float) -> bool:
    base_acc = baseline["accuracy"]
    base_macro = baseline["macro_f1"]
    dacc = metrics["accuracy"] - base_acc
    dmacro = metrics["macro_f1"] - base_macro
    log.info("=" * 64)
    log.info("BASELINE COMPARISON  (tolerance: %.4f macro-F1)", tol)
    log.info("                       baseline   current    delta")
    log.info("  accuracy             %.4f     %.4f     %+.4f",
             base_acc, metrics["accuracy"], dacc)
    log.info("  macro_f1             %.4f     %.4f     %+.4f",
             base_macro, metrics["macro_f1"], dmacro)
    log.info("  per-class F1:")
    base_pcf = baseline.get("per_class_f1", {})
    for cls in sorted(set(metrics["per_class_f1"]) | set(base_pcf)):
        bf = base_pcf.get(cls)
        cf = metrics["per_class_f1"].get(cls)
        if bf is None:
            log.info("    %-18s   ——         %.4f     (new class)", cls, cf)
        elif cf is None:
            log.info("    %-18s   %.4f     ——         (missing)", cls, bf)
        else:
            log.info("    %-18s   %.4f     %.4f     %+.4f", cls, bf, cf, cf - bf)
    log.info("=" * 64)
    return dmacro >= -tol


def write_baseline(metrics: dict, bundle: dict, fingerprint: str) -> None:
    payload = {
        "accuracy": metrics["accuracy"],
        "macro_f1": metrics["macro_f1"],
        "per_class_f1": metrics["per_class_f1"],
        "confusion_matrix": metrics["confusion_matrix"],
        "labels_in_test": metrics["labels_in_test"],
        "n_test": metrics["n_test"],
        "head_name": bundle["head_name"],
        "temperature": float(bundle["temperature"]),
        "feature_dim": int(bundle["feature_dim"]),
        "classes": list(bundle["classes"]),
        "trained_at": bundle["trained_at"],
        "dataset_fingerprint": fingerprint,
        "tolerance_macro_f1": DEFAULT_TOL,
    }
    BASELINE_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    log.info("Wrote baseline → %s", BASELINE_PATH)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-clips", type=int, default=20,
                    help="Minimum clips per species — must match training")
    ap.add_argument("--tolerance", type=float, default=None,
                    help="Override baseline.json tolerance_macro_f1")
    ap.add_argument("--write-baseline", action="store_true",
                    help="Persist current metrics as the new baseline. "
                         "Use only after a deliberate model update.")
    args = ap.parse_args()

    if not MODEL_PATH.exists():
        log.error("Missing %s — run scripts/train_panns_head.py first.", MODEL_PATH)
        return 2

    bundle = joblib.load(MODEL_PATH)
    paths, labels, _ = collect_clip_paths(args.min_clips)
    # Encode labels exactly the way training did, so the split's stratify
    # vector matches and idx_test resolves to the same clips.
    le = bundle["label_encoder"]
    pooled = [LABEL_REMAP.get(l, l) for l in labels]
    # If a class appears in the dataset that isn't in the saved encoder,
    # encode it as -1 so it goes into stratify without colliding with real
    # classes — the per-clip filter in evaluate() drops these later.
    known = set(le.classes_)
    y_enc = np.array([
        int(le.transform([p])[0]) if p in known else -1
        for p in pooled
    ])
    idx_test = reproduce_test_indices(len(paths), y_enc)
    fingerprint = dataset_fingerprint(paths)

    tagger = load_panns()
    metrics = evaluate(bundle, paths, idx_test, tagger)
    log.info("\n%s", metrics["report"])
    log.info("Test accuracy: %.4f  Macro F1: %.4f  (n=%d)",
             metrics["accuracy"], metrics["macro_f1"], metrics["n_test"])

    if args.write_baseline:
        write_baseline(metrics, bundle, fingerprint)
        return 0

    if not BASELINE_PATH.exists():
        log.error("Missing %s — run with --write-baseline to create it.",
                  BASELINE_PATH)
        return 2

    baseline = json.loads(BASELINE_PATH.read_text())

    if baseline.get("dataset_fingerprint") not in (None, fingerprint):
        log.warning(
            "Dataset fingerprint drift (baseline=%s, current=%s) — the "
            "deterministic test fold may have shifted. Re-baseline after "
            "the next training run.",
            baseline["dataset_fingerprint"][:12], fingerprint[:12],
        )

    tol = args.tolerance if args.tolerance is not None else baseline.get(
        "tolerance_macro_f1", DEFAULT_TOL
    )
    ok = compare_to_baseline(metrics, baseline, tol)
    if ok:
        log.info("PASS — no regression beyond tolerance.")
        return 0
    log.error("FAIL — macro_f1 regressed by more than %.4f", tol)
    return 1


if __name__ == "__main__":
    sys.exit(main())
