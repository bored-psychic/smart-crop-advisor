"""
Train a small classifier head on top of YAMNet embeddings.

Pipeline
--------
1. Walk data/audio_samples/<species>/*.wav (built by fetch_audio_dataset.py)
2. For each clip:
     - resample to 16 kHz mono
     - run YAMNet  → (frames, 1024) embeddings
     - mean-pool   → (1024,) feature vector
3. Stratified 80/10/10 split (train / val / test)
4. Try LogisticRegression first; if val accuracy < 0.80, escalate to
   MLPClassifier(hidden=(128,))
5. Save bundle to backend/models/yamnet_head.joblib:
       {'clf', 'label_encoder', 'classes', 'test_accuracy',
        'per_class_f1', 'confusion_matrix', 'trained_at'}
6. Exit 1 if final test accuracy < 0.80 (the user's explicit bar)

USAGE
-----
    python scripts/train_yamnet_head.py
    python scripts/train_yamnet_head.py --min-clips 50  # lower the floor
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
from pathlib import Path

import joblib
import librosa
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix, f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import LabelEncoder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("train_yamnet")

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "audio_samples"
MODEL_OUT = REPO_ROOT / "backend" / "models" / "yamnet_head.joblib"

YAMNET_TFHUB = "https://tfhub.dev/google/yamnet/1"
SAMPLE_RATE = 16000  # YAMNet's required input rate


def _slug_to_species(slug: str) -> str:
    """Inverse of fetch_audio_dataset._slug — Moth_Butterfly → Moth/Butterfly."""
    return slug.replace("Moth_Butterfly", "Moth/Butterfly").replace("_", " ")


def load_yamnet():
    """Lazy import keeps `import` cheap and lets the script work even when TF
    isn't installed yet (the error surfaces here rather than at module load)."""
    import tensorflow_hub as hub
    log.info("Loading YAMNet from TF Hub: %s", YAMNET_TFHUB)
    return hub.load(YAMNET_TFHUB)


def embed_clip(yamnet, wav_path: Path) -> np.ndarray | None:
    """Return one mean-pooled 1024-dim embedding per clip, or None on error."""
    try:
        pcm, _ = librosa.load(wav_path, sr=SAMPLE_RATE, mono=True)
    except Exception as exc:
        log.warning("librosa load failed for %s: %s", wav_path.name, exc)
        return None
    if pcm.size < SAMPLE_RATE // 2:  # <0.5 s; skip
        return None
    # YAMNet returns (scores, embeddings, log_mel_spectrogram).
    # embeddings shape: (n_frames, 1024). Mean-pool over time.
    _, emb, _ = yamnet(pcm.astype(np.float32))
    return emb.numpy().mean(axis=0)


def collect_dataset(min_clips: int) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Walk DATA_DIR, embed every clip, return X, y, species_list."""
    if not DATA_DIR.exists():
        log.error("Dataset dir missing: %s", DATA_DIR)
        log.error("Run scripts/fetch_audio_dataset.py first.")
        sys.exit(2)

    yamnet = load_yamnet()

    X_rows, y_rows = [], []
    species_seen: list[str] = []
    for species_dir in sorted(DATA_DIR.iterdir()):
        if not species_dir.is_dir():
            continue
        species = _slug_to_species(species_dir.name)
        wavs = sorted(species_dir.glob("*.wav"))
        if len(wavs) < min_clips:
            log.warning("Skipping %s — only %d clips (need ≥%d)",
                        species, len(wavs), min_clips)
            continue
        species_seen.append(species)
        log.info("Embedding %s (%d clips) …", species, len(wavs))
        for w in wavs:
            v = embed_clip(yamnet, w)
            if v is None:
                continue
            X_rows.append(v)
            y_rows.append(species)

    if not X_rows:
        log.error("No usable clips found.")
        sys.exit(2)

    return np.vstack(X_rows), np.array(y_rows), species_seen


def train_head(X: np.ndarray, y_enc: np.ndarray) -> tuple[object, dict]:
    """Try LogReg → MLP if needed. Return (best_clf, metrics_dict)."""
    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y_enc, test_size=0.10, random_state=42, stratify=y_enc,
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval, test_size=0.111, random_state=42, stratify=y_trainval,
    )  # 0.111 of 90 % ≈ 10 %, so split is 80/10/10

    log.info("Split sizes — train=%d val=%d test=%d",
             len(X_train), len(X_val), len(X_test))

    log.info("Training LogisticRegression head …")
    lr = LogisticRegression(max_iter=2000, class_weight="balanced", n_jobs=-1)
    lr.fit(X_train, y_train)
    val_acc = accuracy_score(y_val, lr.predict(X_val))
    log.info("LogReg val accuracy: %.3f", val_acc)

    chosen = lr
    if val_acc < 0.80:
        log.info("Val < 0.80 — escalating to MLP(128) …")
        mlp = MLPClassifier(hidden_layer_sizes=(128,), max_iter=500,
                            early_stopping=True, random_state=42)
        mlp.fit(X_train, y_train)
        mlp_val = accuracy_score(y_val, mlp.predict(X_val))
        log.info("MLP val accuracy: %.3f", mlp_val)
        if mlp_val > val_acc:
            chosen = mlp
            val_acc = mlp_val

    test_pred = chosen.predict(X_test)
    test_acc = float(accuracy_score(y_test, test_pred))
    f1_per_class = f1_score(y_test, test_pred, average=None, labels=np.unique(y_test))
    cm = confusion_matrix(y_test, test_pred, labels=np.unique(y_test)).tolist()

    metrics = {
        "val_accuracy": float(val_acc),
        "test_accuracy": test_acc,
        "per_class_f1": {int(c): float(s) for c, s in zip(np.unique(y_test), f1_per_class)},
        "confusion_matrix": cm,
        "classification_report": classification_report(
            y_test, test_pred, labels=np.unique(y_test), zero_division=0
        ),
    }
    return chosen, metrics


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-clips", type=int, default=20,
                    help="Minimum clips per species to include in training")
    ap.add_argument("--accuracy-floor", type=float, default=0.80,
                    help="Test-accuracy bar; exit 1 if missed")
    args = ap.parse_args()

    X, y_str, species_seen = collect_dataset(args.min_clips)
    le = LabelEncoder().fit(y_str)
    y_enc = le.transform(y_str)
    log.info("Total samples: %d across %d classes", len(X), len(le.classes_))

    clf, metrics = train_head(X, y_enc)

    bundle = {
        "clf": clf,
        "label_encoder": le,
        "classes": le.classes_.tolist(),
        "test_accuracy": metrics["test_accuracy"],
        "val_accuracy": metrics["val_accuracy"],
        "per_class_f1": {le.inverse_transform([k])[0]: v
                         for k, v in metrics["per_class_f1"].items()},
        "confusion_matrix": metrics["confusion_matrix"],
        "trained_at": dt.datetime.utcnow().isoformat() + "Z",
    }

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, MODEL_OUT)
    log.info("Saved classifier head → %s", MODEL_OUT)

    log.info("\n%s", metrics["classification_report"])
    log.info("Test accuracy: %.3f (floor %.2f)",
             metrics["test_accuracy"], args.accuracy_floor)

    if metrics["test_accuracy"] < args.accuracy_floor:
        log.error("FAIL — test accuracy below floor. Collect more data or "
                  "augment, then re-run.")
        return 1
    log.info("PASS — accuracy meets bar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
