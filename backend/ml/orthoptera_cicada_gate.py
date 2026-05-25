"""
Orthoptera-vs-Cicada tie-breaker gate.

A pure-function discriminator + gate that nudges the PANNs head's softmax
ONLY when both Top-1 and Top-2 are in {Grasshopper, Locust, Cicada} AND span
different groups (one Orthoptera, one Cicada) AND the margin between them is
below GATE_MARGIN_FLOOR. Inert otherwise — never modifies probabilities of
Bee/Beetle/Cricket/Wasp/Non-biological.

Physics prior (validated on 10 clean Cicada + 10 clean Grasshopper clips
via scripts/probe_physics_prior.py; median delta (var_ortho - var_cicada)
= -0.00034 on Cicada side, +0.03356 on Grasshopper side):

  True Cicada clip:
    head returns high cicada probability throughout (with some bounce) →
    HIGH var(cicada_pw), LOW var(ortho_pw) [head correctly suppresses ortho].
  True Orthoptera clip:
    head returns high ortho probability throughout (with bounce) →
    HIGH var(ortho_pw), LOW var(cicada_pw).

So on real PANNs head: var of the TRUE class is HIGH (signal-driven bounce),
var of the FALSE class is LOW (consistently suppressed). The pulsed-vs-tonal
distinction in raw audio doesn't translate to raw probability variance —
it translates to which class is "active" and therefore variable.

Discriminator score sums two contributions:
  (1) variance term: (var_cicada - var_ortho) * W_VARIANCE
      → positive when cicada is the active class → favors cicada.
  (2) onset term:    (NEUTRAL_ONSET - onset_density_per_sec) * W_ONSET
      → positive when onsets are sparse (tonal signature) → favors cicada.
      → None onset_density contributes 0.

Score > 0 → nudge mass FROM top-Orthoptera class TO Cicada.
Score < 0 → nudge mass FROM Cicada TO top-Orthoptera class.
Nudge magnitude = tanh(|score| * SCORE_SLOPE) * GATE_NUDGE_CAP — bounded.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

ORTHOPTERA_LABELS = ("Grasshopper", "Locust")
CICADA_LABEL = "Cicada"

GATE_MARGIN_FLOOR = 0.15
GATE_NUDGE_CAP = 0.05

W_VARIANCE = 6.0
W_ONSET = 0.08
NEUTRAL_ONSET = 3.0
SCORE_SLOPE = 1.5


def discriminator_score(
    per_window_probs: np.ndarray,
    classes: list[str],
    onset_density_per_sec: Optional[float],
) -> float:
    """Signed score: positive favors Cicada, negative favors Orthoptera."""
    cicada_idx = classes.index(CICADA_LABEL)
    ortho_idx = [classes.index(c) for c in ORTHOPTERA_LABELS if c in classes]
    if not ortho_idx:
        return 0.0

    cicada_pw = per_window_probs[:, cicada_idx]
    ortho_pw = per_window_probs[:, ortho_idx].sum(axis=1)

    var_cicada = float(np.var(cicada_pw))
    var_ortho = float(np.var(ortho_pw))
    variance_term = (var_cicada - var_ortho) * W_VARIANCE

    if onset_density_per_sec is None:
        onset_term = 0.0
    else:
        onset_term = (NEUTRAL_ONSET - float(onset_density_per_sec)) * W_ONSET

    return float(variance_term + onset_term)


def apply_gate(
    probs: np.ndarray,
    ordered_classes: list[str],
    per_window_probs: np.ndarray,
    onset_density_per_sec: Optional[float] = None,
) -> tuple[np.ndarray, bool, dict]:
    """Apply the Orthoptera-vs-Cicada tie-breaker if activation conditions
    hold. Returns (new_probs, gate_fired, telemetry).

    Activation conditions (ALL must hold):
      1. Top-1 ∈ {Grasshopper, Locust, Cicada}
      2. Top-2 ∈ {Grasshopper, Locust, Cicada}
      3. Top-1 and Top-2 span different groups (one Orthoptera, one Cicada)
      4. Top-1 probability − Top-2 probability < GATE_MARGIN_FLOOR
    """
    probs = np.asarray(probs, dtype=np.float64).copy()

    target_labels = set(ORTHOPTERA_LABELS) | {CICADA_LABEL}
    target_idx = [i for i, c in enumerate(ordered_classes) if c in target_labels]
    if not target_idx:
        return probs.astype(np.float32), False, {"reason": "no_target_classes"}

    order = np.argsort(probs)[::-1]
    top1_idx, top2_idx = int(order[0]), int(order[1])
    top1_lbl, top2_lbl = ordered_classes[top1_idx], ordered_classes[top2_idx]
    margin = float(probs[top1_idx] - probs[top2_idx])

    if top1_lbl not in target_labels or top2_lbl not in target_labels:
        return probs.astype(np.float32), False, {"reason": "top2_outside_targets"}

    grp1 = "cicada" if top1_lbl == CICADA_LABEL else "orthoptera"
    grp2 = "cicada" if top2_lbl == CICADA_LABEL else "orthoptera"
    if grp1 == grp2:
        return probs.astype(np.float32), False, {"reason": "same_group"}

    if margin >= GATE_MARGIN_FLOOR:
        return probs.astype(np.float32), False, {
            "reason": "margin_above_floor", "margin": margin,
        }

    score = discriminator_score(per_window_probs, ordered_classes, onset_density_per_sec)
    nudge = float(np.tanh(abs(score) * SCORE_SLOPE) * GATE_NUDGE_CAP)
    direction = "to_cicada" if score > 0 else "to_orthoptera"

    cicada_idx = ordered_classes.index(CICADA_LABEL)
    ortho_present = [(c, ordered_classes.index(c))
                     for c in ORTHOPTERA_LABELS if c in ordered_classes]
    top_ortho_idx = max(ortho_present, key=lambda x: probs[x[1]])[1]

    if direction == "to_cicada":
        donor_idx, recipient_idx = top_ortho_idx, cicada_idx
    else:
        donor_idx, recipient_idx = cicada_idx, top_ortho_idx

    actual_nudge = min(nudge, float(probs[donor_idx]))
    probs[donor_idx] -= actual_nudge
    probs[recipient_idx] += actual_nudge

    s = float(probs.sum())
    if s > 0 and abs(s - 1.0) > 1e-9:
        probs = probs / s

    telemetry = {
        "reason": "fired",
        "direction": direction,
        "score": score,
        "nudge": actual_nudge,
        "margin_before": margin,
        "top1_lbl": top1_lbl,
        "top2_lbl": top2_lbl,
        "onset_density_per_sec": onset_density_per_sec,
    }
    return probs.astype(np.float32), True, telemetry
