"""
train_pulse_swarm.py — Unified Mungbean + Blackgram YMD Specialist (YOLO11n-cls)

Joint-training strategy: both species share the same viral vector (Bemisia tabaci)
and produce visually identical Yellow Mosaic Disease (YMD) patterns. A single
3-class model is trained on pooled images; crop-specific treatment advice is
delivered by the Streamlit selectbox gatekeeper at inference time.

Target classes:
  yellow_mosaic   — bright yellow mottling / vein clearing, reduced leaf size;
                    characteristic "vein chlorosis → total chlorosis" progression.
  cercospora_spot — small circular spots, grayish centers, reddish-brown borders
                    (Cercospora canescens — common in humid monsoon conditions).
  healthy         — uniform dark-green erect foliage, no mottling or spots.

Datasets (mix freely — all map to the same 3 classes):
  Primary: ABCGMP Vigna Mungo / Radiata datasets (Kaggle)
  Supplementary: any directory containing YMD or Cercospora leaf images

Supported directory-naming conventions:
  Mungbean_Yellow_Mosaic_Disease/, Blackgram_Yellow_Mosaic/,
  Yellow_Mosaic/, YMD/, Cercospora_Leaf_Spot/, Cercospora_Spot/,
  Mungbean_Healthy/, Blackgram_Healthy/, Healthy/, Normal/
  (see CLASS_MAP below for the full list)

Kharif-season augmentation (June–October): diffuse monsoon light, wet glistening
leaves, moving shadows from overhead cloud cover, hand-held phone camera.
Aggressive HSV augmentation forces the model to learn structural chlorosis
(vein-clearing, mottling geometry) rather than simply detecting "yellow pixels" —
the critical distinction between pathogenic YMD and ordinary senescence or lighting.

Usage:
  python train_pulse_swarm.py --data data/vigna_raw
  python train_pulse_swarm.py --data data/vigna_raw --epochs 70 --device mps
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

# All recognised source directory names → target class label.
# Add new naming variants here as additional datasets are sourced.
CLASS_MAP: dict[str, str] = {
    # Yellow Mosaic variants — Mungbean (Vigna radiata)
    'Mungbean_Yellow_Mosaic_Disease':   'yellow_mosaic',
    'Mungbean_Yellow_Mosaic':           'yellow_mosaic',
    'mungbean_yellow_mosaic':           'yellow_mosaic',
    # Yellow Mosaic variants — Blackgram / Urdbean (Vigna mungo)
    'Blackgram_Yellow_Mosaic_Disease':  'yellow_mosaic',
    'Blackgram_Yellow_Mosaic':          'yellow_mosaic',
    'blackgram_yellow_mosaic':          'yellow_mosaic',
    'Urdbean_Yellow_Mosaic':            'yellow_mosaic',
    # Yellow Mosaic variants — generic
    'Yellow_Mosaic_Disease':            'yellow_mosaic',
    'Yellow_Mosaic':                    'yellow_mosaic',
    'yellow_mosaic':                    'yellow_mosaic',
    'YMD':                              'yellow_mosaic',
    # Cercospora Leaf Spot variants
    'Mungbean_Cercospora_Leaf_Spot':    'cercospora_spot',
    'Blackgram_Cercospora_Leaf_Spot':   'cercospora_spot',
    'Cercospora_Leaf_Spot':             'cercospora_spot',
    'Cercospora_Spot':                  'cercospora_spot',
    'cercospora_spot':                  'cercospora_spot',
    'CercosporaLeafSpot':               'cercospora_spot',
    # Healthy variants — Mungbean
    'Mungbean_Healthy':                 'healthy',
    'mungbean_healthy':                 'healthy',
    # Healthy variants — Blackgram
    'Blackgram_Healthy':                'healthy',
    'blackgram_healthy':                'healthy',
    # Healthy variants — generic
    'Healthy':                          'healthy',
    'healthy':                          'healthy',
    'Normal':                           'healthy',
    'normal':                           'healthy',
}

LABEL_FILE               = 'pulse_swarm_classes.npy'
VAL_SPLIT                = 0.15
SEED                     = 42
IMG_SIZE                 = 224
MIN_IMAGES_PER_CLASS     = 200


# ---------------------------------------------------------------------------
# Step 1: Build dataset
# ---------------------------------------------------------------------------

def build_dataset(raw_root: Path, out_root: Path, aug_factor: int) -> list[str]:
    """
    Walk raw_root one level deep. Map recognised directory names to target
    classes via CLASS_MAP; pool images from multiple source dirs that share
    the same target class (e.g., Mungbean_Yellow_Mosaic +
    Blackgram_Yellow_Mosaic → yellow_mosaic).

    Returns sorted list of class names written.
    """
    try:
        import albumentations as A
    except ImportError:
        raise SystemExit("Install albumentations: pip install albumentations")

    # Kharif field conditions: aggressive HSV teaches structural chlorosis,
    # not "yellow pixel" detection.  RandomShadow simulates cloud-diffuse light.
    aug_pipeline = A.Compose([
        A.HueSaturationValue(hue_shift_limit=20, sat_shift_limit=45,
                             val_shift_limit=30, p=0.85),
        A.RandomBrightnessContrast(brightness_limit=0.40, contrast_limit=0.35, p=0.80),
        A.RandomShadow(shadow_roi=(0, 0.0, 1, 1), num_shadows_lower=1,
                       num_shadows_upper=2, shadow_dimension=5, p=0.30),
        A.GaussNoise(var_limit=(10.0, 45.0), p=0.40),
        A.MotionBlur(blur_limit=5, p=0.25),
        A.CoarseDropout(max_holes=8, max_height=18, max_width=18,
                        fill_value=0, p=0.35),
        A.RandomRotate90(p=0.5),
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.25),
        A.Resize(IMG_SIZE, IMG_SIZE),
    ])
    resize_only = A.Resize(IMG_SIZE, IMG_SIZE)

    random.seed(SEED)
    np.random.seed(SEED)

    # Aggregate all images per target class first, then split
    class_images: dict[str, list[Path]] = {}

    matched = 0
    for dir_path in sorted(raw_root.iterdir()):
        if not dir_path.is_dir():
            continue
        target = CLASS_MAP.get(dir_path.name)
        if target is None:
            print(f"  [SKIP] '{dir_path.name}' — not in CLASS_MAP")
            continue

        images = (list(dir_path.glob('*.jpg')) + list(dir_path.glob('*.jpeg'))
                  + list(dir_path.glob('*.png')) + list(dir_path.glob('*.JPG'))
                  + list(dir_path.glob('*.PNG')))
        if not images:
            continue

        matched += 1
        class_images.setdefault(target, []).extend(images)
        print(f"  {dir_path.name:45s} → {target}  ({len(images)} images)")

    if matched == 0:
        print(
            f"\nWARNING: No recognised directories found in '{raw_root}'.\n"
            "Check directory names against CLASS_MAP in train_pulse_swarm.py.\n"
            "Download datasets from Kaggle ABCGMP Vigna Mungo/Radiata pages."
        )
        return []

    # Write splits
    written_classes = []
    for target, images in sorted(class_images.items()):
        random.shuffle(images)
        n_val   = max(1, int(len(images) * VAL_SPLIT))
        val_imgs   = images[:n_val]
        train_imgs = images[n_val:]

        n_train = len(train_imgs)
        if n_train < MIN_IMAGES_PER_CLASS:
            print(
                f"  WARNING: '{target}' has only {n_train} base training images "
                f"(aug_factor={aug_factor} → ~{n_train * aug_factor} samples). "
                f"Collect ≥{MIN_IMAGES_PER_CLASS} distinct photos for reliable accuracy."
            )

        print(f"  → {target:20s}  total={len(images)}  "
              f"train={n_train} (×{aug_factor} aug)  val={len(val_imgs)}")

        for split, img_list in [('val', val_imgs), ('train', train_imgs)]:
            dest = out_root / split / target
            dest.mkdir(parents=True, exist_ok=True)
            for img_path in img_list:
                try:
                    img_np = np.array(Image.open(img_path).convert('RGB'))
                except Exception:
                    continue

                out = resize_only(image=img_np)['image']
                # Use a unique name prefix to avoid collisions when pooling
                # images from multiple source directories
                dest_name = f"{img_path.parent.name}__{img_path.name}"
                Image.fromarray(out).save(dest / dest_name)

                if split == 'train':
                    stem   = dest_name.rsplit('.', 1)[0]
                    suffix = '.' + dest_name.rsplit('.', 1)[-1]
                    for k in range(aug_factor):
                        aug = aug_pipeline(image=img_np)['image']
                        Image.fromarray(aug).save(dest / f"{stem}_aug{k}{suffix}")

        written_classes.append(target)

    print(f"\nFinal classes ({len(written_classes)}): {sorted(written_classes)}")
    return sorted(written_classes)


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
        project='runs/pulse_swarm',
        name='v1',
        augment=False,   # data already pre-augmented in build_dataset()
        mosaic=0.0,      # mosaic blends 4 images — destroys single-leaf chlorosis patterns
        patience=15,
        save_period=10,
        verbose=True,
    )

    best_pt = Path(results.save_dir) / 'weights' / 'best.pt'
    print(f"\nBest weights: {best_pt}")
    return best_pt


# ---------------------------------------------------------------------------
# Step 3: Export
# ---------------------------------------------------------------------------

def export_tflite(pt_path: Path, app_dir: Path, classes: list[str]) -> None:
    """Export INT8 TFLite and save the class label list into the app root."""
    from ultralytics import YOLO

    model   = YOLO(str(pt_path))
    exp_out = model.export(format='tflite', imgsz=IMG_SIZE, int8=True)

    tflite_dst = app_dir / 'pulse_swarm_model.tflite'
    shutil.copy(Path(exp_out), tflite_dst)
    print(f"Copied TFLite model → {tflite_dst}")

    # Save sorted class list explicitly — never rely on model.names (it's a
    # {int: str} dict and np.array() on a dict produces an unusable object array).
    np.save(app_dir / LABEL_FILE, np.array(sorted(classes)))
    print(f"Classes ({len(classes)}): {sorted(classes)}")
    print(f"Saved class list → {app_dir / LABEL_FILE}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Train Mungbean + Blackgram YMD Pulse Swarm Specialist (YOLO11n-cls)'
    )
    parser.add_argument(
        '--data', required=True,
        help='Root directory containing disease-class subdirectories '
             '(Mungbean_Yellow_Mosaic/, Blackgram_Healthy/, etc.)'
    )
    parser.add_argument('--out',        default='data/pulse_swarm_ready',
                        help='Processed dataset output directory')
    parser.add_argument('--app-dir',    default='.',
                        help='App root to copy final model files into')
    parser.add_argument('--epochs',     type=int, default=70)
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

    raw_root = Path(args.data)
    out_root = Path(args.out)
    app_dir  = Path(args.app_dir)

    print(
        "Joint-training strategy: Mungbean + Blackgram YMD images train a single\n"
        "model. Crop-specific treatment advice is provided by the Streamlit selectbox.\n"
    )

    classes: list[str] = []
    if not args.skip_prep:
        if not raw_root.exists():
            print(f"\nDataset not found at '{raw_root}'.")
            print("Download ABCGMP Vigna datasets from Kaggle and extract to that path.")
            return

        print(f"=== Step 1: Building joint dataset (aug_factor={args.aug_factor}) ===")
        if out_root.exists():
            shutil.rmtree(out_root)
        classes = build_dataset(raw_root, out_root, aug_factor=args.aug_factor)

        for split in ['train', 'val']:
            print(f"\n{split} distribution:")
            split_dir = out_root / split
            if split_dir.exists():
                for cls_dir in sorted(split_dir.iterdir()):
                    n = sum(1 for _ in cls_dir.iterdir())
                    print(f"  {cls_dir.name:25s} {n:5d} images")
    else:
        print("Skipping data prep (--skip-prep)")
        train_dir = out_root / 'train'
        if train_dir.exists():
            classes = sorted(d.name for d in train_dir.iterdir() if d.is_dir())
        if not classes:
            print("WARNING: Could not determine class list from existing dataset.")

    print("\n=== Step 2: Training YOLO11n-cls (joint Mungbean + Blackgram) ===")
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
        print("\nRestart the Streamlit app — it will auto-detect the pulse swarm specialist.")
    else:
        print(f"\nSkipped export. Best weights at: {best_pt}")


if __name__ == '__main__':
    main()
