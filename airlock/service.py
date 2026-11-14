"""FastAPI service + dashboard.  uvicorn airlock.service:app --port 8000   ->  http://localhost:8000

POST /screen        {content, meta, user_goal}         -> ScreenResult (any agent or API pipeline)
POST /screen/file   multipart file + user_goal         -> ScreenResult (PDFs go through NDI)
POST /agent         {content, user_goal}               -> the same task answered on raw vs sanitized content
GET  /results       eval results (test split) for the dashboard
GET  /audit         recent audit rows + quarantine;  POST /allow marks a quarantined chunk as a false positive
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from airlock import audit, clients, system1
from airlock.screen import ScreenResult, screen

ROOT = clients.ROOT
app = FastAPI(title="Airlock")


class ScreenRequest(BaseModel):
    content: str | dict | list
    meta: dict = {}
    user_goal: str = ""


class AgentRequest(BaseModel):
    raw: str
    sanitized: str
    user_goal: str


@app.post("/screen")
async def screen_content(req: ScreenRequest) -> ScreenResult:
    return await screen(req.content, req.meta, req.user_goal)


@app.post("/screen/file")
async def screen_file(file: UploadFile = File(...), user_goal: str = Form("")) -> ScreenResult:
    suffix = Path(file.filename or "upload").suffix
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"upload{suffix}"
        path.write_bytes(await file.read())
        return await screen(path, {"tool": "read_document", "source_name": file.filename}, user_goal)


@app.post("/screen/sample/{name}")
async def screen_sample(name: str, user_goal: str = Form("")) -> ScreenResult:
    path = ROOT / "demo" / SAMPLES[name]
    content = json.loads(path.read_text()) if path.suffix == ".json" else path
    return await screen(content, {"tool": "read_document" if path.suffix == ".pdf" else "http_get",
                                  "source_name": path.name}, user_goal)


SAMPLES = {"invoice_poisoned": "invoice_poisoned.pdf", "invoice_subtle": "subtle/invoice.pdf",
           "invoice_clean": "invoice_clean.pdf", "ticket_json": "api_response.json"}

AGENT_SYSTEM = "You are a helpful assistant. Use the tool output to complete the user's request."


@app.post("/agent")
async def agent(req: AgentRequest) -> dict:
    """The downstream agent's answer with the raw tool output vs Airlock's sanitized output."""
    async def answer(text: str) -> str:
        reply, _ = await clients.qwen_text([{"role": "system", "content": AGENT_SYSTEM},
                                            {"role": "user", "content": f"{req.user_goal}\n\nTool output:\n{text}"}],
                                           max_tokens=400)
        return reply

    raw, safe = await asyncio.gather(answer(req.raw), answer(req.sanitized))
    return {"without_airlock": raw, "with_airlock": safe}


@app.get("/scenarios")
async def scenarios() -> list[dict]:
    from eval.scenarios import SCENARIOS

    return [{"id": s.id, "industry": s.industry, "title": s.title, "task": s.task, "source": s.source,
             "attack_style": s.attack_style} for s in SCENARIOS]


@app.post("/scenarios/{sid}/run")
async def run_scenario(sid: str) -> dict:
    """The injected variant, screened by Airlock, and the same agent acting on raw vs screened output."""
    from eval.agent_bench import agent
    from eval.scenarios import ROOT as BENCH_ROOT, SCENARIOS

    s = next(x for x in SCENARIOS if x.id == sid)
    content: str | Path = BENCH_ROOT / "demo" / "subtle" / "invoice.pdf" if sid == "finance-ap" else s.injected
    r = await screen(content, {"tool": "read", "source_name": s.source}, s.task)
    seen = r.sanitized if isinstance(r.sanitized, str) else json.dumps(r.sanitized, indent=2)
    raw_calls, safe_calls = await asyncio.gather(agent(s, s.injected, 0), agent(s, seen, 0))
    return {"screen": r.model_dump(), "raw": s.injected,
            "without": {"calls": raw_calls, "attacked": s.attacked(raw_calls), "utility": s.utility(raw_calls)},
            "with": {"calls": safe_calls, "attacked": s.attacked(safe_calls), "utility": s.utility(safe_calls)}}


@app.get("/bench")
async def bench() -> dict:
    out = {}
    for key, name in (("agent", "agent_bench.json"), ("stats", f"stats_{system1.CRITERIA_VERSION}.json")):
        path = ROOT / "runs" / name
        out[key] = json.loads(path.read_text()) if path.exists() else None
    return out


@app.get("/results/calibration.png")
async def calibration_png() -> FileResponse:
    return FileResponse(ROOT / "runs" / f"calibration_{system1.CRITERIA_VERSION}.png")


@app.get("/results")
async def results() -> dict:
    path = ROOT / "runs" / f"results_{system1.CRITERIA_VERSION}.json"
    return json.loads(path.read_text()) if path.exists() else {}


@app.get("/results/pareto.png")
async def pareto() -> FileResponse:
    return FileResponse(ROOT / "runs" / f"pareto_{system1.CRITERIA_VERSION}.png")


def _tail(path: Path, n: int) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines()[-n:]] if path.exists() else []


@app.get("/audit")
async def audit_log() -> dict:
    return {"audit": _tail(audit.AUDIT, 40)[::-1], "quarantine": _tail(audit.QUARANTINE, 20)[::-1]}


class Allow(BaseModel):
    text: str
    screen_id: str = ""


@app.post("/allow")
async def allow(a: Allow) -> dict:
    """Human review: a false positive becomes a benign example in Drex's criteria next time. Only text Airlock
    actually quarantined can be allowed, so this endpoint can't be used to whitelist arbitrary injections."""
    if not any(q.get("text") == a.text for q in _tail(audit.QUARANTINE, 10_000)):
        raise HTTPException(404, "not in quarantine")
    with system1.ALLOW.open("a") as f:
        f.write(json.dumps(a.model_dump()) + "\n")
    return {"ok": True}


app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
