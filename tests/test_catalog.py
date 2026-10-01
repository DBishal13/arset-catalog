import copy

from arset import catalog, ingest, tagging
from arset.track import _match_session


def test_repository_catalog_is_valid():
    errors, _ = catalog.validate(catalog.load())
    assert errors == []


def test_unknown_reference_is_an_error():
    cat = catalog.load()
    cat["training"]["t"] = {"id": "t", "title": "Test training", "status": "draft",
                            "source_url": "https://example.com/t", "satellites": ["no-such-satellite"]}
    errors, _ = catalog.validate(cat)
    assert any("unknown satellite 'no-such-satellite'" in e for e in errors)


def test_tagging_uses_aliases_and_instruments():
    cat = catalog.load()
    hits = tagging.suggest(cat, {"title": "Mapping floods with Sentinel-1 and MODIS in QGIS"})
    assert {"sentinel-1", "terra", "aqua"} <= set(hits["satellites"])
    assert hits["tools"] == ["qgis"]
    assert "disasters" in hits["applications"]
    # capitalised aliases are case-sensitive: "sar" in a word must not match anything
    assert tagging.suggest(cat, "the tsar of gee whiz") == {}


def test_application_tags_need_weight():
    cat = catalog.load()
    # one passing mention deep in the text is not enough for an application area...
    assert "applications" not in tagging.suggest(cat, {"body": "The forest is nice."})
    # ...but the title is, and at most three areas are kept
    many = {"title": "Floods, crops, wildfires, air quality and forests", "summary": "", "body": ""}
    assert len(tagging.suggest(cat, many)["applications"]) == 3


def test_site_data_omits_copied_text():
    from arset.build import SITE_OMIT, site_data
    data = {"trainings": [{"id": "t", "title": "T", "summary": "s", "description": "d", "objectives": ["o"], "audience": ["a"]}]}
    out = site_data(data)
    assert not any(k in out["trainings"][0] for k in SITE_OMIT)
    assert out["trainings"][0]["summary"] == "s"
    assert data["trainings"][0]["description"] == "d"  # the local catalog keeps it


def test_match_session_by_title_and_part():
    trainings = [{"id": "x", "sessions": [{"part": 2, "title": "Flash Drought Detection and Prediction"}]}]
    assert _match_session("NASA ARSET: Flash Drought Detection and Prediction, Part 2/2", trainings)
    assert _match_session("NASA ARSET: Flash Drought Detection and Prediction, Part 1/2", trainings) is None
    assert _match_session("Some other video", trainings) is None


BASE = {
    "id": "t", "title": "T", "status": "reviewed", "source_url": "https://example.com/t",
    "sessions": [{"part": 1, "title": "One", "videos": [{"youtube": "AAAAAAAAAAA", "title": "a"}]}],
}


def test_merge_adds_new_items_without_touching_reviewed_fields(monkeypatch):
    monkeypatch.setattr(ingest.youtube, "enrich", lambda v: v)
    existing = copy.deepcopy(BASE)
    scraped = {
        "id": "t", "title": "Changed title", "satellites": ["smap"],
        "sessions": [
            {"part": 1, "title": "One", "videos": [{"youtube": "AAAAAAAAAAA"}, {"youtube": "BBBBBBBBBBB"}],
             "materials": [{"type": "slides", "url": "https://example.com/1.pdf"}]},
            {"part": 2, "title": "Two", "date": "2026-10-01"},
        ],
    }
    changes = ingest.merge(existing, scraped)
    assert existing["title"] == "T"
    assert "satellites" not in existing  # reviewed: removed tags stay removed
    assert [v["youtube"] for v in existing["sessions"][0]["videos"]] == ["AAAAAAAAAAA", "BBBBBBBBBBB"]
    assert existing["sessions"][0]["materials"][0]["type"] == "slides"
    assert existing["sessions"][1] == {"part": 2, "title": "Two", "date": "2026-10-01"}
    assert len(changes) == 3
    assert ingest.merge(existing, scraped) == []  # idempotent


def test_merge_fills_missing_fields_on_drafts(monkeypatch):
    monkeypatch.setattr(ingest.youtube, "enrich", lambda v: v)
    existing = copy.deepcopy(BASE) | {"status": "draft"}
    ingest.merge(existing, {"id": "t", "title": "x", "satellites": ["smap"], "level": "advanced"})
    assert existing["satellites"] == ["smap"] and existing["level"] == "advanced"
    assert list(existing)[:4] == ["id", "title", "status", "source_url"]
