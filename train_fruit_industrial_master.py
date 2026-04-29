"""
train_fruit_industrial_master.py — Fruit & Industrial Crop Master Head (YOLO11n-cls)

Pools datasets for 12 high-value crops into a 27-class unified specialist:
  Mango, Banana, Pomegranate, Citrus/Orange, Papaya, Coconut,
  Cotton, Coffee, Jute, Grape (supplement), Apple (supplement)

Why a master head instead of per-crop specialists?
  These crops share visual feature spaces (fungal lesion texture, chlorosis
  gradients, surface necrosis) that benefit from joint feature extraction.
  Training together regularises the model against overfitting on small per-crop
  datasets, especially for Coconut, Jute, and Pomegranate where <2000 images
  are typically available.

imgsz=256: Fruit surface diseases (Mango Anthracnose, Citrus Greening blotchy
  mottle, Coffee Rust orange pustules) require more spatial resolution than
  leaf-patch diseases. 256 px captures fine surface texture within YOLO11n-cls
  compute budget.

"Bengaluru Summer" augmentation (March–May, 35–42°C):
  Harsh direct sun → extreme brightness/contrast shifts
  Dry dusty air → reduced saturation, haze blur
  Phone camera heat → colour noise, occasional flare
  Zero fog — explicitly excluded (contrast with kharif/chickpea scripts)

Datasets (recommended sources):
  Mango        : kaggle datasets download -d warcoder/mango-leaf-disease-dataset
  Banana       : kaggle datasets download -d joshuakyalo/banana-leaf-diseases-dataset
  Pomegranate  : any Kaggle "pomegranate disease" dataset
  Citrus/Orange: kaggle datasets download -d jonathansilva2020/orange-diseases-dataset
  Papaya       : kaggle datasets download -d seharnaqvi/papaya-disease-dataset
  Coconut      : kaggle datasets download -d vipoooool/new-plant-diseases-dataset (coconut subset)
  Cotton       : kaggle datasets download -d janmejaybhoi/cotton-disease-dataset
  Coffee       : kaggle datasets download -d alxmamaev/flowers-recognition (coffee subset)
                  OR kaggle datasets download -d gauravduttakiit/coffee-leaf-disease
  Jute         : ICAR open-access, or kaggle search "jute disease"
  Grape suppl. : PlantVillage grape directories (not covered by specialist heads)
  Apple suppl. : PlantVillage apple directories

Usage:
  python train_fruit_industrial_master.py --data data/fruit_raw
  python train_fruit_industrial_master.py --data data/fruit_raw --epochs 100 \\
      --device 0 --imgsz 256 --skip-export

Directory naming: see CLASS_MAP below — all naming variants from major Kaggle
datasets are included. Unknown directories are skipped with a warning.
"""

import argparse
import math
import os
import random
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# Target classes (27 + healthy = 28)
# ---------------------------------------------------------------------------
# Format: source_directory_name → master_class_label
# Keys cover PlantVillage naming, Kaggle dataset naming, and ABCGMP variants.
CLASS_MAP: dict[str, str] = {

    # ── Mango ────────────────────────────────────────────────────────────────
    'Mango_Anthracnose':             'mango_anthracnose',
    'mango_anthracnose':             'mango_anthracnose',
    'Anthracnose':                   'mango_anthracnose',    # dataset-specific; accept if in mango dir tree
    'Mango_Powdery_Mildew':          'mango_powdery_mildew',
    'mango_powdery_mildew':          'mango_powdery_mildew',
    'Mango_Sooty_Mould':             'mango_sooty_mould',
    'mango_sooty_mould':             'mango_sooty_mould',
    'Sooty_Mold':                    'mango_sooty_mould',
    'Mango_Bacterial_Canker':        'mango_bacterial_canker',
    'mango_bacterial_canker':        'mango_bacterial_canker',
    'Mango_Die_Back':                'mango_dieback',
    'mango_dieback':                 'mango_dieback',

    # ── Banana ───────────────────────────────────────────────────────────────
    'Banana_Sigatoka':               'banana_sigatoka',
    'Black_Sigatoka':                'banana_sigatoka',
    'Yellow_Sigatoka':               'banana_sigatoka',
    'banana_sigatoka':               'banana_sigatoka',
    'Sigatoka':                      'banana_sigatoka',
    'Banana_Cordana':                'banana_cordana',
    'banana_cordana':                'banana_cordana',
    'Cordana_Leaf_Spot':             'banana_cordana',
    'Banana_Bunchy_Top':             'banana_bunchy_top',
    'banana_bunchy_top':             'banana_bunchy_top',
    'Bunchy_Top':                    'banana_bunchy_top',
    'Banana_Panama_Wilt':            'banana_fusarium_wilt',
    'banana_fusarium_wilt':          'banana_fusarium_wilt',

    # ── Pomegranate ──────────────────────────────────────────────────────────
    'Pomegranate_Blight':            'pomegranate_blight',
    'pomegranate_blight':            'pomegranate_blight',
    'Bacterial_Blight_Pomegranate':  'pomegranate_blight',
    'Pomegranate_Cercospora':        'pomegranate_cercospora',
    'pomegranate_cercospora':        'pomegranate_cercospora',
    'Pomegranate_Fruit_Rot':         'pomegranate_fruit_rot',
    'pomegranate_fruit_rot':         'pomegranate_fruit_rot',

    # ── Citrus / Orange ──────────────────────────────────────────────────────
    'Citrus_Greening':               'citrus_greening',
    'citrus_greening':               'citrus_greening',
    'Orange_Greening':               'citrus_greening',
    'HLB':                           'citrus_greening',
    'Citrus_HLB':                    'citrus_greening',
    'Citrus_Canker':                 'citrus_canker',
    'citrus_canker':                 'citrus_canker',
    'Orange_Canker':                 'citrus_canker',
    'Citrus_Alternaria':             'citrus_alternaria',
    'citrus_alternaria':             'citrus_alternaria',

    # ── Papaya ───────────────────────────────────────────────────────────────
    'Papaya_Ringspot':               'papaya_ringspot',
    'papaya_ringspot':               'papaya_ringspot',
    'PRSV':                          'papaya_ringspot',
    'Papaya_Powdery_Mildew':         'papaya_powdery_mildew',
    'papaya_powdery_mildew':         'papaya_powdery_mildew',
    'Papaya_Anthracnose':            'papaya_anthracnose',
    'papaya_anthracnose':            'papaya_anthracnose',

    # ── Coconut ──────────────────────────────────────────────────────────────
    'Coconut_Bud_Rot':               'coconut_bud_rot',
    'coconut_bud_rot':               'coconut_bud_rot',
    'Bud_Rot':                       'coconut_bud_rot',
    'Coconut_Root_Wilt':             'coconut_root_wilt',
    'coconut_root_wilt':             'coconut_root_wilt',
    'Coconut_Leaf_Blight':           'coconut_leaf_blight',
    'coconut_leaf_blight':           'coconut_leaf_blight',

    # ── Cotton ───────────────────────────────────────────────────────────────
    'Cotton_Leaf_Curl':              'cotton_leaf_curl',
    'cotton_leaf_curl':              'cotton_leaf_curl',
    'CLCuV':                         'cotton_leaf_curl',
    'Cotton_Leaf_Curl_Virus':        'cotton_leaf_curl',
    'Cotton_Bacterial_Blight':       'cotton_bacterial_blight',
    'cotton_bacterial_blight':       'cotton_bacterial_blight',
    'Cotton_Alternaria':             'cotton_alternaria',
    'cotton_alternaria':             'cotton_alternaria',
    'Alternaria_Leaf_Spot_Cotton':   'cotton_alternaria',

    # ── Coffee ───────────────────────────────────────────────────────────────
    'Coffee_Rust':                   'coffee_rust',
    'coffee_rust':                   'coffee_rust',
    'Coffee_Leaf_Rust':              'coffee_rust',
    'Coffee_Brown_Eye_Spot':         'coffee_brown_eye_spot',
    'coffee_brown_eye_spot':         'coffee_brown_eye_spot',
    'Cercospora_Coffee':             'coffee_brown_eye_spot',

    # ── Jute ─────────────────────────────────────────────────────────────────
    'Jute_Stem_Rot':                 'jute_stem_rot',
    'jute_stem_rot':                 'jute_stem_rot',
    'Stem_Rot_Jute':                 'jute_stem_rot',
    'Jute_Anthracnose':              'jute_anthracnose',
    'jute_anthracnose':              'jute_anthracnose',

    # ── Grape (supplement — PlantVillage naming) ─────────────────────────────
    'Grape___Black_rot':             'grape_black_rot',
    'Grape_Black_Rot':               'grape_black_rot',
    'grape_black_rot':               'grape_black_rot',
    'Grape___Esca_(Black_Measles)':  'grape_esca',
    'Grape_Esca':                    'grape_esca',
    'grape_esca':                    'grape_esca',
    'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)': 'grape_leaf_blight',
    'Grape_Downy_Mildew':            'grape_downy_mildew',
    'grape_downy_mildew':            'grape_downy_mildew',

    # ── Apple (supplement — PlantVillage naming) ─────────────────────────────
    'Apple___Apple_scab':            'apple_scab',
    'Apple_Scab':                    'apple_scab',
    'apple_scab':                    'apple_scab',
    'Apple___Black_rot':             'apple_black_rot',
    'Apple_Black_Rot':               'apple_black_rot',
    'apple_black_rot':               'apple_black_rot',
    'Apple___Cedar_apple_rust':      'apple_cedar_rust',
    'Apple_Cedar_Rust':              'apple_cedar_rust',
    'Apple_Fire_Blight':             'apple_fire_blight',
    'apple_fire_blight':             'apple_fire_blight',

    # ── Healthy — all crops pooled ────────────────────────────────────────────
    'Mango_Healthy':                 'healthy',
    'Banana_Healthy':                'healthy',
    'Pomegranate_Healthy':           'healthy',
    'Citrus_Healthy':                'healthy',
    'Orange_Healthy':                'healthy',
    'Papaya_Healthy':                'healthy',
    'Coconut_Healthy':               'healthy',
    'Cotton_Healthy':                'healthy',
    'Coffee_Healthy':                'healthy',
    'Jute_Healthy':                  'healthy',
    'Grape___healthy':               'healthy',
    'Apple___healthy':               'healthy',
    'Healthy':                       'healthy',
    'healthy':                       'healthy',
    'Normal':                        'healthy',
    'mango_healthy':                 'healthy',
    'banana_healthy':                'healthy',
}

LABEL_FILE           = 'fruit_master_classes.npy'
VAL_SPLIT            = 0.15
SEED                 = 42
IMG_SIZE             = 256     # larger than standard 224 for fruit surface texture
MIN_IMAGES_PER_CLASS = 200


# ---------------------------------------------------------------------------
# Step 1: Build dataset
# ---------------------------------------------------------------------------

def build_dataset(raw_root: Path, out_root: Path, aug_factor: int) -> list[str]:
    """
    Walk raw_root one level deep; map recognised dirs to master classes via
    CLASS_MAP; pool images from multiple sources into each target class.
    Applies "Bengaluru Summer" augmentation to training images.
    Returns sorted list of classes written.
    """
    try:
        import albumentations as A
    except ImportError:
        raise SystemExit("Install albumentations: pip install albumentations")

    # Bengaluru Summer (March–May): 35–42°C, harsh direct sun, dry dusty air.
    # Extreme brightness range; RandomGamma models harsh direct vs hazy indirect
    # sun; NO fog (contrast with kharif/rabi augmentation profiles).
    aug_pipeline = A.Compose([
        A.RandomBrightnessContrast(brightness_limit=0.50, contrast_limit=0.45, p=0.85),
        A.HueSaturationValue(hue_shift_limit=18, sat_shift_limit=30,
                             val_shift_limit=35, p=0.80),
        A.RandomGamma(gamma_limit=(60, 140), p=0.35),   # harsh direct vs dusty-haze
        A.GaussNoise(var_limit=(12.0, 55.0), p=0.40),
        A.MotionBlur(blur_limit=7, p=0.30),
        A.CoarseDropout(max_holes=9, max_height=20, max_width=20,
                        fill_value=0, p=0.35),
        A.RandomRotate90(p=0.5),
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.25),
        A.Resize(IMG_SIZE, IMG_SIZE),
    ])
    resize_only = A.Resize(IMG_SIZE, IMG_SIZE)

    random.seed(SEED)
    np.random.seed(SEED)

    # Aggregate all images per target class before splitting
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
        print(f"  {dir_path.name:50s} → {target}  ({len(images)} images)")

    if matched == 0:
        print(
            f"\nWARNING: No recognised directories found in '{raw_root}'.\n"
            "Check directory names against CLASS_MAP in train_fruit_industrial_master.py."
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
                f"Collect ≥{MIN_IMAGES_PER_CLASS} images before deploying."
            )

        print(f"  → {target:35s}  total={len(images)}  "
              f"train={n_train} (×{aug_factor} aug)  val={len(val_imgs)}")

        for split, img_list in [('val', val_imgs), ('train', train_imgs)]:
            dest = out_root / split / target
            dest.mkdir(parents=True, exist_ok=True)
            for img_path in img_list:
                try:
                    img_np = np.array(Image.open(img_path).convert('RGB'))
                except Exception:
                    continue

                out      = resize_only(image=img_np)['image']
                # Collision-safe: prefix with source directory name
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

def train(data_dir: Path, epochs: int, device: str, batch: int,
          imgsz: int) -> Path:
    try:
        from ultralytics import YOLO
    except ImportError:
        raise SystemExit("Install ultralytics: pip install ultralytics")

    model = YOLO('yolo11n-cls.pt')

    print(f"\n  imgsz={imgsz} — increased from standard 224 for fruit surface texture.")
    print(f"  Realistic CPU inference (deployed TFLite INT8): 35–80 ms/image at 256 px.")

    results = model.train(
        data=str(data_dir),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project='runs/fruit_master',
        name='v1',
        augment=False,   # data already pre-augmented in build_dataset()
        mosaic=0.0,      # classification — mosaic destroys single-disease-area patterns
        patience=20,     # more patience for high class count (27+ classes)
        save_period=10,
        verbose=True,
    )

    best_pt = Path(results.save_dir) / 'weights' / 'best.pt'
    print(f"\nBest weights: {best_pt}")
    return best_pt


# ---------------------------------------------------------------------------
# Step 3: Export
# ---------------------------------------------------------------------------

def export_tflite(pt_path: Path, app_dir: Path, classes: list[str],
                  imgsz: int) -> None:
    from ultralytics import YOLO

    model   = YOLO(str(pt_path))
    exp_out = model.export(format='tflite', imgsz=imgsz, int8=True)

    tflite_dst = app_dir / 'fruit_master_model.tflite'
    shutil.copy(Path(exp_out), tflite_dst)
    print(f"Copied TFLite model → {tflite_dst}")

    # Save sorted class list explicitly — NOT model.names (it's a {int:str} dict;
    # np.array() on a dict produces a single-element object array, not a list).
    np.save(app_dir / LABEL_FILE, np.array(sorted(classes)))
    print(f"Classes ({len(classes)}): {sorted(classes)}")
    print(f"Saved class list → {app_dir / LABEL_FILE}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Train Fruit & Industrial Crop Master Head (YOLO11n-cls, 27+ classes)'
    )
    parser.add_argument(
        '--data', required=True,
        help='Root directory containing disease-class subdirectories '
             '(Mango_Anthracnose/, Banana_Sigatoka/, Cotton_Leaf_Curl/, etc.)'
    )
    parser.add_argument('--out',        default='data/fruit_master_ready',
                        help='Processed dataset output directory')
    parser.add_argument('--app-dir',    default='.',
                        help='App root to copy final model files into')
    parser.add_argument('--epochs',     type=int, default=100,
                        help='Training epochs (100 recommended for 27+ classes)')
    parser.add_argument('--batch',      type=int, default=32)
    parser.add_argument('--imgsz',      type=int, default=256,
                        help='Input resolution (256 recommended for fruit texture)')
    parser.add_argument('--device',     default='cpu',
                        help='cpu | 0 (cuda) | mps')
    parser.add_argument('--aug-factor', type=int, default=3,
                        help='Augmented copies per training image')
    parser.add_argument('--skip-prep',   action='store_true',
                        help='Skip data prep (dataset already built in --out)')
    parser.add_argument('--skip-export', action='store_true',
                        help='Skip TFLite export (keep .pt only)')
    args = parser.parse_args()

    raw_root = Path(args.data)
    out_root = Path(args.out)
    app_dir  = Path(args.app_dir)

    print(
        "Master Head: 27+ disease classes across Mango, Banana, Pomegranate,\n"
        "Citrus, Papaya, Coconut, Cotton, Coffee, Jute, Grape, Apple.\n"
        f"Resolution: {args.imgsz}×{args.imgsz} px  Epochs: {args.epochs}\n"
    )

    classes: list[str] = []

    if not args.skip_prep:
        if not raw_root.exists():
            print(f"\nDataset not found at '{raw_root}'.")
            print("See module docstring for recommended Kaggle dataset downloads.")
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
                    print(f"  {cls_dir.name:40s} {n:5d} images")
    else:
        print("Skipping data prep (--skip-prep)")
        train_dir = out_root / 'train'
        if train_dir.exists():
            classes = sorted(d.name for d in train_dir.iterdir() if d.is_dir())
        if not classes:
            print("WARNING: Could not determine class list from existing dataset.")

    print("\n=== Step 2: Training YOLO11n-cls (100-epoch marathon) ===")
    print(f"  epochs={args.epochs}  batch={args.batch}  "
          f"device={args.device}  imgsz={args.imgsz}")
    best_pt = train(out_root, args.epochs, args.device, args.batch, args.imgsz)

    if not args.skip_export:
        if not classes:
            raise SystemExit("No class list available. Run without --skip-prep.")
        print("\n=== Step 3: Exporting to TFLite (INT8) ===")
        export_tflite(best_pt, app_dir, classes, args.imgsz)
        print("\nRestart the Streamlit app — it will auto-detect the fruit master model.")
    else:
        print(f"\nSkipped export. Best weights at: {best_pt}")


if __name__ == '__main__':
    main()
