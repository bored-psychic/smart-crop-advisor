"""One-off diagnostic: does the head distribute-shift on xc Cricket the same way it
did on xc Grasshopper (12% other-class)? Cricket is the one class with built-in xc
training diversity; the comparison is the discriminator for the monoculture hypothesis."""

from __future__ import annotations
import json
import os
import sys
from collections import Counter
from pathlib import Path

import librosa
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.ml.panns_model import load, PANNsAbstain  # noqa: E402

TRAIN_CRICKET = REPO_ROOT / "data" / "audio_samples" / "Cricket"
PROBE_DIR = Path("/tmp/cricket_xc_probe/cricket")
RESULTS = Path("/tmp/cricket_xc_probe_results.json")

XC_API = "https://xeno-canto.org/api/3/recordings"
XC_KEY = os.environ.get("XC_API_KEY", "")

TARGET_N = 50
SR = 16000
DURATION = 10.0


def held_out_xc_ids() -> set[str]:
    """Return xc IDs already present in training so we exclude them."""
    return {
        p.stem.split("_")[1]
        for p in TRAIN_CRICKET.glob("xc_*.wav")
        if len(p.stem.split("_")) >= 2
    }


def fetch_xc_cricket(target_n: int, exclude_ids: set[str]) -> list[Path]:
    """Fetch xc Cricket recordings not in training. Returns local paths."""
    if not XC_KEY:
        print("ERROR: XC_API_KEY env var not set", file=sys.stderr)
        sys.exit(2)
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    fetched: list[Path] = []
    page = 1
    while len(fetched) < target_n and page <= 6:
        r = requests.get(
            XC_API,
            params={"query": "fam:gryllidae", "page": page, "key": XC_KEY},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        for rec in data.get("recordings", []):
            xc_id = str(rec.get("id"))
            if xc_id in exclude_ids:
                continue
            url = rec.get("file") or rec.get("file-name")
            if not url:
                continue
            if url.startswith("//"):
                url = "https:" + url
            try:
                audio = requests.get(url, timeout=120).content
            except Exception:
                continue
            out = PROBE_DIR / f"xc_{xc_id}_Cricket.wav"
            out.write_bytes(audio)
            fetched.append(out)
            print(f"fetched {out.name} ({len(fetched)}/{target_n})")
            if len(fetched) >= target_n:
                break
        page += 1
    return fetched


def score(clips: list[Path]) -> dict:
    """Run bundle.predict on each clip; bucket into correct / cross-group / other / abstain."""
    bundle = load()
    buckets: Counter[str] = Counter()
    cross_files: list[tuple[str, str, int]] = []
    other_files: list[tuple[str, str, int]] = []
    CRICKET_GROUP = {"Cricket"}
    ORTHOPTERA = {"Grasshopper", "Locust", "Cicada"}
    for clip in clips:
        try:
            y, _ = librosa.load(str(clip), sr=SR, duration=DURATION, mono=True)
            out = bundle.predict(y, SR)
        except PANNsAbstain:
            buckets["abstain"] += 1
            continue
        except Exception as e:
            print(f"skip {clip.name}: {e}", file=sys.stderr)
            continue
        pest = out["pest"]
        conf = int(out["confidence"])
        if pest in CRICKET_GROUP:
            buckets["correct_group"] += 1
        elif pest in ORTHOPTERA:
            buckets["cross_orthoptera"] += 1
            cross_files.append((clip.name, pest, conf))
        else:
            buckets["other"] += 1
            other_files.append((clip.name, pest, conf))
    return {
        "stats": dict(buckets),
        "n": sum(buckets.values()),
        "cross_orthoptera_files": cross_files,
        "other_files": other_files,
    }


def main() -> int:
    held_out = held_out_xc_ids()
    print(f"excluding {len(held_out)} xc IDs already in training")
    clips = sorted(PROBE_DIR.glob("xc_*_Cricket.wav"))
    if len(clips) < TARGET_N:
        fetch_xc_cricket(TARGET_N - len(clips), held_out)
        clips = sorted(PROBE_DIR.glob("xc_*_Cricket.wav"))
    print(f"scoring {len(clips)} clips...")
    result = score(clips)
    RESULTS.write_text(json.dumps(result, indent=2))
    print(json.dumps(result["stats"], indent=2))
    print(f"results -> {RESULTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
