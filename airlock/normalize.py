"""Step 1: any tool result -> markdown text + kind. PDFs go through NDI (keeps hidden text); URLs through Keenable."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def parse_document_ndi(path: str | Path) -> str:
    """NDI parse -> markdown, cached by file hash. Raises on any failure so callers can fall back."""
    from airlock.clients import CACHE

    cached = CACHE / f"ndi-{hashlib.sha256(Path(path).read_bytes()).hexdigest()[:32]}.md"
    if cached.exists():
        return cached.read_text()
    markdown = _ndi_parse(path)
    cached.write_text(markdown)
    return markdown


def _ndi_parse(path: str | Path) -> str:
    from nace_sdk import NaceClient

    # Same host as Drex (clients.DREX_URL); console.nace.ai sits behind a bot checkpoint under load.
    with NaceClient(api_key=os.environ["NACE_API_KEY"], base_url=os.getenv("NACE_BASE_URL", "https://drex.nace.ai")) as client:
        uploaded = client.documents.upload(Path(path), on_conflict="new_version")
        job = client.documents.parse(uploaded.as_source(), output={"formats": ["markdown"]})
        done = client.jobs.wait(job.job_id, timeout=120)
        doc = done.result["document"]
        if doc.get("markdown"):
            return doc["markdown"]
        out = Path(path).with_suffix(".ndi.md")
        client.jobs.download(job.job_id, doc["content_url"], out)
        return out.read_text()


def parse_document_pypdf(path: str | Path) -> str:
    from pypdf import PdfReader

    return "\n\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)


def parse_document(path: str | Path) -> tuple[str, str | None]:
    """Returns (text_layer, visible_markdown).

    The text layer is what an agent's file reader ingests, hidden text included. NDI parses the document as
    rendered, i.e. what a human sees. Text in the first but not the second is hidden (white/tiny/off-page).
    visible_markdown is None if NDI is unavailable (then we have no visibility signal and say so).
    """
    layer = parse_document_pypdf(path) if Path(path).suffix.lower() == ".pdf" else ""
    try:
        visible = parse_document_ndi(path)
    except Exception as e:  # NDI down/slow: fall back, and say so
        print(f"[airlock] NDI parse failed ({type(e).__name__}: {e}); no visibility signal")
        visible = None
    return (layer or visible or ""), visible


def fetch_url(url: str) -> str:
    import keenable

    page = keenable.Keenable().fetch(url, max_chars=20000)
    return page.content or ""


def normalize(content: Any, meta: dict | None = None) -> tuple[str | dict | list, str]:
    """Returns (text or parsed JSON, kind). kind in {text, json, document, web}.

    Content is untrusted, so a string is never opened as a file or fetched as a URL on its own say-so: only a
    `Path` passed by our own code is parsed, and only `meta["fetch"] = True` (the caller asking) fetches a URL.
    """
    meta = meta if meta is not None else {}
    if isinstance(content, (dict, list)):
        return content, "json"
    if isinstance(content, Path):
        text, visible = parse_document(content)
        layer = "pypdf+" if content.suffix.lower() == ".pdf" else ""
        meta["parser"] = f"{layer}ndi" if visible is not None else "pypdf"
        meta["visible_text"] = visible
        return text, "document"
    if meta.get("fetch") and isinstance(content, str) and content.strip().startswith(("http://", "https://")):
        return fetch_url(content.strip()), "web"
    if isinstance(content, str):
        s = content.strip()
        if s[:1] in "{[":
            try:
                return json.loads(s), "json"
            except json.JSONDecodeError:
                pass
        return content, "text"
    return str(content), "text"
