from __future__ import annotations

import argparse
import json
import sys

from .adapters import (
    JOBSPY_SITES, ReedUKAdapter, ats_scrapers_search, discover_freehire_boards,
    expand_title, jobspy_search, source_plan, submodule_preflight,
)
from .core import filter_jobs, save_sqlite, write_output


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Conservative multi-platform job aggregation")
    p.add_argument("--title", action="append", required=True, help="Job title; repeat for multiple titles")
    p.add_argument("--industry")
    p.add_argument("--location", action="append", required=True)
    p.add_argument("--country", default="UK")
    p.add_argument("--radius", type=int, default=25)
    p.add_argument("--posted-within-hours", type=int)
    p.add_argument("--platform", "--platforms", dest="platform", action="append", default=None, help="Compatible JobSpy/Reed platform; repeat to select multiple")
    p.add_argument("--no-expand-titles", action="store_true")
    p.add_argument("--output", required=True)
    p.add_argument("--sqlite", help="Optional SQLite database path")
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--allow-partial-sources", action="store_true", help="Run with missing or uninitialized source submodules")
    p.add_argument("--board-limit", type=int, default=5, help="Maximum discovered ATS boards")
    p.add_argument("--concurrency", type=int, default=4, help="Maximum concurrent ATS board fetches")
    p.add_argument("--timeout", type=float, default=15, help="ATS board fetch timeout in seconds")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    if args.limit <= 0 or args.board_limit <= 0 or args.concurrency <= 0 or args.timeout <= 0:
        raise ValueError("limit, board-limit, concurrency, and timeout must be positive")
    missing_sources = submodule_preflight(allow_partial=args.allow_partial_sources)
    titles = [alias for title in args.title for alias in ([title] if args.no_expand_titles else expand_title(title))]
    default_path = args.platform is None
    platforms = list(dict.fromkeys(x.lower() for x in (args.platform or ["indeed"])))
    selected = source_plan(platforms or None)
    jobs = []
    failures = 0
    attempted = 0
    jobspy_sites = [x for x in platforms if x in JOBSPY_SITES]
    if jobspy_sites:
        attempted += 1
        jobs += jobspy_search(titles, args.location, args.country, args.radius, args.posted_within_hours, jobspy_sites, args.limit)
    if "reed_uk" in platforms and args.country.upper() in {"UK", "GB", "UNITED KINGDOM"}:
        attempted += 1
        jobs += ReedUKAdapter().search(titles, args.location, args.radius, args.posted_within_hours, args.limit)
    if default_path:
        attempted += 2
        try:
            boards = discover_freehire_boards(" ".join(args.title), limit=args.board_limit)
            ats_jobs, ats_failures = ats_scrapers_search(boards, limit=args.limit, timeout=args.timeout, concurrency=args.concurrency)
            jobs += ats_jobs
            failures += ats_failures
        except Exception:
            failures += 1
    jobs = filter_jobs(jobs, args.title, args.industry, args.posted_within_hours)
    health = {
        "plan": selected,
        "missing_submodules": missing_sources,
        "sources_attempted": attempted,
        "jobs_found": len(jobs),
        "failures": failures,
    }
    print("source_health=" + json.dumps(health, sort_keys=True), file=sys.stderr)
    write_output(jobs, args.output)
    with open(args.output + ".meta.json", "w", encoding="utf-8") as meta:
        json.dump({"source_plan": selected, "source_health": health, "limits": vars(args)}, meta, indent=2, default=str)
    if args.sqlite:
        save_sqlite(jobs, args.sqlite)
    print(f"wrote {len(jobs)} jobs to {args.output}")


if __name__ == "__main__":
    main()
