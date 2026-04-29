"""
train_maize_head.py — Maize Disease Specialist Classifier (YOLO11n-cls)

IMPORTANT: The general disease_model.tflite already covers all 4 target classes:
  Corn___Common_rust, Corn___Cercospora_leaf_spot Gray_leaf_spot,
  Corn___Northern_Leaf_Blight, Corn___healthy.
This specialist is worth training because:
  (a) It is ~10x smaller (4 classes vs 38) → faster inference, smaller app bundle.
  (b) Removing 34 unrelated crop classes reduces inter-class confusion on maize images.
If the general model already gives you ≥90% on maize validation images,
test before assuming a specialist improves things.

Dataset options (pick one):
  A. PlantVillage corn subset — already downloaded for the general model.
     Filter to Corn_* directories. Widely available, well-labeled.
  B. Kaggle "kaustavbiswal/maize-diseases" — additional field images.
     kaggle datasets download -d kaustavbiswal/maize-diseases -p data/maize_raw --unzip

Target classes:
  northern_leaf_blight  (Exserohilum turcicum — large cigar-shaped lesions)
  common_rust           (Puccinia sorghi — cinnamon-brown powdery pustules)
  gray_leaf_spot        (Cercospora zeae-maydis — rectangular tan/gray veinal lesions)
  healthy

Expected CPU inference (deployed TFLite INT8): 20–55 ms/image.
"sub-15ms" is achievable on GPU (cuda/mps) or Apple Silicon, not generic CPU.

NOTE on the provided snippet: the Albumentations pipeline must be applied in
build_dataset() during data prep. Creating aug = A.Compose([...]) and not calling
it produces no augmentation — the variable is simply unused.

Setup:
    pip install ultralytics albumentations

Usage:
    # Option A: PlantVillage corn directories
    python train_maize_head.py --data data/plantvillage/corn --source plantvillage

    # Option B: Kaggle maize dataset
    python train_maize_head.py --data data/maize_raw --source kaggle --epochs 75
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

# PlantVillage directory names → specialist class names
PLANTVILLAGE_CLASSES = {
    'Corn___Northern_Leaf_Blight':                   'northern_leaf_blight',
    'Corn___Common_rust':                            'common_rust',
    'Corn___Cercospora_leaf_spot Gray_leaf_spot':    'gray_leaf_spot',
    'Corn___healthy':                                'healthy',
}

# Kaggle "kaustavbiswal/maize-diseases" directory names (adjust if structure differs)
KAGGLE_CLASSES = {
    'Blight':       'northern_leaf_blight',
    'Common_Rust':  'common_rust',
    'Gray_Leaf_Spot': 'gray_leaf_spot',
    'Healthy':      'healthy',
}

LABEL_FILE = 'maize_classes.npy'
VAL_SPLIT  = 0.15
SEED       = 42
IMG_SIZE   = 224
MIN_IMAGES_PER_CLASS = 200


# ---------------------------------------------------------------------------
# Step 1: Build augmented dataset
# ---------------------------------------------------------------------------

def build_dataset(raw_root: Path, out_root: Path,
                  class_map: dict, aug_factor: int = 3) -> None:
    """
    Filter source dataset to target classes, apply Albumentations augmentation,
    write train/val splits in ImageFolder format.

    The augmentation pipeline is applied HERE during data prep — not passed to
    model.train(). Ultralytics' built-in augmentation (augment=False in train())
    is disabled separately to avoid double-augmenting.
    """
    try:
        import albumentations as A
    except ImportError:
        raise SystemExit("Install albumentations: pip install albumentations")

    # Bengaluru field conditions: harsh midday sun, hand-held phone, outdoor haze.
    aug_pipeline = A.Compose([
        A.RandomBrightnessContrast(brightness_limit=0.35, contrast_limit=0.3, p=0.8),
        A.HueSaturationValue(hue_shift_limit=15, sat_shift_limit=20, val_shift_limit=15, p=0.5),
        A.MotionBlur(blur_limit=7, p=0.3),
        A.GaussNoise(var_limit=(10.0, 40.0), p=0.35),
        A.CoarseDropout(max_holes=8, max_height=16, max_width=16, fill_value=0, p=0.4),
        A.RandomRotate90(p=0.5),
        A.HorizontalFlip(p=0.5),
        A.Resize(IMG_SIZE, IMG_SIZE),
    ])
    resize_only = A.Resize(IMG_SIZE, IMG_SIZE)

    random.seed(SEED)
    np.random.seed(SEED)

    for src_name, app_label in class_map.items():
        src_dir = raw_root / src_name
        if not src_dir.exists():
            print(f"  [SKIP] '{src_name}' not found in {raw_root}")
            continue

        images = list(src_dir.glob('*.jpg')) + list(src_dir.glob('*.png')) + \
                 list(src_dir.glob('*.JPG')) + list(src_dir.glob('*.jpeg'))
        random.shuffle(images)

        if len(images) < MIN_IMAGES_PER_CLASS:
            print(f"  WARNING: {src_name} has only {len(images)} images "
                  f"(recommended ≥{MIN_IMAGES_PER_CLASS}). "
                  f"aug_factor={aug_factor} → ~{len(images) * aug_factor} training samples.")

        n_val      = max(1, int(len(images) * VAL_SPLIT))
        val_imgs   = images[:n_val]
        train_imgs = images[n_val:]

        print(f"  {src_name:50s} → {app_label:25s}  "
              f"train={len(train_imgs)} (×{aug_factor} aug)  val={len(val_imgs)}")

        for split, img_list in [('train', train_imgs), ('val', val_imgs)]:
            dest = out_root / split / app_label
            dest.mkdir(parents=True, exist_ok=True)

            for img_path in img_list:
                try:
                    img_np = np.array(Image.open(img_path).convert('RGB'))
                except Exception:
                    continue

                # Validation: resize only, never augment
                out = resize_only(image=img_np)['image']
                Image.fromarray(out).save(dest / img_path.name)

                if split == 'train':
                    stem, suffix = img_path.stem, img_path.suffix
                    for k in range(aug_factor):
                        aug = aug_pipeline(image=img_np)['image']
                        Image.fromarray(aug).save(dest / f"{stem}_aug{k}{suffix}")


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
        project='runs/maize_head',
        name='v1',
        augment=False,   # data already pre-augmented in build_dataset()
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

def export_tflite(pt_path: Path, app_dir: Path, class_map: dict) -> None:
    """Export to INT8 TFLite and copy into the app directory."""
    from ultralytics import YOLO

    model = YOLO(str(pt_path))
    export_path = model.export(format='tflite', imgsz=IMG_SIZE, int8=True)

    tflite_dst = app_dir / 'maize_model.tflite'
    shutil.copy(Path(export_path), tflite_dst)
    print(f"Copied TFLite model → {tflite_dst}")

    classes = sorted(set(class_map.values()))
    np.save(app_dir / LABEL_FILE, np.array(classes))
    print(f"Classes ({len(classes)}): {classes}")
    print(f"Saved class list → {app_dir / LABEL_FILE}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Train Maize Disease Specialist Head')
    parser.add_argument('--data',    required=True,       help='Path to raw dataset root')
    parser.add_argument('--source',  default='plantvillage',
                        choices=['plantvillage', 'kaggle'],
                        help='Dataset format: plantvillage (Corn___*) or kaggle (Blight/ etc.)')
    parser.add_argument('--out',     default='data/maize_ready')
    parser.add_argument('--app-dir', default='.')
    parser.add_argument('--epochs',  type=int, default=75)
    parser.add_argument('--batch',   type=int, default=32)
    parser.add_argument('--device',  default='cpu')
    parser.add_argument('--aug-factor', type=int, default=3)
    parser.add_argument('--skip-prep',   action='store_true')
    parser.add_argument('--skip-export', action='store_true')
    args = parser.parse_args()

    raw_root  = Path(args.data)
    out_root  = Path(args.out)
    app_dir   = Path(args.app_dir)
    class_map = PLANTVILLAGE_CLASSES if args.source == 'plantvillage' else KAGGLE_CLASSES

    print("NOTE: The general disease_model.tflite already covers all 4 maize classes.")
    print("This specialist trades breadth for speed + reduced inter-class confusion.\n")

    if not args.skip_prep:
        if not raw_root.exists():
            print(f"Dataset not found at '{raw_root}'.")
            if args.source == 'plantvillage':
                print("Filter PlantVillage to Corn_* directories and point --data there.")
            else:
                print("Download: kaggle datasets download -d kaustavbiswal/maize-diseases "
                      f"-p {raw_root} --unzip")
            return

        print("=== Step 1: Building dataset ===")
        if out_root.exists():
            shutil.rmtree(out_root)
        build_dataset(raw_root, out_root, class_map, aug_factor=args.aug_factor)

    print("\n=== Step 2: Training YOLO11n-cls ===")
    best_pt = train(out_root, args.epochs, args.device, args.batch)

    if not args.skip_export:
        print("\n=== Step 3: Exporting to TFLite (INT8) ===")
        export_tflite(best_pt, app_dir, class_map)
        print(f"\nRestart the Streamlit app — it will auto-detect the maize specialist.")


if __name__ == '__main__':
    main()
