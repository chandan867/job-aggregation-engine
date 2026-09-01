"""Optional source adapters. Network clients are intentionally imported at runtime."""
from __future__ import annotations
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from .core import Job

JOBSPY_SITES = {"indeed", "linkedin", "glassdoor", "zip_recruiter", "google", "bayt", "bdjobs", "naukri"}
REQUIRED_SUBMODULES = ("vendor/jobspy", "vendor/ats-scrapers", "vendor/freehire")
SOURCE_PLAN = ("jobspy", "freehire_discovery", "ats_scrapers")
ATS_PROVIDERS = ("greenhouse", "lever", "ashby", "smartrecruiters", "workable", "recruitee", "bamboohr", "breezy", "personio", "jazzhr", "jobvite", "teamtailor", "traffit")


def _load_freehire():
    scripts = Path(__file__).resolve().parents[2] / "vendor" / "freehire" / "scripts"
    if not scripts.exists():
        raise RuntimeError("Freehire source is not initialized")
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    import ats_boards
    return ats_boards


def _freehire_sources_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "vendor" / "freehire" / "sources"


def discover_freehire_boards(query: str, providers: tuple[str, ...] = ATS_PROVIDERS, limit: int = 5) -> list[tuple[str, str, str]]:
    """Discover a bounded set of ATS boards without writing to the vendor checkout."""
    _load_freehire()
    discover = __import__("discover_boards")
    ats_boards = sys.modules["ats_boards"]
    supported = [provider for provider in providers if provider in discover.PROVIDER_HOSTS]
    found = []
    seen = set()
    try:
        boards = discover.collect_candidates(supported, ["ddg"], query, limit)
        for (provider, slug), name in boards.items():
            if ats_boards.validate(provider, slug):
                key = (provider, slug)
                if key not in seen:
                    seen.add(key)
                    found.append((provider, slug, name))
                if len(found) >= limit:
                    return found
    except Exception:
        pass

    if len(found) < limit:
        sources = _freehire_sources_dir()
        q_tokens = [t.lower() for t in query.split() if len(t) > 2]
        for provider in supported:
            p = sources / f"{provider}.yml"
            if not p.exists():
                continue
            entries = re.findall(r'-\s+company:\s*(.+)\n\s+board:\s*(.+)', p.read_text(encoding="utf-8", errors="ignore"))
            for comp, slug in entries:
                comp_clean = comp.strip(' "\'')
                slug_clean = slug.strip(' "\'')
                if q_tokens and not any(t in comp_clean.lower() or t in slug_clean.lower() for t in q_tokens):
                    continue
                key = (provider, slug_clean)
                if key not in seen and ats_boards.validate(provider, slug_clean):
                    seen.add(key)
                    found.append((provider, slug_clean, comp_clean))
                    if len(found) >= limit:
                        return found

        for provider in supported:
            p = sources / f"{provider}.yml"
            if not p.exists():
                continue
            entries = re.findall(r'-\s+company:\s*(.+)\n\s+board:\s*(.+)', p.read_text(encoding="utf-8", errors="ignore"))
            for comp, slug in entries:
                comp_clean = comp.strip(' "\'')
                slug_clean = slug.strip(' "\'')
                key = (provider, slug_clean)
                if key not in seen and ats_boards.validate(provider, slug_clean):
                    seen.add(key)
                    found.append((provider, slug_clean, comp_clean))
                    if len(found) >= limit:
                        return found

    return found


def _ats_job(job, provider: str, board: str) -> Job | None:
    url = str(getattr(job, "url", "") or "")
    if not url:
        return None
    posted = getattr(job, "posted_at", None)
    if hasattr(posted, "isoformat"):
        posted = posted.isoformat()
    return Job(
        title=str(getattr(job, "title", "") or ""), company=str(getattr(job, "company", "") or board),
        salary=getattr(job, "salary_summary", None), remote=bool(getattr(job, "is_remote", False)),
        description=str(getattr(job, "description", "") or ""), industry=None, method="ats_scrapers",
        confidence=0.75, date_posted=str(posted) if posted else None,
        location=str(getattr(job, "location", "") or ""), platform=provider,
        job_url=url, apply_url=str(getattr(job, "apply_url", "") or url),
    )


def ats_scrapers_search(boards: list[tuple[str, str, str]], limit: int = 25, timeout: float = 15, concurrency: int = 4) -> tuple[list[Job], int]:
    """Fetch discovered boards concurrently; failures are isolated per board."""
    vendor = Path(__file__).resolve().parents[2] / "vendor" / "ats-scrapers" / "src"
    if not vendor.exists():
        raise RuntimeError("ats-scrapers source is not initialized")
    if str(vendor) not in sys.path:
        sys.path.insert(0, str(vendor))
    from ats_scrapers.scrapers import get_scraper
    def fetch_one(item):
        provider, board, _ = item
        try:
            converted = []
            for row in get_scraper(provider, board, timeout=timeout).fetch()[:limit]:
                converted_job = _ats_job(row, provider, board)
                if converted_job:
                    converted.append(converted_job)
            return converted
        except Exception:
            return None
    jobs, failures = [], 0
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futures = [pool.submit(fetch_one, item) for item in boards]
        for future in as_completed(futures):
            result = future.result()
            if result is None:
                failures += 1
            else:
                jobs.extend(result)
    return jobs, failures


def submodule_preflight(root: str = ".", allow_partial: bool = False) -> list[str]:
    """Verify required gitlinks have initialized submodule worktrees."""
    root_path = Path(root)
    missing = []
    for relative in REQUIRED_SUBMODULES:
        checkout = root_path / relative
        try:
            mode = subprocess.run(
                ["git", "-C", str(root_path), "ls-files", "--stage", "--", relative],
                check=True, capture_output=True, text=True,
            ).stdout.split(maxsplit=1)[0]
            initialized = subprocess.run(
                ["git", "-C", str(checkout), "rev-parse", "--is-inside-work-tree"],
                check=True, capture_output=True, text=True,
            ).stdout.strip() == "true"
        except (OSError, subprocess.CalledProcessError, IndexError):
            mode, initialized = "", False
        if mode != "160000" or not initialized:
            missing.append(relative)
    if missing and not allow_partial:
        command = "git submodule update --init --recursive"
        raise RuntimeError("Required source submodules are not initialized: " + ", ".join(missing) + f". Run `{command}` or pass --allow-partial-sources.")
    return missing


def source_plan(platforms: list[str] | None = None) -> list[str]:
    """Return the stable default source identifiers.

    Platform selection is interpreted by compatible adapters; it does not remove
    required source families from the plan.
    """
    return list(SOURCE_PLAN)


def expand_title(title: str) -> list[str]:
    words = [title.strip()]
    aliases = {"tax advisor": ["tax consultant", "tax manager"], "software engineer": ["software developer", "backend engineer"]}
    return list(dict.fromkeys(words + aliases.get(title.strip().lower(), [])))


def jobspy_search(titles, locations, country, radius, hours, platforms, limit=25):
    try:
        from jobspy import scrape_jobs
    except ImportError as exc:
        raise RuntimeError("JobSpy is optional; install with `pip install .[jobspy]`") from exc
    country_code = "uk" if country.upper() in {"UK", "GB", "UNITED KINGDOM"} else "usa"
    jobs=[]
    for title in titles:
        for location in locations:
            frame=scrape_jobs(site_name=platforms, search_term=title, location=location, country_indeed=country_code,
                              distance=radius, hours_old=hours, results_wanted=limit, verbose=0)
            for row in frame.to_dict("records"):
                url=str(row.get("job_url") or row.get("url") or "")
                if not url: continue
                posted=row.get("date_posted")
                if hasattr(posted, "isoformat"): posted=posted.isoformat()
                jobs.append(Job(title=str(row.get("title") or ""), company=str(row.get("company") or ""),
                    salary=row.get("min_amount") and str(row.get("min_amount")) or row.get("salary_source"),
                    remote=bool(row.get("is_remote", False)), description=str(row.get("description") or ""),
                    industry=None, method="jobspy", confidence=0.8, date_posted=str(posted) if posted else None,
                    location=str(row.get("location") or location), platform=str(row.get("site") or "jobspy"),
                    job_url=url, apply_url=row.get("job_url_direct") or row.get("job_url")))
    return jobs


class ReedUKAdapter:
    """Original Reed UK HTML adapter; no date is inferred when Reed omits it."""
    base_url="https://www.reed.co.uk"
    def search(self, titles, locations, radius=25, hours=None, limit=25):
        try:
            import httpx
            from bs4 import BeautifulSoup
        except ImportError as exc: raise RuntimeError("Install `pip install .[reed]` for Reed support") from exc
        jobs=[]
        for title in titles:
            slug=re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
            for location in locations:
                city=re.sub(r"[^a-zA-Z0-9]+", "-", location.lower()).strip("-")
                url=f"{self.base_url}/jobs/{slug}-jobs-in-{city}?distancefromlocation={radius}"
                soup=BeautifulSoup(httpx.get(url, timeout=15, follow_redirects=True).text, "html.parser")
                for article in soup.find_all("article")[:limit]:
                    heading=article.find(["h2", "h3"]); link=heading.find("a") if heading else None
                    if not link or not link.get("href"): continue
                    href=link["href"].split("?")[0]
                    jobs.append(Job(heading.get_text(" ", strip=True), "", None, False, "", None, "reed_html", .75, None, location, "reed_uk", self.base_url+href, self.base_url+href))
        return jobs
