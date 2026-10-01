# EO Training Atlas

A personal, non-commercial index of NASA's [Applied Remote Sensing Training (ARSET)](https://www.earthdata.nasa.gov/data/projects/arset) program: its trainings, sessions, recordings, materials, instructors, satellites, datasets, tools and application areas. A tracker picks up new trainings and recordings automatically. A build step compiles everything into JSON, SQLite and a static website.

> **Independent project.** EO Training Atlas is not affiliated with or endorsed by NASA or the ARSET program. Trainings, recordings and materials belong to their authors. The site links to them on NASA Earthdata and YouTube rather than hosting them. Long text from the training pages (descriptions, objectives, audience) is kept in the local catalog for search and analysis but is not republished on the website.

## Layout

```
data/
  trainings/      one YAML per training (id = Earthdata URL slug)
  instructors/    people who teach ARSET trainings
  satellites/     missions/platforms, with their instruments
  datasets/       data products (IMERG, SPL3SMP, HLS, OPERA DSWx, ...)
  applications/   application areas (water resources, disasters, ...)
  tools/          software used in trainings (QGIS, Earth Engine, ...)
schemas/          JSON Schema for each record type
arset/            Python package: validate, track, add, build, serve
site/             source of the static website (HTML/CSS/JS, no framework)
inbox/            tracker output: REPORT.md and videos.yaml (unassigned videos)
state/            what the tracker has already seen
build/            generated catalog.json, arset.sqlite and site/ (not committed)
tracker.yaml      which pages and YouTube channels the tracker watches
```

Trainings reference the other record types by id:

```yaml
satellites: [oco-2, smap]
datasets: [oco-2-sif-lite]
instructors: [erika-podest]
sessions:
  - part: 1
    title: Introduction to Flash Drought Monitoring using SIF and Soil Moisture
    date: '2026-09-24'
    videos:
      - youtube: ZMQZBUs6n0g
        title: 'NASA ARSET: Introduction to Flash Drought Monitoring ..., Part 1/2'
    materials:
      - type: slides
        url: https://www.earthdata.nasa.gov/s3fs-public/2026-09/arset-2026-sif-part1.pdf
```

## Setup

```
pip install -r requirements.txt
```

## Commands

| Command | What it does |
| --- | --- |
| `python -m arset track` | Finds new trainings, recordings and materials. Writes drafts and `inbox/REPORT.md`. Add `--dry-run` to only report, or `--all` to re-scrape every training. |
| `python -m arset add <url> ...` | Adds or refreshes specific trainings from their Earthdata page URLs. |
| `python -m arset backfill --wayback --youtube state/youtube_arset_videos.txt` | Finds older trainings and attaches their recordings. See [Backfilling older trainings](#backfilling-older-trainings). |
| `python -m arset validate` | Checks every record against its schema and that every reference exists. |
| `python -m arset build` | Writes `build/catalog.json`, `build/arset.sqlite` and the website in `build/site/`. |
| `python -m arset serve` | Builds, then serves the site at http://127.0.0.1:8000/. |
| `python -m arset stats` | Prints counts and the most-used satellites and applications. |
| `python -m arset datasets` | Looks up each dataset's latest collections in NASA's CMR catalog and saves download and exploration links to `state/dataset_access.json`. |
| `python -m arset chat` / `ask "…"` | Chats with the assistant in the terminal. See [Chatbot](#chatbot). |
| `python -m arset review` | Lists draft trainings with their tags. Add `--mark <id> ...` to mark trainings or instructors as reviewed. |
| `python -m arset retag` | Re-runs auto-tagging on draft trainings, for example after adding aliases. |
| `python -m pytest tests` | Runs the tests. |

## Website

`python -m arset serve` builds the site and serves it at http://127.0.0.1:8000/. It is plain HTML, CSS and JavaScript in `site/`, with no framework or build step. The site has:

- **Home.** A search box, the next live training with a countdown, topic tiles, the latest recordings and the satellites used.
- **Trainings.** Filters for timing, level, application, language and satellite, shown as a grid or as a timeline. Filter settings are kept in the URL, so you can share a filtered view.
- **A page for each training.** The sessions appear as a timeline with recordings (which play in a pop-up), slides, homework and agendas. There's an "Add to calendar" download for upcoming trainings, and a sidebar with instructors, satellites, datasets, tools and prerequisites.
- **Instructors, satellites, datasets, tools and applications.** Each record has a page showing its trainings and recordings. The satellites page also has a launch timeline.
- **Search everywhere.** Press Ctrl+K (or /) to search every record type.
- **Review.** Draft records and unassigned inbox videos.
- **Light and dark themes**, with a toggle in the header.

The catalog is embedded in `build/site/data.js`. You can also open `build/site/index.html` directly by double-clicking it, but YouTube may refuse to play embedded videos on a `file://` page, so use `serve` if you want the players.

`.github/workflows/pages.yml` publishes the site to GitHub Pages on every push to `main`. To turn it on, go to Settings → Pages → Source and choose "GitHub Actions".

### Getting the data

Each dataset page has a **Get the data** section for the latest version of each collection, built from NASA's public CMR catalog by `python -m arset datasets`. It links to:
- Earthdata Search, for the files;
- the archive's own subsetting tool;
- AppEEARS, Giovanni and Worldview, for exploring without downloading;
- the user guide and DOI.

It also lists any sample data used in trainings that use the dataset. Downloading from NASA archives needs a free [Earthdata Login](https://urs.earthdata.nasa.gov/users/new). Product codes live in each dataset's `cmr_short_names`.

## Chatbot

A local assistant answers questions from the trainings, slides and Q&A transcripts, with links to the exact page. It runs on your machine. Only the question and the retrieved excerpts are sent to the language model.

```
pip install -r requirements-rag.txt
python -m arset rag collect      # download the PDFs, keep their text in corpus/ (~1,000 files, ~30 min)
python -m arset rag build        # split into ~37,000 pieces and index them (~40 min on a laptop CPU)
python -m arset rag eval         # check search quality on eval/questions.yaml
python -m arset rag search "open SMAP in QGIS"   # search without a model
python -m arset chat             # needs GOOGLE_API_KEY in .env
python -m arset serve            # the website with an "Ask the Atlas" chat panel, at http://127.0.0.1:8000/
```

The chat panel appears only when the site runs through `python -m arset serve`, which adds a small local API (`/api/ask`, bound to 127.0.0.1). The published GitHub Pages site has no API, so it shows no chat. Conversations stay in memory and are lost when the server stops.

- **Search** combines meaning-based search (Chroma with a small on-device embedding model) and keyword search (SQLite FTS5), so both "soil water content" and exact codes like `SPL3SMP` work. Results can be filtered by material type, level and year. Slides are split one piece per page, and Q&A transcripts one piece per question-and-answer pair.
- **The agent** (`arset/agent.py`) uses Gemini through LangChain and has five tools: search the materials, get a training, filter trainings, count trainings by domain/satellite/dataset/year, and get a dataset's download links. Get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) and put `GOOGLE_API_KEY=…` in `.env`, which is git-ignored. Set `ARSET_LLM_MODEL` to use a different Gemini model.
- `corpus/` (the text and the index) is git-ignored. The materials belong to their authors and are kept only as a local search index.
- Once the corpus exists, `python -m arset retag` also uses the material text: a satellite, dataset or tool mentioned often enough in a training's slides gets tagged.

## How new content is found

1. **Training pages.** The tracker reads the listing pages in `tracker.yaml` and follows every `/learn/trainings/<slug>` link. A page from a new ARSET training becomes a draft record. From each page it takes the title, level, format, dates, languages, description, objectives, audience, prerequisites, instructors, sessions and agendas, the embedded YouTube recordings, and the material links (slides, homework, notebooks).
2. **Re-checks.** Drafts, and trainings that ended less than 45 days ago, are scraped again, because recordings and homework get posted after the sessions. New items are added to the record. Nothing is ever overwritten or deleted.
3. **YouTube feeds.** The tracker reads the recent uploads from the channels in `tracker.yaml`. Since about 2023, ARSET recordings are posted on **NASA Video** with titles like `NASA ARSET: <session title>, Part N/M`. When a title matches a session in the catalog, the video is attached to that session. Anything else goes to `inbox/videos.yaml` for a person to assign.
4. **Auto-tagging.** Satellites, datasets, tools and application areas are suggested by matching their names, `aliases` and instrument names against the training text. To improve tagging, add aliases to the records.

New records have `status: draft`. When you review one, fix the tags and set `status: reviewed`. After that, the tracker only adds new sessions, videos and materials to it, so tags you removed stay removed.

### Running the tracker on a schedule

Earthdata returns 403 to GitHub-hosted runners, so the tracker runs on a local Windows PC instead. To register the scheduled task, run once:

```
powershell -ExecutionPolicy Bypass -File scripts\install-task.ps1
```

It runs `scripts/track-and-pr.ps1` every Monday and Thursday at 09:00 while you're logged on, or as soon as possible afterwards if the PC was off. When the tracker finds new trainings, recordings or materials, the script commits them to a `tracker/<date>` branch, pushes it, and opens a pull request with `inbox/REPORT.md` as the description. It skips the run if the working tree has uncommitted changes. It logs to `build/logs/track-task.log`. To test without changing anything, run `scripts\track-and-pr.ps1 -DryRun`.

`.github/workflows/checks.yml` runs the tests, validation and a build on every push and pull request, so each tracker PR is checked before you merge it.

### Reviewing drafts

`python -m arset review` lists drafts with their tags. Fix any wrong tags in `data/trainings/<id>.yaml`, then run `python -m arset review --mark <id>`. Application tags need several mentions, with the title weighted most, and at most three are kept per training. If an obvious area is missing, add the missing word to that application's `aliases` and run `python -m arset retag`.

## Backfilling older trainings

The listing pages only show current trainings. Earthdata's full paginated catalog is behind a human-verification check that scripts can't pass, so `backfill` uses three other sources:

1. **`--wayback`.** The Internet Archive's URL index gives every `earthdata.nasa.gov/learn/trainings/<slug>` page it has captured, plus the pre-2024 `appliedsciences.nasa.gov/join-mission/training/english/...` URLs, which still redirect to their Earthdata pages. The index and the resolved redirects are cached in `state/`, because the archive rate-limits.
2. **Links between pages.** Every page scraped queues the other trainings it links to, such as its prerequisites.
3. **`--youtube FILE`.** This reads the descriptions of the videos listed in `FILE` (lines of `videoId|title`), follows any training links in them, and attaches each video to the training it points to, when that training's page doesn't embed it already. `state/youtube_arset_videos.txt` lists the ARSET recordings on the NASA Video and NASA ARSET channels. To refresh it, install [yt-dlp](https://github.com/yt-dlp/yt-dlp) (`pip install yt-dlp`) and run:

   ```
   python -m yt_dlp --flat-playlist --print "%(id)s|%(title)s" https://www.youtube.com/@NASAgovVideo/videos | grep -i arset
   ```

Trainings already in the catalog are skipped unless you pass `--refresh`. Every page is fetched with a short pause between requests. A full `--wayback` run takes about half an hour, and the YouTube step takes about a second per uncached video.

To add a single training, use `python -m arset add <url>`.

## Using the build output

`build/arset.sqlite` has these tables:
- `trainings`, `sessions`, `videos`, `materials`
- one table per reference type: `instructors`, `satellites`, `datasets`, `applications`, `tools`
- link tables `training_<field>`
- a full-text index, `trainings_fts`

For example:

```sql
-- every recording that uses SMAP
SELECT t.title, v.title, v.url
FROM training_satellites ts
JOIN trainings t ON t.id = ts.training_id
JOIN videos v ON v.training_id = t.id
WHERE ts.satellite_id = 'smap';
```

`build/catalog.json` holds the same data as one document. Each training carries a computed `state` (upcoming, in-progress, past or self-paced), and every other record lists the trainings that reference it.
