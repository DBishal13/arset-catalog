"""Hybrid search index over the chunks: Chroma (meaning) + SQLite FTS5 (exact terms).

Meaning-based search finds "soil water content" for "soil moisture"; keyword
search finds exact product names ("SPL3SMP", "MOD13Q1") that embeddings blur.
Results from both are merged with reciprocal rank fusion. Everything lives in
corpus/: chroma/ and chunks.sqlite.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

from ..catalog import Catalog
from . import CORPUS
from .chunk import all_chunks, as_dict

CHROMA_DIR = CORPUS / "chroma"
DB = CORPUS / "chunks.sqlite"
COLLECTION = "arset_chunks"
FIELDS = ["id", "kind", "text", "training_id", "training_title", "start_date", "level", "part",
          "material_type", "material_title", "url", "page"]
RRF_K = 60


@dataclass
class Hit:
    chunk: dict
    score: float
    via: str  # "meaning", "keyword" or "both"


def _collection(create: bool = False):
    import chromadb  # imported lazily: only the rag commands need it
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    if create:
        if COLLECTION in [c.name for c in client.list_collections()]:
            client.delete_collection(COLLECTION)
        return client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    return client.get_collection(COLLECTION)


def _meta(c: dict) -> dict:
    """Chroma metadata must be str/int/float/bool; drop empty values, add a year to filter on."""
    m = {k: v for k, v in c.items() if k not in ("id", "text") and v is not None}
    if c.get("start_date"):
        m["year"] = int(c["start_date"][:4])
    return m


def build(cat: Catalog, batch: int = 256) -> int:
    chunks = [as_dict(c) for c in all_chunks(cat)]
    CORPUS.mkdir(exist_ok=True)

    DB.unlink(missing_ok=True)
    db = sqlite3.connect(DB)
    db.execute(f"CREATE TABLE chunks ({', '.join(FIELDS)}, PRIMARY KEY (id))")
    db.executemany(f"INSERT INTO chunks VALUES ({', '.join('?' * len(FIELDS))})",
                   [tuple(c[f] for f in FIELDS) for c in chunks])
    db.execute("CREATE VIRTUAL TABLE chunks_fts USING fts5(id UNINDEXED, text, tokenize='porter unicode61')")
    db.execute("INSERT INTO chunks_fts SELECT id, text FROM chunks")
    db.commit()
    db.close()

    col = _collection(create=True)
    for i in range(0, len(chunks), batch):
        part = chunks[i:i + batch]
        col.add(ids=[c["id"] for c in part], documents=[c["text"] for c in part], metadatas=[_meta(c) for c in part])
        if (i // batch) % 20 == 0:
            print(f"  embedded {min(i + batch, len(chunks))}/{len(chunks)}", flush=True)
    return len(chunks)


def _where(filters: dict) -> dict | None:
    clauses = []
    for key in ("kind", "material_type", "training_id", "level"):
        if filters.get(key):
            clauses.append({key: filters[key]})
    if filters.get("since_year"):
        clauses.append({"year": {"$gte": int(filters["since_year"])}})
    return None if not clauses else clauses[0] if len(clauses) == 1 else {"$and": clauses}


def _fts_query(query: str) -> str | None:
    terms = [t for t in re.findall(r"[\w.-]+", query.lower()) if len(t) > 1]
    return " OR ".join(f'"{t}"' for t in terms) or None


def _sql_filters(filters: dict) -> tuple[str, list]:
    sql, args = [], []
    for key in ("kind", "material_type", "training_id", "level"):
        if filters.get(key):
            sql.append(f"c.{key} = ?")
            args.append(filters[key])
    if filters.get("since_year"):
        sql.append("substr(c.start_date, 1, 4) >= ?")
        args.append(str(filters["since_year"]))
    return ("AND " + " AND ".join(sql)) if sql else "", args


def search(query: str, k: int = 8, per_training: int = 2, **filters) -> list[Hit]:
    """Top-k chunks for a query, merged from meaning-based and keyword search."""
    pool = k * 6
    ranks: dict[str, dict[str, int]] = {}

    res = _collection().query(query_texts=[query], n_results=pool, where=_where(filters))
    for rank, cid in enumerate(res["ids"][0]):
        ranks.setdefault(cid, {})["meaning"] = rank

    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    fts = _fts_query(query)
    if fts:
        where, args = _sql_filters(filters)
        rows = db.execute(
            f"SELECT f.id FROM chunks_fts f JOIN chunks c ON c.id = f.id "
            f"WHERE chunks_fts MATCH ? {where} ORDER BY bm25(chunks_fts) LIMIT ?", [fts, *args, pool]).fetchall()
        for rank, row in enumerate(rows):
            ranks.setdefault(row["id"], {})["keyword"] = rank

    scored = sorted(((sum(1 / (RRF_K + r) for r in rk.values()), cid, rk) for cid, rk in ranks.items()), reverse=True)
    hits, per = [], {}
    for score, cid, rk in scored:
        row = db.execute("SELECT * FROM chunks WHERE id = ?", [cid]).fetchone()
        if row is None:
            continue
        chunk = dict(row)
        if per.get(chunk["training_id"], 0) >= per_training:
            continue  # keep results diverse across trainings
        per[chunk["training_id"]] = per.get(chunk["training_id"], 0) + 1
        hits.append(Hit(chunk, score, "both" if len(rk) == 2 else next(iter(rk))))
        if len(hits) == k:
            break
    db.close()
    return hits
