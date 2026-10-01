"""Turn Earthdata ARSET training pages into training records."""
from __future__ import annotations

import datetime as dt
import re
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag
from requests.utils import requote_uri

from .catalog import slugify

BASE = "https://www.earthdata.nasa.gov"
USER_AGENT = "Mozilla/5.0 (compatible; arset-catalog/0.1)"

TRAINING_PATH = re.compile(r"^/learn/trainings/([a-z0-9-]+)/?$")  # English pages only
YOUTUBE_ID = re.compile(
    r"(?:youtu\.be/|youtube(?:-nocookie)?\.com/(?:watch\?(?:[^\"'\s]*&)?v=|embed/|live/|shorts/|v/))"
    r"([A-Za-z0-9_-]{11})"
)
MONTHS = {
    name: i
    for i, names in enumerate(
        [("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"),
         ("may",), ("jun", "june"), ("jul", "july"), ("aug", "august"),
         ("sep", "sept", "september"), ("oct", "october"), ("nov", "november"), ("dec", "december")],
        start=1,
    )
    for name in names
}
DATE_TOKEN = re.compile(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:\s*[-–]\s*(\d{1,2})(?!\d))?(?:,\s*(\d{4}))?")
LANGUAGE_WORDS = {
    "english": "en", "spanish": "es", "español": "es", "espanol": "es",
    "french": "fr", "français": "fr", "francais": "fr",
    "portuguese": "pt", "português": "pt", "arabic": "ar",
}
LEVELS = {"fundamentals", "introductory", "intermediate", "advanced"}
FORMATS = {
    "online-instructor-led": "online-instructor-led",
    "online-self-paced": "online-self-paced",
    "in-person-training": "in-person",
    "in-person": "in-person",
}


def fetch(url: str) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    return resp.text


def training_slug(href: str) -> str | None:
    url = urlparse(urljoin(BASE, href))
    if url.netloc and not url.netloc.endswith("earthdata.nasa.gov"):
        return None
    m = TRAINING_PATH.match(url.path)
    return m.group(1) if m else None


def training_url(slug: str) -> str:
    return f"{BASE}/learn/trainings/{slug}"


def discover(listing_urls: list[str]) -> list[str]:
    """Slugs of every training linked from the listing pages, in page order."""
    slugs: list[str] = []
    for url in listing_urls:
        soup = BeautifulSoup(fetch(url), "html.parser")
        for a in soup.find_all("a", href=True):
            slug = training_slug(a["href"])
            if slug and slug not in slugs:
                slugs.append(slug)
    return slugs


def parse_dates(text: str) -> list[dt.date]:
    """'Sept. 24-29, 2026' -> [2026-09-24, 2026-09-29]; 'Sep. 30 - Oct. 7, 2026' works too."""
    raw = []  # [month, day, year|None]
    for month, day, day2, year in DATE_TOKEN.findall(text):
        m = MONTHS.get(month.lower())
        if not m:
            continue
        raw.append([m, int(day), int(year) if year else None])
        if day2:
            raw.append([m, int(day2), int(year) if year else None])
    # A year written once at the end applies to the dates before it.
    year = None
    for item in reversed(raw):
        if item[2] is None:
            item[2] = year
        year = item[2]
    dates = []
    for i, (m, d, y) in enumerate(raw):
        if y is None:
            continue
        # "Dec. 30 - Jan. 2, 2026": the December date belongs to the year before.
        if i + 1 < len(raw) and raw[i + 1][2] == y and m > raw[i + 1][0]:
            y -= 1
        try:
            dates.append(dt.date(y, m, d))
        except ValueError:
            pass
    return dates


def _text(el: Tag | None) -> str:
    if not el:
        return ""
    text = " ".join(el.get_text(" ", strip=True).split())
    # get_text(" ") puts spaces around inline links: "( OCO-2 )" -> "(OCO-2)"
    return re.sub(r"\s+([),.;:!?])", r"\1", re.sub(r"\(\s+", "(", text))


def _field(soup: BeautifulSoup, name: str) -> Tag | None:
    return soup.select_one(f".field--name-{name}")


def _one_date(text: str) -> str | None:
    dates = parse_dates(text)
    return dates[0].isoformat() if dates else None


def _language_of(text: str) -> str | None:
    low = text.lower()
    for word, code in LANGUAGE_WORDS.items():
        if code != "en" and re.search(rf"\b{word}\b", low):
            return code
    return None


def _classify(text: str, href: str) -> str:
    low = f"{text} {href}".lower()
    if "homework" in low:
        return "homework"
    if "slide" in low or "presentation" in low:
        return "slides"
    if ".ipynb" in low or "notebook" in low or "colab" in low or "github.com" in low:
        return "notebook"
    if "exercise" in low:
        return "exercise"
    if "transcript" in low:
        return "transcript"
    if "q&a" in low or "question" in low or re.search(r"[-_]qa\.", low):
        return "qa"
    if re.search(r"\.(zip|csv|tif|tiff|nc|h5|kml|kmz|shp)(\?|$)", href.lower()):
        return "data"
    return "other"


def _youtube_ids(el: Tag) -> list[str]:
    found = []
    for value in el.attrs.values():
        for v in value if isinstance(value, list) else [value]:
            if isinstance(v, str):
                found += YOUTUBE_ID.findall(unquote(v))
    return found


PERSON = re.compile(r"^[A-Z][\w'.\-]*(?:\s+[A-Za-z][\w'.\-]*){1,4}$")


def people_from_text(text: str, title: str) -> list[dict]:
    """'Pawan Gupta, Melanie Follette-Cook, and Sarah Strode' / 'Sujung Go (UMBC/NASA GSFC)' -> people."""
    people = []
    for part in re.split(r",\s*(?:and\s+)?(?![^()]*\))|\s+and\s+(?![^()]*\))|;", text):
        part = part.strip().strip(".")
        m = re.match(r"^(.*?)\s*\(([^)]*)\)$", part)
        name, affiliation = (m.group(1).strip(), m.group(2).strip()) if m else (part, "")
        if PERSON.match(name) and not any(c.isdigit() for c in name):
            person = {"name": name, "title": title}
            if affiliation:
                person["affiliation"] = affiliation
            people.append(person)
    return people


def _instructors(root: Tag, from_text: list[dict]) -> list[dict]:
    """Instructors from tables (newer pages), then from 'Instructors' paragraphs (older pages)."""
    people: dict[str, dict] = {}
    for table in root.find_all("table"):
        rows = [[_text(c) for c in tr.find_all(["td", "th"])] for tr in table.find_all("tr")]
        if not rows:
            continue
        header = [h.lower() for h in rows[0]]
        if "name" not in header:
            continue
        col = {h: header.index(h) for h in ("name", "title", "affiliation") if h in header}
        for row in rows[1:]:
            get = lambda h: row[col[h]].strip() if h in col and col[h] < len(row) else ""
            name = get("name")
            if name and name not in people:
                person = {"name": name, "title": get("title"), "affiliation": get("affiliation")}
                people[name] = {k: v for k, v in person.items() if v}
    for person in from_text:
        people.setdefault(person["name"], person)
    return list(people.values())


def parse_training(html: str, url: str) -> dict:
    """Return a draft training record plus private keys: `_is_arset` (bool),
    `_instructors` (name/title/affiliation dicts) and `_linked` (slugs of other trainings linked)."""
    soup = BeautifulSoup(html, "html.parser")
    slug = training_slug(url) or slugify(url.rstrip("/").rsplit("/", 1)[-1])

    title = _text(soup.select_one("h1.field--name-title") or soup.find("h1"))
    if not title:
        og = soup.find("meta", property="og:title")
        title = (og.get("content", "") if og else "").split(" | ")[0]

    project_text = " ".join(_text(_field(soup, n)) for n in ("field-projects", "field-long-name"))
    is_arset = "ARSET" in project_text or "Applied Remote Sensing Training" in project_text or "ARSET" in title

    level = _text(_field(soup, "field-level")).lower()
    fmt = FORMATS.get(slugify(_text(_field(soup, "field-training-type"))))
    dates = parse_dates(_text(_field(soup, "field-start-and-end-dates")).split("Times")[0])

    record: dict = {
        "id": slug,
        "title": title,
        "status": "draft",
        "source_url": training_url(slug),
        "level": level if level in LEVELS else None,
        "format": fmt,
        "languages": ["en"],
        "start_date": dates[0].isoformat() if dates else None,
        "end_date": dates[-1].isoformat() if dates else None,
        "published": _one_date(_text(_field(soup, "published-at"))),
        "last_updated": _one_date(_text(_field(soup, "field-last-updated"))),
        "summary": _text(_field(soup, "field-summary")) or None,
    }

    root = soup.find("main") or soup
    description: list[str] = []
    objectives: list[str] = []
    audience: list[str] = []
    prerequisites: list[str] = []
    format_text: list[str] = []
    sessions: list[dict] = []
    videos: list[dict] = []  # videos outside any session
    materials: list[dict] = []
    seen_videos: set[str] = set()
    seen_urls: set[str] = set()
    linked: set[str] = set()  # every other training this page links to
    listed_people: list[dict] = []  # from "Instructors" paragraphs on older pages
    section = ""
    sub = ""  # h4 heading inside a session ("Materials", "ARSET Instructors", ...)
    session: dict | None = None

    for el in root.find_all(True):
        if el.name in ("h2", "h3", "h4"):
            heading = _text(el)
            m = re.match(r"part\s*(\d+)\s*[:.\-–]?\s*(.*)", heading, re.I)
            if m:
                session = {"part": int(m.group(1)), "title": m.group(2) or heading,
                           "date": None, "agenda": [], "videos": [], "materials": []}
                sessions.append(session)
                section, sub = "session", ""
            elif heading and el.name == "h4" and session is not None:
                sub = heading.lower()
            elif heading:
                session, sub = None, ""
                section = heading.lower()
            if section in ("citation", "details"):
                break  # the rest is page chrome; metadata fields were read above
            continue

        for vid in _youtube_ids(el):
            if vid not in seen_videos:
                seen_videos.add(vid)
                (session["videos"] if session else videos).append({"youtube": vid})

        if el.name in ("p", "li") and not (el.name == "p" and el.find_parent("li")):
            text = _text(el)
            if not text:
                continue
            heading_now = sub if session is not None else section
            if "instructor" in heading_now:
                role = "Guest Instructor" if "guest" in heading_now else "ARSET Instructor"
                listed_people += people_from_text(text, role)
            elif section == "description" and el.name == "p":
                description.append(text)
            elif section == "objectives" and el.name == "li":
                objectives.append(text)
            elif section == "target audience" and (el.name == "li" or not el.find_parent("ul")):
                audience.append(text)
            elif section == "course format":
                format_text.append(text)
            elif session is not None and "material" not in sub:
                if el.name == "p" and not session["date"] and len(text) < 40 and parse_dates(text):
                    session["date"] = parse_dates(text)[0].isoformat()
                elif el.name == "li" and not el.find("a") and not el.find("li"):
                    session["agenda"].append(text)

        if el.name == "a" and el.get("href"):
            href = requote_uri(urljoin(url, el["href"].strip()))  # some file links contain raw spaces
            if not href.startswith("http"):
                continue
            pre = training_slug(href)
            if pre and pre != slug:
                linked.add(pre)
            if section == "prerequisites":
                if pre and pre not in prerequisites:
                    prerequisites.append(pre)
                continue
            if session is None or pre or YOUTUBE_ID.search(href):
                continue
            label = _text(el)
            if href in seen_urls:
                # Pages often wrap an icon and the text in separate links: keep the labelled one.
                earlier = next((m for s in sessions for m in s["materials"] if m["url"] == href), None)
                if earlier is not None and label and "title" not in earlier:
                    earlier.update(title=label, type=_classify(label, href))
                continue
            seen_urls.add(href)
            material = {"type": _classify(label, href), "title": label or None, "url": href,
                        "language": _language_of(label)}
            session["materials"].append({k: v for k, v in material.items() if v})

    languages = ["en"]
    for text in format_text + [project_text]:
        code = _language_of(text)
        if code and code not in languages:
            languages.append(code)
    for link in soup.find_all("link", rel="alternate", hreflang=True):
        code = link["hreflang"][:2].lower()
        if re.fullmatch(r"[a-z]{2}", code) and code not in languages and link["hreflang"] != "x-default":
            languages.append(code)

    record.update({
        "languages": languages,
        "description": "\n\n".join(description) or None,
        "objectives": objectives or None,
        "audience": audience or None,
        "prerequisites": prerequisites or None,
        "sessions": [{k: v for k, v in s.items() if v} for s in sessions] or None,
        "videos": videos or None,
        "materials": materials or None,
    })
    record = {k: v for k, v in record.items() if v not in (None, [], "")}
    record["_is_arset"] = is_arset
    record["_instructors"] = _instructors(root, listed_people)
    record["_linked"] = sorted(linked)
    return record
