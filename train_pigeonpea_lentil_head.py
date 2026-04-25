"""
train_pigeonpea_lentil_head.py — Pigeonpea + Lentil Disease Specialist (YOLO11n-cls)

Joint-training strategy: both crops share agronomically adjacent disease categories
(mosaic viruses, vascular wilt, rust fungi). A single 4-class model covers both;
crop-specific treatment advice is delivered by the Streamlit selectbox at inference time.

Target classes:
  sterility_mosaic  Pigeonpea Sterility Mosaic Virus (PPSMV), vector: Aceria cajani
                    mite — mottled light-green leaves, sterile shoots, no pod set.
  wilt              Fusarium udum (Pigeonpea) — progressive yellowing, vascular
                    browning of stem cross-section, plant death.
  rust              Uromyces viciae-fabae (Lentil) — orange-brown powdery pustules
                    on leaves and stems; Puccinia spp. in other legumes.
  healthy           Uniform dark-green foliage from either species.

Datasets (recommended):
  Pigeonpea SMD / Wilt — any Kaggle pigeonpea disease dataset; search:
      "pigeonpea sterility mosaic", "toor dal disease", "arhar disease"
  Lentil Rust — CLFD (Crop Leaf Fungal Disease) dataset or:
      kaggle datasets download -d nafisur/lentil-leaf-disease

Supported directory-naming conventions (see CLASS_MAP for full list):
  Pigeonpea_Sterility_Mosaic/, SMD/, Mosaic/,
  Pigeonpea_Wilt/, Wilt/, Fusarium_Wilt/,
  Lentil_Rust/, Rust/,
  Pigeonpea_Healthy/, Lentil_Healthy/, Healthy/

Mixed-season augmentation (Pigeonpea = kharif, Lentil = rabi):
  Conservative parameters that are robust across both lighting regimes —
  neither the extreme brightness of monsoon sun nor the low winter angle.

Usage:
  python train_pigeonpea_lentil_head.py --data data/pigeonpea_lentil_raw
  python train_pigeonpea_lentil_head.py --data data/pigeonpea_lentil_raw \\
      --epochs 75 --device mps
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

CLASS_MAP: dict[str, str] = {
    # Sterility Mosaic / SMD (Pigeonpea)
    'Pigeonpea_Sterility_Mosaic':           'sterility_mosaic',
    'Pigeonpea_Sterility_Mosaic_Disease':   'sterility_mosaic',
    'Sterility_Mosaic_Disease':             'sterility_mosaic',
    'Sterility_Mosaic':                     'sterility_mosaic',
    'sterility_mosaic':                     'sterility_mosaic',
    'SMD':                                  'sterility_mosaic',
    'Mosaic':                               'sterility_mosaic',
    # Fusarium Wilt (Pigeonpea)
    'Pigeonpea_Wilt':                       'wilt',
    'Pigeonpea_Fusarium_Wilt':              'wilt',
    'Fusarium_Wilt':                        'wilt',
    'Wilt':                                 'wilt',
    'wilt':                                 'wilt',
    # Rust (Lentil / general legume)
    'Lentil_Rust':                          'rust',
    'Rust':                                 'rust',
    'rust':                                 'rust',
    # Healthy — both species
    'Pigeonpea_Healthy':                    'healthy',
    'Lentil_Healthy':                       'healthy',
    'Healthy':                              'healthy',
    'healthy':                              'healthy',
    'Normal':                               'healthy',
    'normal':                               'healthy',
}

LABEL_FILE           = 'pigeonpea_lentil_classes.npy'
VAL_SPLIT            = 0.15
SEED                 = 42
IMG_SIZE             = 224
MIN_IMAGES_PER_CLASS = 150


# ---------------------------------------------------------------------------
# Step 1: Build dataset
# ---------------------------------------------------------------------------

def build_dataset(raw_root: Path, out_root: Path, aug_factor: int) -> list[str]:
    """
    Map source directories to target classes, pool images from multiple
    source dirs sharing the same class, and write augmented train/val splits.
    Mixed-season augmentation covers both kharif (pigeonpea) and rabi (lentil).
    """
    try:
        import albumentations as A
    except ImportError:
        raise SystemExit("Install albumentations: pip install albumentations")

    # Conservative mixed-season augmentation — robust to both monsoon and rabi lighting.
    # HSV shift is moderately aggressive (rust pustules and SMD mottling have distinct
    # hue signatures that should be learnable across lighting conditions).
    aug_pipeline = A.Compose([
        A.HueSaturationValue(hue_shift_limit=15, sat_shift_limit=35,
                             val_shift_limit=25, p=0.80),
        A.RandomBrightnessContrast(brightness_limit=0.35, contrast_limit=0.30, p=0.80),
        A.GaussNoise(var_limit=(8.0, 40.0), p=0.38),
        A.MotionBlur(blur_limit=5, p=0.25),
        A.CoarseDropout(max_holes=7, max_height=16, max_width=16,
                        fill_value=0, p=0.35),
        A.RandomRotate90(p=0.5),
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.25),
        A.Resize(IMG_SIZE, IMG_SIZE),
    ])
    resize_only = A.Resize(IMG_SIZE, IMG_SIZE)

    random.seed(SEED)
    np.random.seed(SEED)

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
            "Check directory names against CLASS_MAP in train_pigeonpea_lentil_head.py."
        )
        return []

    written_classes = []
    for target, images in sorted(class_images.items()):
        random.shuffle(images)
        n_val   = max(1, int(len(images) * VAL_SPLIT))
        val_imgs   = images[:n_val]
        train_imgs = images[n_val:]
        n_train    = len(train_imgs)

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

    results = model.train(
        data=str(data_dir),
        epochs=epochs,
        imgsz=IMG_SIZE,
        batch=batch,
        device=device,
        project='runs/pigeonpea_lentil',
        name='v1',
        augment=False,   # pre-augmented in build_dataset()
        mosaic=0.0,      # classification task — mosaic destroys single-leaf features
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
    from ultralytics import YOLO

    model   = YOLO(str(pt_path))
    exp_out = model.export(format='tflite', imgsz=IMG_SIZE, int8=True)

    tflite_dst = app_dir / 'pigeonpea_lentil_model.tflite'
    shutil.copy(Path(exp_out), tflite_dst)
    print(f"Copied TFLite model → {tflite_dst}")

    np.save(app_dir / LABEL_FILE, np.array(sorted(classes)))
    print(f"Classes ({len(classes)}): {sorted(classes)}")
    print(f"Saved class list → {app_dir / LABEL_FILE}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Train Pigeonpea + Lentil Disease Specialist (YOLO11n-cls)'
    )
    parser.add_argument(
        '--data', required=True,
        help='Root directory containing disease-class subdirectories '
             '(Pigeonpea_Sterility_Mosaic/, Lentil_Rust/, Healthy/, etc.)'
    )
    parser.add_argument('--out',        default='data/pigeonpea_lentil_ready')
    parser.add_argument('--app-dir',    default='.')
    parser.add_argument('--epochs',     type=int, default=75)
    parser.add_argument('--batch',      type=int, default=32)
    parser.add_argument('--device',     default='cpu')
    parser.add_argument('--aug-factor', type=int, default=3)
    parser.add_argument('--skip-prep',   action='store_true')
    parser.add_argument('--skip-export', action='store_true')
    args = parser.parse_args()

    raw_root = Path(args.data)
    out_root = Path(args.out)
    app_dir  = Path(args.app_dir)

    print(
        "Joint model: Pigeonpea (Sterility Mosaic + Wilt) + Lentil (Rust) + Healthy.\n"
        "Crop-specific treatment advice delivered by the Streamlit selectbox gatekeeper.\n"
    )

    classes: list[str] = []
    if not args.skip_prep:
        if not raw_root.exists():
            print(f"\nDataset not found at '{raw_root}'.")
            print("Download pigeonpea/lentil disease datasets from Kaggle and extract there.")
            return

        print(f"=== Step 1: Building dataset (aug_factor={args.aug_factor}) ===")
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

    print("\n=== Step 2: Training YOLO11n-cls ===")
    print(f"  epochs={args.epochs}  batch={args.batch}  device={args.device}")
    best_pt = train(out_root, args.epochs, args.device, args.batch)

    if not args.skip_export:
        if not classes:
            raise SystemExit("No class list available. Run without --skip-prep.")
        print("\n=== Step 3: Exporting to TFLite (INT8) ===")
        export_tflite(best_pt, app_dir, classes)
        print("\nRestart the Streamlit app — it will auto-detect the pigeonpea/lentil specialist.")
    else:
        print(f"\nSkipped export. Best weights at: {best_pt}")


if __name__ == '__main__':
    main()
