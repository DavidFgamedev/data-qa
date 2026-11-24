"""The README's rule list against the rule table it is generated from.

This is the test that makes "one rule table" true rather than aspirational.
"""

from __future__ import annotations

import os

from data_qa.docs import END, START, render_rules_markdown
from data_qa.rules import RULES

README = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")


def readme_text():
    with open(README, encoding="utf-8") as handle:
        return handle.read()


def test_readme_has_the_generated_block():
    text = readme_text()
    assert START in text and END in text


def test_readme_rule_list_matches_the_rule_table_exactly():
    text = readme_text()
    block = text.split(START)[1].split(END)[0].strip()
    assert block == render_rules_markdown().strip(), (
        "README rule list is stale. Regenerate it: python -m data_qa rules"
    )


def test_every_rule_summary_is_one_line():
    for rule in RULES:
        assert "\n" not in rule.summary
        assert rule.summary.endswith(".")


def test_rule_ids_are_unique_and_sequential():
    ids = [rule.id for rule in RULES]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)
    assert ids == [f"DQ{n:03d}" for n in range(1, len(ids) + 1)]
