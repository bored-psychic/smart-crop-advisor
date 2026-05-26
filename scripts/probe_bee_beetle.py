"""
Probe: measure Bee↔Beetle confusion on held-out iNat clips.

Branch C (2026-05-26) — Bee↔Beetle pivot. Falsified Branch A (monoculture)
diagnostic motivated this: Bee→Beetle 12.3% test-fold confusion (matrix row 0
= [53, 9, 1, 3, 2, 4, 0, 1] → 9/73) is the next-worst off-diagonal and isn't
monoculture-induced. Beetle→Bee is only 2.7% (row 1, [1, 28, …] → 1/37) — the
confusion is asymmetric, so this probe reports both directions but the gate
(if any) will fire only on top1=Beetle (see plan adaptive-munching-mitten.md).

Sources:
  (1) Held-out iNat Apoidea/Coleoptera clips not in data/audio_samples/.
  (2) Synthetic mixed overlays are DELIBERATELY omitted — they answer a
      different question (overlap energy) than the held-out one (out-of-train
      acoustic-overlap measurement).

Outputs /tmp/bee_beetle_probe_results.json with per-source confusion stats.
This script DOES NOT modify any model — it's pure measurement.

USAGE
-----
    # Full probe (~5–15 min depending on iNat throttle):
    python scripts/probe_bee_beetle.py

    # Skip iNat fetch and reuse a cached probe dir:
    python scripts/probe_bee_beetle.py --skip-fetch \\
        --probe-dir /tmp/bee_beetle_probe

    # xc fallback (NOT YET IMPLEMENTED — single point of extension):
    python scripts/probe_bee_beetle.py --source xc
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bee_beetle_probe")

BEE = {"Bee"}
BEETLE = {"Beetle"}

PROBE_INAT_TAXA = {
    "Bee":    ["Apis", "Bombus", "Xylocopa", "Halictus", "Osmia",
               "Megachile", "Anthophora", "Andrena"],
    "Beetle": ["Cerambycidae", "Elateridae", "Passalidae", "Lucanus",
               "Dynastinae", "Scolytinae", "Dytiscidae", "Prionus"],
}

INAT_API = "https://api.inaturalist.org/v1/observations"


def bb_group(label: str) -> Optional[str]:
    """Map a class label to {'bee', 'beetle', None}."""
    if label in BEE:
        return "bee"
    if label in BEETLE:
        return "beetle"
    return None


def _existing_inat_keys(species: str) -> set[str]:
    """Return set of inat observation/sound keys already present in training set.

    Filename convention: `inat_<obs_id>_<sound_id>.wav` -> key `<obs_id>_<sound_id>`.
    Used to filter probe fetch to genuinely held-out clips.
    """
    keys: set[str] = set()
    src = REPO_ROOT / "data" / "audio_samples" / species
    if not src.exists():
        return keys
    pat = re.compile(r"^inat_(\d+)_(\d+)\.wav$")
    for f in src.glob("inat_*.wav"):
        m = pat.match(f.name)
        if m:
            keys.add(f"{m.group(1)}_{m.group(2)}")
    return keys


def fetch_probe_inat(probe_dir: Path, max_per_species: int = 60) -> dict[str, int]:
    """Fetch held-out iNat clips for our 2 target classes (Bee, Beetle).

    Filters out any iNat (obs_id, sound_id) pair already present in
    data/audio_samples/<species>/. Returns per-species counts.
    """
    import requests
    import librosa

    counts: dict[str, int] = {sp: 0 for sp in PROBE_INAT_TAXA}
    cache_dir = REPO_ROOT / "data" / "_cache" / "bee_beetle_probe"
    cache_dir.mkdir(parents=True, exist_ok=True)

    for species, taxa in PROBE_INAT_TAXA.items():
        existing = _existing_inat_keys(species)
        group = bb_group(species)
        if group is None:
            continue
        dest_dir = probe_dir / group
        dest_dir.mkdir(parents=True, exist_ok=True)
        log.info("iNat %s: %d already in training (skipping)", species, len(existing))

        for taxon_name in taxa:
            if counts[species] >= max_per_species:
                break
            page = 1
            while counts[species] < max_per_species and page <= 50:
                try:
                    r = requests.get(
                        INAT_API,
                        params={"taxon_name": taxon_name, "sounds": "true",
                                "per_page": 50, "page": page},
                        timeout=30,
                    )
                    r.raise_for_status()
                    payload = r.json()
                except Exception as exc:
                    log.warning("iNat %s/%s page %d failed: %s",
                                species, taxon_name, page, exc)
                    break

                results = payload.get("results") or []
                if not results:
                    break

                for obs in results:
                    if counts[species] >= max_per_species:
                        break
                    obs_id = obs.get("id")
                    for snd in (obs.get("sounds") or []):
                        sound_id = snd.get("id")
                        url = snd.get("file_url")
                        if not (obs_id and sound_id and url):
                            continue
                        key = f"{obs_id}_{sound_id}"
                        if key in existing:
                            continue
                        out = dest_dir / f"inat_{species}_{key}.wav"
                        if out.exists():
                            counts[species] += 1
                            break
                        try:
                            raw = requests.get(url, timeout=60).content
                            tmp = cache_dir / f"inat_{key}.bin"
                            tmp.write_bytes(raw)
                            pcm, _ = librosa.load(tmp, sr=16000, mono=True,
                                                  duration=10.0)
                            sf.write(out, pcm, 16000, subtype="PCM_16")
                            tmp.unlink(missing_ok=True)
                            counts[species] += 1
                            break
                        except Exception as exc:
                            log.warning("iNat %s/%s download/transcode failed: %s",
                                        species, key, exc)
                            continue
                    time.sleep(0.2)
                page += 1
        log.info("iNat %s: %d held-out clips fetched", species, counts[species])

    return counts


def assemble_probe_dir(probe_dir: Path, skip_fetch: bool,
                       max_per_species: int = 60) -> dict:
    """Assemble the probe set under `probe_dir/{bee,beetle}/`.

    Returns a dict describing the assembled set: { source -> count }.
    Raises SystemExit if either class is starved (<30 held-out).
    """
    probe_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("bee", "beetle"):
        (probe_dir / sub).mkdir(exist_ok=True)

    counts = {"bee": 0, "beetle": 0, "inat_fetched": {}}

    if not skip_fetch:
        log.info("Fetching held-out iNat clips under %s/{bee,beetle} …", probe_dir)
        inat_counts = fetch_probe_inat(probe_dir, max_per_species=max_per_species)
        counts["inat_fetched"] = inat_counts

    counts["bee"] = len(list((probe_dir / "bee").glob("*.wav")))
    counts["beetle"] = len(list((probe_dir / "beetle").glob("*.wav")))

    bee_n = counts["bee"]
    beetle_n = counts["beetle"]
    if bee_n < 30 or beetle_n < 30:
        raise SystemExit(
            f"iNat starvation: bee={bee_n}, beetle={beetle_n} (need ≥30 each). "
            f"Rerun with --source xc to fall back to xeno-canto."
        )

    return counts


def score_probe(probe_dir: Path) -> dict:
    """Run the current PANNs bundle over the probe set and return confusion stats.

    Asymmetric reporting (Branch C plan):
      true=Bee,    pred=Beetle  -> bee_to_beetle   (target failure)
      true=Beetle, pred=Bee     -> beetle_to_bee   (reverse, observational only)
    """
    from backend.ml.panns_model import load, PANNsAbstain
    bundle = load()

    by_source = {}
    for sub in ("bee", "beetle"):
        sub_dir = probe_dir / sub
        wavs = sorted(sub_dir.glob("*.wav"))
        if not wavs:
            continue
        stats = {"n": 0, "correct_group": 0,
                 "bee_to_beetle": 0, "beetle_to_bee": 0,
                 "other": 0, "abstain": 0,
                 "details": []}
        true_label = "Bee" if sub == "bee" else "Beetle"
        for wav in wavs:
            try:
                pcm, sr = sf.read(wav, dtype="float32", always_2d=False)
            except Exception:
                continue
            try:
                out = bundle.predict(pcm, sr)
                pred = out["pest"]
                conf = out.get("confidence", 0.0)
                top3 = out.get("top3", [])
                all_class_confidence = out.get("all_class_confidence", {})
            except PANNsAbstain:
                stats["abstain"] += 1
                stats["n"] += 1
                continue
            true_grp = bb_group(true_label)
            pred_grp = bb_group(pred)
            stats["n"] += 1
            if true_grp == pred_grp:
                stats["correct_group"] += 1
            elif true_label == "Bee" and pred == "Beetle":
                stats["bee_to_beetle"] += 1
                stats["details"].append({
                    "file": wav.name, "true": true_label, "pred": pred,
                    "confidence": conf,
                    "top3": top3,
                    "all_class_confidence": all_class_confidence,
                })
            elif true_label == "Beetle" and pred == "Bee":
                stats["beetle_to_bee"] += 1
                stats["details"].append({
                    "file": wav.name, "true": true_label, "pred": pred,
                    "confidence": conf,
                    "top3": top3,
                    "all_class_confidence": all_class_confidence,
                })
            else:
                stats["other"] += 1
                stats["details"].append({
                    "file": wav.name, "true": true_label, "pred": pred,
                    "confidence": conf,
                    "top3": top3,
                    "all_class_confidence": all_class_confidence,
                })
        by_source[sub] = stats

    agg = {"n": 0, "bee_to_beetle": 0, "beetle_to_bee": 0, "abstain": 0}
    for s in by_source.values():
        agg["n"] += s["n"]
        agg["bee_to_beetle"] += s["bee_to_beetle"]
        agg["beetle_to_bee"] += s["beetle_to_bee"]
        agg["abstain"] += s["abstain"]
    decided = agg["n"] - agg["abstain"]
    agg["bee_to_beetle_rate"] = (agg["bee_to_beetle"] / decided) if decided > 0 else 0.0
    agg["beetle_to_bee_rate"] = (agg["beetle_to_bee"] / decided) if decided > 0 else 0.0
    return {"by_source": by_source, "aggregate": agg}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-dir", type=Path, default=Path("/tmp/bee_beetle_probe"))
    ap.add_argument("--skip-fetch", action="store_true")
    ap.add_argument("--score-only", action="store_true",
                    help="Skip assembly, score the existing probe dir only")
    ap.add_argument("--max-per-species", type=int, default=60)
    ap.add_argument("--output", type=Path,
                    default=Path("/tmp/bee_beetle_probe_results.json"))
    ap.add_argument("--source", choices=["inat", "xc"], default="inat",
                    help="Audio source. Only 'inat' implemented; 'xc' fallback "
                         "is YAGNI until iNat starves.")
    args = ap.parse_args()

    if args.source == "xc":
        raise NotImplementedError(
            "xc fallback (fam:apidae / fam:scarabaeidae) not yet implemented. "
            "Extend fetch_probe_inat -> fetch_probe_xc here when iNat starves."
        )

    if not args.score_only:
        log.info("Assembling probe set under %s …", args.probe_dir)
        counts = assemble_probe_dir(args.probe_dir, skip_fetch=args.skip_fetch,
                                    max_per_species=args.max_per_species)
        log.info("Assembled: %s", counts)
    log.info("Scoring probe set …")
    results = score_probe(args.probe_dir)
    args.output.write_text(json.dumps(results, indent=2))
    log.info("Wrote %s", args.output)
    log.info("AGGREGATE bee→beetle: %.1f%% (%d / %d decided)",
             results["aggregate"]["bee_to_beetle_rate"] * 100,
             results["aggregate"]["bee_to_beetle"],
             results["aggregate"]["n"] - results["aggregate"]["abstain"])
    log.info("AGGREGATE beetle→bee: %.1f%% (%d / %d decided)",
             results["aggregate"]["beetle_to_bee_rate"] * 100,
             results["aggregate"]["beetle_to_bee"],
             results["aggregate"]["n"] - results["aggregate"]["abstain"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
