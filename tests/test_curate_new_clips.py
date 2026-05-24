"""Unit tests for scripts/curate_new_clips.py — duration filter + dedup."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.curate_new_clips import curate_directory  # noqa: E402


def _write_wav(path: Path, seconds: float, sr: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(seconds * sr)
    sf.write(path, np.zeros(n, dtype=np.float32), sr, subtype="PCM_16")


def test_drops_clips_shorter_than_min_duration(tmp_path):
    _write_wav(tmp_path / "long.wav", 2.0)
    _write_wav(tmp_path / "short.wav", 0.5)
    report = curate_directory(tmp_path, min_duration_s=1.0, dry_run=False)
    assert report["dropped_short"] == 1
    assert report["kept"] == 1
    assert (tmp_path / "long.wav").exists()
    assert not (tmp_path / "short.wav").exists()


def test_dry_run_drops_nothing(tmp_path):
    _write_wav(tmp_path / "short.wav", 0.5)
    report = curate_directory(tmp_path, min_duration_s=1.0, dry_run=True)
    assert report["dropped_short"] == 1
    assert (tmp_path / "short.wav").exists(), "dry_run must not delete"


def test_ignores_non_wav_files(tmp_path):
    (tmp_path / "notes.txt").write_text("hi")
    _write_wav(tmp_path / "ok.wav", 2.0)
    report = curate_directory(tmp_path, min_duration_s=1.0, dry_run=False)
    assert report["scanned"] == 1  # only the .wav
    assert (tmp_path / "notes.txt").exists()


def test_empty_directory(tmp_path):
    report = curate_directory(tmp_path, min_duration_s=1.0, dry_run=False)
    assert report == {"scanned": 0, "kept": 0, "dropped_short": 0, "dropped_unreadable": 0}


def test_handles_unreadable_file(tmp_path):
    bad = tmp_path / "corrupt.wav"
    bad.write_bytes(b"not a wav file")
    report = curate_directory(tmp_path, min_duration_s=1.0, dry_run=False)
    assert report["dropped_unreadable"] == 1
    assert not bad.exists()
