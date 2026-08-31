from __future__ import annotations
import argparse
from .adapters import expand_title, jobspy_search, ReedUKAdapter
from .core import filter_jobs, write_output, save_sqlite

def parser():
 p=argparse.ArgumentParser(description="Conservative multi-platform job aggregation")
 p.add_argument("--title", action="append", required=True, help="Job title; repeat for multiple titles")
 p.add_argument("--industry")
 p.add_argument("--location", action="append", required=True)
 p.add_argument("--country", default="UK"); p.add_argument("--radius", type=int, default=25)
 p.add_argument("--posted-within-hours", type=int); p.add_argument("--platform", action="append", default=["indeed"])
 p.add_argument("--no-expand-titles", action="store_true"); p.add_argument("--output", required=True)
 p.add_argument("--sqlite", help="Optional SQLite database path"); p.add_argument("--limit", type=int, default=25)
 return p

def main(argv=None):
 a=parser().parse_args(argv); titles=[]
 for t in a.title: titles += [t] if a.no_expand_titles else expand_title(t)
 platforms=list(dict.fromkeys(x.lower() for x in a.platform)); jobs=[]
 jobspy_sites=[x for x in platforms if x in {"indeed","linkedin","glassdoor","zip_recruiter","google","bayt","bdjobs","naukri"}]
 if jobspy_sites: jobs += jobspy_search(titles, a.location, a.country, a.radius, a.posted_within_hours, jobspy_sites, a.limit)
 if "reed_uk" in platforms and a.country.upper() in {"UK","GB","UNITED KINGDOM"}: jobs += ReedUKAdapter().search(titles, a.location, a.radius, a.posted_within_hours, a.limit)
 jobs=filter_jobs(jobs, a.title, a.industry, a.posted_within_hours)
 write_output(jobs, a.output)
 if a.sqlite: save_sqlite(jobs, a.sqlite)
 print(f"wrote {len(jobs)} jobs to {a.output}")

if __name__ == "__main__": main()
