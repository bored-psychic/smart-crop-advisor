"""
train_rice_head.py — Rice Disease Specialist Classifier (YOLO11n-cls)

Trains a 4-class rice disease model on the Paddy Doctor dataset and exports
it as TFLite so it slots into the existing app inference pipeline with
zero new app dependencies.

Dataset: Paddy Doctor (Kaggle) — 10,407 field images, 10 classes
Target classes used here:
    blast        (~1,800 images)
    brown_spot   (~1,977 images)
    normal       (~1,764 images, labelled as healthy in-app)
    dead_heart   (~983 images — closest proxy to Leaf Smut symptoms available)

Note on "Leaf Smut": not present in any major public rice dataset as of 2025.
dead_heart (stem borer damage) is the nearest visual proxy. Replace with
a dedicated leaf smut dataset if you source one from IRRI or TNAU.

Expected inference on CPU (deployed TFLite):  25–60 ms per image
Expected inference on GPU (PyTorch .pt):       3–8 ms per image
The 0.05 ms figure from the NumPy HSV step is a pixel-array op, not a CNN.

Setup (run once):
    pip install ultralytics albumentations kaggle

Then download the dataset:
    kaggle datasets download -d sadhliroomyprime/paddydoctor -p data/paddy_raw
    # or manually from https://www.kaggle.com/datasets/sadhliroomyprime/paddydoctor

Usage:
    python train_rice_head.py --data data/paddy_raw --epochs 60 --device cpu
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

# Primary dataset: Paddy Doctor (Kaggle: sadhliroomyprime/paddydoctor)
# For leaf_smut: use a dedicated dataset that explicitly labels it (e.g., search
# Kaggle for "rice leaf smut"). If found, add it here as 'leaf_smut': 'leaf_smut'.
# The 'dead_heart' fallback below is visually dissimilar and increases false-positives.
#
# On small leaf smut datasets (< 100 images):
#   40 images × aug_factor=15 = 600 training samples — limited diversity.
#   Collect 300+ distinct field photos before deploying a leaf smut class to production.
TARGET_CLASSES = {
    'blast':       'blast',
    'brown_spot':  'brown_spot',
    'normal':      'healthy',        # Paddy Doctor label → in-app display label
    'leaf_smut':   'leaf_smut',      # Real fungal smut data — preferred over proxy
    # Fallback: if 'leaf_smut' directory absent, build_dataset will skip it.
    # Uncomment below and comment 'leaf_smut' line above if no real smut data:
    # 'dead_heart': 'leaf_smut_proxy',  # stem-borer damage — dissimilar visual
}

MIN_IMAGES_PER_CLASS = 100   # warn (not fail) if a class has fewer images

LABEL_FILE = 'rice_classes.npy'   # saved alongside rice_model.tflite in app dir
VAL_SPLIT  = 0.15                  # 85/15 train/val
SEED       = 42
IMG_SIZE   = 224                   # YOLO11n-cls standard


# ---------------------------------------------------------------------------
# Step 1: Build augmented dataset directory
# ---------------------------------------------------------------------------

def build_dataset(raw_root: Path, out_root: Path, aug_factor: int = 3) -> None:
    """
    Filter Paddy Doctor to TARGET_CLASSES, apply Albumentations augmentation,
    and write train/val splits to out_root in ImageFolder format.

    aug_factor: how many augmented copies to create per original image.
                3 triples the training set size. Set to 1 to skip augmentation.
    """
    try:
        import albumentations as A
        from albumentations.pytorch import ToTensorV2  # noqa: F401 (only checks install)
    except ImportError:
        raise SystemExit("Install albumentations: pip install albumentations")

    # Albumentations pipeline tuned for Bengaluru field conditions:
    # - Harsh midday sun → brightness/contrast shifts
    # - Hand-held phone camera → blur, rotation
    # - Outdoor ambient → hue/saturation drift
    aug_pipeline = A.Compose([
        A.RandomRotate90(p=0.5),
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.3),
        A.RandomBrightnessContrast(brightness_limit=0.35, contrast_limit=0.35, p=0.8),
        A.HueSaturationValue(hue_shift_limit=15, sat_shift_limit=30, val_shift_limit=20, p=0.6),
        A.GaussNoise(var_limit=(10.0, 50.0), p=0.4),
        A.MotionBlur(blur_limit=5, p=0.3),
        A.CoarseDropout(max_holes=8, max_height=16, max_width=16, fill_value=0, p=0.3),
        A.Resize(IMG_SIZE, IMG_SIZE),
    ])

    no_aug = A.Resize(IMG_SIZE, IMG_SIZE)

    random.seed(SEED)
    np.random.seed(SEED)

    for paddy_label, app_label in TARGET_CLASSES.items():
        src_dir = raw_root / paddy_label
        if not src_dir.exists():
            # Some Kaggle downloads unzip with a parent dir
            src_dir = raw_root / 'train_images' / paddy_label
        if not src_dir.exists():
            print(f"  [SKIP] {paddy_label} not found in {raw_root}")
            continue

        images = list(src_dir.glob('*.jpg')) + list(src_dir.glob('*.png'))
        random.shuffle(images)

        if len(images) < MIN_IMAGES_PER_CLASS:
            effective = len(images) * aug_factor
            print(f"  WARNING: {paddy_label} has only {len(images)} images "
                  f"(recommended ≥{MIN_IMAGES_PER_CLASS}). "
                  f"aug_factor={aug_factor} will produce ~{effective} training samples "
                  f"but with limited visual diversity.")

        n_val  = max(1, int(len(images) * VAL_SPLIT))
        val_imgs   = images[:n_val]
        train_imgs = images[n_val:]

        print(f"  {paddy_label:20s} → {app_label:25s}  "
              f"train={len(train_imgs)} (×{aug_factor} aug)  val={len(val_imgs)}")

        for split, img_list in [('train', train_imgs), ('val', val_imgs)]:
            dest = out_root / split / app_label
            dest.mkdir(parents=True, exist_ok=True)

            for img_path in img_list:
                img_np = np.array(Image.open(img_path).convert('RGB'))

                if split == 'val':
                    # Validation: only resize, no augmentation
                    out = no_aug(image=img_np)['image']
                    Image.fromarray(out).save(dest / img_path.name)
                else:
                    # Training: save original + aug_factor augmented copies
                    orig = no_aug(image=img_np)['image']
                    Image.fromarray(orig).save(dest / img_path.name)

                    stem, suffix = img_path.stem, img_path.suffix
                    for k in range(aug_factor):
                        aug = aug_pipeline(image=img_np)['image']
                        Image.fromarray(aug).save(dest / f"{stem}_aug{k}{suffix}")


# ---------------------------------------------------------------------------
# Step 2: Train with YOLO11n-cls
# ---------------------------------------------------------------------------

def train(data_dir: Path, epochs: int, device: str, batch: int) -> Path:
    try:
        from ultralytics import YOLO
    except ImportError:
        raise SystemExit("Install ultralytics: pip install ultralytics")

    model = YOLO('yolo11n-cls.pt')   # downloads ~2.7 MB pretrained weights

    results = model.train(
        data=str(data_dir),
        epochs=epochs,
        imgsz=IMG_SIZE,
        batch=batch,
        device=device,
        project='runs/rice_head',
        name='v1',
        # Ultralytics built-in augmentation (complements Albumentations in data prep)
        augment=False,              # we already pre-augmented; avoid double-augmenting
        hsv_h=0.015, hsv_s=0.5, hsv_v=0.3,
        degrees=10, translate=0.1, scale=0.4, fliplr=0.5,
        mosaic=0.0,                 # mosaic makes no sense for single-leaf classification
        patience=15,                # early stop if no improvement for 15 epochs
        save_period=10,
        verbose=True,
    )

    best_pt = Path(results.save_dir) / 'weights' / 'best.pt'
    print(f"\nBest weights: {best_pt}")
    return best_pt


# ---------------------------------------------------------------------------
# Step 3: Export to TFLite for zero-dependency app integration
# ---------------------------------------------------------------------------

def export_tflite(pt_path: Path, app_dir: Path) -> None:
    """
    Export YOLO11n-cls .pt → TFLite INT8-quantized for CPU-optimised inference.
    Copies rice_model.tflite + rice_classes.npy into the app root directory.
    """
    from ultralytics import YOLO

    model = YOLO(str(pt_path))
    export_path = model.export(
        format='tflite',
        imgsz=IMG_SIZE,
        int8=True,          # quantise to INT8: ~4x smaller, ~2x faster on CPU
        data=None,          # calibration data optional for INT8 (uses training mean/std)
    )
    tflite_src = Path(export_path)

    # Copy into app root
    app_dir.mkdir(parents=True, exist_ok=True)
    tflite_dst = app_dir / 'rice_model.tflite'
    shutil.copy(tflite_src, tflite_dst)
    print(f"Copied TFLite model → {tflite_dst}")

    # Save class names aligned with the export (alphabetical by default)
    classes = sorted(TARGET_CLASSES.values())
    np.save(app_dir / LABEL_FILE, np.array(classes))
    print(f"Classes ({len(classes)}): {classes}")
    print(f"Saved class list → {app_dir / LABEL_FILE}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Train Rice Disease Specialist Head')
    parser.add_argument('--data',    default='data/paddy_raw',   help='Path to raw Paddy Doctor download')
    parser.add_argument('--out',     default='data/rice_ready',  help='Processed dataset output directory')
    parser.add_argument('--app-dir', default='.',                 help='App root to copy final model into')
    parser.add_argument('--epochs',  type=int, default=60)
    parser.add_argument('--batch',   type=int, default=32)
    parser.add_argument('--device',  default='cpu',              help='cpu | 0 (cuda) | mps')
    parser.add_argument('--aug-factor', type=int, default=3,
                        help='Augmented copies per training image (0 to skip augmentation)')
    parser.add_argument('--skip-prep',   action='store_true', help='Skip data prep (dataset already built)')
    parser.add_argument('--skip-export', action='store_true', help='Skip TFLite export')
    args = parser.parse_args()

    raw_root = Path(args.data)
    out_root = Path(args.out)
    app_dir  = Path(args.app_dir)

    # 1. Data preparation
    if not args.skip_prep:
        if not raw_root.exists():
            print(f"\nDataset not found at '{raw_root}'.")
            print("Download it with:")
            print("  kaggle datasets download -d sadhliroomyprime/paddydoctor -p data/paddy_raw --unzip")
            print("Or manually from: https://www.kaggle.com/datasets/sadhliroomyprime/paddydoctor")
            return

        print(f"\n=== Step 1: Building dataset (aug_factor={args.aug_factor}) ===")
        if out_root.exists():
            shutil.rmtree(out_root)
        build_dataset(raw_root, out_root, aug_factor=args.aug_factor)

        # Print class distribution after prep
        for split in ['train', 'val']:
            print(f"\n{split} distribution:")
            for cls_dir in sorted((out_root / split).iterdir()):
                n = sum(1 for _ in cls_dir.iterdir())
                print(f"  {cls_dir.name:30s} {n:5d} images")
    else:
        print("Skipping data prep (--skip-prep)")

    # 2. Train
    print("\n=== Step 2: Training YOLO11n-cls ===")
    print(f"  epochs={args.epochs}  batch={args.batch}  device={args.device}")
    print(f"  Realistic CPU inference after export: ~25–60 ms/image")
    print(f"  (The 0.05 ms figure is for the NumPy HSV pixel op, not CNN inference)")
    best_pt = train(out_root, args.epochs, args.device, args.batch)

    # 3. Export to TFLite
    if not args.skip_export:
        print("\n=== Step 3: Exporting to TFLite (INT8) ===")
        export_tflite(best_pt, app_dir)
        print("\nIntegration: rice_model.tflite + rice_classes.npy are now in", app_dir)
        print("Restart the Streamlit app — it will auto-detect the rice specialist.")
    else:
        print(f"\nSkipped export. Best weights at: {best_pt}")


if __name__ == '__main__':
    main()
