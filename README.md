# Job Aggregation Engine

A clean, original Python 3.11+ package and CLI for conservative job discovery. The runtime remains independent of the optional upstream source repositories vendored as Git submodules under `vendor/`.

## Install

```bash
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test,reed]'
```

For the default JobSpy-backed CLI sources (Indeed, LinkedIn, Glassdoor, Google, ZipRecruiter, and others), install:

```bash
pip install -e '.[jobspy]'
```

The default CLI does not require Git submodules. Install the `reed` extra only when selecting `reed_uk`, and install `test` when running the test suite.

## Examples

```bash
job-aggregation --title 'Tax Advisor' --title 'Tax Manager' --industry 'Finance & Accounting / Tax' --location London --country UK --radius 25 --posted-within-hours 72 --platform reed_uk --platform indeed --output results.jsonl --sqlite jobs.db
job-aggregation --title 'Software Engineer' --location 'New York, NY' --country US --platform indeed --output results.csv
```

Repeat `--title`, `--location`, and `--platform`. Use `--no-expand-titles` to disable small deterministic title aliases. Output is JSONL or CSV based on the path suffix. Records contain full description, industry, method/confidence, actual `date_posted` or null, location, platform, job URL, apply URL, title, company, salary, and remote status.

## Optional upstream source catalogs

The `vendor/` entries are pinned Git submodules containing optional upstream references and integration sources; they are not copied into this repository and are not required at runtime. To inspect them as a teammate:

```bash
git clone --recurse-submodules https://github.com/chandan867/job-aggregation-engine.git
# or, after a normal clone:
git submodule update --init --recursive
```

Their coverage contributions are deliberately separate from the current CLI:

- **JobSpy**: aggregators for job boards such as Indeed, LinkedIn, Glassdoor, Google, and ZipRecruiter. The current CLI already uses the installed `python-jobspy` package when those platforms are selected.
- **ats-scrapers**: reusable Python adapters and hosted public feeds for ATS platforms and company career sources. The current CLI does not automatically invoke these adapters.
- **freehire**: an ATS-board registry and source/discovery catalog for direct company career postings. The current CLI does not automatically consume its catalog.

These are optional upstream references/integration sources. Before using any adapter, feed, catalog, proxy, or resulting data, review and follow the upstream repository's license and source Terms of Service, robots rules, rate limits, and anti-bot policies. Availability and coverage can change independently of this package.

## Contract and caveats

Adapters may return incomplete descriptions or company/salary data when a source blocks requests. JobSpy is optional and imported only when selected. Reed is an original HTML adapter and does not infer publication dates: unknown dates remain null, never “Recent”. Configure an HTTP proxy in the environment when permitted by each source's terms. ATS integrations are deliberately not included yet; the `ats-scrapers` and `freehire` submodules document possible future integration sources only.

Relevance is intentionally conservative: requested title overlap is required, and an industry signal cannot rescue an unrelated title. This rejects the known “Multi-Systemic Therapy” false positive for Tax/Finance searches. Indeed `jk` is retained as the stable query identity while tracking parameters are stripped.

`examples/latest_job_results.csv` is a copied legacy prototype export from the source workspace. It is provided for comparison only; its fields/date behavior may not satisfy this package's contract.

## Tests

```bash
python -m pytest -q
python -m job_aggregation_engine.cli --help
```
