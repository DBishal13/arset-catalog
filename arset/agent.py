"""Chat agent over the ARSET catalog and training materials.

A tool-calling agent (LangChain create_agent) with four tools: hybrid search
over slides/Q&A/training text (rag.index), training details, structured
filtering, and catalog statistics for "which data is used in which domain"
questions. The model is Gemini via the free Gemini Developer API by default
(set GOOGLE_API_KEY in .env); ARSET_LLM_MODEL overrides the model name.
"""
from __future__ import annotations

import os
from collections import Counter
from functools import lru_cache

from dotenv import load_dotenv
from langchain_core.tools import tool

from . import catalog as catalog_module
from .catalog import ROOT, TRAINING_REFS

load_dotenv(ROOT / ".env")
MODEL = os.environ.get("ARSET_LLM_MODEL", "gemini-flash-lite-latest")
GROUPS = {"application": "applications", "satellite": "satellites", "dataset": "datasets", "tool": "tools",
          "instructor": "instructors"}

SYSTEM_PROMPT = """You are the EO Training Atlas assistant. You help one person navigate NASA ARSET's \
Earth-observation trainings: which training covers a topic, where a method is explained, what was \
answered in past Q&A sessions, and which datasets and satellites are used in which application domains.

Always answer from the tools, never from memory: training content, dates and links change, and you \
must not invent trainings, URLs, page numbers or quotes.
- For "how do I / where is / what did they say about" questions, call search_materials. Search again \
with different wording or filters if the first results are off-topic.
- For questions about one training (sessions, recordings, slides, instructors), call get_training.
- For lists ("trainings on SAR since 2022", "intermediate air quality trainings"), call find_trainings.
- For counts and comparisons across the archive ("which domains use GPM", "how has SAR coverage \
changed"), call catalog_stats. Say that tags are auto-generated, so counts are approximate.
- For "where do I download / get" a dataset, call dataset_access and give the Earthdata Search link \
first, mention the free Earthdata Login, and suggest AppEEARS or Giovanni to avoid large downloads.

Cite every claim with a markdown link to its source, using the url a tool returned, written like \
[Training title, Part 2 slides p.14](url). Prefer the most recent training unless asked otherwise, \
and say which year a training is from. If the tools return nothing relevant, say the archive doesn't \
seem to cover it rather than guessing. Keep answers short and practical: a few sentences or a short \
list, with the links."""


@lru_cache(maxsize=1)
def _cat():
    return catalog_module.load()


def _year(t: dict) -> str:
    return (t.get("start_date") or "")[:4] or "self-paced"


def _page_url(url: str, page: int | None) -> str:
    return f"{url}#page={page}" if page and url.lower().split("?")[0].endswith(".pdf") else url


@tool
def search_materials(query: str, kind: str | None = None, material_type: str | None = None,
                     level: str | None = None, since_year: int | None = None) -> list[dict]:
    """Search slides, Q&A transcripts, homework/exercises and training descriptions.

    query: what to look for, in plain words (e.g. "open SMAP soil moisture in QGIS").
    kind: optional "qa" (answers from past Q&A sessions), "page" (slides and documents) or
          "catalog" (training descriptions - good for "which training covers X").
    material_type: optional "slides", "transcript", "exercise" or "homework".
    level: optional "fundamentals", "introductory", "intermediate" or "advanced".
    since_year: optional, only trainings from this year on.
    """
    from .rag.index import search
    filters = {k: v for k, v in {"kind": kind, "material_type": material_type, "level": level,
                                 "since_year": since_year}.items() if v}
    out = []
    for hit in search(query, k=8, **filters):
        c = hit.chunk
        out.append({
            "training_id": c["training_id"], "training": c["training_title"], "year": (c["start_date"] or "")[:4],
            "part": c["part"], "source": c["material_title"] or c["material_type"] or "training page",
            "page": c["page"], "url": _page_url(c["url"], c["page"]), "excerpt": c["text"][:900],
        })
    return out


@tool
def get_training(training_id: str) -> dict:
    """Full details of one training: dates, level, summary, objectives, instructors, and each session's
    recordings and materials with links. training_id comes from the other tools' results."""
    cat = _cat()
    t = cat["training"].get(training_id)
    if t is None:
        return {"error": f"no training with id {training_id!r}"}
    people = [{"name": cat["instructor"].get(i, {}).get("name", i),
               "affiliation": cat["instructor"].get(i, {}).get("affiliation")} for i in t.get("instructors") or []]
    sessions = [{
        "part": s["part"], "title": s["title"], "date": s.get("date"),
        "recordings": [{"title": v.get("title"), "url": f"https://www.youtube.com/watch?v={v['youtube']}"}
                       for v in s.get("videos") or []],
        "materials": [{"type": m["type"], "title": m.get("title"), "url": m["url"]} for m in s.get("materials") or []],
    } for s in t.get("sessions") or []]
    return {
        "id": t["id"], "title": t["title"], "year": _year(t), "dates": [t.get("start_date"), t.get("end_date")],
        "level": t.get("level"), "format": t.get("format"), "languages": t.get("languages"),
        "summary": t.get("summary"), "objectives": t.get("objectives"), "instructors": people,
        "sessions": sessions, "prerequisites": t.get("prerequisites"), "official_page": t["source_url"],
        **{f: t.get(f) for f in TRAINING_REFS if f != "instructors"},
    }


def _matches(t: dict, application, satellite, dataset, tool_name, level, year_from, year_to, text) -> bool:
    year = (t.get("start_date") or "")[:4]
    checks = [
        (application, lambda v: v in (t.get("applications") or [])),
        (satellite, lambda v: v in (t.get("satellites") or [])),
        (dataset, lambda v: v in (t.get("datasets") or [])),
        (tool_name, lambda v: v in (t.get("tools") or [])),
        (level, lambda v: t.get("level") == v),
        (year_from, lambda v: year and year >= str(v)),
        (year_to, lambda v: year and year <= str(v)),
        (text, lambda v: v.lower() in f"{t['title']} {t.get('summary', '')} {t.get('description', '')}".lower()),
    ]
    return all(fn(value) for value, fn in checks if value)


@tool
def find_trainings(application: str | None = None, satellite: str | None = None, dataset: str | None = None,
                   tool_name: str | None = None, level: str | None = None, year_from: int | None = None,
                   year_to: int | None = None, text: str | None = None) -> dict:
    """List trainings matching structured filters (all optional, combined with AND).

    application/satellite/dataset/tool_name: catalog ids - call catalog_stats(group_by=...) with no
        filters first if you need the valid ids (e.g. satellite "gpm", application "water-resources").
    level: "fundamentals", "introductory", "intermediate" or "advanced".
    year_from/year_to: training start year range.
    text: words that must appear in the title, summary or description.
    """
    found = [t for t in _cat()["training"].values()
             if _matches(t, application, satellite, dataset, tool_name, level, year_from, year_to, text)]
    found.sort(key=lambda t: t.get("start_date") or "", reverse=True)
    return {"count": len(found), "trainings": [
        {"id": t["id"], "title": t["title"], "year": _year(t), "level": t.get("level"),
         "applications": t.get("applications"), "satellites": t.get("satellites"), "url": t["source_url"]}
        for t in found[:25]]}


@tool
def catalog_stats(group_by: str, application: str | None = None, satellite: str | None = None,
                  dataset: str | None = None, tool_name: str | None = None, level: str | None = None,
                  year_from: int | None = None, year_to: int | None = None) -> dict:
    """Count trainings grouped by "application", "satellite", "dataset", "tool", "instructor", "year" or
    "level", optionally within filters (same meaning as in find_trainings). With no filters this also
    lists every valid id for that group. Example: which application domains use GPM data ->
    group_by="application", satellite="gpm". Tags are auto-generated, so counts are approximate."""
    cat = _cat()
    found = [t for t in cat["training"].values()
             if _matches(t, application, satellite, dataset, tool_name, level, year_from, year_to, None)]
    counts: Counter = Counter()
    for t in found:
        if group_by == "year":
            counts[_year(t)] += 1
        elif group_by == "level":
            counts[t.get("level") or "unknown"] += 1
        elif group_by in GROUPS:
            counts.update(t.get(GROUPS[group_by]) or [])
        else:
            return {"error": f"group_by must be one of {sorted([*GROUPS, 'year', 'level'])}"}
    kind = group_by if group_by in GROUPS else None
    names = {i: (r.get("name") or i) for i, r in cat[kind].items()} if kind else {}
    return {"trainings_matched": len(found), "counts": [
        {"id": k, "name": names.get(k, k), "trainings": n} for k, n in counts.most_common()]}


@tool
def dataset_access(dataset_id: str) -> dict:
    """Where to download or explore a dataset: NASA Earthdata Search, the archive's subsetting tool,
    AppEEARS/Giovanni/Worldview, user guide and DOI, per collection (latest version). dataset_id is a
    catalog id such as "smap-l3-soil-moisture" or "gpm-imerg"; call catalog_stats(group_by="dataset")
    to list them. Downloading needs a free Earthdata Login."""
    from .datasets import EARTHDATA_SIGNUP, load_access
    d = _cat()["dataset"].get(dataset_id)
    if d is None:
        return {"error": f"no dataset with id {dataset_id!r}"}
    return {"dataset": d["name"], "provider": d.get("provider"), "collections": load_access().get(dataset_id, []),
            "earthdata_login_signup": EARTHDATA_SIGNUP}


TOOLS = [search_materials, get_training, find_trainings, catalog_stats, dataset_access]


@lru_cache(maxsize=1)
def build_agent():
    from langchain.agents import create_agent
    from langchain_google_genai import ChatGoogleGenerativeAI

    if not (os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")):
        raise SystemExit("No Gemini key found. Create a free key at https://aistudio.google.com/apikey and put "
                         "GOOGLE_API_KEY=... in D:\\ARSET\\.env")
    return create_agent(ChatGoogleGenerativeAI(model=MODEL), TOOLS, system_prompt=SYSTEM_PROMPT)


def _text(content) -> str:
    """Gemini returns a list of content blocks (text plus extras); flatten to the text."""
    if isinstance(content, list):
        return "\n".join(b["text"] for b in content if isinstance(b, dict) and b.get("type") == "text")
    return content


def ask(question: str, history: list | None = None) -> tuple[str, list]:
    """Answer a question; returns (answer, updated message history for follow-ups)."""
    messages = (history or []) + [{"role": "user", "content": question}]
    result = build_agent().invoke({"messages": messages})
    return _text(result["messages"][-1].content), result["messages"]
