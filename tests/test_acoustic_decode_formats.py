"""Round-trip every supported audio format through _decode_audio.

The pydub fallback in `backend.services.acoustic.dsp._decode_audio` shells
out to the ffmpeg binary for everything other than WAV. WAV always runs.
MP3/OGG/M4A self-skip when the ffmpeg binary is missing — that keeps the
suite green on dev boxes that haven't installed it, but the moment ffmpeg
lands all four formats are guarded against regressions.
"""
from __future__ import annotations

import shutil

import pytest

from backend.services.acoustic.dsp import _decode_audio

FFMPEG_MISSING = shutil.which("ffmpeg") is None
SKIP_NO_FFMPEG = pytest.mark.skipif(
    FFMPEG_MISSING, reason="ffmpeg binary not installed",
)


@pytest.mark.parametrize(
    "fmt,expected_method",
    [
        ("wav", "scipy_wav"),
        pytest.param("mp3", "pydub_ffmpeg", marks=SKIP_NO_FFMPEG),
        pytest.param("ogg", "pydub_ffmpeg", marks=SKIP_NO_FFMPEG),
        pytest.param("m4a", "pydub_ffmpeg", marks=SKIP_NO_FFMPEG),
    ],
)
def test_decode_audio_supports_format(
    synth_audio_bytes: dict[str, bytes], fmt: str, expected_method: str,
) -> None:
    audio_bytes = synth_audio_bytes[fmt]
    assert audio_bytes, f"{fmt} fixture is empty — ffmpeg export may have failed"

    pcm, rate, method = _decode_audio(audio_bytes)

    assert pcm is not None, f"{fmt} returned None from _decode_audio"
    assert rate > 0, f"{fmt} returned non-positive sample rate"
    assert pcm.size > 0, f"{fmt} returned empty PCM array"
    assert method == expected_method, (
        f"{fmt} decoded via {method}, expected {expected_method}"
    )
