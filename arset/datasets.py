"""Where to get each dataset: links from NASA's Common Metadata Repository (CMR).

`python -m arset datasets` looks up every dataset's cmr_short_names (latest
version of each collection) and writes state/dataset_access.json, which the
build merges into the site and the chatbot reads. CMR is public; downloading
the files themselves needs a free Earthdata Login, which the site links to.
"""
from __future__ import annotations

import json

import requests

from .catalog import ROOT, Catalog

CMR = "https://cmr.earthdata.nasa.gov/search/collections.umm_json"
ACCESS_FILE = ROOT / "state" / "dataset_access.json"
EARTHDATA_SIGNUP = "https://urs.earthdata.nasa.gov/users/new"

# CMR RelatedUrls (Type, Subtype) -> our link name; first match wins.
LINK_RULES = [
    ("earthdata_search", "GET DATA", {"EARTHDATA SEARCH"}),
    ("browse_files", "GET DATA", {"DIRECT DOWNLOAD", "DATA TREE"}),
    ("appeears", "GET DATA", {"APPEEARS"}),
    ("access_tool", "GET DATA", {"DATA ACCESS TOOL", "SUBSETTER", "DATA COLLECTION BUNDLE", "ORDER"}),
    ("giovanni", "GET RELATED VISUALIZATION", {"GIOVANNI"}),
    ("worldview", "GET RELATED VISUALIZATION", {"WORLDVIEW"}),
    ("landing_page", "DATA SET LANDING PAGE", {""}),
    ("user_guide", "VIEW RELATED INFORMATION", {"USER'S GUIDE", "READ-ME"}),
    ("atbd", "VIEW RELATED INFORMATION", {"ALGORITHM THEORETICAL BASIS DOCUMENT (ATBD)"}),
]


def _latest(short_name: str) -> dict | None:
    items = requests.get(CMR, params={"short_name": short_name, "page_size": 20}, timeout=60).json().get("items", [])
    return max(items, key=lambda i: (i["umm"].get("Version") or ""), default=None)


def collection_access(short_name: str) -> dict | None:
    item = _latest(short_name)
    if item is None:
        return None
    umm, concept = item["umm"], item["meta"]["concept-id"]
    links: dict[str, str] = {}
    for related in umm.get("RelatedUrls") or []:
        kind, sub, url = related.get("Type", ""), (related.get("Subtype") or "").upper(), related.get("URL", "")
        for name, rule_type, subtypes in LINK_RULES:
            if name not in links and kind == rule_type and sub in subtypes:
                if name == "worldview" and "/images/" in url:
                    continue  # a preview image, not the interactive viewer
                links[name] = url
                break
    links.setdefault("earthdata_search", f"https://search.earthdata.nasa.gov/search/granules?p={concept}")
    doi = (umm.get("DOI") or {}).get("DOI")
    return {
        "short_name": short_name, "version": umm.get("Version"), "title": umm.get("EntryTitle"),
        "concept_id": concept, "doi": doi, "links": links,
    }


def refresh(cat: Catalog) -> dict:
    out = {}
    for id_, d in sorted(cat["dataset"].items()):
        collections = []
        for short_name in d.get("cmr_short_names") or []:
            try:
                info = collection_access(short_name)
            except requests.RequestException as e:
                print(f"  {id_}: {short_name}: {e}")
                continue
            if info:
                collections.append(info)
            else:
                print(f"  {id_}: {short_name} not found in CMR")
        if collections:
            out[id_] = collections
            print(f"{id_}: {', '.join(c['short_name'] + ' v' + str(c['version']) for c in collections)}")
    ACCESS_FILE.parent.mkdir(exist_ok=True)
    ACCESS_FILE.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return out


def load_access() -> dict:
    return json.loads(ACCESS_FILE.read_text(encoding="utf-8")) if ACCESS_FILE.exists() else {}
