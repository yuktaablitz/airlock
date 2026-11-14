"""Step 8: one JSON line per chunk in runs/audit.jsonl; removed text in runs/quarantine.jsonl for review."""

from __future__ import annotations

import json
import time

from airlock.clients import ROOT

RUNS = ROOT / "runs"
AUDIT, QUARANTINE = RUNS / "audit.jsonl", RUNS / "quarantine.jsonl"


def write(screen_id: str, source: dict, rows: list[dict], removed: list[dict]) -> None:
    ts = time.time()
    with AUDIT.open("a") as f:
        for r in rows:
            f.write(json.dumps({"ts": ts, "screen_id": screen_id, "source": source, **r}) + "\n")
    if removed:
        with QUARANTINE.open("a") as f:
            for r in removed:
                f.write(json.dumps({"ts": ts, "screen_id": screen_id, "source": source, **r}) + "\n")
