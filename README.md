# Job Aggregation Engine

A clean, original Python 3.11+ package and CLI for conservative job discovery. Upstream source repositories are vendored as Git submodules under `vendor/` and checked by the default CLI preflight.

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

The default CLI requires all source submodules. Install the `reed` extra only when selecting `reed_uk`, and install `test` when running the test suite.

After cloning, initialize sources with `git submodule update --init --recursive`. Runs fail closed if `vendor/jobspy`, `vendor/ats-scrapers`, or `vendor/freehire` is missing; use `--allow-partial-sources` only when accepting reduced coverage and source failures.

## Examples

```bash
job-aggregation --title 'Tax Advisor' --title 'Tax Manager' --industry 'Finance & Accounting / Tax' --location London --country UK --radius 25 --posted-within-hours 72 --platform reed_uk --platform indeed --output results.jsonl --sqlite jobs.db
job-aggregation --title 'Software Engineer' --location 'New York, NY' --country US --platform indeed --output results.csv
```

Repeat `--title`, `--location`, and `--platform`. Use `--no-expand-titles` to disable small deterministic title aliases. Output is JSONL or CSV based on the path suffix. Records contain full description, industry, method/confidence, actual `date_posted` or null, location, platform, job URL, apply URL, title, company, salary, and remote status.

## Optional upstream source catalogs

The `vendor/` entries are pinned Git submodules containing required upstream references and integration sources; they are not copied into this repository. Recursive clone is mandatory for the default run. To inspect them as a teammate:

```bash
git clone --recurse-submodules https://github.com/chandan867/job-aggregation-engine.git
# or, after a normal clone:
git submodule update --init --recursive
```

The default source plan reports the required source identifiers `jobspy`, `freehire_discovery`, and `ats_scrapers`. The default path discovers a bounded set of relevant boards through Freehire and fetches them concurrently via `ats-scrapers`, alongside JobSpy. CLI platform selection via `--platform` remains available for explicitly selecting individual compatible adapters.

These are upstream integration sources. Before using any adapter, feed, catalog, proxy, or resulting data, review and follow the upstream repository's license and source Terms of Service, robots rules, rate limits, and anti-bot policies. Availability and coverage can change independently of this package.

## Contract and caveats

Adapters may return incomplete descriptions or company/salary data when a source blocks requests. JobSpy is optional and imported only when selected or when using the default full-source path. Reed is an original HTML adapter and does not infer publication dates: unknown dates remain null, never “Recent”. Configure an HTTP proxy in the environment when permitted by each source's terms.

Relevance is intentionally conservative: requested title overlap is required, and an industry signal cannot rescue an unrelated title. This rejects the known “Multi-Systemic Therapy” false positive for Tax/Finance searches. Indeed `jk` is retained as the stable query identity while tracking parameters are stripped.

`examples/latest_job_results.csv` is a copied legacy prototype export from the source workspace. It is provided for comparison only; its fields/date behavior may not satisfy this package's contract.

## Tests

```bash
python -m pytest -q
python -m job_aggregation_engine.cli --help
```
