"""Step 3: cheap, model-free hints. They go into Drex's state; they never decide anything alone."""

from __future__ import annotations

import re

from airlock.chunk import Chunk

PATTERNS = {
    "zero_width_or_bidi": re.compile("[​-‏‪-‮⁠-⁤﻿]"),
    "role_tag": re.compile(r"(<\|im_start\|>|<\|system\|>|\[/?INST\]|^\s*(system|assistant)\s*:)", re.I | re.M),
    "ignore_previous": re.compile(r"\b(ignore|disregard|forget)\b.{0,30}\b(previous|prior|above|earlier)\b", re.I),
    "addresses_ai": re.compile(r"\b(AI|assistant|agent|LLM|language model|chatbot|GPT|Claude)\b.{0,40}\b(must|should|please|now|instead|when)\b", re.I),
    "base64_blob": re.compile(r"[A-Za-z0-9+/]{60,}={0,2}"),
    "hidden_marker": re.compile(r"(color:\s*(white|#fff)|font-size:\s*0|display:\s*none|<!--)", re.I),
    "secrecy": re.compile(r"\b(do not|don't|never)\b.{0,20}\b(mention|tell|reveal|disclose)\b", re.I),
}


_WORD = re.compile(r"[a-z0-9]{3,}")


def annotate(chunks: list[Chunk], visible_text: str | None = None) -> list[Chunk]:
    """`visible_text`: NDI's rendering of the document. A chunk mostly absent from it is hidden from humans."""
    seen = set(_WORD.findall(visible_text.lower())) if visible_text else None
    for c in chunks:
        c.signals = [name for name, rx in PATTERNS.items() if rx.search(c.text)]
        if seen is not None:
            words = _WORD.findall(c.text.lower())
            if words and sum(w in seen for w in words) / len(words) < 0.6:
                c.signals.append("hidden_text_not_visible_when_rendered")
    return chunks
