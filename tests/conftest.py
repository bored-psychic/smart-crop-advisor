"""Shared pytest fixtures.

The ``auth_headers`` fixture mints a JWT for a synthetic phone via
``backend.auth.issue_token`` so router tests can authenticate against
the JWT-gated endpoints introduced in P0 Task 3 and P1 Task 9.
"""
from __future__ import annotations

import io

import numpy as np
import pytest
import scipy.io.wavfile as wav

from backend.auth import issue_token


@pytest.fixture(scope="session")
def test_phone() -> str:
    """E.164 phone used by the JWT fixture. Synthetic — not a real number."""
    return "+919999999999"


@pytest.fixture(scope="session")
def auth_token(test_phone: str) -> str:
    """A valid JWT signed with the test settings' secret."""
    token, _ = issue_token(test_phone)
    return token


@pytest.fixture(scope="session")
def auth_headers(auth_token: str) -> dict[str, str]:
    """Authorization header ready to splat into a TestClient call."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="session")
def synth_audio_bytes() -> dict[str, bytes]:
    """In-memory audio bytes for every format the acoustic pipeline accepts.

    WAV is built with scipy.io.wavfile — no ffmpeg needed. MP3/OGG/M4A go
    through pydub.AudioSegment.export, which shells out to ffmpeg; when
    ffmpeg is missing those keys map to b"" so tests can self-skip rather
    than fail with a confusing pydub stack trace.
    """
    rate = 22050
    duration_s = 1.0
    t = np.linspace(0, duration_s, int(rate * duration_s), endpoint=False)
    sine = (0.3 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)
    int16 = (sine * 32767.0).astype(np.int16)

    wav_buf = io.BytesIO()
    wav.write(wav_buf, rate, int16)
    out: dict[str, bytes] = {"wav": wav_buf.getvalue()}

    try:
        from pydub import AudioSegment

        seg = AudioSegment(
            int16.tobytes(), frame_rate=rate, sample_width=2, channels=1,
        )
        # Some Homebrew ffmpeg builds ship without libvorbis (the native
        # `vorbis` encoder is flagged experimental and pydub refuses it by
        # default), so the ogg slot tries libvorbis first and falls back to
        # libopus — both produce a real `.ogg`-container clip that the
        # pipeline's pydub→ffmpeg decode path handles identically.
        export_attempts: dict[str, list[dict[str, str]]] = {
            "mp3": [{"format": "mp3"}],
            "ogg": [
                {"format": "ogg", "codec": "libvorbis"},
                {"format": "ogg", "codec": "libopus"},
            ],
            "m4a": [{"format": "ipod"}],
        }
        for fmt, attempts in export_attempts.items():
            out[fmt] = b""
            for kwargs in attempts:
                try:
                    buf = io.BytesIO()
                    seg.export(buf, **kwargs)
                    encoded = buf.getvalue()
                    if encoded:
                        out[fmt] = encoded
                        break
                except Exception:
                    continue
    except Exception:
        out.update({"mp3": b"", "ogg": b"", "m4a": b""})

    return out
