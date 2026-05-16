"""
Fetch real audio clips for the YAMNet acoustic classifier head.

Pulls clips from public bioacoustic datasets, normalizes each to 16 kHz mono
WAV (the format YAMNet expects), and writes them under
`data/audio_samples/<species>/<source>_<id>.wav`.

Sources (most reliable first):
    1. ESC-50  — small, well-curated, has cricket + insect categories
    2. Xeno-canto — large API-driven archive (mostly birds, but has crickets,
                    cicadas, grasshoppers, locusts, bees, mosquitoes if you
                    search by Latin name)
    3. iNaturalist  — sound observations; supplemental for beetles, moths
                      (manual download recommended; we do best-effort search)

Target: ≥100 clips per species, ~3-5 s each. Coverage report printed at the
end so you can see which species need extra manual sourcing.

USAGE
-----
    python scripts/fetch_audio_dataset.py                # fetch all sources
    python scripts/fetch_audio_dataset.py --skip-esc50   # skip ESC-50
    python scripts/fetch_audio_dataset.py --xc-only      # Xeno-canto only
    python scripts/fetch_audio_dataset.py --max-per-species 50

DEPENDENCIES
------------
    pip install requests librosa soundfile  # all already in requirements.txt
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path
from typing import Optional

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("fetch_audio")

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "audio_samples"
CACHE_DIR = REPO_ROOT / "data" / "_cache"

# ── Class set (must match backend/core/constants.PEST_META keys) ──────────────
SPECIES = [
    "Bee", "Locust", "Cicada", "Cricket",
    "Grasshopper", "Beetle", "Wasp",
]

# Non-biological training class — feeds the bio/non-bio gate in the two-stage
# local pipeline. Populated from ESC-50 ambient-noise categories.
NON_BIO_CLASS = "Non-biological"


def _slug(species: str) -> str:
    """Filesystem-safe folder name (Moth/Butterfly → Moth_Butterfly)."""
    return species.replace("/", "_").replace(" ", "_")


# ── ESC-50 ────────────────────────────────────────────────────────────────────
ESC50_ZIP_URL = "https://github.com/karolpiczak/ESC-50/archive/refs/heads/master.zip"
ESC50_CATEGORY_TO_SPECIES = {
    "cricket": "Cricket",
    "insects": "Cricket",   # ESC-50 "insects" is dominated by cricket-like
    # Non-biological ambient-noise categories → bio/non-bio gate training data.
    "wind": NON_BIO_CLASS,
    "rain": NON_BIO_CLASS,
    "sea_waves": NON_BIO_CLASS,
    "crackling_fire": NON_BIO_CLASS,
    "engine": NON_BIO_CLASS,
    "clock_tick": NON_BIO_CLASS,
    "water_drops": NON_BIO_CLASS,
    "thunderstorm": NON_BIO_CLASS,
    "toilet_flush": NON_BIO_CLASS,
    "pouring_water": NON_BIO_CLASS,
}


def fetch_esc50(target_dir: Path, max_per_species: int) -> dict[str, int]:
    """Download ESC-50 zip once, extract clips for our classes."""
    counts: dict[str, int] = {sp: 0 for sp in SPECIES + [NON_BIO_CLASS]}
    zip_path = CACHE_DIR / "esc50.zip"

    if not zip_path.exists():
        log.info("Downloading ESC-50 (~600 MB) …")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        r = requests.get(ESC50_ZIP_URL, stream=True, timeout=300)
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            shutil.copyfileobj(r.raw, f)
        log.info("ESC-50 cached at %s", zip_path)

    with zipfile.ZipFile(zip_path) as zf:
        meta_name = next(n for n in zf.namelist() if n.endswith("meta/esc50.csv"))
        with zf.open(meta_name) as f:
            header = f.readline().decode().strip().split(",")
            fname_idx, cat_idx = header.index("filename"), header.index("category")
            rows = [line.decode().strip().split(",") for line in f.readlines()]

        for row in rows:
            fname, category = row[fname_idx], row[cat_idx]
            species = ESC50_CATEGORY_TO_SPECIES.get(category)
            if species is None:
                continue
            if counts[species] >= max_per_species:
                continue

            wav_member = next((n for n in zf.namelist() if n.endswith(f"audio/{fname}")), None)
            if wav_member is None:
                continue
            out = target_dir / _slug(species) / f"esc50_{fname}"
            out.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(wav_member) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst)
            counts[species] += 1

    return counts


# ── Xeno-canto ────────────────────────────────────────────────────────────────
XC_API = "https://xeno-canto.org/api/3/recordings"
XC_API_KEY = os.environ.get("XC_API_KEY", "")
# Search queries by species — Xeno-canto's `grp:` filter accepts insects
# (`grp:8`). We search by Latin name for precision.
XC_QUERIES = {
    "Cricket":        ["fam:gryllidae"],
    "Grasshopper":    ["fam:acrididae", "fam:tettigoniidae"],
}


def fetch_xeno_canto(target_dir: Path, max_per_species: int) -> dict[str, int]:
    """Search Xeno-canto by genus/family, download MP3s, transcode to 16k WAV."""
    import librosa
    import soundfile as sf

    counts: dict[str, int] = {sp: 0 for sp in SPECIES}
    for species, queries in XC_QUERIES.items():
        for query in queries:
            if counts[species] >= max_per_species:
                break
            page = 1
            while counts[species] < max_per_species and page <= 5:
                try:
                    r = requests.get(XC_API, params={"query": query, "page": page, "key": XC_API_KEY}, timeout=30)
                    r.raise_for_status()
                    payload = r.json()
                except Exception as exc:
                    log.warning("xeno-canto %s page %s failed: %s", query, page, exc)
                    break

                recordings = payload.get("recordings") or []
                if not recordings:
                    break

                for rec in recordings:
                    if counts[species] >= max_per_species:
                        break
                    rec_id = rec.get("id")
                    file_url = rec.get("file") or rec.get("file-name")
                    if not rec_id or not file_url:
                        continue
                    if not file_url.startswith("http"):
                        file_url = f"https:{file_url}"

                    out = target_dir / _slug(species) / f"xc_{rec_id}.wav"
                    if out.exists():
                        counts[species] += 1
                        continue

                    try:
                        mp3 = requests.get(file_url, timeout=60).content
                        # Write to a tmp file because librosa needs a path or
                        # an audioread-compatible buffer.
                        tmp = CACHE_DIR / f"xc_{rec_id}.mp3"
                        tmp.write_bytes(mp3)
                        pcm, _ = librosa.load(tmp, sr=16000, mono=True, duration=10.0)
                        out.parent.mkdir(parents=True, exist_ok=True)
                        sf.write(out, pcm, 16000, subtype="PCM_16")
                        tmp.unlink(missing_ok=True)
                        counts[species] += 1
                    except Exception as exc:
                        log.warning("xc %s download/transcode failed: %s", rec_id, exc)
                        continue

                    time.sleep(0.25)  # be polite

                page += 1

    return counts


# ── iNaturalist (best-effort search) ──────────────────────────────────────────
INAT_API = "https://api.inaturalist.org/v1/observations"
INAT_QUERIES = {
    "Bee":          ["Apis", "Bombus", "Xylocopa", "Halictus", "Osmia",
                     "Megachile", "Anthophora", "Andrena"],
    "Locust":       ["Locusta", "Schistocerca", "Nomadacris", "Dociostaurus",
                     "Chortoicetes", "Melanoplus"],
    "Cicada":       ["Magicicada", "Cicadidae", "Cryptotympana", "Tibicen",
                     "Neotibicen", "Meimuna", "Graptopsaltria", "Dundubia"],
    "Cricket":      ["Gryllidae", "Gryllus", "Acheta", "Teleogryllus",
                     "Oecanthus", "Gryllotalpa", "Nemobius"],
    "Grasshopper":  ["Chorthippus", "Acrididae", "Gomphocerinae", "Acrida",
                     "Melanoplinae", "Tettigoniidae", "Conocephalus", "Ruspolia"],
    "Beetle":       ["Cerambycidae", "Elateridae", "Passalidae", "Lucanus",
                     "Dynastinae", "Scolytinae", "Dytiscidae", "Prionus"],
    "Wasp":         ["Vespa", "Vespula", "Dolichovespula", "Polistes",
                     "Sceliphron", "Pepsis", "Bembix", "Sphecius"],
}


def fetch_inaturalist(target_dir: Path, max_per_species: int) -> dict[str, int]:
    """Best-effort: pull research-grade sound observations from iNat."""
    import librosa
    import soundfile as sf

    counts: dict[str, int] = {sp: 0 for sp in SPECIES}
    for species, taxa in INAT_QUERIES.items():
        for taxon_name in taxa:
            if counts[species] >= max_per_species:
                break
            page = 1
            while counts[species] < max_per_species and page <= 50:
                q = {"taxon_name": taxon_name, "sounds": "true",
                     "per_page": 50, "page": page}
                try:
                    r = requests.get(INAT_API, params=q, timeout=30)
                    r.raise_for_status()
                    payload = r.json()
                except Exception as exc:
                    log.warning("iNat %s/%s page %s failed: %s",
                                species, taxon_name, page, exc)
                    break

                results = payload.get("results") or []
                if not results:
                    break

                for obs in results:
                    if counts[species] >= max_per_species:
                        break
                    obs_id = obs.get("id")
                    sounds = obs.get("sounds") or []
                    for snd in sounds:
                        url = snd.get("file_url")
                        if not url:
                            continue
                        out = target_dir / _slug(species) / f"inat_{obs_id}_{snd.get('id')}.wav"
                        if out.exists():
                            counts[species] += 1
                            break
                        try:
                            raw = requests.get(url, timeout=60).content
                            tmp = CACHE_DIR / f"inat_{obs_id}.bin"
                            tmp.write_bytes(raw)
                            pcm, _ = librosa.load(tmp, sr=16000, mono=True, duration=10.0)
                            out.parent.mkdir(parents=True, exist_ok=True)
                            sf.write(out, pcm, 16000, subtype="PCM_16")
                            tmp.unlink(missing_ok=True)
                            counts[species] += 1
                            break
                        except Exception as exc:
                            log.warning("iNat %s download/transcode failed: %s",
                                        obs_id, exc)
                            continue

                    time.sleep(0.2)

                page += 1

    return counts


# ── Coverage report ───────────────────────────────────────────────────────────
def coverage_report(target_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for sp in SPECIES + [NON_BIO_CLASS]:
        d = target_dir / _slug(sp)
        n = len(list(d.glob("*.wav"))) if d.exists() else 0
        counts[sp] = n
    return counts


def print_report(counts: dict[str, int], target: int) -> None:
    log.info("=" * 60)
    log.info("Coverage report (target: %d clips per species)", target)
    log.info("=" * 60)
    for sp, n in counts.items():
        marker = "OK " if n >= target else "LOW"
        log.info("  [%s] %-18s %4d", marker, sp, n)
    short = [sp for sp, n in counts.items() if n < target]
    if short:
        log.warning(
            "Below target: %s. Consider manual download from "
            "https://research.google.com/audioset/ or "
            "https://www.inaturalist.org/observations?sounds=true",
            ", ".join(short),
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-per-species", type=int, default=120,
                    help="Stop fetching once we have this many clips per species")
    ap.add_argument("--skip-esc50", action="store_true")
    ap.add_argument("--skip-xc", action="store_true")
    ap.add_argument("--skip-inat", action="store_true")
    ap.add_argument("--xc-only", action="store_true")
    args = ap.parse_args()

    if args.xc_only:
        args.skip_esc50 = True
        args.skip_inat = True

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if not args.skip_esc50:
        log.info("─── ESC-50 ───")
        try:
            added = fetch_esc50(DATA_DIR, args.max_per_species)
            log.info("ESC-50 added: %s", {k: v for k, v in added.items() if v})
        except Exception as exc:
            log.error("ESC-50 fetch failed: %s", exc)

    if not args.skip_xc:
        log.info("─── Xeno-canto ───")
        try:
            added = fetch_xeno_canto(DATA_DIR, args.max_per_species)
            log.info("Xeno-canto added: %s", {k: v for k, v in added.items() if v})
        except Exception as exc:
            log.error("Xeno-canto fetch failed: %s", exc)

    if not args.skip_inat:
        log.info("─── iNaturalist ───")
        try:
            added = fetch_inaturalist(DATA_DIR, args.max_per_species)
            log.info("iNat added: %s", {k: v for k, v in added.items() if v})
        except Exception as exc:
            log.error("iNat fetch failed: %s", exc)

    final = coverage_report(DATA_DIR)
    print_report(final, args.max_per_species)
    return 0


if __name__ == "__main__":
    sys.exit(main())
