"""Airlock as an Intern extension: every tool result is screened before it enters the agent's context.

    intern --extension airlock.intern_ext:Airlock -p --json -- "Read demo/invoice_poisoned.pdf and summarize ..."

Intern's tool-call guard runs before a call; nothing checked what a tool *returned*. `tool_result` runs after the
tool and before the window bound, so Airlock replaces only the offending spans and reports them as an
`extension` event. It also adds `read_document`, since Intern's `read` refuses binary files: it returns the PDF's
text layer (what a file reader ingests, hidden text included) and keeps NDI's rendering for the visibility signal.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, Field

from intern.events import ExtensionEvent
from intern.hooks import Extension, RunContext
from intern.journal import MessageEntry
from intern.messages import ToolCall, ToolResult, UserMessage
from intern.tools.base import Effect, Tool, ToolContext, ToolOutput, fail

from airlock.normalize import parse_document
from airlock.screen import screen

# Tools whose results are the agent's own doing, not third-party content.
SKIP = {"write", "edit", "todo"}
MIN_CHARS = int(os.getenv("AIRLOCK_MIN_CHARS", "40"))


class ReadDocumentArgs(BaseModel):
    path: str = Field(description="PDF or other document, relative to the working directory or absolute.")


class ReadDocumentTool(Tool):
    name = "read_document"
    description = "Read a PDF or other document and return its text."
    Args = ReadDocumentArgs
    effects: ClassVar[frozenset[Effect]] = frozenset({"read"})

    def __init__(self, visible: dict[str, str | None]) -> None:
        self.visible = visible

    async def run(self, args: ReadDocumentArgs, ctx: ToolContext) -> ToolOutput:
        path = ctx.resolve(args.path)
        if not path.is_file():
            return fail(f"{args.path} does not exist", "Check the name with find.", argument="path")
        text, visible = await asyncio.to_thread(parse_document, path)
        self.visible[str(path)] = visible
        return ToolOutput(content=text)


class Removal(BaseModel):
    tool: str
    call_id: str
    verdict: str
    doc_intent: str
    removed: list[dict]
    stats: dict


def user_goal(ctx: RunContext) -> str:
    """The latest request the user typed (not the engine's own nudges)."""
    for entry in reversed(ctx.journal.active_path()):
        if isinstance(entry, MessageEntry) and isinstance(entry.message, UserMessage) and entry.message.source == "user":
            return entry.message.content
    return ""


class Airlock(Extension):
    name: ClassVar[str] = "airlock"

    def __init__(self) -> None:
        self.visible: dict[str, str | None] = {}

    def tools(self) -> list[Tool]:
        return [ReadDocumentTool(self.visible)]

    async def tool_result(self, call: ToolCall, result: ToolResult, ctx: RunContext) -> ToolResult | None:
        if result.status != "ok" or call.name in SKIP or len(result.content) < MIN_CHARS:
            return None
        meta = {"tool": call.name, "source_name": str(call.arguments.get("path") or call.arguments.get("url") or "")}
        if call.name == "read_document":
            meta["visible_text"] = self.visible.get(str(Path(ctx.cwd, meta["source_name"]).resolve()))
        r = await screen(result.content, meta, user_goal(ctx))
        ctx.emit(ExtensionEvent.of(self.name, "screen", Removal(
            tool=call.name, call_id=call.id, verdict=r.verdict, doc_intent=r.doc_intent,
            removed=[x.model_dump() for x in r.removed],
            stats={k: v for k, v in r.stats.items() if k in ("chunks", "s1_ms", "s2_calls", "total_ms", "request_ids")})))
        if r.verdict == "clean":
            return None
        sanitized = r.sanitized if isinstance(r.sanitized, str) else json.dumps(r.sanitized, indent=2)
        return result.model_copy(update={"content": sanitized})


class DocumentReader(Extension):
    """Only the `read_document` tool, no screening: the 'without Airlock' arm of the demo."""

    name: ClassVar[str] = "document-reader"

    def tools(self) -> list[Tool]:
        return [ReadDocumentTool({})]
