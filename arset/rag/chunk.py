"""Split the catalog and extracted materials into search chunks.

Chunk types, each with the training/part/material context needed to cite it:
- "catalog": one per training, from its title, summary, description,
  objectives and session agendas - answers "which training covers X?".
- "qa": one per question/answer pair in Q&A transcripts.
- "page": one per slide or document page; long pages are split into
  overlapping windows. Pages too short to mean anything are dropped.

The embedding model reads ~256 tokens, so chunk text is kept to ~180 words;
the short header (training title, part) is part of the text it embeds.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass

from ..catalog import Catalog
from . import TEXT_DIR

MAX_WORDS = 180
OVERLAP_WORDS = 40
MIN_WORDS = 12  # title-only slides, page numbers, logos
QA_MARK = re.compile(r"(?m)^\s*(?:[Qq]uestion\s*\d*\s*[:.)]|Q\s*\d*\s*:)")
ANSWER_MARK = re.compile(r"\b[Aa]nswer\s*\d*\s*[:.)]|\bA\s*\d*\s*:")


@dataclass
class Chunk:
    id: str
    kind: str  # catalog | qa | page
    text: str  # what is embedded and keyword-indexed
    training_id: str
    training_title: str
    start_date: str | None = None
    level: str | None = None
    part: int | None = None
    material_type: str | None = None  # slides, transcript, homework, ...
    material_title: str | None = None
    url: str | None = None
    page: int | None = None  # 1-based page in the PDF


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _windows(words: list[str]) -> list[str]:
    if len(words) <= MAX_WORDS:
        return [" ".join(words)]
    step = MAX_WORDS - OVERLAP_WORDS
    return [" ".join(words[i:i + MAX_WORDS]) for i in range(0, max(len(words) - OVERLAP_WORDS, 1), step)]


def _header(m: dict) -> str:
    part = f", Part {m['part']}" if m.get("part") else ""
    return f"{m['training_title']}{part}."


def catalog_chunks(cat: Catalog) -> list[Chunk]:
    chunks = []
    for t in cat["training"].values():
        sessions = "; ".join(
            f"Part {s['part']}: {s['title']}" + (f" ({', '.join(s['agenda'])})" if s.get("agenda") else "")
            for s in t.get("sessions") or [])
        parts = [t["title"] + ".", t.get("summary", ""), t.get("description", ""),
                 "Objectives: " + " ".join(t.get("objectives") or []), sessions]
        words = _clean(" ".join(p for p in parts if p)).split()
        base = {"training_id": t["id"], "training_title": t["title"], "start_date": t.get("start_date"),
                "level": t.get("level"), "url": t["source_url"]}
        for i, text in enumerate(_windows(words)):
            chunks.append(Chunk(id=f"cat:{t['id']}:{i}", kind="catalog", text=text, **base))
    return chunks


def _qa_pairs(text: str) -> list[tuple[int, str]]:
    """Split a transcript at each 'Question N:'; keep pieces that contain an answer.
    Returns (offset in text, cleaned piece)."""
    starts = [m.start() for m in QA_MARK.finditer(text)]
    pieces = [(a, text[a:b]) for a, b in zip(starts, starts[1:] + [len(text)])]
    return [(a, _clean(p)) for a, p in pieces if ANSWER_MARK.search(p)]


def material_chunks(material: dict) -> list[Chunk]:
    m = material
    base = {"training_id": m["training_id"], "training_title": m["training_title"],
            "start_date": m.get("start_date"), "level": m.get("level"), "part": m.get("part"),
            "material_type": m["type"], "material_title": m.get("title"), "url": m["url"]}
    header = _header(m)
    chunks: list[Chunk] = []

    if m["type"] in ("transcript", "qa"):
        # Pairs can span pages, so join the pages and cite the page each pair starts on.
        page_starts, full = [], ""
        for text in m["pages"]:
            page_starts.append(len(full))
            full += text + "\n"
        for i, (pos, pair) in enumerate(_qa_pairs(full)):
            page = sum(1 for s in page_starts if s <= pos) or 1
            for j, text in enumerate(_windows(pair.split())):
                chunks.append(Chunk(id=f"qa:{m['id']}:{i}:{j}", kind="qa", text=f"{header} {text}", page=page, **base))
        if chunks:
            return chunks  # otherwise fall through and index it page by page

    for page_no, text in enumerate(m["pages"], 1):
        words = _clean(text).split()
        if len(words) < MIN_WORDS:
            continue
        for j, piece in enumerate(_windows(words)):
            chunks.append(Chunk(id=f"pg:{m['id']}:{page_no}:{j}", kind="page", text=f"{header} {piece}",
                                page=page_no, **base))
    return chunks


BROKEN_TI = re.compile(r"\b[A-Za-z]+[4?][A-Za-z]+\b")


def ligature_fixer(materials: list[dict]):
    """Older slide decks extract the "ti" ligature as "4" or "?" ("applica4ons").
    Repair a word only if its repaired form occurs elsewhere in the corpus, so
    URLs ("watch?v") and real names ("sen4stat") are left alone."""
    vocab = {w.lower() for m in materials for p in m["pages"] for w in re.findall(r"[A-Za-z]{4,}", p)}

    def repair(match: re.Match) -> str:
        word = match.group(0)
        fixed = re.sub(r"[4?]", "ti", word)
        return fixed if fixed.lower() in vocab else word

    return lambda text: BROKEN_TI.sub(repair, text)


def all_chunks(cat: Catalog) -> list[Chunk]:
    materials = []
    for path in sorted(TEXT_DIR.glob("*.json")):
        try:
            materials.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:  # still being written by a running collect
            continue
    fix = ligature_fixer(materials)
    chunks = catalog_chunks(cat)
    for m in materials:
        chunks += material_chunks(m | {"pages": [fix(p) for p in m["pages"]]})
    return chunks


def as_dict(chunk: Chunk) -> dict:
    return asdict(chunk)
