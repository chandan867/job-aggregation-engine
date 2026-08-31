# Job Aggregation Engine

A clean, original Python 3.11+ package and CLI for conservative job discovery. It has no dependency on the sibling JobSpy, ats-scrapers, freehire, or `.venv` projects.

## Install

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test,reed]'
# optional JobSpy sources (Indeed, LinkedIn and other supported sites)
python -m pip install -e '.[jobspy]'
```

## Examples

```bash
job-aggregation --title 'Tax Advisor' --title 'Tax Manager' --industry 'Finance & Accounting / Tax' --location London --country UK --radius 25 --posted-within-hours 72 --platform reed_uk --platform indeed --output results.jsonl --sqlite jobs.db
job-aggregation --title 'Software Engineer' --location 'New York, NY' --country US --platform indeed --output results.csv
```

Repeat `--title`, `--location`, and `--platform`. Use `--no-expand-titles` to disable small deterministic title aliases. Output is JSONL or CSV based on the path suffix. Records contain full description, industry, method/confidence, actual `date_posted` or null, location, platform, job URL, apply URL, title, company, salary, and remote status.

## Contract and caveats

Adapters may return incomplete descriptions or company/salary data when a source blocks requests. JobSpy is optional and imported only when selected. Reed is an original HTML adapter and does not infer publication dates: unknown dates remain null, never “Recent”. Configure an HTTP proxy in the environment when permitted by each source's terms. ATS integrations are deliberately not included yet.

Relevance is intentionally conservative: requested title overlap is required, and an industry signal cannot rescue an unrelated title. This rejects the known “Multi-Systemic Therapy” false positive for Tax/Finance searches. Indeed `jk` is retained as the stable query identity while tracking parameters are stripped.

`examples/latest_job_results.csv` is a copied legacy prototype export from the source workspace. It is provided for comparison only; its fields/date behavior may not satisfy this package's contract.

## Tests

```bash
python -m pytest -q
python -m job_aggregation_engine.cli --help
```
