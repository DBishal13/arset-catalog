"""Create or update training records from scraped pages."""
from __future__ import annotations

import json
from dataclasses import dataclass

from . import scrape, tagging, youtube
from .catalog import SCHEMAS, Catalog, iter_materials, iter_videos, slugify

TRAINING_FIELDS = list(
    json.loads((SCHEMAS / "training.schema.json").read_text(encoding="utf-8"))["properties"]
)


def _ordered(record: dict) -> dict:
    """Schema field order, with any unknown keys kept at the end for validation to flag."""
    known = {k: record[k] for k in TRAINING_FIELDS if k in record}
    return known | {k: v for k, v in record.items() if k not in known}


@dataclass
class Scraped:
    record: dict  # draft training record; videos not enriched yet
    people: list[dict]  # instructors as listed on the page
    is_arset: bool
    linked: list[str]  # slugs of other trainings the page links to


def scrape_training(cat: Catalog, url: str) -> Scraped:
    record = scrape.parse_training(scrape.fetch(url), url)
    is_arset = record.pop("_is_arset")
    people = record.pop("_instructors")
    linked = record.pop("_linked")
    record["instructors"] = [slugify(p["name"]) for p in people] or None
    record.update(tagging.suggest(cat, tagging.training_text(record)))
    return Scraped(_ordered({k: v for k, v in record.items() if v}), people, is_arset, linked)


def add_new(cat: Catalog, scraped: Scraped) -> list[str]:
    """Save a scraped training that is not in the catalog yet. Returns ids of instructors created."""
    enrich_videos(scraped.record)
    created = ensure_instructors(cat, scraped.people)
    cat.save("training", scraped.record)
    return created


def update_existing(cat: Catalog, existing: dict, scraped: Scraped, save: bool = True) -> list[str]:
    """Merge a re-scraped page into its record; create stubs for instructors it now references."""
    changes = merge(existing, scraped.record)
    if changes and save:
        referenced = set(existing.get("instructors") or [])
        ensure_instructors(cat, [p for p in scraped.people if slugify(p["name"]) in referenced])
        cat.save("training", existing)
    return changes


def ensure_instructors(cat: Catalog, people: list[dict]) -> list[str]:
    """Create draft instructor records for people not in the catalog yet."""
    created = []
    for person in people:
        id_ = slugify(person["name"])
        if id_ not in cat["instructor"]:
            cat.save("instructor", {"id": id_, "name": person["name"], "status": "draft",
                                    **{k: person[k] for k in ("title", "affiliation") if k in person}})
            created.append(id_)
    return created


def enrich_videos(record: dict) -> None:
    for _, video in iter_videos(record):
        if "title" not in video:
            youtube.enrich(video)


def merge(existing: dict, scraped: dict) -> list[str]:
    """Add what the page has and the record lacks. Never overwrites or deletes.

    Drafts also get missing top-level fields filled in; reviewed records only
    gain new sessions, videos and materials, so removed tags stay removed.
    Returns a human-readable list of changes.
    """
    changes = []
    if existing.get("status") == "draft":
        for key, value in scraped.items():
            if key not in existing and key not in ("status", "sessions", "videos", "materials"):
                existing[key] = value
                changes.append(f"added {key}")

    known_videos = {v["youtube"] for _, v in iter_videos(existing)}
    known_urls = {m["url"] for _, m in iter_materials(existing)}
    sessions = {s["part"]: s for s in existing.setdefault("sessions", [])}

    def add_items(target: dict, source: dict, where: str) -> None:
        for video in source.get("videos") or []:
            if video["youtube"] not in known_videos:
                youtube.enrich(video)
                target.setdefault("videos", []).append(video)
                known_videos.add(video["youtube"])
                changes.append(f"{where}: new video {video['youtube']} {video.get('title', '')}".rstrip())
        for material in source.get("materials") or []:
            if material["url"] not in known_urls:
                target.setdefault("materials", []).append(material)
                known_urls.add(material["url"])
                changes.append(f"{where}: new {material['type']} {material.get('title', material['url'])}")

    for session in scraped.get("sessions") or []:
        part = session["part"]
        if part not in sessions:
            new = {k: v for k, v in session.items() if k not in ("videos", "materials")}
            existing["sessions"].append(new)
            sessions[part] = new
            changes.append(f"new session: Part {part} {session['title']}")
        elif "date" in session and "date" not in sessions[part]:
            sessions[part]["date"] = session["date"]
        add_items(sessions[part], session, f"Part {part}")
    existing["sessions"].sort(key=lambda s: s["part"])
    if not existing["sessions"]:
        del existing["sessions"]
    add_items(existing, scraped, "training")

    ordered = _ordered(existing)
    existing.clear()
    existing.update(ordered)
    return changes
