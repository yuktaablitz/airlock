"""Step 2: text -> chunks of ~300-500 chars on paragraph/sentence boundaries, with exact offsets.
JSON -> one chunk per string leaf (long leaves split the same way), tagged with its json_path."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

TARGET, MAX = 400, 600
_SENT = re.compile(r"(?<=[.!?:])\s+(?=\S)|\n")


@dataclass
class Chunk:
    id: str
    text: str
    start: int
    end: int
    json_path: str | None = None
    signals: list[str] = field(default_factory=list)


def _pieces(text: str) -> list[tuple[int, int]]:
    """Sentence-ish spans (start, end) covering all non-blank text."""
    spans, pos = [], 0
    for m in _SENT.finditer(text):
        if text[pos:m.start()].strip():
            spans.append((pos, m.start()))
        pos = m.end()
    if text[pos:].strip():
        spans.append((pos, len(text)))
    out = []
    for s, e in spans:  # hard-split runaway sentences
        while e - s > MAX:
            out.append((s, s + MAX))
            s += MAX
        out.append((s, e))
    return out


def split_spans(text: str) -> list[tuple[int, int]]:
    """Merge sentence spans into chunks; a blank line ends a chunk once it is past half the target."""
    chunks: list[tuple[int, int]] = []
    cur: tuple[int, int] | None = None
    for s, e in _pieces(text):
        if cur is None:
            cur = (s, e)
            continue
        para_break = "\n\n" in text[cur[1]:s]
        if e - cur[0] > TARGET or (para_break and cur[1] - cur[0] > TARGET // 2):
            chunks.append(cur)
            cur = (s, e)
        else:
            cur = (cur[0], e)
    if cur:
        chunks.append(cur)
    return chunks


def chunk_text(text: str, prefix: str = "c") -> list[Chunk]:
    return [Chunk(f"{prefix}{i}", text[s:e], s, e) for i, (s, e) in enumerate(split_spans(text))]


def iter_leaves(obj, path: str = ""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_leaves(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from iter_leaves(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def chunk_json(obj) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path, value in iter_leaves(obj):
        if len(value.strip()) < 12:  # ids, enums, short codes carry no instructions
            continue
        for s, e in split_spans(value):
            chunks.append(Chunk(f"c{len(chunks)}", value[s:e], s, e, json_path=path))
    return chunks
