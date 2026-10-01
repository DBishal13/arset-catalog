"""python -m arset <command>"""
from __future__ import annotations

import argparse
import sys
from collections import Counter

from . import catalog, ingest, scrape
from .catalog import iter_videos


def cmd_validate(args) -> int:
    errors, warnings = catalog.validate(catalog.load())
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error:   {e}")
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


def cmd_build(args) -> int:
    cat = catalog.load()
    errors, _ = catalog.validate(cat)
    if errors:
        print("Catalog has errors; run `python -m arset validate`.")
        return 1
    from .build import build
    for path in build(cat):
        print(f"wrote {path.relative_to(catalog.ROOT)}")
    return 0


def cmd_serve(args) -> int:
    status = cmd_build(args)
    if status:
        return status
    from .build import BUILD
    from .server import serve
    serve(str(BUILD / "site"), args.port)
    return 0


def cmd_track(args) -> int:
    from .track import run
    report = run(catalog.load(), refresh_all=args.all, dry_run=args.dry_run)
    print(report.markdown())
    if not args.dry_run:
        print("(also written to inbox/REPORT.md)")
    # Fail when errors are all there is to show, so CI flags it instead of opening an empty PR.
    found = report.new_trainings or report.updated or report.new_videos
    return 1 if report.errors and not found else 0


def cmd_add(args) -> int:
    cat = catalog.load()
    status = 0
    for url in args.urls:
        slug = scrape.training_slug(url)
        if not slug:
            print(f"skip: {url} is not an Earthdata /learn/trainings/ page")
            status = 1
            continue
        scraped = ingest.scrape_training(cat, scrape.training_url(slug))
        if not scraped.is_arset and not args.force:
            print(f"skip: {slug} does not look like an ARSET training (use --force)")
            status = 1
            continue
        if slug in cat["training"]:
            changes = ingest.update_existing(cat, cat["training"][slug], scraped)
            print(f"updated {slug}: " + ("; ".join(changes) or "no changes"))
        else:
            created = ingest.add_new(cat, scraped)
            print(f"added {catalog.record_path('training', slug).relative_to(catalog.ROOT)}")
            for id_ in created:
                print(f"  + instructor {id_}")
    return status


def cmd_retag(args) -> int:
    """Re-run auto-tagging on draft trainings (reviewed ones keep their tags)."""
    from . import tagging
    cat = catalog.load()
    materials = tagging.materials_text_by_training()
    if materials:
        print(f"using extracted material text for {len(materials)} trainings")
    changed = 0
    for t in cat["training"].values():
        if t.get("status") != "draft" and not args.all:
            continue
        new = tagging.suggest(cat, tagging.training_text(t) | {"materials": materials.get(t["id"], "")})
        before = {f: t.get(f) for f in tagging.FIELD_KIND}
        for field in tagging.FIELD_KIND:
            if new.get(field):
                t[field] = new[field]
            else:
                t.pop(field, None)
        if before != {f: t.get(f) for f in tagging.FIELD_KIND}:
            cat.save("training", ingest._ordered(t))
            changed += 1
    print(f"retagged {changed} training(s)")
    return 0


def cmd_review(args) -> int:
    cat = catalog.load()
    if args.mark:
        status = 0
        for id_ in args.mark:
            kind = next((k for k in ("training", "instructor") if id_ in cat[k]), None)
            if kind is None:
                print(f"unknown id: {id_}")
                status = 1
                continue
            cat[kind][id_]["status"] = "reviewed"
            cat.save(kind, cat[kind][id_])
            print(f"reviewed: {kind} {id_}")
        return status

    drafts = sorted((t for t in cat["training"].values() if t.get("status") == "draft"),
                    key=lambda t: t.get("start_date") or "", reverse=True)
    for t in drafts[: args.limit]:
        print(f"\n{t['id']}\n  {t['title']} ({t.get('start_date', 'self-paced')})")
        for field in ("applications", "satellites", "datasets", "tools", "instructors"):
            print(f"  {field:<13} {', '.join(t.get(field) or []) or '-'}")
    left = len(drafts) - args.limit
    people = sum(1 for p in cat["instructor"].values() if p.get("status") == "draft")
    print(f"\n{len(drafts)} draft trainings{f' ({left} more not shown)' if left > 0 else ''}, {people} draft instructors.")
    print("Edit data/trainings/<id>.yaml, then: python -m arset review --mark <id> [<id> ...]")
    return 0


def cmd_rag(args) -> int:
    cat = catalog.load()
    if args.rag_command == "collect":
        from .rag.collect import collect
        collect(cat, limit=args.limit)
    elif args.rag_command == "build":
        from .rag.index import build
        print(f"indexed {build(cat)} chunks into corpus/")
    elif args.rag_command == "eval":
        from .rag.evaluate import evaluate
        evaluate(k=args.k, verbose=args.verbose)
    elif args.rag_command == "search":
        from .rag.index import search
        filters = {k: getattr(args, k) for k in ("kind", "material_type", "level", "since_year")}
        for i, hit in enumerate(search(args.query, k=args.k, **filters), 1):
            c = hit.chunk
            where = f"Part {c['part']}, " if c["part"] else ""
            what = f"{c['material_title'] or c['material_type']}, p.{c['page']}" if c["kind"] != "catalog" else "training page"
            print(f"\n{i}. [{c['kind']} via {hit.via}] {c['training_title']} ({(c['start_date'] or '')[:4]})")
            print(f"   {where}{what}  {c['url']}")
            print(f"   {c['text'][:260]}")
    return 0


def cmd_datasets(args) -> int:
    from .datasets import ACCESS_FILE, refresh
    found = refresh(catalog.load())
    print(f"\nwrote {ACCESS_FILE.relative_to(catalog.ROOT)} ({len(found)} datasets with download links)")
    return 0


def cmd_ask(args) -> int:
    from .agent import ask
    answer, _ = ask(args.question)
    print(answer)
    return 0


def cmd_chat(args) -> int:
    from .agent import MODEL, ask
    print(f"EO Training Atlas chat ({MODEL}). Ask about ARSET trainings; empty line or Ctrl+C to quit.")
    history: list = []
    try:
        while question := input("\nyou> ").strip():
            answer, history = ask(question, history)
            print(f"\n{answer}")
    except (KeyboardInterrupt, EOFError):
        pass
    return 0


def cmd_backfill(args) -> int:
    from .backfill import crawl
    cat = catalog.load()
    seeds = [scrape.training_slug(u) or u for u in args.seeds]
    crawl(cat, seeds=seeds, limit=args.max, youtube_ids_file=args.youtube, wayback=args.wayback,
          refresh=args.refresh)
    return 0


def cmd_stats(args) -> int:
    cat = catalog.load()
    trainings = cat["training"].values()
    print("records:")
    for kind, folder in catalog.KINDS.items():
        print(f"  {folder:<13} {len(cat[kind])}")
    print(f"videos:        {sum(1 for t in trainings for _ in iter_videos(t))}")
    print("trainings by status:", dict(Counter(t.get("status") for t in trainings)))
    print("trainings by level: ", dict(Counter(t.get("level", "?") for t in trainings)))
    for field in ("applications", "satellites"):
        top = Counter(r for t in trainings for r in t.get(field) or []).most_common(8)
        print(f"top {field}:", ", ".join(f"{k} ({n})" for k, n in top) or "-")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m arset", description="ARSET training catalog tools")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("validate", help="check every record against its schema and references").set_defaults(fn=cmd_validate)
    sub.add_parser("build", help="compile build/catalog.json, build/arset.sqlite and build/site/").set_defaults(fn=cmd_build)
    p = sub.add_parser("serve", help="build, then serve the site on localhost")
    p.add_argument("--port", type=int, default=8000)
    p.set_defaults(fn=cmd_serve)
    sub.add_parser("stats", help="summarize the catalog").set_defaults(fn=cmd_stats)

    p = sub.add_parser("track", help="look for new trainings, recordings and materials")
    p.add_argument("--all", action="store_true", help="re-scrape every known training, not just recent ones")
    p.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    p.set_defaults(fn=cmd_track)

    p = sub.add_parser("rag", help="build and query the local search index over training materials")
    rag = p.add_subparsers(dest="rag_command", required=True)
    q = rag.add_parser("collect", help="download PDF materials and extract their text into corpus/")
    q.add_argument("--limit", type=int, help="only fetch this many (for testing)")
    rag.add_parser("build", help="split the catalog and extracted materials into chunks and index them")
    q = rag.add_parser("eval", help="score retrieval against eval/questions.yaml")
    q.add_argument("-k", type=int, default=5)
    q.add_argument("-v", "--verbose", action="store_true")
    q = rag.add_parser("search", help="search the index")
    q.add_argument("query")
    q.add_argument("-k", type=int, default=8, help="number of results")
    q.add_argument("--kind", choices=["catalog", "qa", "page"])
    q.add_argument("--material-type", dest="material_type", help="slides, transcript, homework, exercise, ...")
    q.add_argument("--level", choices=["fundamentals", "introductory", "intermediate", "advanced"])
    q.add_argument("--since-year", dest="since_year", type=int)
    p.set_defaults(fn=cmd_rag)

    sub.add_parser("datasets", help="look up download links for every dataset in NASA's CMR catalog").set_defaults(
        fn=cmd_datasets)

    p = sub.add_parser("ask", help="ask the chatbot one question")
    p.add_argument("question")
    p.set_defaults(fn=cmd_ask)
    sub.add_parser("chat", help="chat with the bot in the terminal").set_defaults(fn=cmd_chat)

    p = sub.add_parser("retag", help="re-run auto-tagging on draft trainings")
    p.add_argument("--all", action="store_true", help="also retag reviewed trainings (overwrites their tags)")
    p.set_defaults(fn=cmd_retag)

    p = sub.add_parser("review", help="list draft records, or mark them reviewed")
    p.add_argument("--mark", nargs="+", metavar="ID", help="training or instructor ids to mark as reviewed")
    p.add_argument("--limit", type=int, default=20, help="how many drafts to list")
    p.set_defaults(fn=cmd_review)

    p = sub.add_parser("backfill", help="crawl older trainings via links between training pages (and YouTube)")
    p.add_argument("seeds", nargs="*", help="extra training URLs or slugs to start from")
    p.add_argument("--max", type=int, default=500, help="stop after fetching this many pages")
    p.add_argument("--refresh", action="store_true",
                   help="re-read trainings already in the catalog (for new content and links)")
    p.add_argument("--wayback", action="store_true",
                   help="also start from every training URL the Internet Archive has captured")
    p.add_argument("--youtube", metavar="FILE",
                   help="text file of 'videoId|title' lines (ARSET videos only); their descriptions are "
                        "searched for training links")
    p.set_defaults(fn=cmd_backfill)

    p = sub.add_parser("add", help="add (or update) trainings from Earthdata page URLs")
    p.add_argument("urls", nargs="+")
    p.add_argument("--force", action="store_true", help="add even if the page is not marked as ARSET")
    p.set_defaults(fn=cmd_add)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
