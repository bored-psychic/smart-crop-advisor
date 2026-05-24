"""
Train a small classifier head on top of PANNs CNN14 embeddings.

Pipeline
--------
1. Walk data/audio_samples/<species>/*.wav (built by fetch_audio_dataset.py).
2. For each clip:
     - resample to 32 kHz mono
     - chunk into 2 s windows with 1 s hop, run CNN14 on the batch
     - mean-pool the per-window 2048-d embeddings and 527-d AudioSet clipwise
       outputs, concatenate → 2575-d feature
     - cache the feature under ~/panns_data/embeddings_cache/ (keyed by
       species, stem, augmentation id, and CACHE_VERSION)
3. Stratified 80/10/10 split (train / val / test).
4. Fit LogisticRegressionCV (sweeps C ∈ {0.01 .. 100}). Temperature-scale on
   val. MLP escalation was dropped — it never won on these embeddings.
5. Save bundle to backend/models/panns_head.joblib with the trained head,
   label encoder, accuracy + macro-F1, confusion matrix, temperature, and
   CACHE_VERSION / window params so backend/ml/panns_model.py can sanity-check
   feature_dim at load time.
6. Exit 1 if final test accuracy < --accuracy-floor (default 0.85).

USAGE
-----
    SSL_CERT_FILE=$(python3 -c "import certifi; print(certifi.where())") \\
        python3 scripts/train_panns_head.py
    python3 scripts/train_panns_head.py --min-clips 50
    python3 scripts/train_panns_head.py --accuracy-floor 0.80
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import logging
import os
import sys
from pathlib import Path

import joblib
import librosa
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegressionCV
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix, f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# Pickle-stable location for the ensemble wrapper — defined in backend/ml so
# joblib can unpickle the bundle at runtime without depending on scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.ml.panns_model import SoftVoteEnsemble  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("train_panns")

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "audio_samples"
MODEL_OUT = REPO_ROOT / "backend" / "models" / "panns_head.joblib"
EMBED_CACHE_DIR = Path(os.path.expanduser("~/panns_data/embeddings_cache"))

SAMPLE_RATE = 32000  # CNN14's required input rate

# Mirror the inference-time aggregation in backend/ml/panns_model.py so the
# trained head and the deployed model see embeddings drawn from the same
# distribution. 2 s window / 1 s hop gives ≥ 2× temporal overlap on the
# typical 4 – 10 s training clips and still fits short (~2 s) clips.
WINDOW_SECONDS = 2.0
HOP_SECONDS = 1.0

# Bump if the windowing/feature-extraction code changes — cached embeddings
# only encode the logic of whichever CACHE_VERSION wrote them.
CACHE_VERSION = "v2-window2.0-hop1.0-clipwise-concat"

# Augmentation variants applied to **training clips only** (val/test stay
# clean — we measure generalization, not augmentation-fit). Each variant
# gets its own cache entry keyed by aug_id so re-tunes of the head reuse
# previously generated augmentations.
#   - "stretch": librosa.effects.time_stretch(rate ∈ U(0.92, 1.08)) —
#     preserves pitch (insect species identity is pitch-encoded).
#   - "noise":   additive Gaussian noise at SNR ∈ U(15, 25) dB — simulates
#     field-recording hiss / wind without overwhelming the source signal.
# NO pitch-shift: cicada vs cricket are largely pitch-distinguished, so
# perturbing pitch corrupts the label.
AUG_VARIANTS_TRAIN = ("clean", "stretch", "noise")
AUG_VARIANTS_EVAL = ("clean",)

# Empty: every collected species trains as its own class. Locust and
# Grasshopper are acoustically similar (gregarious-phase grasshoppers
# stridulate the same way) but the treatment-advice gap is large enough
# that the user prefers two noisy classes over one tidy aggregate —
# locust events trigger State-level escalation while grasshoppers get
# routine field spraying.
LABEL_REMAP: dict[str, str] = {}


def _slug_to_species(slug: str) -> str:
    """Inverse of fetch_audio_dataset._slug — Moth_Butterfly → Moth/Butterfly."""
    return slug.replace("Moth_Butterfly", "Moth/Butterfly").replace("_", " ")


def load_panns():
    """Lazy import keeps `import` cheap and surfaces install errors at use time."""
    from panns_inference import AudioTagging
    log.info("Loading CNN14 via panns_inference (CPU) …")
    return AudioTagging(checkpoint_path=None, device="cpu")


def _windows(pcm: np.ndarray) -> np.ndarray:
    """Stack `pcm` into (N, win) windows. Pads/repeats clips shorter than one
    window. CNN14 needs ≥ 1024 samples for its STFT; 2 s @ 32 kHz = 64000."""
    win = int(WINDOW_SECONDS * SAMPLE_RATE)
    hop = int(HOP_SECONDS * SAMPLE_RATE)
    if pcm.size < win:
        # Repeat then trim so short clips still see a full window.
        repeats = (win + pcm.size - 1) // pcm.size
        pcm = np.tile(pcm, repeats)[:win]
        return pcm.astype(np.float32, copy=False).reshape(1, win)
    n = 1 + (pcm.size - win) // hop
    return np.stack([pcm[i * hop:i * hop + win] for i in range(n)]).astype(
        np.float32, copy=False
    )


def embed_clip_windowed(tagger, pcm: np.ndarray) -> np.ndarray:
    """Return one (2048 + 527,)-dim feature: per-window mean of CNN14
    embedding concatenated with per-window mean of AudioSet clipwise softmax.
    The clipwise mean carries domain priors (insect/wing-beat/chirp classes)
    that the 2048-d embedding alone leaves implicit."""
    audio = _windows(pcm)
    clipwise, embedding = tagger.inference(audio)
    emb_mean = embedding.mean(axis=0)         # (2048,)
    clip_mean = clipwise.mean(axis=0)         # (527,)
    return np.concatenate([emb_mean, clip_mean], axis=0).astype(np.float32)


def _cache_path(species_dir_name: str, stem: str, aug_id: str) -> Path:
    """Cache key encodes (species_dir_slug, clip_stem, augmentation_id,
    CACHE_VERSION) so logic changes invalidate stale features automatically."""
    safe = stem.replace("/", "_")
    return EMBED_CACHE_DIR / f"{CACHE_VERSION}__{species_dir_name}__{safe}__{aug_id}.npz"


def _augment_seed(species_dir_name: str, stem: str, aug_id: str) -> int:
    """Deterministic seed per (species, stem, aug_id) so cached augmentations
    are reproducible across runs — re-augmenting the same clip with different
    random parameters would defeat the cache and could shift the test bar
    run-to-run."""
    h = hashlib.sha256(f"{species_dir_name}__{stem}__{aug_id}".encode()).digest()
    return int.from_bytes(h[:8], "big")


def audio_augment(
    pcm: np.ndarray, sr: int, aug_id: str, rng: np.random.Generator
) -> np.ndarray:
    """Apply a pitch-preserving augmentation to a PCM clip.
       - 'stretch': time-stretch by rate ∈ U(0.92, 1.08) — preserves pitch.
       - 'noise':   additive Gaussian noise at SNR ∈ U(15, 25) dB.
    """
    if aug_id == "stretch":
        rate = float(rng.uniform(0.92, 1.08))
        stretched = librosa.effects.time_stretch(pcm, rate=rate)
        return stretched.astype(np.float32, copy=False)
    if aug_id == "noise":
        snr_db = float(rng.uniform(15.0, 25.0))
        sig_pow = float(np.mean(pcm ** 2)) + 1e-12
        noise_pow = sig_pow / (10.0 ** (snr_db / 10.0))
        noise = rng.normal(0.0, np.sqrt(noise_pow), size=pcm.shape)
        return (pcm + noise).astype(np.float32, copy=False)
    raise ValueError(f"Unknown aug_id: {aug_id!r}")


def cached_embed(tagger, wav_path: Path, aug_id: str = "clean") -> np.ndarray | None:
    """Return a feature vector for `wav_path`. Reads from cache when present;
    otherwise loads audio, applies the requested augmentation (if any),
    embeds it, and writes the result."""
    cache_path = _cache_path(wav_path.parent.name, wav_path.stem, aug_id)
    if cache_path.exists():
        try:
            return np.load(cache_path)["feat"]
        except Exception as exc:
            log.warning("Cache read failed for %s: %s — recomputing", cache_path.name, exc)

    try:
        pcm, _ = librosa.load(wav_path, sr=SAMPLE_RATE, mono=True)
    except Exception as exc:
        log.warning("librosa load failed for %s: %s", wav_path.name, exc)
        return None
    if pcm.size < SAMPLE_RATE // 2:  # < 0.5 s; skip
        return None

    if aug_id != "clean":
        seed = _augment_seed(wav_path.parent.name, wav_path.stem, aug_id)
        rng = np.random.default_rng(seed)
        try:
            pcm = audio_augment(pcm, SAMPLE_RATE, aug_id, rng)
        except Exception as exc:
            log.warning("Augment '%s' failed for %s: %s", aug_id, wav_path.name, exc)
            return None
        if pcm.size < SAMPLE_RATE // 2:
            return None  # time-stretch can compress short clips below the floor

    feat = embed_clip_windowed(tagger, pcm)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        np.savez_compressed(cache_path, feat=feat)
    except Exception as exc:
        log.warning("Cache write failed for %s: %s", cache_path.name, exc)
    return feat


def collect_clip_paths(min_clips: int) -> tuple[list[Path], list[str], list[str]]:
    """Walk DATA_DIR, return (paths, labels, species_seen). No embedding —
    we want to split clip-by-clip first so augmentation only touches the
    training partition."""
    if not DATA_DIR.exists():
        log.error("Dataset dir missing: %s", DATA_DIR)
        log.error("Run scripts/fetch_audio_dataset.py first.")
        sys.exit(2)

    paths: list[Path] = []
    labels: list[str] = []
    species_seen: list[str] = []
    for species_dir in sorted(DATA_DIR.iterdir()):
        if not species_dir.is_dir():
            continue
        raw_species = _slug_to_species(species_dir.name)
        species = LABEL_REMAP.get(raw_species, raw_species)
        wavs = sorted(species_dir.glob("*.wav"))
        if len(wavs) < min_clips:
            log.warning("Skipping %s — only %d clips (need ≥%d)",
                        raw_species, len(wavs), min_clips)
            continue
        if species != raw_species:
            log.info("Pooling %s → %s (%d clips)", raw_species, species, len(wavs))
        if species not in species_seen:
            species_seen.append(species)
        for w in wavs:
            paths.append(w)
            labels.append(species)

    if not paths:
        log.error("No usable clips found.")
        sys.exit(2)
    return paths, labels, species_seen


def embed_partition(
    tagger,
    paths: list[Path],
    indices: np.ndarray,
    y_enc: np.ndarray,
    aug_ids: tuple[str, ...],
    label: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Embed `paths[indices]` once per aug_id, dropping any clip that fails
    to load or augment. Returns (X, y) with each successful (clip × aug_id)
    pair as one row."""
    X_rows: list[np.ndarray] = []
    y_rows: list[int] = []
    for aug in aug_ids:
        n_ok = n_skip = 0
        for i in indices:
            v = cached_embed(tagger, paths[i], aug_id=aug)
            if v is None:
                n_skip += 1
                continue
            X_rows.append(v)
            y_rows.append(int(y_enc[i]))
            n_ok += 1
        log.info("  %s/%s — %d ok, %d skipped", label, aug, n_ok, n_skip)
    return np.vstack(X_rows), np.array(y_rows)


def _fit_temperature(clf, X_val: np.ndarray, y_val: np.ndarray) -> float:
    """Fit a single-parameter temperature scalar T that minimizes NLL on the
    val set. Same routine as train_yamnet_head._fit_temperature.
    """
    try:
        from scipy.optimize import minimize_scalar
    except Exception as exc:
        log.warning("scipy not available; skipping temperature scaling (%s)", exc)
        return 1.0

    if hasattr(clf, "decision_function"):
        logits = np.atleast_2d(clf.decision_function(X_val))
    else:
        proba = clf.predict_proba(X_val)
        logits = np.log(np.clip(proba, 1e-9, 1.0))

    if logits.ndim != 2 or logits.shape[0] != len(y_val):
        log.warning("Unexpected logits shape %s; T=1.0", logits.shape)
        return 1.0

    n_classes = logits.shape[1]
    y_oh = np.eye(n_classes)[y_val]

    def nll(T: float) -> float:
        T = max(float(T), 1e-3)
        scaled = logits / T
        scaled = scaled - scaled.max(axis=1, keepdims=True)
        p = np.exp(scaled)
        p = p / p.sum(axis=1, keepdims=True)
        return float(-np.mean(np.sum(y_oh * np.log(p + 1e-9), axis=1)))

    res = minimize_scalar(nll, bounds=(0.5, 5.0), method="bounded")
    T = float(res.x) if res.success else 1.0
    log.info("Fitted temperature T=%.3f (val NLL %.4f → %.4f)",
             T, nll(1.0), nll(T))
    return T


def train_head(
    X_train: np.ndarray, y_train: np.ndarray,
    X_val: np.ndarray, y_val: np.ndarray,
    X_test: np.ndarray, y_test: np.ndarray,
) -> tuple[object, dict]:
    """Fit LogisticRegressionCV + HistGradientBoostingClassifier on
    (X_train, y_train), build a soft-vote ensemble, and pick whichever scores
    best on the val set. Test metrics are reported only for the winner.
    """
    log.info("Split sizes — train=%d val=%d test=%d",
             len(X_train), len(X_val), len(X_test))

    log.info("Training LogisticRegressionCV head (Cs sweep) …")
    lr = LogisticRegressionCV(
        Cs=[0.01, 0.1, 1.0, 10.0, 100.0],
        cv=3,
        max_iter=5000,
        class_weight="balanced",
        scoring="accuracy",
        n_jobs=-1,
    )
    lr.fit(X_train, y_train)
    val_acc_lr = float(accuracy_score(y_val, lr.predict(X_val)))
    best_C = float(np.mean(list(lr.C_))) if hasattr(lr, "C_") else float("nan")
    log.info("LogRegCV val accuracy: %.3f (mean best C=%.4g)", val_acc_lr, best_C)

    log.info("Training HistGradientBoostingClassifier head …")
    hgb = HistGradientBoostingClassifier(
        max_iter=300,
        learning_rate=0.05,
        max_depth=8,
        l2_regularization=1.0,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.15,
        n_iter_no_change=20,
    )
    hgb.fit(X_train, y_train)
    val_acc_hgb = float(accuracy_score(y_val, hgb.predict(X_val)))
    log.info("HistGB val accuracy: %.3f (n_iter=%d)", val_acc_hgb, int(hgb.n_iter_))

    ensemble = SoftVoteEnsemble([lr, hgb], name="logreg+histgb")
    val_acc_ens = float(accuracy_score(y_val, ensemble.predict(X_val)))
    log.info("Ensemble (logreg+histgb) val accuracy: %.3f", val_acc_ens)

    candidates = [
        ("logreg", lr, val_acc_lr),
        ("histgb", hgb, val_acc_hgb),
        ("ensemble", ensemble, val_acc_ens),
    ]
    name, chosen, val_acc = max(candidates, key=lambda c: c[2])
    log.info("Selected head on val: %s (val_acc=%.3f)", name, val_acc)

    test_pred = chosen.predict(X_test)
    test_acc = float(accuracy_score(y_test, test_pred))
    f1_per_class = f1_score(y_test, test_pred, average=None, labels=np.unique(y_test))
    macro_f1 = float(f1_score(y_test, test_pred, average="macro",
                              labels=np.unique(y_test)))
    cm = confusion_matrix(y_test, test_pred, labels=np.unique(y_test)).tolist()

    temperature = _fit_temperature(chosen, X_val, y_val)

    metrics = {
        "val_accuracy": float(val_acc),
        "val_accuracy_logreg": val_acc_lr,
        "val_accuracy_histgb": val_acc_hgb,
        "val_accuracy_ensemble": val_acc_ens,
        "head_name": name,
        "test_accuracy": test_acc,
        "macro_f1": macro_f1,
        "per_class_f1": {int(c): float(s) for c, s in zip(np.unique(y_test), f1_per_class)},
        "confusion_matrix": cm,
        "classification_report": classification_report(
            y_test, test_pred, labels=np.unique(y_test), zero_division=0
        ),
        "temperature": temperature,
    }
    return chosen, metrics


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-clips", type=int, default=20,
                    help="Minimum clips per species to include in training")
    ap.add_argument("--accuracy-floor", type=float, default=0.85,
                    help="Test-accuracy bar; exit 1 if missed")
    ap.add_argument("--no-augment", action="store_true",
                    help="Disable Tier-2 audio augmentation (train on clean only)")
    args = ap.parse_args()

    paths, labels, species_seen = collect_clip_paths(args.min_clips)
    le = LabelEncoder().fit(labels)
    y_enc = le.transform(labels)
    log.info("Collected %d clips across %d classes", len(paths), len(le.classes_))

    # Split at clip-path level FIRST so augmentation only inflates the
    # training partition. 80 / 10 / 10 stratified by class.
    idx_all = np.arange(len(paths))
    idx_trainval, idx_test = train_test_split(
        idx_all, test_size=0.10, random_state=42, stratify=y_enc,
    )
    idx_train, idx_val = train_test_split(
        idx_trainval, test_size=0.111, random_state=42,
        stratify=y_enc[idx_trainval],
    )

    tagger = load_panns()

    train_augs = AUG_VARIANTS_EVAL if args.no_augment else AUG_VARIANTS_TRAIN
    log.info("Embedding train clips (augs=%s) …", ",".join(train_augs))
    X_train, y_train = embed_partition(tagger, paths, idx_train, y_enc, train_augs, "train")
    log.info("Embedding val clips (clean) …")
    X_val, y_val = embed_partition(tagger, paths, idx_val, y_enc, AUG_VARIANTS_EVAL, "val")
    log.info("Embedding test clips (clean) …")
    X_test, y_test = embed_partition(tagger, paths, idx_test, y_enc, AUG_VARIANTS_EVAL, "test")

    clf, metrics = train_head(X_train, y_train, X_val, y_val, X_test, y_test)

    bundle = {
        "clf": clf,
        "label_encoder": le,
        "classes": le.classes_.tolist(),
        "head_name": metrics["head_name"],
        "test_accuracy": metrics["test_accuracy"],
        "val_accuracy": metrics["val_accuracy"],
        "val_accuracy_logreg": metrics["val_accuracy_logreg"],
        "val_accuracy_histgb": metrics["val_accuracy_histgb"],
        "val_accuracy_ensemble": metrics["val_accuracy_ensemble"],
        "macro_f1": metrics["macro_f1"],
        "per_class_f1": {le.inverse_transform([k])[0]: v
                         for k, v in metrics["per_class_f1"].items()},
        "confusion_matrix": metrics["confusion_matrix"],
        "temperature": metrics["temperature"],
        "feature_dim": int(X_train.shape[1]),
        "cache_version": CACHE_VERSION,
        "window_seconds": WINDOW_SECONDS,
        "hop_seconds": HOP_SECONDS,
        "augmentations": list(train_augs),
        "trained_at": dt.datetime.utcnow().isoformat() + "Z",
    }

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, MODEL_OUT)
    log.info("Saved classifier head → %s", MODEL_OUT)

    log.info("\n%s", metrics["classification_report"])
    log.info("Test accuracy: %.3f  Macro F1: %.3f  (floor %.2f)",
             metrics["test_accuracy"], metrics["macro_f1"], args.accuracy_floor)

    if metrics["test_accuracy"] < args.accuracy_floor:
        log.error("FAIL — test accuracy below floor. Collect more data or "
                  "augment, then re-run.")
        return 1
    log.info("PASS — accuracy meets bar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
