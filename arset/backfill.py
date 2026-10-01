"""Find older ARSET trainings that the listing pages no longer show.

The Earthdata catalog's paginated listing sits behind a human-verification
challenge, so it cannot be read by scripts. Other sources can:

0. The Internet Archive's URL index (`--wayback`). It lists every
   earthdata.nasa.gov/learn/trainings/<slug> page it has captured, plus the
   pre-2024 appliedsciences.nasa.gov training URLs, which still redirect to
   their Earthdata pages. The live pages are then scraped as usual.
1. Links between training pages. Every page links to its prerequisites (and
   often to related trainings); crawling those links outward from the trainings
   already in the catalog reaches much of the archive.
2. YouTube descriptions. ARSET recordings usually link back to their training
   page. Given a list of video ids, their descriptions are searched for training
   links (old appliedsciences.nasa.gov / go.nasa.gov links are followed through
   their redirects), and each video is attached to the training it points to.
"""
from __future__ import annotations

import json
import re
import time
from collections import deque
from pathlib import Path

import requests

from . import ingest, scrape, youtube
from .catalog import ROOT, Catalog, iter_videos
from .track import STATE, _load_state, _match_session

YOUTUBE_CACHE = ROOT / "state" / "youtube_links.json"
REDIRECT_CACHE = ROOT / "state" / "redirects.json"
CDX = "https://web.archive.org/cdx/search/cdx"
OLD_TRAINING = re.compile(r"^appliedsciences\.nasa\.gov/join-mission/training/english/[a-z0-9-]+$")
LINK = re.compile(
    r"https?://(?:www\.)?(?:earthdata\.nasa\.gov|appliedsciences\.nasa\.gov|go\.nasa\.gov|arset\.gsfc\.nasa\.gov)"
    r"/[^\s\"'<>)\]]+",
    re.I,
)
PAUSE = 0.5  # seconds between Earthdata requests


def _log(msg: str) -> None:
    print(msg, flush=True)


def resolve_training(url: str) -> str | None:
    """Follow redirects from an old or short link to an Earthdata training slug."""
    slug = scrape.training_slug(url)
    if slug:
        return slug
    try:
        resp = requests.head(url, allow_redirects=True, timeout=20,
                             headers={"User-Agent": scrape.USER_AGENT})
    except requests.RequestException:
        return None
    return scrape.training_slug(resp.url)


CDX_CACHE = ROOT / "state" / "wayback_urls.json"


def _cdx(prefix: str) -> list[str]:
    """Archived URLs under a prefix. Cached, because the archive rate-limits (HTTP 429)."""
    cache = json.loads(CDX_CACHE.read_text(encoding="utf-8")) if CDX_CACHE.exists() else {}
    for attempt in range(4):
        try:
            resp = requests.get(CDX, timeout=300, params={
                "url": prefix, "matchType": "prefix", "fl": "original", "collapse": "urlkey", "limit": 50000,
            })
            resp.raise_for_status()
        except requests.RequestException as e:
            if attempt < 3:
                _log(f"  archive: {e.__class__.__name__}; retrying in {30 * (attempt + 1)}s")
                time.sleep(30 * (attempt + 1))
            elif prefix in cache:
                _log("  archive unavailable; using the cached URL list")
                return cache[prefix]
            else:
                raise
        else:
            cache[prefix] = sorted(set(resp.text.split()))
            CDX_CACHE.parent.mkdir(exist_ok=True)
            CDX_CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
            return cache[prefix]
    return []


def _bare(url: str) -> str:
    """'http://www.x.gov:80/a/b/?q' -> 'x.gov/a/b'"""
    url = re.sub(r"^https?://(www\.)?", "", url)
    return re.sub(r"[?#].*$", "", url.replace(":80/", "/")).rstrip("/")


def wayback_slugs() -> list[str]:
    """Every training slug the Internet Archive has seen, old URLs resolved to current ones."""
    slugs = {
        slug for url in _cdx("earthdata.nasa.gov/learn/trainings/")
        if (slug := scrape.training_slug("https://" + _bare(url)))
    }
    _log(f"Wayback: {len(slugs)} Earthdata training pages")

    cache = json.loads(REDIRECT_CACHE.read_text(encoding="utf-8")) if REDIRECT_CACHE.exists() else {}
    old = sorted({b for url in _cdx("appliedsciences.nasa.gov/join-mission/training/english/")
                  if OLD_TRAINING.match(b := _bare(url))})
    todo = [u for u in old if u not in cache]
    _log(f"Wayback: {len(old)} old appliedsciences.nasa.gov URLs, {len(todo)} to resolve")
    for i, url in enumerate(todo, 1):
        cache[url] = resolve_training("https://" + url)
        if i % 50 == 0 or i == len(todo):
            _log(f"  {i}/{len(todo)} resolved")
            REDIRECT_CACHE.parent.mkdir(exist_ok=True)
            REDIRECT_CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True), encoding="utf-8")
    resolved = {s for u in old if (s := cache.get(u))}
    _log(f"Wayback: {len(resolved - slugs)} more trainings found through old URLs")
    return sorted(slugs | resolved)


def youtube_links(video_ids: list[str]) -> dict[str, list[str]]:
    """video id -> training slugs linked from its description (cached in state/)."""
    cache = json.loads(YOUTUBE_CACHE.read_text(encoding="utf-8")) if YOUTUBE_CACHE.exists() else {}
    todo = [v for v in video_ids if v not in cache]
    _log(f"YouTube: {len(video_ids)} videos, {len(todo)} descriptions to fetch")
    session = youtube.session()
    for i, vid in enumerate(todo, 1):
        try:
            text = youtube.description(vid, session)
        except requests.RequestException as e:
            _log(f"  {vid}: {e.__class__.__name__}")
            continue
        if text is None:  # private or removed
            cache[vid] = []
            continue
        slugs = []
        for url in dict.fromkeys(LINK.findall(text)):
            slug = resolve_training(url.rstrip(".,;"))
            if slug and slug not in slugs:
                slugs.append(slug)
        cache[vid] = slugs
        if i % 25 == 0 or i == len(todo):
            _log(f"  {i}/{len(todo)} descriptions read")
            YOUTUBE_CACHE.parent.mkdir(exist_ok=True)
            YOUTUBE_CACHE.write_text(json.dumps(cache, indent=1, sort_keys=True), encoding="utf-8")
    return {v: cache.get(v, []) for v in video_ids}


def _read_video_list(path: Path) -> list[tuple[str, str]]:
    rows = []
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:  # yt-dlp output redirected on Windows is in the console code page
        text = raw.decode("cp1252", errors="replace")
    for line in text.splitlines():
        vid, _, title = line.partition("|")
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid.strip()):
            rows.append((vid.strip(), title.strip()))
    return rows


def crawl(cat: Catalog, seeds: list[str], limit: int = 500, youtube_ids_file: str | None = None,
          wayback: bool = False, refresh: bool = False) -> None:
    state = _load_state()
    known = cat["training"]
    queue: deque[str] = deque(seeds)
    if wayback:
        queue.extend(wayback_slugs())
    for t in list(known.values()):
        if refresh:
            queue.append(t["id"])  # re-read known pages for new content and links
        queue.extend(p for p in t.get("prerequisites") or [] if p not in known)

    videos: list[tuple[str, str]] = []
    video_slugs: dict[str, list[str]] = {}
    if youtube_ids_file:
        videos = _read_video_list(Path(youtube_ids_file))
        video_slugs = youtube_links([v for v, _ in videos])
        for slugs in video_slugs.values():
            queue.extend(slugs)

    visited: set[str] = set()
    added = updated = fetched = 0
    while queue and fetched < limit:
        slug = queue.popleft()
        if slug in visited or state["pages"].get(slug, {}).get("arset") is False:
            continue
        visited.add(slug)
        fetched += 1
        time.sleep(PAUSE)
        try:
            scraped = ingest.scrape_training(cat, scrape.training_url(slug))
        except requests.RequestException as e:
            _log(f"  ! {slug}: {e}")
            continue
        state["pages"][slug] = {"arset": scraped.is_arset, "last_checked": time.strftime("%Y-%m-%d")}
        queue.extend(s for s in scraped.linked if s not in visited)
        if not scraped.is_arset:
            continue
        if slug in known:
            if ingest.update_existing(cat, known[slug], scraped):
                updated += 1
        else:
            ingest.add_new(cat, scraped)
            added += 1
            _log(f"+ {scraped.record['title']}")

    # Attach recordings the training pages do not embed themselves.
    attached = 0
    assigned = {v["youtube"] for t in known.values() for _, v in iter_videos(t)}
    for vid, title in videos:
        slugs = [s for s in video_slugs.get(vid, []) if s in known]
        if vid in assigned or len(slugs) != 1:
            continue
        t = known[slugs[0]]
        entry = {"youtube": vid, "title": title}
        lang = youtube.guess_language(title)
        if lang:
            entry["language"] = lang
        match = _match_session(title, [t])
        target = match[1] if match else t
        target.setdefault("videos", []).append(entry)
        assigned.add(vid)
        cat.save("training", t)
        attached += 1

    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    left = len([s for s in queue if s not in visited])
    _log(f"\nfetched {fetched} pages: {added} trainings added, {updated} updated, "
         f"{attached} videos attached from YouTube" + (f"; {left} pages still queued (raise --max)" if left else ""))
