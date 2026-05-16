"""
Retrain the YAMNet classifier head using farmer-corrected clips.

Run this script after collecting enough feedback (e.g. weekly via cron):

    # cron example — every Sunday at 2 am:
    # 0 2 * * 0  cd /path/to/smart-crop-advisor && python scripts/retrain_from_feedback.py

What it does:
    1. Count new feedback clips in data/audio_samples/ (written by the
       /acoustic/feedback endpoint when a farmer submits a correction).
    2. Report the current queue size from data/feedback_queue/feedback.jsonl.
    3. Run train_yamnet_head.py to rebuild the classifier head.
    4. Archive processed feedback.jsonl entries to
       data/feedback_queue/feedback_<timestamp>.jsonl.bak so they are not
       double-counted but can be audited.

USAGE
-----
    python scripts/retrain_from_feedback.py
    python scripts/retrain_from_feedback.py --dry-run   # report only, no train
    python scripts/retrain_from_feedback.py --min-new 10  # require ≥10 new clips
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("retrain_feedback")

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIO_SAMPLES_DIR = REPO_ROOT / "data" / "audio_samples"
FEEDBACK_QUEUE_FILE = REPO_ROOT / "data" / "feedback_queue" / "feedback.jsonl"
TRAIN_SCRIPT = REPO_ROOT / "scripts" / "train_yamnet_head.py"


def _count_feedback_clips() -> dict[str, int]:
    """Count feedback_*.wav files per species directory."""
    counts: dict[str, int] = {}
    if not AUDIO_SAMPLES_DIR.exists():
        return counts
    for sp_dir in sorted(AUDIO_SAMPLES_DIR.iterdir()):
        if not sp_dir.is_dir():
            continue
        n = len(list(sp_dir.glob("feedback_*.wav")))
        if n:
            counts[sp_dir.name] = n
    return counts


def _count_queue_entries() -> int:
    if not FEEDBACK_QUEUE_FILE.exists():
        return 0
    with FEEDBACK_QUEUE_FILE.open() as fh:
        return sum(1 for line in fh if line.strip())


def _archive_queue() -> None:
    if not FEEDBACK_QUEUE_FILE.exists() or FEEDBACK_QUEUE_FILE.stat().st_size == 0:
        return
    ts = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    bak = FEEDBACK_QUEUE_FILE.with_name(f"feedback_{ts}.jsonl.bak")
    FEEDBACK_QUEUE_FILE.rename(bak)
    log.info("Queue archived → %s", bak)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Report counts; skip training")
    ap.add_argument("--min-new", type=int, default=5,
                    help="Minimum new feedback clips required before retraining")
    args = ap.parse_args()

    feedback_clips = _count_feedback_clips()
    total_new = sum(feedback_clips.values())
    queue_entries = _count_queue_entries()

    log.info("New feedback clips by species:")
    if feedback_clips:
        for sp, n in sorted(feedback_clips.items()):
            log.info("  %-20s  %d", sp, n)
    else:
        log.info("  (none)")
    log.info("Feedback queue entries: %d", queue_entries)
    log.info("Total new clips: %d (threshold: %d)", total_new, args.min_new)

    if total_new < args.min_new:
        log.info("Not enough new clips — skipping retrain. "
                 "Collect more feedback or lower --min-new.")
        return 0

    if args.dry_run:
        log.info("--dry-run: would retrain now.")
        return 0

    log.info("Launching train_yamnet_head.py …")
    rc = subprocess.call([sys.executable, str(TRAIN_SCRIPT)])
    if rc == 0:
        log.info("Retrain complete. Archiving queue …")
        _archive_queue()
    else:
        log.error("train_yamnet_head.py exited with code %d — queue NOT archived.", rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
