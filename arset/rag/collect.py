"""Download each PDF material, extract its text page by page, keep only the text.

Output: corpus/text/<material id>.json with the material's catalog context
(training, part, type, title, url) and a list of page texts. PDFs are only
held in memory, never written to disk, so the corpus stays small (tens of MB
instead of several GB). Re-runs skip materials already extracted; failures
are listed in corpus/collect_errors.json.
"""
from __future__ import annotations

import hashlib
import json
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import fitz  # PyMuPDF: keeps word spacing where pypdf glues words together on some ARSET PDFs
import requests

from .. import scrape
from ..catalog import Catalog
from . import CORPUS, TEXT_DIR

WORKERS = 3
PAUSE = 0.3  # seconds between downloads, per worker
fitz.TOOLS.mupdf_display_errors(False)  # malformed-PDF warnings are noise here


def material_id(url: str) -> str:
    """Stable id from the URL without its query (?VersionId=... changes between uploads)."""
    p = urlparse(url)
    return hashlib.sha1(f"{p.netloc.removeprefix('www.')}{p.path}".encode()).hexdigest()[:16]


def pdf_materials(cat: Catalog) -> list[dict]:
    """Every PDF material in the catalog with its context, deduplicated by URL."""
    out: dict[str, dict] = {}
    for t in cat["training"].values():
        sessions = [(s, s.get("materials") or []) for s in t.get("sessions") or []]
        sessions.append((None, t.get("materials") or []))
        for s, materials in sessions:
            for m in materials:
                if not urlparse(m["url"]).path.lower().endswith(".pdf"):
                    continue
                mid = material_id(m["url"])
                out.setdefault(mid, {
                    "id": mid, "training_id": t["id"], "training_title": t["title"],
                    "start_date": t.get("start_date"), "level": t.get("level"),
                    "part": s["part"] if s else None, "session_title": s["title"] if s else None,
                    "type": m["type"], "title": m.get("title"), "language": m.get("language", "en"),
                    "url": m["url"],
                })
    return list(out.values())


def extract(pdf_bytes: bytes) -> list[str]:
    """Page texts, with ligatures ("ﬁ") and odd Unicode forms normalized."""
    pages = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            try:
                pages.append(unicodedata.normalize("NFKC", page.get_text()))
            except Exception:  # one broken page should not lose the whole document
                pages.append("")
    return pages


def _fetch(material: dict, session: requests.Session) -> dict:
    resp = session.get(material["url"], timeout=120)
    resp.raise_for_status()
    pages = extract(resp.content)
    record = material | {"pages": pages, "bytes": len(resp.content)}
    (TEXT_DIR / f"{material['id']}.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    time.sleep(PAUSE)
    return record


def collect(cat: Catalog, limit: int | None = None) -> None:
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    materials = pdf_materials(cat)
    missing = [m for m in materials if not (TEXT_DIR / f"{m['id']}.json").exists()]
    todo = missing[:limit]
    print(f"{len(materials)} PDF materials, {len(materials) - len(missing)} already extracted, "
          f"{len(todo)} to fetch", flush=True)
    session = requests.Session()
    session.headers["User-Agent"] = scrape.USER_AGENT
    errors, done, empty = {}, 0, 0
    with ThreadPoolExecutor(WORKERS) as pool:
        futures = {pool.submit(_fetch, m, session): m for m in todo}
        for future in as_completed(futures):
            m = futures[future]
            try:
                record = future.result()
                done += 1
                if not any(p.strip() for p in record["pages"]):
                    empty += 1  # scanned/image-only PDF
            except Exception as e:  # network, HTTP or PDF parsing errors
                errors[m["url"]] = f"{e.__class__.__name__}: {e}"
            if (done + len(errors)) % 50 == 0:
                print(f"  {done + len(errors)}/{len(todo)}", flush=True)
    (CORPUS / "collect_errors.json").write_text(json.dumps(errors, indent=1), encoding="utf-8")
    print(f"extracted {done} ({empty} had no extractable text), {len(errors)} failed "
          f"(see corpus/collect_errors.json)", flush=True)
