import numpy as np
import io
import base64
import json
import importlib
import scipy.io.wavfile as wav
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Dict, Any, Optional, Tuple
from core.config import settings

PEST_ICONS = {
    'Healthy Plant':          '✅',
    'Aphid Colony':           '🟡',
    'Whitefly Infestation':   '🟡',
    'Locust Activity':        '🔴',
    'Stem Borer':             '🔴',
    'Early Fungal Infection': '🔴',
    'Spider Mite':            '🟡',
    'Thrips Infestation':     '🟡',
}


class AcousticService:
    @staticmethod
    async def analyze_audio(audio_bytes: bytes, crop_type: str = "Unknown") -> Dict[str, Any]:
        if not settings.ANTHROPIC_API_KEY:
            return AcousticService._fallback_result("No API key — add ANTHROPIC_API_KEY to .env")

        wav_bytes, decode_warnings = AcousticService._to_wav_bytes(audio_bytes)
        if wav_bytes is None:
            return AcousticService._fallback_result(
                "Could not decode audio. WAV works natively; for MP3/M4A/OGG install ffmpeg: "
                "brew install ffmpeg"
            )
        spec_bytes, band_energy, quality_meta = AcousticService._make_spectrogram(wav_bytes)
        if spec_bytes is None:
            quality_warnings = quality_meta.get('quality_warnings', []) + decode_warnings
            return AcousticService._fallback_result(
                "Could not generate spectrogram from decoded audio.",
                quality_warnings=quality_warnings,
            )

        result = await AcousticService._claude_analyze(spec_bytes, crop_type)
        result['band_energy'] = band_energy
        result['duration_seconds'] = quality_meta.get('duration_seconds', 0.0)
        result['analyzed_seconds'] = quality_meta.get('analyzed_seconds', 0.0)
        result['quality_warnings'] = quality_meta.get('quality_warnings', [])
        result['quality_warnings'].extend(decode_warnings)
        result['truncated'] = quality_meta.get('truncated', False)
        result['ml_used'] = False
        result['claude_advice'] = None
        result.setdefault('icon', PEST_ICONS.get(result.get('pest', ''), '⚠️'))
        return result

    @staticmethod
    def _to_wav_bytes(audio_bytes: bytes) -> Tuple[Optional[bytes], list[str]]:
        warnings: list[str] = []
        # Fast-path: if upload is already WAV, avoid ffmpeg dependency entirely.
        try:
            wav.read(io.BytesIO(audio_bytes))
            return audio_bytes, warnings
        except Exception:
            warnings.append("not_native_wav")

        try:
            audio_segment = importlib.import_module("pydub").AudioSegment
            # Using dynamic import keeps pydub optional and avoids static resolution warnings.
            seg = audio_segment.from_file(io.BytesIO(audio_bytes))
            out = io.BytesIO()
            seg.export(out, format="wav")
            return out.getvalue(), warnings
        except Exception:
            warnings.append("pydub_ffmpeg_decode_failed")
            return None, warnings

    @staticmethod
    def _make_spectrogram(wav_bytes: bytes):
        try:
            rate, data = wav.read(io.BytesIO(wav_bytes))
            if data.ndim > 1:
                data = data[:, 0]
            raw = data.astype(np.float32) / (32768.0 if data.dtype == np.int16 else 1.0)

            max_seconds = 10
            duration_seconds = (len(raw) / rate) if rate else 0.0
            truncated = duration_seconds > max_seconds
            analyzed_seconds = min(duration_seconds, max_seconds)
            warnings = ["truncated_to_10s"] if truncated else []

            seg = raw[:rate * max_seconds]  # first 10s max
            if len(seg) == 0:
                return None, None, {
                    "truncated": False,
                    "duration_seconds": round(duration_seconds, 2),
                    "analyzed_seconds": 0.0,
                    "quality_warnings": ["empty_audio"],
                }

            # Band energy for chart
            fft_vals = np.abs(np.fft.rfft(seg))
            freqs = np.fft.rfftfreq(len(seg), 1.0 / rate)
            band_energy = {
                '50-200 Hz':    round(float(np.mean(fft_vals[(freqs >= 50)   & (freqs < 200)])),  4),
                '200-500 Hz':   round(float(np.mean(fft_vals[(freqs >= 200)  & (freqs < 500)])),  4),
                '500-1200 Hz':  round(float(np.mean(fft_vals[(freqs >= 500)  & (freqs < 1200)])), 4),
                '1200-4000 Hz': round(float(np.mean(fft_vals[(freqs >= 1200) & (freqs < 4000)])), 4),
            }

            fig, ax = plt.subplots(figsize=(8, 4))
            ax.specgram(seg, Fs=rate, cmap='inferno', NFFT=512, noverlap=256)
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Frequency (Hz)')
            ax.set_ylim(0, min(8000, rate // 2))
            ax.set_title('Field Audio Spectrogram')
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=80, bbox_inches='tight')
            plt.close(fig)
            buf.seek(0)
            return buf.read(), band_energy, {
                "truncated": truncated,
                "duration_seconds": round(duration_seconds, 2),
                "analyzed_seconds": round(analyzed_seconds, 2),
                "quality_warnings": warnings,
            }
        except Exception:
            return None, None, {
                "truncated": False,
                "duration_seconds": 0.0,
                "analyzed_seconds": 0.0,
                "quality_warnings": ["spectrogram_generation_failed"],
            }

    @staticmethod
    async def _claude_analyze(spec_bytes: bytes, crop: str) -> Dict[str, Any]:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        img_b64 = base64.standard_b64encode(spec_bytes).decode()

        resp = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system=[{
                "type": "text",
                "text": (
                    "You are an expert bioacoustics analyst for crop pest detection. "
                    "Analyze spectrogram images of field audio recordings and identify pest signatures.\n\n"
                    "Known pest signatures in spectrograms:\n"
                    "- Healthy Plant: flat noise floor, low energy across all bands\n"
                    "- Aphid Colony: clustered mid-frequency bursts 200-400 Hz\n"
                    "- Whitefly Infestation: wing-beat harmonic series 400-700 Hz\n"
                    "- Locust Activity: high-amplitude low-frequency pulses 50-200 Hz\n"
                    "- Stem Borer: rhythmic low-frequency gnawing 50-150 Hz\n"
                    "- Early Fungal Infection: high-frequency crackling 800-1200 Hz\n"
                    "- Spider Mite: ultra-high-frequency scratching 1200-4000 Hz\n"
                    "- Thrips Infestation: rapid mid-frequency staccato 350-500 Hz\n\n"
                    "If the sound does not match any pest (e.g. it is music, speech, ambient noise, "
                    "or an unrelated insect), set pest to 'Healthy Plant' and explain in action.\n\n"
                    "Respond ONLY with valid JSON, no markdown fences:\n"
                    '{"pest":"name","severity":"high|medium|low","freq_range":"e.g. 50-150 Hz",'
                    '"pattern":"describe what you see in spectrogram","energy_level":"Very High|High|Moderate|Low-moderate|Background",'
                    '"confidence":85,"action":"specific actionable advice for Indian farmer",'
                    '"top3":[["Pest1",85],["Pest2",10],["Pest3",5]]}'
                ),
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": img_b64},
                    },
                    {
                        "type": "text",
                        "text": f"Crop: {crop}. Analyze this field audio spectrogram for pest signatures. Respond with JSON only.",
                    },
                ],
            }],
        )
        return json.loads(resp.content[0].text)

    @staticmethod
    def _fallback_result(msg: str, quality_warnings: Optional[list[str]] = None) -> Dict[str, Any]:
        return {
            "pest": msg,
            "severity": "low",
            "confidence": 0,
            "freq_range": "N/A",
            "pattern": "N/A",
            "energy_level": "N/A",
            "action": "Check configuration and restart backend.",
            "icon": "⚠️",
            "top3": [],
            "ml_used": False,
            "claude_advice": None,
            "band_energy": None,
            "quality_warnings": quality_warnings or [],
        }
