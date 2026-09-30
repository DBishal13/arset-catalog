# ARSET catalog

A structured, version-controlled catalog of NASA's [Applied Remote Sensing Training (ARSET)](https://www.earthdata.nasa.gov/data/projects/arset) program: its trainings, sessions, recordings, materials, instructors, satellites, datasets, tools and application areas. A tracker picks up new trainings and recordings automatically. A build step compiles everything into JSON and SQLite that apps can use.

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
| `python -m arset add <url> ...` | Adds one or more trainings from Earthdata page URLs. Use it to backfill older trainings. |
| `python -m arset validate` | Checks every record against its schema and that every reference exists. |
| `python -m arset build` | Writes `build/catalog.json`, `build/arset.sqlite` and the website in `build/site/`. |
| `python -m arset serve` | Builds, then serves the site at http://127.0.0.1:8000/. |
| `python -m arset stats` | Prints counts and the most-used satellites and applications. |
| `python -m pytest tests` | Runs the tests. |

## Website

`python -m arset serve` builds the site and serves it at http://127.0.0.1:8000/. The site has:

- **Trainings.** Search and filters for application, satellite, level, language and timing. Trainings are grouped as upcoming, self-paced or past. Filter settings are kept in the URL, so you can share a filtered view.
- **A page for each training.** It shows the sessions with their YouTube players (a player only loads when you click its thumbnail), slides, homework and agenda, and a sidebar with instructors, satellites, datasets, tools and prerequisites.
- **Instructors, satellites, datasets, tools and applications.** Each record has a page listing every training that uses it.
- **Review.** Draft records and unassigned inbox videos.

The catalog is embedded in `build/site/data.js`. You can also open `build/site/index.html` directly by double-clicking it, but YouTube may refuse to play embedded videos on a `file://` page, so use `serve` if you want the players.

`.github/workflows/pages.yml` publishes the site to GitHub Pages on every push to `main`. To turn it on, go to Settings → Pages → Source and choose "GitHub Actions".

## How new content is found

1. **Training pages.** The tracker reads the listing pages in `tracker.yaml` and follows every `/learn/trainings/<slug>` link. A page from a new ARSET training becomes a draft record. From each page it takes the title, level, format, dates, languages, description, objectives, audience, prerequisites, instructors, sessions and agendas, the embedded YouTube recordings, and the material links (slides, homework, notebooks).
2. **Re-checks.** Drafts, and trainings that ended less than 45 days ago, are scraped again, because recordings and homework get posted after the sessions. New items are added to the record. Nothing is ever overwritten or deleted.
3. **YouTube feeds.** The tracker reads the recent uploads from the channels in `tracker.yaml`. Since about 2023, ARSET recordings are posted on **NASA Video** with titles like `NASA ARSET: <session title>, Part N/M`. When a title matches a session in the catalog, the video is attached to that session. Anything else goes to `inbox/videos.yaml` for a person to assign.
4. **Auto-tagging.** Satellites, datasets, tools and application areas are suggested by matching their names, `aliases` and instrument names against the training text. To improve tagging, add aliases to the records.

New records have `status: draft`. When you review one, fix the tags and set `status: reviewed`. After that, the tracker only adds new sessions, videos and materials to it, so tags you removed stay removed.

The GitHub Action in `.github/workflows/track.yml` runs the tracker twice a week and opens a pull request with the report as its description.

## Backfilling older trainings

The listing pages only show current trainings. To add older ones, pass their URLs to `add`:

```
python -m arset add https://www.earthdata.nasa.gov/learn/trainings/introduction-synthetic-aperture-radar
```

Good places to find them:
- `python -m arset validate` warns about every prerequisite that isn't in the catalog yet.
- The ARSET resource guide, linked from the program page.
- `inbox/videos.yaml`, which holds older uploads from the ARSET YouTube channel.

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
