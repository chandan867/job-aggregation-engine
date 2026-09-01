from __future__ import annotations

import argparse
import json
import sys

from .adapters import JOBSPY_SITES, ReedUKAdapter, expand_title, jobspy_search, source_plan, submodule_preflight
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
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    if args.limit <= 0:
        raise ValueError("limit must be positive")
    missing_sources = submodule_preflight(allow_partial=args.allow_partial_sources)
    titles = [alias for title in args.title for alias in ([title] if args.no_expand_titles else expand_title(title))]
    platforms = list(dict.fromkeys(x.lower() for x in (args.platform or [])))
    selected = source_plan(platforms or None)
    jobs = []
    jobspy_sites = [x for x in platforms if x in JOBSPY_SITES]
    if jobspy_sites:
        jobs += jobspy_search(titles, args.location, args.country, args.radius, args.posted_within_hours, jobspy_sites, args.limit)
    if "reed_uk" in platforms and args.country.upper() in {"UK", "GB", "UNITED KINGDOM"}:
        jobs += ReedUKAdapter().search(titles, args.location, args.radius, args.posted_within_hours, args.limit)
    jobs = filter_jobs(jobs, args.title, args.industry, args.posted_within_hours)
    health = {
        "plan": selected,
        "missing_submodules": missing_sources,
        "sources_attempted": int(bool(jobspy_sites)) + int("reed_uk" in platforms and args.country.upper() in {"UK", "GB", "UNITED KINGDOM"}),
        "jobs_found": len(jobs),
        "failures": 0,
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
