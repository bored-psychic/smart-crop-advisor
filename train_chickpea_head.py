"""
train_chickpea_head.py — Chickpea Disease Specialist Classifier (YOLO11n-cls)

Primary dataset (required):
  tolgahayit/fusarium-wilt-disease-in-chickpea-dataset  (~4,300 images, 9 severity levels)
  kaggle datasets download -d tolgahayit/fusarium-wilt-disease-in-chickpea-dataset \\
      -p data/chickpea_wilt_raw --unzip

Optional additional directories for the other two disease classes:
  data/chickpea_extra/Ascochyta_Blight/   (any image source — Kaggle, field photos)
  data/chickpea_extra/Dry_Root_Rot/

Severity grouping (maximises inter-class distance):
  HR / R / MR  or  dirs 1-3  →  healthy         (Highly/Moderately Resistant)
  MS / dirs 4-6              →  SKIPPED          (ambiguous boundary, not used)
  S  / HS      or  dirs 7-9  →  fusarium_wilt    (Susceptible / Highly Susceptible)

Target classes:
  fusarium_wilt     Fusarium oxysporum       — progressive yellowing from base, vascular browning
  ascochyta_blight  Ascochyta rabiei         — circular/elongated brown spots on leaves & pods
  dry_root_rot      Macrophomina phaseolina  — sudden wilt, brittle black-shredded roots
  healthy           N/A                      — vibrant green erect foliage, no necrotic spots

Rabi season augmentation (Dec–Mar): low-sun winter light, morning fog/dew, dust haze.

Usage:
  # Minimal — only wilt vs healthy from the Kaggle dataset
  python train_chickpea_head.py --wilt-data data/chickpea_wilt_raw

  # Full 4-class run (add extra disease dirs)
  python train_chickpea_head.py \\
      --wilt-data data/chickpea_wilt_raw \\
      --extra-data data/chickpea_extra \\
      --epochs 80 --device cpu
"""

import argparse
import os
import shutil
import random
from pathlib import Path

import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Severity-level → target class mapping.
# Supports both numeric dir names ("1"–"9") and the resistance-label convention
# ("HR", "R", "MR", "MS", "S", "HS") used by some dataset uploads.
SEVERITY_CLASS_MAP: dict[str, str] = {
    # Highly Resistant / Resistant / Moderately Resistant → treated as healthy
    'HR': 'healthy', 'R': 'healthy', 'MR': 'healthy',
    '1':  'healthy', '2': 'healthy', '3':  'healthy',
    # Susceptible / Highly Susceptible → fusarium wilt
    'S':  'fusarium_wilt', 'HS': 'fusarium_wilt',
    '7':  'fusarium_wilt', '8':  'fusarium_wilt', '9': 'fusarium_wilt',
    # MS / 4-6 deliberately omitted — ambiguous boundary, hurts class separation
}

# Additional disease directories (from --extra-data root).
# Keys are directory names; values are the target class labels.
EXTRA_CLASS_MAP: dict[str, str] = {
    'Ascochyta_Blight':  'ascochyta_blight',
    'ascochyta_blight':  'ascochyta_blight',
    'Ascochyta':         'ascochyta_blight',
    'Dry_Root_Rot':      'dry_root_rot',
    'dry_root_rot':      'dry_root_rot',
    'DryRootRot':        'dry_root_rot',
    # Allow a manually added healthy supplement directory
    'Healthy':           'healthy',
    'healthy':           'healthy',
}

LABEL_FILE = 'chickpea_classes.npy'
VAL_SPLIT  = 0.15
SEED       = 42
IMG_SIZE   = 224
MIN_IMAGES_PER_CLASS = 150   # warn (not fail) below this


# ---------------------------------------------------------------------------
# Step 1: Build dataset
# ---------------------------------------------------------------------------

def _copy_split(img_list: list, dest_train: Path, dest_val: Path,
                aug_pipeline, resize_only, aug_factor: int) -> None:
    """Apply augmentation to training images; resize-only for validation."""
    n_val      = max(1, int(len(img_list) * VAL_SPLIT))
    val_imgs   = img_list[:n_val]
    train_imgs = img_list[n_val:]

    for split, imgs, dest in [('val', val_imgs, dest_val),
                               ('train', train_imgs, dest_train)]:
        dest.mkdir(parents=True, exist_ok=True)
        for img_path in imgs:
            try:
                img_np = np.array(Image.open(img_path).convert('RGB'))
            except Exception:
                continue

            out = resize_only(image=img_np)['image']
            Image.fromarray(out).save(dest / img_path.name)

            if split == 'train':
                stem, suffix = img_path.stem, img_path.suffix
                for k in range(aug_factor):
                    aug = aug_pipeline(image=img_np)['image']
                    Image.fromarray(aug).save(dest / f"{stem}_aug{k}{suffix}")


def build_dataset(wilt_root: Path, extra_root: Path | None,
                  out_root: Path, aug_factor: int) -> list[str]:
    """
    Build train/val ImageFolder structure from:
      1. Severity-level dirs in wilt_root  (fusarium wilt dataset)
      2. Optional extra_root dirs          (ascochyta blight, dry root rot)

    Returns sorted list of class names that ended up in the dataset.
    """
    try:
        import albumentations as A
    except ImportError:
        raise SystemExit("Install albumentations: pip install albumentations")

    # Rabi-season field conditions: low winter sun, morning dew, dust haze
    aug_pipeline = A.Compose([
        A.RandomBrightnessContrast(brightness_limit=(-0.30, 0.20),
                                   contrast_limit=0.30, p=0.8),
        A.HueSaturationValue(hue_shift_limit=12, sat_shift_limit=25,
                             val_shift_limit=18, p=0.6),
        A.RandomFog(fog_coef_lower=0.05, fog_coef_upper=0.25, p=0.25),
        A.GaussNoise(var_limit=(8.0, 35.0), p=0.35),
        A.MotionBlur(blur_limit=5, p=0.30),
        A.CoarseDropout(max_holes=6, max_height=16, max_width=16,
                        fill_value=0, p=0.35),
        A.RandomRotate90(p=0.5),
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.25),
        A.Resize(IMG_SIZE, IMG_SIZE),
    ])
    resize_only = A.Resize(IMG_SIZE, IMG_SIZE)

    random.seed(SEED)
    np.random.seed(SEED)

    class_counts: dict[str, int] = {}

    # ── 1. Fusarium wilt severity dirs ────────────────────────────────────────
    if not wilt_root.exists():
        raise SystemExit(
            f"Wilt dataset not found at '{wilt_root}'.\n"
            "Download: kaggle datasets download "
            "-d tolgahayit/fusarium-wilt-disease-in-chickpea-dataset "
            f"-p {wilt_root} --unzip"
        )

    severity_hits = 0
    for dir_path in sorted(wilt_root.iterdir()):
        if not dir_path.is_dir():
            continue
        target = SEVERITY_CLASS_MAP.get(dir_path.name)
        if target is None:
            # Skip MS (4–6) and any unrecognised dirs
            continue

        images = (list(dir_path.glob('*.jpg')) + list(dir_path.glob('*.jpeg'))
                  + list(dir_path.glob('*.png')) + list(dir_path.glob('*.JPG')))
        random.shuffle(images)
        if not images:
            continue

        severity_hits += 1
        dest_train = out_root / 'train' / target
        dest_val   = out_root / 'val'   / target

        n_train = max(0, len(images) - max(1, int(len(images) * VAL_SPLIT)))
        print(f"  {dir_path.name:6s} → {target:18s}  "
              f"train={n_train} (×{aug_factor} aug)  "
              f"val={len(images)-n_train}")

        _copy_split(images, dest_train, dest_val,
                    aug_pipeline, resize_only, aug_factor)
        class_counts[target] = class_counts.get(target, 0) + n_train

    if severity_hits == 0:
        print(
            f"WARNING: No recognised severity directories found in '{wilt_root}'.\n"
            "Expected dirs named 1–9 or HR/R/MR/MS/S/HS. "
            "Check the dataset zip structure."
        )

    # ── 2. Optional extra disease dirs ────────────────────────────────────────
    if extra_root and extra_root.exists():
        for dir_path in sorted(extra_root.iterdir()):
            if not dir_path.is_dir():
                continue
            target = EXTRA_CLASS_MAP.get(dir_path.name)
            if target is None:
                print(f"  [SKIP] '{dir_path.name}' not in EXTRA_CLASS_MAP")
                continue

            images = (list(dir_path.glob('*.jpg')) + list(dir_path.glob('*.jpeg'))
                      + list(dir_path.glob('*.png')) + list(dir_path.glob('*.JPG')))
            random.shuffle(images)
            if not images:
                continue

            dest_train = out_root / 'train' / target
            dest_val   = out_root / 'val'   / target
            n_train = max(0, len(images) - max(1, int(len(images) * VAL_SPLIT)))
            print(f"  {dir_path.name:20s} → {target:18s}  "
                  f"train={n_train} (×{aug_factor} aug)  "
                  f"val={len(images)-n_train}")

            _copy_split(images, dest_train, dest_val,
                        aug_pipeline, resize_only, aug_factor)
            class_counts[target] = class_counts.get(target, 0) + n_train
    elif extra_root:
        print(f"  [INFO] --extra-data '{extra_root}' not found — skipping "
              f"ascochyta_blight and dry_root_rot classes.")

    # ── Warn on thin classes ─────────────────────────────────────────────────
    for cls, count in sorted(class_counts.items()):
        if count < MIN_IMAGES_PER_CLASS:
            eff = count * aug_factor
            print(
                f"  WARNING: '{cls}' has only {count} base training images "
                f"(aug_factor={aug_factor} → ~{eff} samples). "
                f"Collect ≥{MIN_IMAGES_PER_CLASS} distinct photos for reliable accuracy."
            )

    all_classes = sorted(class_counts.keys())
    print(f"\nFinal classes ({len(all_classes)}): {all_classes}")
    return all_classes


# ---------------------------------------------------------------------------
# Step 2: Train
# ---------------------------------------------------------------------------

def train(data_dir: Path, epochs: int, device: str, batch: int) -> Path:
    try:
        from ultralytics import YOLO
    except ImportError:
        raise SystemExit("Install ultralytics: pip install ultralytics")

    model = YOLO('yolo11n-cls.pt')

    print(f"\n  Realistic CPU inference (deployed TFLite INT8): 20–55 ms/image")
    print(f"  GPU inference (cuda/mps): 5–15 ms/image")

    results = model.train(
        data=str(data_dir),
        epochs=epochs,
        imgsz=IMG_SIZE,
        batch=batch,
        device=device,
        project='runs/chickpea_head',
        name='v1',
        augment=False,   # data already pre-augmented in build_dataset()
        mosaic=0.0,      # mosaic is for detection — destroys single-leaf patterns
        patience=15,
        save_period=10,
        verbose=True,
    )

    best_pt = Path(results.save_dir) / 'weights' / 'best.pt'
    print(f"\nBest weights: {best_pt}")
    return best_pt


# ---------------------------------------------------------------------------
# Step 3: Export to TFLite
# ---------------------------------------------------------------------------

def export_tflite(pt_path: Path, app_dir: Path, classes: list[str]) -> None:
    """Export INT8 TFLite and save class labels into the app root directory."""
    from ultralytics import YOLO

    model   = YOLO(str(pt_path))
    exp_out = model.export(format='tflite', imgsz=IMG_SIZE, int8=True)

    tflite_dst = app_dir / 'chickpea_model.tflite'
    shutil.copy(Path(exp_out), tflite_dst)
    print(f"Copied TFLite model → {tflite_dst}")

    # Save the class list we built ourselves — do NOT rely on model.names,
    # which is a {int: str} dict and produces an object-array when np.save'd.
    np.save(app_dir / LABEL_FILE, np.array(sorted(classes)))
    print(f"Classes ({len(classes)}): {sorted(classes)}")
    print(f"Saved class list → {app_dir / LABEL_FILE}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Train Chickpea Disease Specialist Head (YOLO11n-cls)'
    )
    parser.add_argument(
        '--wilt-data', required=True,
        help='Root of the tolgahayit fusarium-wilt dataset (contains severity dirs 1-9 or HR/R/…/HS)'
    )
    parser.add_argument(
        '--extra-data', default=None,
        help='Optional root containing additional disease dirs: Ascochyta_Blight/, Dry_Root_Rot/'
    )
    parser.add_argument('--out',        default='data/chickpea_ready',
                        help='Processed dataset output directory')
    parser.add_argument('--app-dir',    default='.',
                        help='App root to copy final model files into')
    parser.add_argument('--epochs',     type=int, default=80)
    parser.add_argument('--batch',      type=int, default=32)
    parser.add_argument('--device',     default='cpu',
                        help='cpu | 0 (cuda) | mps')
    parser.add_argument('--aug-factor', type=int, default=3,
                        help='Augmented copies per training image')
    parser.add_argument('--skip-prep',   action='store_true',
                        help='Skip data prep (dataset already built)')
    parser.add_argument('--skip-export', action='store_true',
                        help='Skip TFLite export')
    args = parser.parse_args()

    wilt_root  = Path(args.wilt_data)
    extra_root = Path(args.extra_data) if args.extra_data else None
    out_root   = Path(args.out)
    app_dir    = Path(args.app_dir)

    print(
        "NOTE: Severity 4-6 (Moderately Susceptible) is excluded — "
        "maximises Healthy vs Wilt inter-class distance.\n"
    )

    classes: list[str] = []
    if not args.skip_prep:
        print(f"=== Step 1: Building dataset (aug_factor={args.aug_factor}) ===")
        if out_root.exists():
            shutil.rmtree(out_root)
        classes = build_dataset(wilt_root, extra_root, out_root,
                                aug_factor=args.aug_factor)

        for split in ['train', 'val']:
            print(f"\n{split} distribution:")
            split_dir = out_root / split
            if split_dir.exists():
                for cls_dir in sorted(split_dir.iterdir()):
                    n = sum(1 for _ in cls_dir.iterdir())
                    print(f"  {cls_dir.name:25s} {n:5d} images")
    else:
        print("Skipping data prep (--skip-prep)")
        # Reconstruct class list from the already-built dataset
        train_dir = out_root / 'train'
        if train_dir.exists():
            classes = sorted(d.name for d in train_dir.iterdir() if d.is_dir())
        if not classes:
            print("WARNING: Could not determine class list from existing dataset.")

    print("\n=== Step 2: Training YOLO11n-cls ===")
    print(f"  epochs={args.epochs}  batch={args.batch}  device={args.device}")
    best_pt = train(out_root, args.epochs, args.device, args.batch)

    if not args.skip_export:
        if not classes:
            raise SystemExit(
                "No class list available for export. "
                "Run without --skip-prep, or re-run with --skip-export."
            )
        print("\n=== Step 3: Exporting to TFLite (INT8) ===")
        export_tflite(best_pt, app_dir, classes)
        print(f"\nRestart the Streamlit app — it will auto-detect the chickpea specialist.")
    else:
        print(f"\nSkipped export. Best weights at: {best_pt}")


if __name__ == '__main__':
    main()
