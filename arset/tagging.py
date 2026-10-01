"""Suggest satellites/datasets/tools/applications for a training from its text.

Each record's name and `aliases` (plus instrument names for satellites) are
matched as whole words. Aliases written in capitals ("SAR", "GPM") are matched
case-sensitively so they do not hit ordinary words.

Mentions are weighted by where they appear (title > summary > the rest).
Satellites, datasets and tools have specific names, so one mention anywhere
is enough. Application areas are matched on common words ("forest",
"climate"), so they need more weight and only the strongest few are kept.

When the extracted slide/transcript text is available (corpus/, see
arset.rag), it is used too: a satellite, dataset or tool mentioned at least
MATERIAL_MENTIONS[field] times across a training's materials is tagged. Application
areas ignore it - their words are too common in slides.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from functools import lru_cache

from .catalog import ROOT, Catalog

FIELD_KIND = {"satellites": "satellite", "datasets": "dataset", "tools": "tool", "applications": "application"}
WEIGHTS = {"title": 3, "summary": 2, "body": 1}
MIN_SCORE = {"applications": 3}  # others: 1
MAX_TAGS = {"applications": 3}
# Mentions across a training's materials needed per tag. Overview slides name-drop many
# missions, so satellites need the most; dataset names are the most specific.
MATERIAL_MENTIONS = {"satellites": 10, "tools": 5, "datasets": 3}
CORPUS_TEXT = ROOT / "corpus" / "text"


def materials_text_by_training() -> dict[str, str]:
    """All extracted material text per training id ({} if the corpus hasn't been collected)."""
    out: dict[str, list[str]] = defaultdict(list)
    for path in CORPUS_TEXT.glob("*.json") if CORPUS_TEXT.exists() else []:
        m = json.loads(path.read_text(encoding="utf-8"))
        out[m["training_id"]].extend(m["pages"])
    return {k: "\n".join(v) for k, v in out.items()}


def _terms(kind: str, rec: dict) -> list[str]:
    terms = [rec.get("name", "")] + list(rec.get("aliases") or [])
    if kind == "satellite":
        terms += [i["name"] for i in rec.get("instruments") or []]
    if kind == "dataset" and rec.get("short_name"):
        terms.append(rec["short_name"])
    return [t for t in terms if t and len(t) >= 3]


@lru_cache(maxsize=None)
def _pattern(term: str) -> re.Pattern:
    flags = re.IGNORECASE if any(c.islower() for c in term) else 0
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", flags)


def training_text(t: dict) -> dict[str, str]:
    """The training's text split by where it appears, for weighting."""
    body = [t.get("description", "")] + list(t.get("objectives") or [])
    for s in t.get("sessions") or []:
        body.append(s.get("title", ""))
        body += s.get("agenda") or []
        body += [m.get("title", "") for m in s.get("materials") or []]
    return {"title": t.get("title", ""), "summary": t.get("summary", ""), "body": "\n".join(p for p in body if p)}


def suggest(cat: Catalog, text: dict[str, str] | str) -> dict[str, list[str]]:
    if isinstance(text, str):
        text = {"body": text}
    out: dict[str, list[str]] = {}
    for field, kind in FIELD_KIND.items():
        scores = {}
        for id_, rec in cat[kind].items():
            terms = _terms(kind, rec)
            score = sum(w * sum(1 for term in terms if _pattern(term).search(text.get(part, "")))
                        for part, w in WEIGHTS.items())
            if field != "applications" and text.get("materials"):
                mentions = sum(len(_pattern(term).findall(text["materials"])) for term in terms)
                score += mentions // MATERIAL_MENTIONS[field]
            if score >= MIN_SCORE.get(field, 1):
                scores[id_] = score
        ranked = sorted(scores, key=lambda i: (-scores[i], i))[: MAX_TAGS.get(field)]
        if ranked:
            out[field] = sorted(ranked)
    return out
