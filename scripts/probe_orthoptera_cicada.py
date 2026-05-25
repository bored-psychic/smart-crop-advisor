"""
Probe: measure Orthoptera (Grasshopper+Locust) vs Cicada confusion under
production-shaped conditions.

Sources:
  (1) Held-out iNat Orthoptera/Cicadidae clips not in data/audio_samples/.
  (2) Synthetic pair-wise overlays (Cicada+Grasshopper at SNRs +5/+10 dB).
      0 dB excluded: at equal RMS, the "dominant" label is ambiguous.

Outputs /tmp/ortho_cicada_probe_results.json with per-source confusion stats.
This script DOES NOT modify any model — it's pure measurement.

USAGE
-----
    # Full probe (~5–15 min depending on iNat throttle):
    python scripts/probe_orthoptera_cicada.py

    # Skip iNat fetch and reuse a cached probe dir:
    python scripts/probe_orthoptera_cicada.py --skip-fetch \\
        --probe-dir /tmp/ortho_cicada_probe
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
log = logging.getLogger("ortho_probe")

ORTHOPTERA = {"Grasshopper", "Locust"}
CICADA = {"Cicada"}

# Subset of INAT_QUERIES from scripts/fetch_audio_dataset.py — just our 3 species.
PROBE_INAT_TAXA = {
    "Grasshopper": ["Chorthippus", "Acrididae", "Gomphocerinae", "Acrida",
                    "Melanoplinae", "Tettigoniidae", "Conocephalus", "Ruspolia"],
    "Locust": ["Locusta", "Schistocerca", "Nomadacris", "Dociostaurus",
               "Chortoicetes", "Melanoplus"],
    "Cicada": ["Magicicada", "Cicadidae", "Cryptotympana", "Tibicen",
               "Neotibicen", "Meimuna", "Graptopsaltria", "Dundubia"],
}

INAT_API = "https://api.inaturalist.org/v1/observations"


def ortho_group(label: str) -> Optional[str]:
    """Map a class label to {'orthoptera', 'cicada', None}."""
    if label in ORTHOPTERA:
        return "orthoptera"
    if label in CICADA:
        return "cicada"
    return None


def mix_at_snr(signal: np.ndarray, noise: np.ndarray, snr_db: float) -> np.ndarray:
    """Mix `noise` into `signal` at the given SNR (dB), returning float32.

    Both inputs assumed mono, same sample rate, same length. Output RMS-matches
    `signal` so the mix stays in the original signal's dynamic range.
    """
    rms_s = float(np.sqrt(np.mean(signal.astype(np.float64) ** 2)) + 1e-12)
    rms_n = float(np.sqrt(np.mean(noise.astype(np.float64) ** 2)) + 1e-12)
    target_rms_n = rms_s / (10.0 ** (snr_db / 20.0))
    scaled = noise * (target_rms_n / rms_n)
    mix = signal + scaled
    return mix.astype(np.float32)


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
    """Fetch held-out iNat clips for our 3 target species.

    Filters out any iNat (obs_id, sound_id) pair already present in
    data/audio_samples/<species>/. Returns per-species counts.
    """
    import requests
    import librosa

    counts: dict[str, int] = {sp: 0 for sp in PROBE_INAT_TAXA}
    cache_dir = REPO_ROOT / "data" / "_cache" / "ortho_probe"
    cache_dir.mkdir(parents=True, exist_ok=True)

    for species, taxa in PROBE_INAT_TAXA.items():
        existing = _existing_inat_keys(species)
        group = ortho_group(species)
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
    """Assemble the probe set under `probe_dir/{ortho,cicada,mixed}/`.

    Returns a dict describing the assembled set: { source -> count }.
    """
    probe_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("orthoptera", "cicada", "mixed"):
        (probe_dir / sub).mkdir(exist_ok=True)

    counts = {"orthoptera": 0, "cicada": 0, "mixed": 0, "inat_fetched": {}}

    # (1) Real held-out iNat fetch (Fix A1).
    if not skip_fetch:
        log.info("Fetching held-out iNat clips under %s/{orthoptera,cicada} …",
                 probe_dir)
        inat_counts = fetch_probe_inat(probe_dir, max_per_species=max_per_species)
        counts["inat_fetched"] = inat_counts

    # Recount on-disk in case --skip-fetch was passed or some downloads were
    # cached from a previous run.
    counts["orthoptera"] = len(list((probe_dir / "orthoptera").glob("*.wav")))
    counts["cicada"] = len(list((probe_dir / "cicada").glob("*.wav")))

    held_out_total = counts["orthoptera"] + counts["cicada"]
    assert held_out_total >= 30, (
        f"iNat fetch produced too few held-out clips: orthoptera={counts['orthoptera']}, "
        f"cicada={counts['cicada']} (need >=30 total). "
        "iNat taxa under Orthoptera/Cicadidae may be exhausted given existing "
        "training set; collect production clips instead (Path D in critique)."
    )

    # (2) Synthetic mixed overlays — Fix A2: drop SNR=0 dB, add +10 dB.
    train_ortho = sorted((REPO_ROOT / "data" / "audio_samples" / "Grasshopper")
                         .glob("*.wav"))[:20]
    train_cicada = sorted((REPO_ROOT / "data" / "audio_samples" / "Cicada")
                          .glob("*.wav"))[:20]
    pair_n = min(len(train_ortho), len(train_cicada), 20)

    for i in range(pair_n):
        try:
            sig_o, sr_o = sf.read(train_ortho[i], dtype="float32", always_2d=False)
            sig_c, sr_c = sf.read(train_cicada[i], dtype="float32", always_2d=False)
        except Exception as exc:
            log.warning("Skip pair %d: %s", i, exc)
            continue
        if sr_o != sr_c:
            continue
        n = min(sig_o.size, sig_c.size, sr_o * 4)
        sig_o, sig_c = sig_o[:n], sig_c[:n]
        for snr_db, dominant in [(5.0, "ortho"), (10.0, "ortho"),
                                  (5.0, "cicada"), (10.0, "cicada")]:
            if dominant == "ortho":
                mix = mix_at_snr(sig_o, sig_c, snr_db)
                true_label = "Grasshopper"
            else:
                mix = mix_at_snr(sig_c, sig_o, snr_db)
                true_label = "Cicada"
            name = f"mix_{i:03d}_dom-{dominant}_snr{int(snr_db):+02d}_{true_label}.wav"
            sf.write(probe_dir / "mixed" / name, mix, sr_o, subtype="PCM_16")
            counts["mixed"] += 1

    return counts


def score_probe(probe_dir: Path) -> dict:
    """Run the current PANNs bundle over the probe set and return confusion stats.

    Confusion is reported with the Orthoptera-vs-Cicada GROUPING:
      true=ortho,pred=cicada     ← false positive Cicada
      true=cicada,pred=ortho     ← false positive Orthoptera
    """
    from backend.ml.panns_model import load, PANNsAbstain
    bundle = load()

    by_source = {}
    for sub in ("orthoptera", "cicada", "mixed"):
        sub_dir = probe_dir / sub
        wavs = sorted(sub_dir.glob("*.wav"))
        if not wavs:
            continue
        stats = {"n": 0, "correct_group": 0, "cross_group": 0, "other": 0,
                 "abstain": 0, "details": []}
        for wav in wavs:
            try:
                pcm, sr = sf.read(wav, dtype="float32", always_2d=False)
            except Exception:
                continue
            if sub == "mixed":
                # Filename: mix_NNN_dom-XXX_snr+SS_LABEL.wav
                true_label = wav.stem.split("_")[-1]
            elif sub == "orthoptera":
                # Held-out iNat ortho clips: filename `inat_<Species>_<key>.wav`
                # use the species in the filename as ground truth.
                parts = wav.stem.split("_")
                true_label = parts[1] if len(parts) > 2 and parts[1] in ORTHOPTERA else "Grasshopper"
            else:
                true_label = "Cicada"
            try:
                out = bundle.predict(pcm, sr)
                pred = out["pest"]
                conf = out.get("confidence", 0.0)
            except PANNsAbstain:
                stats["abstain"] += 1
                stats["n"] += 1
                continue
            true_grp = ortho_group(true_label)
            pred_grp = ortho_group(pred)
            stats["n"] += 1
            if true_grp == pred_grp:
                stats["correct_group"] += 1
            elif true_grp and pred_grp and true_grp != pred_grp:
                stats["cross_group"] += 1
                stats["details"].append({
                    "file": wav.name, "true": true_label, "pred": pred,
                    "confidence": conf,
                })
            else:
                stats["other"] += 1
        by_source[sub] = stats

    agg = {"n": 0, "cross_group": 0, "abstain": 0}
    for s in by_source.values():
        agg["n"] += s["n"]
        agg["cross_group"] += s["cross_group"]
        agg["abstain"] += s["abstain"]
    decided = agg["n"] - agg["abstain"]
    agg["cross_group_rate"] = (agg["cross_group"] / decided) if decided > 0 else 0.0
    return {"by_source": by_source, "aggregate": agg}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-dir", type=Path, default=Path("/tmp/ortho_cicada_probe"))
    ap.add_argument("--skip-fetch", action="store_true")
    ap.add_argument("--score-only", action="store_true",
                    help="Skip assembly, score the existing probe dir only")
    ap.add_argument("--max-per-species", type=int, default=60)
    ap.add_argument("--output", type=Path,
                    default=Path("/tmp/ortho_cicada_probe_results.json"))
    args = ap.parse_args()

    if not args.score_only:
        log.info("Assembling probe set under %s …", args.probe_dir)
        counts = assemble_probe_dir(args.probe_dir, skip_fetch=args.skip_fetch,
                                    max_per_species=args.max_per_species)
        log.info("Assembled: %s", counts)
    log.info("Scoring probe set …")
    results = score_probe(args.probe_dir)
    args.output.write_text(json.dumps(results, indent=2))
    log.info("Wrote %s", args.output)
    log.info("AGGREGATE cross-group confusion: %.1f%% (%d / %d decided)",
             results["aggregate"]["cross_group_rate"] * 100,
             results["aggregate"]["cross_group"],
             results["aggregate"]["n"] - results["aggregate"]["abstain"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
