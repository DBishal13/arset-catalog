import datetime as dt
from pathlib import Path

import pytest

from arset import scrape

FIXTURE = Path(__file__).parent / "fixtures" / "training_flash_drought.html"
URL = "https://www.earthdata.nasa.gov/learn/trainings/agricultural-flash-drought-detection-using-solar-induced-fluorescence-sif-soil"


@pytest.mark.parametrize("text, expected", [
    ("Sept. 24-29, 2026", [(2026, 9, 24), (2026, 9, 29)]),
    ("Sep. 30 - Oct. 7, 2026", [(2026, 9, 30), (2026, 10, 7)]),
    ("Dec. 30 - Jan. 2, 2026", [(2025, 12, 30), (2026, 1, 2)]),
    ("October 20, 2026", [(2026, 10, 20)]),
    ("Part 1 Marine 5", []),
    ("Sept. 24", []),  # no year anywhere: not a date we can trust
])
def test_parse_dates(text, expected):
    assert scrape.parse_dates(text) == [dt.date(*d) for d in expected]


@pytest.mark.parametrize("href, slug", [
    ("/learn/trainings/fundamentals-remote-sensing", "fundamentals-remote-sensing"),
    ("https://www.earthdata.nasa.gov/learn/trainings/fundamentals-remote-sensing/", "fundamentals-remote-sensing"),
    ("/es/learn/trainings/fundamentos-de-la-teledeteccion", None),
    ("https://example.com/learn/trainings/x", None),
    ("/learn/trainings", None),
])
def test_training_slug(href, slug):
    assert scrape.training_slug(href) == slug


@pytest.fixture(scope="module")
def record():
    return scrape.parse_training(FIXTURE.read_text(encoding="utf-8"), URL)


def test_metadata(record):
    assert record["_is_arset"]
    assert record["id"] == "agricultural-flash-drought-detection-using-solar-induced-fluorescence-sif-soil"
    assert record["title"].startswith("Agricultural Flash Drought Detection")
    assert record["level"] == "intermediate"
    assert record["format"] == "online-instructor-led"
    assert (record["start_date"], record["end_date"]) == ("2026-09-24", "2026-09-29")
    assert "(OCO-2)" in record["description"]
    assert len(record["objectives"]) == 6
    assert "fundamentals-remote-sensing" in record["prerequisites"]


def test_sessions(record):
    part1, part2 = record["sessions"]
    assert (part1["part"], part1["date"]) == (1, "2026-09-24")
    assert part1["title"] == "Introduction to Flash Drought Monitoring using SIF and Soil Moisture"
    assert [v["youtube"] for v in part1["videos"]] == ["ZMQZBUs6n0g", "FQZgIbWOoiE"]
    assert part1["materials"][0]["type"] == "slides"
    assert part1["materials"][0]["url"].endswith("arset-2026-sif-part1.pdf")
    assert {m["type"] for m in part2["materials"]} == {"slides", "homework"}
    assert "Q&A Session" in part2["agenda"]


def test_instructors(record):
    names = [p["name"] for p in record["_instructors"]]
    assert names == ["Erika Podest", "Nick Parazoo", "Jackie Ryan"]
    assert record["_instructors"][0]["title"] == "ARSET Instructor"
