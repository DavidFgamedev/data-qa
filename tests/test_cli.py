"""The exit-code contract, asserted directly.

Exit 2 is the one worth testing hardest. A tool that could not run must not be readable
as a pass, and the way that breaks is always the same: a new failure path returns 1, a
pipeline treats 1 as "findings, continue", and the run that checked nothing is recorded
as a run that found nothing.
"""

from __future__ import annotations

import json
import os

import pytest
from conftest import BROKEN, CLEAN, broken_dirs, rule_id_of

from data_qa.cli import EXIT_CLEAN, EXIT_FINDINGS, EXIT_USAGE, main


def test_clean_set_exits_zero(capsys):
    assert main(["check", CLEAN]) == EXIT_CLEAN
    assert "No findings" in capsys.readouterr().out


@pytest.mark.parametrize("path", broken_dirs(), ids=os.path.basename)
def test_every_broken_fixture_exits_one(path, capsys):
    assert main(["check", path]) == EXIT_FINDINGS
    out = capsys.readouterr().out
    assert rule_id_of(path) in out


def test_no_command_is_a_usage_error(capsys):
    assert main([]) == EXIT_USAGE


def test_a_missing_directory_is_a_usage_error_not_a_pass(capsys):
    assert main(["check", os.path.join(CLEAN, "no-such-directory")]) == EXIT_USAGE
    assert "not a directory" in capsys.readouterr().err


def test_an_unusable_schema_is_a_usage_error_not_a_pass(capsys, tmp_path):
    bad = tmp_path / "schema.json"
    bad.write_text("{ not json", encoding="utf-8")
    assert main(["check", CLEAN, "--schema", str(bad)]) == EXIT_USAGE
    assert "not valid JSON" in capsys.readouterr().err


def test_a_schema_with_no_tables_is_a_usage_error(capsys, tmp_path):
    bad = tmp_path / "schema.json"
    bad.write_text(json.dumps({"tables": {}}), encoding="utf-8")
    assert main(["check", CLEAN, "--schema", str(bad)]) == EXIT_USAGE


def test_an_empty_directory_is_findings_not_a_pass(capsys, tmp_path):
    """Pointing the tool at the wrong folder must never look like a clean bill."""
    assert main(["check", str(tmp_path)]) == EXIT_FINDINGS
    assert "DQ002" in capsys.readouterr().out


def test_json_output_is_valid_json_and_lists_every_finding(capsys):
    path = os.path.join(BROKEN, "DQ006-out-of-range")
    assert main(["check", path, "--format", "json"]) == EXIT_FINDINGS
    payload = json.loads(capsys.readouterr().out)
    assert payload["tables"] == 5
    assert [f["rule"] for f in payload["findings"]] == ["DQ006"]
    assert payload["findings"][0]["name"] == "out-of-range"


def test_rules_subcommand_prints_every_rule(capsys):
    from data_qa.rules import RULES

    assert main(["rules"]) == EXIT_CLEAN
    out = capsys.readouterr().out
    for rule in RULES:
        assert rule.id in out
        assert rule.name in out


def test_text_output_counts_the_findings(capsys):
    main(["check", os.path.join(BROKEN, "DQ007-duplicate-id")])
    assert "1 finding across 1 of 12 rules." in capsys.readouterr().out
