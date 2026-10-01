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


OLD_FIXTURE = Path(__file__).parent / "fixtures" / "training_geostationary_aq_2022.html"
OLD_URL = "https://www.earthdata.nasa.gov/learn/trainings/accessing-analyzing-air-quality-data-from-geostationary-satellites"


def test_older_page_layout():
    """Pre-2024 pages list materials and instructors under h4 headings inside each part."""
    r = scrape.parse_training(OLD_FIXTURE.read_text(encoding="utf-8"), OLD_URL)
    parts = r["sessions"]
    assert [s["part"] for s in parts] == [1, 2, 3]
    assert parts[0]["date"] == "2022-10-11"
    assert [(m["type"], m["title"]) for m in parts[0]["materials"]] == [
        ("slides", "Part 1 Presentation Slides"),
        ("transcript", "Part 1 Q&A Transcript"),
        ("slides", "Part 1 Presentation Slides (TEMPO)"),
    ]
    assert any(m["title"] == "GEMS Data" for m in parts[2]["materials"])
    assert all("Pawan Gupta" not in a for s in parts for a in s.get("agenda", []))
    people = {p["name"]: p for p in r["_instructors"]}
    assert {"Pawan Gupta", "Melanie Follette-Cook", "Sarah Strode", "Aaron Naeger", "Jhoon Kim"} <= set(people)
    assert people["Aaron Naeger"]["title"] == "Guest Instructor"
    assert people["Sujung Go"]["affiliation"] == "UMBC/NASA GSFC"


@pytest.mark.parametrize("text, names", [
    ("Pawan Gupta, Melanie Follette-Cook, and Sarah Strode", ["Pawan Gupta", "Melanie Follette-Cook", "Sarah Strode"]),
    ("Sujung Go (UMBC/NASA GSFC), and Jhoon Kim", ["Sujung Go", "Jhoon Kim"]),
    ("Amita Mehta and Sean McCartney", ["Amita Mehta", "Sean McCartney"]),
    ("Materials will be posted after the session.", []),
])
def test_people_from_text(text, names):
    assert [p["name"] for p in scrape.people_from_text(text, "ARSET Instructor")] == names


def test_instructors(record):
    names = [p["name"] for p in record["_instructors"]]
    assert names == ["Erika Podest", "Nick Parazoo", "Jackie Ryan"]
    assert record["_instructors"][0]["title"] == "ARSET Instructor"
