"""Core contracts, URL identity, conservative relevance, and persistence."""
from __future__ import annotations
import csv, hashlib, re, sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_KEYS = {"refId", "trackingId", "fccid", "vjs", "gh_src"}

@dataclass
class Job:
    title: str
    company: str
    salary: str | None
    remote: bool
    description: str
    industry: str | None
    method: str
    confidence: float
    date_posted: str | None
    location: str
    platform: str
    job_url: str
    apply_url: str | None

    def record(self) -> dict:
        return asdict(self)

def canonicalize_url(url: str) -> str:
    """Remove tracking while retaining Indeed's `jk` identity parameter."""
    if not url: return ""
    p = urlsplit(url)
    keep = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
            if (k.startswith("utm_") or k in TRACKING_KEYS) is False]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), urlencode(keep), ""))

def url_identity(url: str) -> str:
    return hashlib.sha256(canonicalize_url(url).encode()).hexdigest()

def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))

def is_relevant(job: Job, requested_titles: list[str], industry: str | None = None) -> bool:
    """Require title overlap; this prevents descriptions from matching unrelated jobs."""
    title_words = _tokens(job.title)
    requested = [_tokens(t) for t in requested_titles if t.strip()]
    title_match = any(bool(words) and (words <= title_words or bool(words & title_words) and len(words & title_words) >= max(1, len(words)//2)) for words in requested)
    if not title_match: return False
    if industry:
        wanted = _tokens(industry)
        # Industry is a positive signal, but never lets a mismatched title through.
        text = _tokens(job.title + " " + job.description)
        if wanted and not (wanted & text): return False
    return True

def filter_jobs(jobs: list[Job], requested_titles: list[str], industry: str | None = None, hours: int | None = None, now: datetime | None = None) -> list[Job]:
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(hours=hours) if hours else None
    out=[]
    for job in jobs:
        if not is_relevant(job, requested_titles, industry): continue
        if cutoff and job.date_posted:
            try:
                dt=datetime.fromisoformat(job.date_posted.replace("Z", "+00:00"))
                if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
                if dt < cutoff: continue
            except ValueError: pass
        # Unknown dates are retained, never relabeled as Recent.
        out.append(job)
    return out

def write_output(jobs: list[Job], path: str) -> None:
    target=Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    rows=[j.record() for j in jobs]
    if target.suffix.lower()==".jsonl":
        target.write_text("".join(__import__("json").dumps(r, ensure_ascii=False)+"\n" for r in rows), encoding="utf-8")
    elif target.suffix.lower()==".csv":
        with target.open("w", newline="", encoding="utf-8") as f:
            w=csv.DictWriter(f, fieldnames=list(Job.__dataclass_fields__))
            w.writeheader(); w.writerows(rows)
    else: raise ValueError("output path must end in .jsonl or .csv")

def save_sqlite(jobs: list[Job], path: str) -> None:
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS jobs (identity TEXT PRIMARY KEY, data TEXT NOT NULL)")
        import json
        db.executemany("INSERT OR REPLACE INTO jobs VALUES (?, ?)", [(url_identity(j.job_url), json.dumps(j.record())) for j in jobs])
