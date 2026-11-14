"""One place for every model call: timeout, retry (never on 4xx), on-disk cache, request-id logging."""

from __future__ import annotations

import asyncio
import contextvars
import hashlib
import json
import os
import time
import weakref
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

CACHE = ROOT / "runs" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

# drex.nace.ai is the Drex API host listed in nace-sdk; console.nace.ai sits behind a bot checkpoint under load.
DREX_URL = os.getenv("DREX_URL", "https://drex.nace.ai/v1/systemone")
DREX_MODEL = os.getenv("DREX_MODEL", "drex-max-v1.1")
DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
QWEN_MODEL = os.getenv("QWEN_MODEL", "Qwen/Qwen3.8-27B")

# $ per 1M input / output tokens. Override via env once the console shows exact prices.
DREX_PRICE_IN = float(os.getenv("DREX_PRICE_IN", "0.10"))
DREX_PRICE_OUT = float(os.getenv("DREX_PRICE_OUT", "0.10"))
QWEN_PRICE_IN = float(os.getenv("QWEN_PRICE_IN", "0.20"))  # DeepInfra /models pricing, Qwen3.8-27B
QWEN_PRICE_OUT = float(os.getenv("QWEN_PRICE_OUT", "2.50"))

# Keyed on the loop object (weakly), not id(): a closed loop's id can be reused by the next asyncio.run.
# Live mode (the dashboard's toggle) turns the replay cache off for one request's model calls.
CACHE_ON: contextvars.ContextVar[bool] = contextvars.ContextVar("airlock_cache_on", default=True)

_http: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, httpx.AsyncClient] = weakref.WeakKeyDictionary()


def http() -> httpx.AsyncClient:
    """One pooled client per event loop (asyncio.run in scripts, uvicorn's loop in the service)."""
    loop = asyncio.get_running_loop()
    if loop not in _http:
        _http[loop] = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0),
                                        limits=httpx.Limits(max_connections=64))
    return _http[loop]


def _key(kind: str, body: dict) -> Path:
    h = hashlib.sha256((kind + json.dumps(body, sort_keys=True)).encode()).hexdigest()[:32]
    return CACHE / f"{kind}-{h}.json"


class ModelError(RuntimeError):
    pass


async def post_json(kind: str, url: str, key_env: str, body: dict, *, retries: int = 3,
                    timeout: float = 60.0, use_cache: bool | None = None) -> tuple[dict, float, bool]:
    """POST `body`; returns (response json, wall ms, cache_hit). Cached by body hash."""
    path = _key(kind, body)
    if use_cache is None:
        use_cache = CACHE_ON.get()
    if use_cache and path.exists():
        data = json.loads(path.read_text())
        return data["response"], data["ms"], True
    headers = {"Authorization": f"Bearer {os.environ[key_env]}", "Content-Type": "application/json"}
    last: Exception | None = None
    for attempt in range(retries):
        t0 = time.perf_counter()
        try:
            r = await http().post(url, json=body, headers=headers, timeout=timeout)
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last = e
            await asyncio.sleep(1.5 * (attempt + 1))
            continue
        ms = (time.perf_counter() - t0) * 1000
        if r.status_code == 200:
            data = r.json()
            path.write_text(json.dumps({"response": data, "ms": ms}))
            return data, ms, False
        if r.status_code in (429, 500, 502, 503, 504):
            last = ModelError(f"{kind} {r.status_code}: {r.text[:300]}")
            await asyncio.sleep(2.0 * (attempt + 1))
            continue
        raise ModelError(f"{kind} {r.status_code}: {r.text[:500]}")  # 4xx (incl. 422): fix the body
    raise ModelError(f"{kind} failed after {retries} tries: {last}")


_drex_slots: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore] = weakref.WeakKeyDictionary()


async def drex(state: dict, questions: dict, **kw) -> tuple[dict, float, bool]:
    loop = asyncio.get_running_loop()
    slots = _drex_slots.setdefault(loop, asyncio.Semaphore(int(os.getenv("DREX_CONCURRENCY", "8"))))
    async with slots:  # bounded, so a benchmark burst doesn't look like a flood
        return await post_json("drex", DREX_URL, "NACE_API_KEY",
                               {"model": DREX_MODEL, "state": state, "questions": questions}, **kw)


async def qwen(messages: list[dict], *, max_tokens: int = 300, **kw) -> tuple[dict, float, bool]:
    body = {"model": QWEN_MODEL, "messages": messages, "temperature": 0, "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "chat_template_kwargs": {"enable_thinking": False}}
    return await post_json("qwen", DEEPINFRA_URL, "DEEPINFRA_API_KEY", body, **kw)


async def qwen_text(messages: list[dict], *, max_tokens: int = 500, **kw) -> tuple[str, float]:
    """Plain completion (used by the demo agent, not by the screener)."""
    body = {"model": QWEN_MODEL, "messages": messages, "temperature": 0, "max_tokens": max_tokens,
            "chat_template_kwargs": {"enable_thinking": False}}
    data, ms, _ = await post_json("qwen", DEEPINFRA_URL, "DEEPINFRA_API_KEY", body, **kw)
    return strip_think(data["choices"][0]["message"]["content"] or ""), ms


def strip_think(text: str) -> str:
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    return text.strip()


def parse_json_reply(text: str) -> dict:
    text = strip_think(text)
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])
