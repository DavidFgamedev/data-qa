"""Shared fixtures.

`broken_dirs` is derived from the filesystem rather than listed here, so a new broken
fixture is picked up by the parametrized tests the moment it is added, and a rule with no
fixture fails `test_fixtures.py::test_every_rule_has_a_broken_fixture` instead of being
quietly untested.
"""

from __future__ import annotations

import os

import pytest

from data_qa.loader import load_dataset
from data_qa.schema import load_schema

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
CLEAN = os.path.join(FIXTURES, "clean")
BROKEN = os.path.join(FIXTURES, "broken")


def broken_dirs():
    return sorted(
        os.path.join(BROKEN, name)
        for name in os.listdir(BROKEN)
        if os.path.isdir(os.path.join(BROKEN, name))
    )


def rule_id_of(path: str) -> str:
    return os.path.basename(path).split("-", 1)[0]


@pytest.fixture(scope="session")
def schema():
    return load_schema()


@pytest.fixture(scope="session")
def clean_dir():
    return CLEAN


@pytest.fixture(scope="session")
def clean_dataset(schema):
    return load_dataset(CLEAN, schema)


@pytest.fixture
def dataset_for(schema):
    def build(path: str):
        return load_dataset(path, schema)

    return build
