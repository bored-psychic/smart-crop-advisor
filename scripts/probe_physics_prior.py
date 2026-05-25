"""Fix A3: physics-prior hardgate.

Hypothesis under test (from gate plan):
  Cicada is tonal     → per-window var(Cicada_prob) is LOW relative to var(Ortho).
  Orthoptera is pulsed → per-window var(Ortho_prob) is HIGH relative to var(Cicada).

Procedure:
  - 10 clean Cicada clips from data/audio_samples/Cicada/
  - 10 clean Grasshopper clips from data/audio_samples/Grasshopper/
  - For each clip, compute delta = var(ortho_pw) - var(cicada_pw).
    where ortho_pw = sum of Grasshopper + Locust per-window probabilities.

Pass criteria (BOTH must hold; either failure aborts the plan):
  median delta on Cicada clips    < 0   (variance of ortho > variance of cicada is FALSE on cicada)
  median delta on Grasshopper clips > 0   (variance of ortho > variance of cicada on grasshopper)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import soundfile as sf

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.ml.panns_model import load, _probs_from_clf, _resample_to_32k  # noqa: E402


def per_clip_delta(bundle, wav_path: Path) -> tuple[float, float, float, int]:
    """Return (var_cicada, var_ortho, delta, n_windows) for one clip."""
    pcm, sr = sf.read(wav_path, dtype="float32", always_2d=False)
    w32 = _resample_to_32k(pcm, sr)
    clipwise_per, embedding_per = bundle._embed_windows(w32)
    feats_per = np.concatenate([embedding_per, clipwise_per], axis=1)
    probs_per = _probs_from_clf(bundle.clf, feats_per, bundle.temperature)
    c_idx = bundle.classes.index("Cicada")
    g_idx = bundle.classes.index("Grasshopper")
    l_idx = bundle.classes.index("Locust")
    cicada_pw = probs_per[:, c_idx]
    ortho_pw = probs_per[:, g_idx] + probs_per[:, l_idx]
    var_c = float(np.var(cicada_pw))
    var_o = float(np.var(ortho_pw))
    return var_c, var_o, var_o - var_c, int(probs_per.shape[0])


def run_side(bundle, species: str, n: int) -> tuple[list[float], list[str]]:
    deltas, names = [], []
    src = REPO_ROOT / "data" / "audio_samples" / species
    clips = sorted(src.glob("*.wav"))[:n * 2]  # take 2x in case some fail
    for clip in clips:
        if len(deltas) >= n:
            break
        try:
            vc, vo, delta, nw = per_clip_delta(bundle, clip)
        except Exception as exc:
            print(f"  SKIP {clip.name}: {exc}")
            continue
        deltas.append(delta)
        names.append(clip.name)
        print(f"  {clip.name:50s}  N={nw:2d}  var_cicada={vc:.5f}  var_ortho={vo:.5f}  delta={delta:+.5f}")
    return deltas, names


def main() -> int:
    print("Loading bundle …")
    bundle = load()

    print("\n--- Cicada side (expect median delta < 0) ---")
    cic_deltas, _ = run_side(bundle, "Cicada", 10)
    print("\n--- Grasshopper side (expect median delta > 0) ---")
    gh_deltas, _ = run_side(bundle, "Grasshopper", 10)

    cic_med = float(np.median(cic_deltas)) if cic_deltas else 0.0
    gh_med = float(np.median(gh_deltas)) if gh_deltas else 0.0

    print(f"\nMedian delta on Cicada      clips: {cic_med:+.5f}  "
          f"(need < 0; cicada more tonal → lower variance)")
    print(f"Median delta on Grasshopper clips: {gh_med:+.5f}  "
          f"(need > 0; ortho more pulsed → higher variance)")

    pass_cic = cic_med < 0
    pass_gh = gh_med > 0
    print(f"\nCicada side:      {'PASS' if pass_cic else 'FAIL'}")
    print(f"Grasshopper side: {'PASS' if pass_gh else 'FAIL'}")

    if pass_cic and pass_gh:
        print("\nFix A3: PASS. Physics prior holds. Proceed with gate design.")
        return 0
    print("\nFix A3: FAIL. Abort plan or redesign discriminator signal.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
