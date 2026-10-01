"""YouTube lookups that need no API key: channel RSS feeds and oEmbed."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET

import requests

NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
LANGUAGE_MARKERS = {
    "es": [r"\bspanish\b", r"\bespañol\b", r"\bespanol\b", r"\(es\)", r"\bparte\b", r"\bsesión\b"],
    "fr": [r"\bfrench\b", r"\bfrançais\b", r"\bfrancais\b", r"\(fr\)", r"\bpartie\b"],
    "pt": [r"\bportuguese\b", r"\bportuguês\b", r"\(pt\)"],
}


def watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def channel_feed(channel_id: str) -> list[dict]:
    """The channel's ~15 most recent uploads."""
    resp = requests.get(
        "https://www.youtube.com/feeds/videos.xml", params={"channel_id": channel_id}, timeout=30
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    return [
        {
            "youtube": entry.findtext("yt:videoId", namespaces=NS),
            "title": entry.findtext("a:title", namespaces=NS),
            "published": (entry.findtext("a:published", namespaces=NS) or "")[:10],
        }
        for entry in root.findall("a:entry", NS)
    ]


def oembed(video_id: str) -> dict | None:
    """Title and channel of a public video, or None if it is private/removed."""
    resp = requests.get(
        "https://www.youtube.com/oembed",
        params={"url": watch_url(video_id), "format": "json"},
        timeout=30,
    )
    if resp.status_code != 200:
        return None
    data = resp.json()
    return {"title": data.get("title"), "channel": data.get("author_name")}


DESCRIPTION = re.compile(r'"shortDescription":("(?:[^"\\]|\\.)*")')


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36",
                      "Accept-Language": "en-US,en;q=0.9"})
    s.cookies.set("SOCS", "CAI", domain=".youtube.com")  # skip the EU consent interstitial
    return s


def description(video_id: str, s: requests.Session | None = None) -> str | None:
    """A video's description text from its watch page, or None if the page has none (private/removed)."""
    resp = (s or session()).get(watch_url(video_id), timeout=30)
    resp.raise_for_status()
    m = DESCRIPTION.search(resp.text)
    return json.loads(m.group(1)) if m else None


def guess_language(title: str) -> str | None:
    low = title.lower()
    for code, patterns in LANGUAGE_MARKERS.items():
        if any(re.search(p, low) for p in patterns):
            return code
    return None


def enrich(video: dict) -> dict:
    """Fill in title/channel/language for a {'youtube': id} dict (in place)."""
    info = oembed(video["youtube"])
    if info:
        video.setdefault("title", info["title"])
        video.setdefault("channel", info["channel"])
    if video.get("title") and "language" not in video:
        lang = guess_language(video["title"])
        if lang:
            video["language"] = lang
    return video
