"""Find new ARSET trainings, recordings and materials.

1. Every training linked from the listing pages in tracker.yaml is checked.
   New ARSET trainings become draft records in data/trainings/.
2. Known trainings that are recent (or drafts) are re-scraped; new sessions,
   videos and materials are added to their records.
3. Recent uploads on the YouTube channels in tracker.yaml whose titles match
   the keywords, and that no training references yet, go to inbox/videos.yaml
   for a person to assign.

A summary is written to inbox/REPORT.md. state/tracker.json remembers what was
already seen so dismissed inbox videos do not come back.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass, field

import requests

from . import ingest, scrape, youtube
from .catalog import ROOT, Catalog, iter_videos, read_yaml, write_yaml

CONFIG = ROOT / "tracker.yaml"
STATE = ROOT / "state" / "tracker.json"
INBOX = ROOT / "inbox"


@dataclass
class Report:
    new_trainings: list[tuple[str, str]] = field(default_factory=list)
    new_instructors: list[str] = field(default_factory=list)
    updated: dict[str, list[str]] = field(default_factory=dict)
    new_videos: list[dict] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not (self.new_trainings or self.updated or self.new_videos or self.errors)

    def markdown(self) -> str:
        today = dt.date.today().isoformat()
        out = [f"# Tracker report — {today}", ""]
        if self.empty:
            out.append("Nothing new.")
        if self.new_trainings:
            out += ["## New trainings (drafts to review)", ""]
            out += [f"- [{title}](../data/trainings/{id_}.yaml)" for id_, title in self.new_trainings]
            out.append("")
        if self.new_instructors:
            out += ["## New instructors (drafts to review)", ""]
            out += [f"- [{id_}](../data/instructors/{id_}.yaml)" for id_ in self.new_instructors]
            out.append("")
        if self.updated:
            out += ["## Updated trainings", ""]
            for id_, changes in self.updated.items():
                out.append(f"- **{id_}**")
                out += [f"  - {c}" for c in changes]
            out.append("")
        if self.new_videos:
            out += ["## Unassigned ARSET videos (see inbox/videos.yaml)", ""]
            out += [f"- {v['published']} [{v['title']}]({v['url']}) — {v['channel']}" for v in self.new_videos]
            out.append("")
        if self.errors:
            out += ["## Errors", ""] + [f"- {e}" for e in self.errors] + [""]
        return "\n".join(out)


def _load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"pages": {}, "videos_seen": []}


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _match_session(title: str, trainings: list[dict]) -> tuple[dict, dict] | None:
    """Match 'NASA ARSET: <session title>, Part N/M' to a training session with that title and part."""
    m = re.match(r"(?:nasa\s+)?arset:\s*(.+?),\s*part\s*(\d+)", title, re.I)
    if not m:
        return None
    wanted, part = _norm(m.group(1)), int(m.group(2))
    hits = [(t, s) for t in trainings for s in t.get("sessions") or []
            if s["part"] == part and _norm(s["title"]) == wanted]
    return hits[0] if len(hits) == 1 else None


def _needs_refresh(t: dict, horizon: dt.date) -> bool:
    if t.get("status") == "draft" or not t.get("end_date"):
        return True
    return dt.date.fromisoformat(t["end_date"]) >= horizon


def run(cat: Catalog, refresh_all: bool = False, dry_run: bool = False) -> Report:
    config = read_yaml(CONFIG)
    state = _load_state()
    report = Report()
    today = dt.date.today()
    horizon = today - dt.timedelta(days=config.get("refresh_days_after_end", 45))

    try:
        listed = scrape.discover(config["listing_pages"])
    except requests.RequestException as e:
        listed = []
        report.errors.append(f"listing pages: {e}")

    known = cat["training"]
    new_records: list[dict] = []
    to_check = [s for s in listed if s not in known and state["pages"].get(s, {}).get("arset", True)]
    to_check += [id_ for id_, t in known.items() if refresh_all or _needs_refresh(t, horizon)]

    for slug in dict.fromkeys(to_check):
        url = known[slug]["source_url"] if slug in known else scrape.training_url(slug)
        try:
            record, people, is_arset = ingest.scrape_training(cat, url)
        except requests.RequestException as e:
            report.errors.append(f"{slug}: {e}")
            continue
        state["pages"][slug] = {"arset": is_arset, "last_checked": today.isoformat()}
        if not is_arset:
            report.skipped.append(slug)
            continue
        if slug in known:
            changes = ingest.merge(known[slug], record)
            if changes:
                report.updated[slug] = changes
                if not dry_run:
                    cat.save("training", known[slug])
        else:
            ingest.enrich_videos(record)
            new_records.append(record)
            report.new_trainings.append((slug, record["title"]))
            if not dry_run:
                report.new_instructors += ingest.ensure_instructors(cat, people)
                cat.save("training", record)

    trainings = list(known.values()) + ([] if not dry_run else new_records)
    assigned = {v["youtube"] for t in trainings for _, v in iter_videos(t)}
    seen = set(state["videos_seen"])
    keywords = [k.lower() for k in config.get("youtube_title_keywords", [])]
    for channel, channel_id in config.get("youtube_channels", {}).items():
        try:
            feed = youtube.channel_feed(channel_id)
        except (requests.RequestException, ValueError) as e:
            report.errors.append(f"YouTube feed {channel}: {e}")
            continue
        for video in feed:
            vid = video["youtube"]
            if vid in assigned or vid in seen or not any(k in video["title"].lower() for k in keywords):
                continue
            seen.add(vid)
            match = _match_session(video["title"], trainings)
            if match:
                training, session = match
                entry = {"youtube": vid, "title": video["title"], "channel": channel}
                lang = youtube.guess_language(video["title"])
                if lang:
                    entry["language"] = lang
                session.setdefault("videos", []).append(entry)
                assigned.add(vid)
                report.updated.setdefault(training["id"], []).append(
                    f"Part {session['part']}: new video {vid} {video['title']} (matched from {channel} feed)")
                if not dry_run:
                    cat.save("training", training)
                continue
            report.new_videos.append({**video, "channel": channel, "url": youtube.watch_url(vid)})

    if not dry_run:
        state["videos_seen"] = sorted(seen)
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        inbox_file = INBOX / "videos.yaml"
        inbox = (read_yaml(inbox_file) or []) if inbox_file.exists() else []
        write_yaml(inbox_file, inbox + report.new_videos)
        INBOX.mkdir(exist_ok=True)
        (INBOX / "REPORT.md").write_text(report.markdown(), encoding="utf-8")
    return report
