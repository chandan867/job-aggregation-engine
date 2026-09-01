import subprocess

import pytest

from job_aggregation_engine.adapters import source_plan, submodule_preflight
from job_aggregation_engine.core import Job, canonicalize_url, is_relevant


def test_preflight_requires_initialized_git_submodules(tmp_path):
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    for path in ("vendor/jobspy", "vendor/ats-scrapers", "vendor/freehire"):
        (tmp_path / path).mkdir(parents=True)
    with pytest.raises(RuntimeError, match="git submodule update --init --recursive"):
        submodule_preflight(str(tmp_path))
    assert len(submodule_preflight(str(tmp_path), allow_partial=True)) == 3


def test_default_source_plan_contains_exact_required_identifiers():
    assert source_plan() == ["jobspy", "freehire_discovery", "ats_scrapers"]


def test_platform_selection_does_not_change_source_plan():
    assert source_plan(["reed_uk", "indeed"]) == ["jobspy", "freehire_discovery", "ats_scrapers"]


def test_cli_accepts_platforms_alias():
    from job_aggregation_engine.cli import parser

    args = parser().parse_args(["--title", "Engineer", "--location", "London", "--output", "jobs.jsonl", "--platforms", "indeed"])
    assert args.platform == ["indeed"]


def test_strict_relevance_does_not_use_description_to_rescue_title():
    job = Job("Therapist", "Acme", None, False, "Remote GTM Engineer opportunity", None, "test", .9, None, "Remote", "x", "https://x.test/job", None)
    assert not is_relevant(job, ["Remote GTM Engineer"])


def test_canonical_url_preserves_indeed_jk():
    assert canonicalize_url("https://UK.Indeed.com/viewjob/?jk=abc&utm_source=x&trackingId=y") == "https://uk.indeed.com/viewjob?jk=abc"
