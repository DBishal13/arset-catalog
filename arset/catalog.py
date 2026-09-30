"""Load, validate and write the YAML records under data/."""
from __future__ import annotations

import datetime as dt
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SCHEMAS = ROOT / "schemas"

# record kind -> folder under data/ (schemas are named <kind>.schema.json)
KINDS = {
    "training": "trainings",
    "instructor": "instructors",
    "satellite": "satellites",
    "dataset": "datasets",
    "application": "applications",
    "tool": "tools",
}

# training field -> kind of record it points at
TRAINING_REFS = {
    "instructors": "instructor",
    "satellites": "satellite",
    "datasets": "dataset",
    "applications": "application",
    "tools": "tool",
}


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _plain(obj):
    """YAML parses 2026-09-24 as a date; keep records JSON-friendly."""
    if isinstance(obj, (dt.date, dt.datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_plain(v) for v in obj]
    return obj


def read_yaml(path: Path):
    with open(path, encoding="utf-8") as f:
        return _plain(yaml.safe_load(f))


def write_yaml(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, width=100)


def record_path(kind: str, id_: str) -> Path:
    return DATA / KINDS[kind] / f"{id_}.yaml"


@dataclass
class Catalog:
    records: dict[str, dict[str, dict]]  # kind -> id -> record

    def __getitem__(self, kind: str) -> dict[str, dict]:
        return self.records[kind]

    def save(self, kind: str, record: dict) -> Path:
        path = record_path(kind, record["id"])
        write_yaml(path, record)
        self.records[kind][record["id"]] = record
        return path


def load() -> Catalog:
    records: dict[str, dict[str, dict]] = {kind: {} for kind in KINDS}
    for kind, folder in KINDS.items():
        for path in sorted((DATA / folder).glob("*.yaml")):
            records[kind][path.stem] = read_yaml(path) or {}
    return Catalog(records)


def iter_videos(training: dict):
    """Yield (session or None, video) for every video in a training."""
    for session in training.get("sessions") or []:
        for video in session.get("videos") or []:
            yield session, video
    for video in training.get("videos") or []:
        yield None, video


def iter_materials(training: dict):
    for session in training.get("sessions") or []:
        for material in session.get("materials") or []:
            yield session, material
    for material in training.get("materials") or []:
        yield None, material


def validate(cat: Catalog) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for kind, folder in KINDS.items():
        schema = json.loads((SCHEMAS / f"{kind}.schema.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for id_, rec in cat[kind].items():
            where = f"{folder}/{id_}.yaml"
            if not isinstance(rec, dict):
                errors.append(f"{where}: not a mapping")
                continue
            if rec.get("id") != id_:
                errors.append(f"{where}: id {rec.get('id')!r} must match the file name")
            for err in validator.iter_errors(rec):
                loc = "/".join(map(str, err.absolute_path)) or "(root)"
                errors.append(f"{where}: {loc}: {err.message}")

    video_owner: dict[str, str] = {}
    for id_, t in cat["training"].items():
        where = f"trainings/{id_}.yaml"
        for field, kind in TRAINING_REFS.items():
            for ref in t.get(field) or []:
                if ref not in cat[kind]:
                    errors.append(f"{where}: {field}: unknown {kind} {ref!r}")
        for pre in t.get("prerequisites") or []:
            if pre not in cat["training"]:
                warnings.append(f"{where}: prerequisite {pre!r} is not in the catalog yet")
        if t.get("start_date") and t.get("end_date") and t["end_date"] < t["start_date"]:
            errors.append(f"{where}: end_date is before start_date")
        for _, video in iter_videos(t):
            owner = video_owner.setdefault(video.get("youtube"), id_)
            if owner != id_:
                warnings.append(f"{where}: video {video['youtube']} also appears in {owner}")

    for id_, d in cat["dataset"].items():
        for ref in d.get("satellites") or []:
            if ref not in cat["satellite"]:
                errors.append(f"datasets/{id_}.yaml: satellites: unknown satellite {ref!r}")
    for id_, a in cat["application"].items():
        if a.get("parent") and a["parent"] not in cat["application"]:
            errors.append(f"applications/{id_}.yaml: unknown parent {a['parent']!r}")

    return errors, warnings
