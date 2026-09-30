"""Suggest satellites/datasets/tools/applications for a training from its text.

Each record's name and `aliases` (plus instrument names for satellites) are
matched as whole words. Aliases written in capitals ("SAR", "GPM") are matched
case-sensitively so they do not hit ordinary words.
"""
from __future__ import annotations

import re

from .catalog import Catalog

FIELD_KIND = {"satellites": "satellite", "datasets": "dataset", "tools": "tool", "applications": "application"}


def _terms(kind: str, rec: dict) -> list[str]:
    terms = [rec.get("name", "")] + list(rec.get("aliases") or [])
    if kind == "satellite":
        terms += [i["name"] for i in rec.get("instruments") or []]
    if kind == "dataset" and rec.get("short_name"):
        terms.append(rec["short_name"])
    return [t for t in terms if t and len(t) >= 3]


def _pattern(term: str) -> re.Pattern:
    flags = re.IGNORECASE if any(c.islower() for c in term) else 0
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", flags)


def training_text(t: dict) -> str:
    parts = [t.get("title", ""), t.get("summary", ""), t.get("description", "")]
    parts += t.get("objectives") or []
    for s in t.get("sessions") or []:
        parts.append(s.get("title", ""))
        parts += s.get("agenda") or []
        parts += [m.get("title", "") for m in s.get("materials") or []]
    return "\n".join(p for p in parts if p)


def suggest(cat: Catalog, text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for field, kind in FIELD_KIND.items():
        hits = [
            id_ for id_, rec in sorted(cat[kind].items())
            if any(_pattern(term).search(text) for term in _terms(kind, rec))
        ]
        if hits:
            out[field] = hits
    return out
