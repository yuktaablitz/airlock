"""Step 5: probability -> PASS / ESCALATE / BLOCK. Thresholds are fixed on the dev split (see eval/report.py).

Two operating points, both tuned on dev for the active criteria version:
  recall              Drex decides the clear cases, Qwen judges the band between τ_low and τ_high.
  precision (default) Drex alone at its own threshold; no LLM call, fewest false positives. Same F1 as recall
                      (McNemar p=1, runs/stats_v3.md), a fifth of the false positives.
"""

from __future__ import annotations

import json
import os

from airlock.clients import ROOT
from airlock.system1 import CRITERIA_VERSION

_cfg = ROOT / "runs" / f"thresholds_{CRITERIA_VERSION}.json"
_t = json.loads(_cfg.read_text()) if _cfg.exists() else {}
MODE = os.getenv("AIRLOCK_MODE", "precision")
TAU_LOW = float(os.getenv("AIRLOCK_TAU_LOW", _t.get("tau_low", 0.15)))
TAU_HIGH = float(os.getenv("AIRLOCK_TAU_HIGH", _t.get("tau_high", 0.85)))
DREX_ONLY_TAU = float(os.getenv("AIRLOCK_TAU", _t.get("drex_only_tau", 0.5)))


def thresholds(mode: str = MODE) -> tuple[float, float]:
    """(τ_low, τ_high); precision mode collapses the band to Drex's single threshold."""
    return (DREX_ONLY_TAU, DREX_ONLY_TAU) if mode == "precision" else (TAU_LOW, TAU_HIGH)


def decide(p: float, tau_low: float, tau_high: float) -> str:
    if p >= tau_high:
        return "BLOCK"
    if p <= tau_low:
        return "PASS"
    return "ESCALATE"
