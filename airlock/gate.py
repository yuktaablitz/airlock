"""Step 5: probability -> PASS / ESCALATE / BLOCK. Thresholds are fixed on the dev split (see eval/report.py)."""

from __future__ import annotations

import json
import os

from airlock.clients import ROOT

_cfg = ROOT / "runs" / f"thresholds_{os.getenv('AIRLOCK_CRITERIA', 'v2')}.json"
_t = json.loads(_cfg.read_text()) if _cfg.exists() else {}
TAU_LOW = float(os.getenv("AIRLOCK_TAU_LOW", _t.get("tau_low", 0.15)))
TAU_HIGH = float(os.getenv("AIRLOCK_TAU_HIGH", _t.get("tau_high", 0.85)))


def decide(p: float, tau_low: float = TAU_LOW, tau_high: float = TAU_HIGH) -> str:
    if p >= tau_high:
        return "BLOCK"
    if p <= tau_low:
        return "PASS"
    return "ESCALATE"
