"""The fixtures themselves are under test.

A broken fixture that stops being broken is the quietest failure this tool can have: the
suite stays green and the check it was proving no longer proves anything.
"""

from __future__ import annotations

import os

import pytest
from conftest import broken_dirs, rule_id_of

from data_qa.checks import run_all
from data_qa.rules import RULES


def test_every_rule_has_a_broken_fixture():
    have = {rule_id_of(path) for path in broken_dirs()}
    declared = {rule.id for rule in RULES}
    assert declared == have, f"rules with no fixture: {sorted(declared - have)}"


@pytest.mark.parametrize("path", broken_dirs(), ids=os.path.basename)
def test_broken_fixture_fires_its_own_rule_and_only_its_own(path, dataset_for, schema):
    findings = run_all(dataset_for(path), schema)
    fired = {finding.rule_id for finding in findings}
    assert fired == {rule_id_of(path)}, (
        f"{os.path.basename(path)} fired {sorted(fired)}; a fixture must isolate one rule "
        "or the self-check job cannot attribute a failure"
    )


def test_clean_set_fires_nothing(clean_dataset, schema):
    findings = run_all(clean_dataset, schema)
    assert findings == (), [f.line() for f in findings]


def test_clean_set_loads_every_declared_table(clean_dataset, schema):
    assert set(clean_dataset.tables) == set(schema.tables)
    assert clean_dataset.unreadable == {}


def test_broken_fixtures_are_otherwise_complete():
    """Each broken directory differs from clean in one way, not in whatever is missing."""
    for path in broken_dirs():
        files = set(os.listdir(path))
        if rule_id_of(path) == "DQ002":
            continue  # this one is defined by an absent file
        assert len(files) == 5, f"{os.path.basename(path)} has {sorted(files)}"
