"""Compile data/ into build/catalog.json, build/arset.sqlite and the static site in build/site/."""
from __future__ import annotations

import datetime as dt
import json
import shutil
import sqlite3
from pathlib import Path

from .catalog import KINDS, ROOT, TRAINING_REFS, Catalog, iter_materials, iter_videos, read_yaml

BUILD = ROOT / "build"
SITE_SRC = ROOT / "site"
INBOX_VIDEOS = ROOT / "inbox" / "videos.yaml"


def training_state(t: dict, today: dt.date) -> str:
    start, end = t.get("start_date"), t.get("end_date") or t.get("start_date")
    if not start:
        return "self-paced" if t.get("format") == "online-self-paced" else "unscheduled"
    if dt.date.fromisoformat(start) > today:
        return "upcoming"
    if dt.date.fromisoformat(end) >= today:
        return "in-progress"
    return "past"


def to_json(cat: Catalog, today: dt.date) -> dict:
    backrefs: dict[str, dict[str, list[str]]] = {kind: {} for kind in KINDS}
    for tid, t in sorted(cat["training"].items()):
        for field, kind in TRAINING_REFS.items():
            for ref in t.get(field) or []:
                backrefs[kind].setdefault(ref, []).append(tid)

    out: dict = {"generated": today.isoformat()}
    for kind, folder in KINDS.items():
        rows = []
        for id_, rec in sorted(cat[kind].items()):
            row = dict(rec)
            if kind == "training":
                row["state"] = training_state(rec, today)
                row["video_count"] = sum(1 for _ in iter_videos(rec))
            else:
                row["trainings"] = backrefs[kind].get(id_, [])
            rows.append(row)
        out[folder] = rows
    out["counts"] = {folder: len(out[folder]) for folder in KINDS.values()}
    out["inbox_videos"] = (read_yaml(INBOX_VIDEOS) or []) if INBOX_VIDEOS.exists() else []
    return out


def to_site(catalog_json: str, dest: Path) -> None:
    """Copy site/ and embed the catalog as data.js so index.html also works from file://."""
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(SITE_SRC, dest)
    (dest / "data.js").write_text(f"window.CATALOG = {catalog_json};\n", encoding="utf-8")


SCHEMA_SQL = """
CREATE TABLE trainings (
  id TEXT PRIMARY KEY, title TEXT NOT NULL, status TEXT, state TEXT, level TEXT, format TEXT,
  start_date TEXT, end_date TEXT, summary TEXT, description TEXT, source_url TEXT,
  languages TEXT, data TEXT NOT NULL
);
CREATE TABLE sessions (
  training_id TEXT REFERENCES trainings(id), part INTEGER, title TEXT, date TEXT,
  PRIMARY KEY (training_id, part)
);
CREATE TABLE videos (
  youtube_id TEXT, training_id TEXT REFERENCES trainings(id), part INTEGER,
  title TEXT, language TEXT, channel TEXT, url TEXT
);
CREATE TABLE materials (
  training_id TEXT REFERENCES trainings(id), part INTEGER, type TEXT,
  title TEXT, url TEXT, language TEXT
);
"""


def to_sqlite(cat: Catalog, path: Path, today: dt.date) -> None:
    path.unlink(missing_ok=True)
    db = sqlite3.connect(path)
    db.executescript(SCHEMA_SQL)
    for kind, folder in KINDS.items():
        if kind != "training":
            db.execute(f"CREATE TABLE {folder} (id TEXT PRIMARY KEY, name TEXT, data TEXT NOT NULL)")
            db.executemany(
                f"INSERT INTO {folder} VALUES (?, ?, ?)",
                [(id_, r.get("name"), json.dumps(r)) for id_, r in cat[kind].items()],
            )
    for field, kind in TRAINING_REFS.items():
        db.execute(
            f"CREATE TABLE training_{field} (training_id TEXT REFERENCES trainings(id), "
            f"{kind}_id TEXT REFERENCES {KINDS[kind]}(id), PRIMARY KEY (training_id, {kind}_id))"
        )

    for tid, t in cat["training"].items():
        db.execute(
            "INSERT INTO trainings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tid, t["title"], t.get("status"), training_state(t, today), t.get("level"), t.get("format"),
             t.get("start_date"), t.get("end_date"), t.get("summary"), t.get("description"),
             t.get("source_url"), json.dumps(t.get("languages", [])), json.dumps(t)),
        )
        for s in t.get("sessions") or []:
            db.execute("INSERT INTO sessions VALUES (?,?,?,?)", (tid, s["part"], s["title"], s.get("date")))
        for s, v in iter_videos(t):
            db.execute(
                "INSERT INTO videos VALUES (?,?,?,?,?,?,?)",
                (v["youtube"], tid, s and s["part"], v.get("title"), v.get("language"), v.get("channel"),
                 f"https://www.youtube.com/watch?v={v['youtube']}"),
            )
        for s, m in iter_materials(t):
            db.execute(
                "INSERT INTO materials VALUES (?,?,?,?,?,?)",
                (tid, s and s["part"], m["type"], m.get("title"), m["url"], m.get("language")),
            )
        for field in TRAINING_REFS:
            db.executemany(f"INSERT INTO training_{field} VALUES (?, ?)", [(tid, r) for r in t.get(field) or []])

    try:  # full-text search, if this SQLite build has FTS5
        db.execute("CREATE VIRTUAL TABLE trainings_fts USING fts5(id UNINDEXED, title, summary, description)")
        db.execute("INSERT INTO trainings_fts SELECT id, title, summary, description FROM trainings")
    except sqlite3.OperationalError:
        pass
    db.commit()
    db.close()


def build(cat: Catalog) -> list[Path]:
    today = dt.date.today()
    BUILD.mkdir(exist_ok=True)
    json_path, db_path = BUILD / "catalog.json", BUILD / "arset.sqlite"
    data = to_json(cat, today)
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    to_sqlite(cat, db_path, today)
    # "</" is escaped so text in the data can never close the <script> element
    to_site(json.dumps(data, ensure_ascii=False).replace("</", "<\\/"), BUILD / "site")
    return [json_path, db_path, BUILD / "site" / "index.html"]
