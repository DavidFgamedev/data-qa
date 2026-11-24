"""Coercion edge cases that a generated string is unlikely to reach."""

from __future__ import annotations

import pytest

from data_qa.coerce import (
    as_integer,
    as_number,
    as_number_list,
    as_string,
    as_string_list,
    as_weight_table,
)


@pytest.mark.parametrize("value", [float("nan"), "nan", "inf", "-inf", "infinity"])
def test_nan_and_infinity_are_not_numbers(value):
    """They parse happily and compare falsely against every bound, so a NaN would pass a
    range check by being neither too low nor too high."""
    assert as_number(value) is None


@pytest.mark.parametrize("value", [True, False])
def test_a_boolean_is_never_a_number(value):
    assert as_integer(value) is None
    assert as_number(value) is None
    assert as_string(value) is None


def test_a_whole_float_is_an_integer_and_a_fractional_one_is_not():
    assert as_integer(12.0) == 12
    assert as_integer(12.5) is None


def test_whitespace_around_a_number_is_tolerated():
    assert as_integer("  12  ") == 12
    assert as_number(" 0.5 ") == 0.5


def test_a_list_is_not_a_scalar_and_a_scalar_is_not_a_list():
    assert as_string(["a"]) is None
    assert as_integer(["1"]) is None
    assert as_string_list(12) is None


def test_an_empty_cell_is_an_empty_list():
    assert as_string_list("") == []
    assert as_number_list("   ") == []


def test_a_number_list_rejects_a_non_numeric_member():
    assert as_number_list([1, "two", 3]) is None
    assert as_number_list("1|two|3") is None


def test_a_string_list_rejects_a_structured_member():
    assert as_string_list(["a", {"b": 1}]) is None


def test_a_weight_table_needs_item_and_weight_on_every_entry():
    assert as_weight_table([{"item": "a", "weight": 1.0}]) == [("a", 1.0)]
    assert as_weight_table([{"item": "a"}]) is None
    assert as_weight_table([{"weight": 1.0}]) is None
    assert as_weight_table(["a"]) is None
    assert as_weight_table("a") is None


def test_none_is_not_a_string():
    assert as_string(None) is None
