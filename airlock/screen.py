"""screen(content, meta, user_goal) -> ScreenResult. Orchestrates steps 1-8."""

from __future__ import annotations

import asyncio
import json
import time
import uuid

from pydantic import BaseModel

from airlock import audit, clients, gate, redact, signals, system1, system2
from airlock.chunk import Chunk, chunk_json, chunk_text
from airlock.normalize import normalize


class Removed(BaseModel):
    id: str
    text: str
    p: float
    by: str
    reason: str = ""
    json_path: str | None = None


class ChunkView(BaseModel):
    id: str
    text: str
    start: int
    end: int
    p: float
    decision: str
    by: str
    signals: list[str]
    json_path: str | None = None
    reason: str = ""


class ScreenResult(BaseModel):
    sanitized: str | dict | list
    verdict: str  # clean | redacted | blocked
    removed: list[Removed]
    doc_intent: str
    intent_probs: dict[str, float] = {}
    kind: str = "text"
    text: str | None = None
    chunks: list[ChunkView] = []
    stats: dict


async def screen(content, meta: dict | None = None, user_goal: str = "", *, escalate: bool = True,
                 tau_low: float | None = None, tau_high: float | None = None, write_audit: bool = True) -> ScreenResult:
    t0 = time.perf_counter()
    meta = dict(meta or {})
    tau_low = gate.TAU_LOW if tau_low is None else tau_low
    tau_high = gate.TAU_HIGH if tau_high is None else tau_high
    if not escalate:  # Drex-only: a single threshold, no band
        tau_low = tau_high

    body, kind = normalize(content, meta)
    chunks: list[Chunk] = chunk_json(body) if kind == "json" else chunk_text(body)
    signals.annotate(chunks, meta.get("visible_text"))
    source = {"tool": meta.get("tool", "unknown"), "name": meta.get("source_name", "")}

    s1 = await system1.score(chunks, user_goal, source)
    decisions = {c.id: gate.decide(s1.p.get(c.id, 0.0), tau_low, tau_high) for c in chunks}
    by = {c.id: "S1" for c in chunks}
    reasons: dict[str, str] = {}

    escalated = [i for i, c in enumerate(chunks) if decisions[c.id] == "ESCALATE"]
    s2_ms, s2_tokens = 0.0, 0
    if escalated:
        verdicts = await asyncio.gather(*(
            system2.judge(chunks[i], chunks[i - 1] if i else None, chunks[i + 1] if i + 1 < len(chunks) else None, user_goal)
            for i in escalated))
        for i, (inj, reason, ms, tok) in zip(escalated, verdicts):
            cid = chunks[i].id
            decisions[cid], by[cid], reasons[cid] = ("BLOCK" if inj else "PASS"), "S2", reason
            s2_ms, s2_tokens = max(s2_ms, ms), s2_tokens + tok

    blocked = [c for c in chunks if decisions[c.id] == "BLOCK"]
    if kind == "json":
        sanitized = redact.redact_json(body, blocked, s1.p)
    else:
        sanitized = redact.header(blocked, s1.p, s1.doc_intent) + redact.redact_text(body, blocked, s1.p)

    total_chars = sum(len(c.text) for c in chunks) or 1
    removed_chars = sum(len(c.text) for c in blocked)
    verdict = "clean" if not blocked else ("blocked" if removed_chars / total_chars > 0.8 else "redacted")
    cost = (s1.tokens * clients.DREX_PRICE_IN + s2_tokens * clients.QWEN_PRICE_IN) / 1e6
    removed = [Removed(id=c.id, text=c.text, p=s1.p.get(c.id, 0.0), by=by[c.id], reason=reasons.get(c.id, ""),
                       json_path=c.json_path) for c in blocked]
    views = [ChunkView(id=c.id, text=c.text, start=c.start, end=c.end, p=s1.p.get(c.id, 0.0), decision=decisions[c.id],
                       by=by[c.id], signals=c.signals, json_path=c.json_path, reason=reasons.get(c.id, ""))
             for c in chunks]
    stats = {"chunks": len(chunks), "s1_ms": round(s1.ms, 1), "s2_calls": len(escalated), "s2_ms": round(s2_ms, 1),
             "tokens": s1.tokens + s2_tokens, "s1_tokens": s1.tokens, "s2_tokens": s2_tokens,
             "cost_usd": cost, "total_ms": round((time.perf_counter() - t0) * 1000, 1),
             "request_ids": s1.request_ids, "cache_hits": s1.cache_hits, "parser": meta.get("parser"),
             "tau_low": tau_low, "tau_high": tau_high}

    if write_audit:
        sid = uuid.uuid4().hex[:12]
        rows = [{"chunk_id": v.id, "p": v.p, "decision": v.decision, "decided_by": v.by, "signals": v.signals,
                 "s1_ms": stats["s1_ms"], "request_ids": s1.request_ids} for v in views]
        audit.write(sid, source, rows, [r.model_dump() for r in removed])
        stats["screen_id"] = sid

    return ScreenResult(sanitized=sanitized, verdict=verdict, removed=removed, doc_intent=s1.doc_intent,
                        intent_probs=s1.intent_probs, kind=kind,
                        text=body if isinstance(body, str) else json.dumps(body, indent=2), chunks=views, stats=stats)


def screen_sync(content, meta: dict | None = None, user_goal: str = "", **kw) -> ScreenResult:
    return asyncio.run(screen(content, meta, user_goal, **kw))
