"""
Hygiene pass for newly-fetched acoustic clips.

Drops anything below ``--min-duration`` seconds and anything ``soundfile``
can't read. Idempotent — safe to re-run after every fetch. Does *not*
attempt SNR estimation or species verification; those are out of scope
for the v1 data-first lift (see docs/superpowers/plans/
2026-05-24-phase-c-prime-data-lift.md).

USAGE
-----
    # Curate the three classes we just supplemented:
    python scripts/curate_new_clips.py \\
        data/audio_samples/Cricket \\
        data/audio_samples/Bee \\
        data/audio_samples/Beetle

    # Report only, don't delete:
    python scripts/curate_new_clips.py --dry-run data/audio_samples/Cricket
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import soundfile as sf

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("curate_clips")


def curate_directory(
    directory: Path,
    min_duration_s: float = 1.0,
    dry_run: bool = False,
) -> dict[str, int]:
    """Walk *.wav in `directory`, drop clips below `min_duration_s` or
    those that can't be opened. Returns a counts dict.
    """
    report = {"scanned": 0, "kept": 0, "dropped_short": 0, "dropped_unreadable": 0}
    if not directory.exists():
        return report

    for wav in sorted(directory.glob("*.wav")):
        report["scanned"] += 1
        try:
            info = sf.info(wav)
            duration = info.frames / float(info.samplerate)
        except Exception as exc:
            log.warning("Unreadable %s — %s", wav.name, exc)
            if not dry_run:
                wav.unlink(missing_ok=True)
            report["dropped_unreadable"] += 1
            continue

        if duration < min_duration_s:
            log.info("Drop %-40s (%.2fs < %.2fs)", wav.name, duration, min_duration_s)
            if not dry_run:
                wav.unlink(missing_ok=True)
            report["dropped_short"] += 1
            continue

        report["kept"] += 1

    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("directories", nargs="+", type=Path,
                    help="One or more audio_samples/<species> dirs to curate")
    ap.add_argument("--min-duration", type=float, default=1.0,
                    help="Drop clips shorter than this many seconds (default 1.0)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Report what would be dropped without deleting")
    args = ap.parse_args()

    totals = {"scanned": 0, "kept": 0, "dropped_short": 0, "dropped_unreadable": 0}
    for d in args.directories:
        log.info("─── %s ───", d)
        r = curate_directory(d, min_duration_s=args.min_duration, dry_run=args.dry_run)
        for k, v in r.items():
            totals[k] += v
        log.info("  scanned=%d kept=%d dropped_short=%d dropped_unreadable=%d",
                 r["scanned"], r["kept"], r["dropped_short"], r["dropped_unreadable"])

    log.info("=" * 60)
    log.info("TOTAL  scanned=%d kept=%d dropped_short=%d dropped_unreadable=%d%s",
             totals["scanned"], totals["kept"],
             totals["dropped_short"], totals["dropped_unreadable"],
             "  (dry-run, nothing deleted)" if args.dry_run else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
