from __future__ import annotations

import argparse

from .adapters import ReedUKAdapter, expand_title, jobspy_search
from .core import filter_jobs, save_sqlite, write_output


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Conservative multi-platform job aggregation")
    p.add_argument("--title", action="append", required=True, help="Job title; repeat for multiple titles")
    p.add_argument("--industry")
    p.add_argument("--location", action="append", required=True)
    p.add_argument("--country", default="UK")
    p.add_argument("--radius", type=int, default=25)
    p.add_argument("--posted-within-hours", type=int)
    p.add_argument("--platform", action="append", default=None, help="Source platform; repeat to select multiple (default: indeed)")
    p.add_argument("--no-expand-titles", action="store_true")
    p.add_argument("--output", required=True)
    p.add_argument("--sqlite", help="Optional SQLite database path")
    p.add_argument("--limit", type=int, default=25)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    titles = [alias for title in args.title for alias in ( [title] if args.no_expand_titles else expand_title(title) )]
    platforms = list(dict.fromkeys(x.lower() for x in (args.platform or ["indeed"])))
    jobs = []
    jobspy_sites = [x for x in platforms if x in {"indeed", "linkedin", "glassdoor", "zip_recruiter", "google", "bayt", "bdjobs", "naukri"}]
    if jobspy_sites:
        jobs += jobspy_search(titles, args.location, args.country, args.radius, args.posted_within_hours, jobspy_sites, args.limit)
    if "reed_uk" in platforms and args.country.upper() in {"UK", "GB", "UNITED KINGDOM"}:
        jobs += ReedUKAdapter().search(titles, args.location, args.radius, args.posted_within_hours, args.limit)
    jobs = filter_jobs(jobs, args.title, args.industry, args.posted_within_hours)
    write_output(jobs, args.output)
    if args.sqlite:
        save_sqlite(jobs, args.sqlite)
    print(f"wrote {len(jobs)} jobs to {args.output}")


if __name__ == "__main__":
    main()
