import json
import subprocess
from pathlib import Path

import pytest

from job_aggregation_engine.adapters import discover_freehire_boards, source_plan, submodule_preflight
from job_aggregation_engine.core import Job, canonicalize_url, is_relevant


def test_preflight_requires_initialized_git_submodules(tmp_path):
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    for path in ("vendor/jobspy", "vendor/ats-scrapers", "vendor/freehire"):
        (tmp_path / path).mkdir(parents=True)
    with pytest.raises(RuntimeError, match="git submodule update --init --recursive"):
        submodule_preflight(str(tmp_path))
    assert len(submodule_preflight(str(tmp_path), allow_partial=True)) == 3


def test_discovery_skips_unsupported_provider_and_fills_limit(monkeypatch):
    import sys
    import types

    boards = {("greenhouse", "dead"): "Dead", ("greenhouse", "live"): "Live"}
    discover = types.SimpleNamespace(PROVIDER_HOSTS={"greenhouse": "jobs.greenhouse.io"}, collect_candidates=lambda *args: boards)
    ats_boards = types.SimpleNamespace(validate=lambda provider, slug: slug == "live")
    monkeypatch.setitem(sys.modules, "discover_boards", discover)
    monkeypatch.setitem(sys.modules, "ats_boards", ats_boards)
    monkeypatch.setattr("job_aggregation_engine.adapters._load_freehire", lambda: ats_boards)

    assert discover_freehire_boards("Engineer", providers=("traffit", "greenhouse"), limit=1) == [("greenhouse", "live", "Live")]


def test_default_source_plan_contains_exact_required_identifiers():
    assert source_plan() == [
        "jobspy",
        "freehire_discovery",
        "ats_scrapers",
    ]


def test_platform_selection_does_not_change_source_plan():
    assert source_plan(["reed_uk", "indeed"]) == [
        "jobspy",
        "freehire_discovery",
        "ats_scrapers",
    ]


def test_cli_accepts_platforms_alias():
    from job_aggregation_engine.cli import parser

    args = parser().parse_args([
        "--title",
        "Engineer",
        "--location",
        "London",
        "--output",
        "jobs.jsonl",
        "--platforms",
        "indeed",
    ])
    assert args.platform == ["indeed"]


def test_strict_relevance_does_not_use_description_to_rescue_title():
    job = Job(
        "Therapist",
        "Acme",
        None,
        False,
        "Remote GTM Engineer opportunity",
        None,
        "test",
        0.9,
        None,
        "Remote",
        "x",
        "https://x.test/job",
        None,
    )
    assert not is_relevant(job, ["Remote GTM Engineer"])


def test_canonical_url_preserves_indeed_jk():
    assert (
        canonicalize_url(
            "https://UK.Indeed.com/viewjob/?jk=abc&utm_source=x&trackingId=y"
        )
        == "https://uk.indeed.com/viewjob?jk=abc"
    )


def test_cli_default_path_discovers_and_fetches_ats_sources(
    monkeypatch, tmp_path, capsys
):
    from job_aggregation_engine import cli

    calls = []
    monkeypatch.setattr(cli, "submodule_preflight", lambda **kwargs: [])
    monkeypatch.setattr(
        cli, "jobspy_search", lambda *args: calls.append("jobspy") or []
    )
    monkeypatch.setattr(
        cli,
        "discover_freehire_boards",
        lambda *args, **kwargs: calls.append("freehire")
        or [("greenhouse", "acme", "Acme")],
    )
    monkeypatch.setattr(
        cli,
        "ats_scrapers_search",
        lambda *args, **kwargs: calls.append("ats") or ([], 2),
    )

    cli.main([
        "--title",
        "Engineer",
        "--location",
        "London",
        "--output",
        str(tmp_path / "jobs.jsonl"),
    ])

    assert calls == ["jobspy", "freehire", "ats"]
    health = json.loads(
        capsys.readouterr().err.removeprefix("source_health=").strip()
    )
    assert health["sources_attempted"] == 3
    assert health["failures"] == 2


def test_discovery_falls_back_to_offline_sources_when_collect_fails(
    monkeypatch, tmp_path
):
    import sys
    import types

    sources_dir = tmp_path / "sources"
    sources_dir.mkdir(parents=True)
    (sources_dir / "greenhouse.yml").write_text(
        "- company: Acme Corp\n  board: acme\n- company: Beta Inc\n  board:"
        " beta\n"
    )

    discover = types.SimpleNamespace(
        PROVIDER_HOSTS={"greenhouse": "jobs.greenhouse.io"},
        collect_candidates=lambda *args: (_ for _ in ()).throw(
            RuntimeError("403")
        ),
    )
    ats_boards = types.SimpleNamespace(validate=lambda provider, slug: True)
    monkeypatch.setitem(sys.modules, "discover_boards", discover)
    monkeypatch.setitem(sys.modules, "ats_boards", ats_boards)
    monkeypatch.setattr(
        "job_aggregation_engine.adapters._load_freehire", lambda: ats_boards
    )

    from job_aggregation_engine import adapters
    monkeypatch.setattr(adapters, "_freehire_sources_dir", lambda: sources_dir)

    results = discover_freehire_boards(
        "Acme", providers=("greenhouse",), limit=2
    )
    assert len(results) >= 1
    assert results[0][0] == "greenhouse"
    assert results[0][1] in {"acme", "beta"}
