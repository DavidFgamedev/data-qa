"""Rendering, and the rule-table lookups it depends on."""

from __future__ import annotations

import pytest

from data_qa.docs import START, splice
from data_qa.model import Finding
from data_qa.report import group_by_rule, render_text
from data_qa.rules import rule


def test_a_finding_renders_one_line():
    finding = Finding("DQ006", "enemies", "row 4, column tier", "9 is above the maximum of 5")
    assert finding.line().startswith("DQ006  enemies  row 4, column tier")


def test_findings_group_by_rule():
    findings = [
        Finding("DQ006", "enemies", "row 1", "a"),
        Finding("DQ006", "enemies", "row 2", "b"),
        Finding("DQ007", "weapons", "row 3", "c"),
    ]
    grouped = group_by_rule(findings)
    assert sorted(grouped) == ["DQ006", "DQ007"]
    assert len(grouped["DQ006"]) == 2


def test_text_output_says_so_when_there_is_nothing_to_say():
    assert "No findings" in render_text([], "data", 5)


def test_an_unknown_rule_id_raises_rather_than_rendering_blank():
    with pytest.raises(KeyError, match="no such rule"):
        rule("DQ999")


def test_splice_replaces_only_the_generated_block():
    readme = f"# title\n\nbefore\n\n{START}\n\nSTALE_BLOCK\n\n<!-- rules:end -->\n\nafter\n"
    out = splice(readme)
    assert "before" in out and "after" in out
    assert "STALE_BLOCK" not in out
    assert "DQ001" in out


def test_splice_refuses_a_readme_with_no_block():
    with pytest.raises(ValueError, match="no <!-- rules:start -->"):
        splice("# title\n\nno block here\n")
