"""Property-based tests, for the checks where a generator beats a table of examples.

The range, positivity, monotonicity and summation checks are each a predicate over
generated numbers, so the honest test is the predicate itself rather than six values
somebody thought of. The structural checks are not here: a generated column name proves
nothing a named example does not.
"""

from __future__ import annotations

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from data_qa.checks.balance import (
    check_cooldown_not_positive,
    check_curve_decreases,
    check_weights_do_not_sum,
)
from data_qa.checks.identifiers import check_duplicate_id
from data_qa.checks.values import check_out_of_range, check_wrong_type
from data_qa.coerce import as_integer, as_number, as_number_list, as_string_list
from data_qa.model import Dataset, Row, Table
from data_qa.schema import load_schema

SCHEMA = load_schema()

# weapons.damage is declared integer, min 1, max 9999 in the shipped schema. The test
# reads the bounds from the schema rather than repeating them, so a schema edit cannot
# leave this test asserting against numbers nobody uses any more.
DAMAGE = SCHEMA.tables["weapons"].columns["damage"]


def weapons_dataset(rows):
    table = Table(
        name="weapons",
        path="weapons.csv",
        columns=("id", "name", "damage", "cooldown_s", "rarity"),
        rows=tuple(Row(number=i, values=v) for i, v in enumerate(rows, start=1)),
    )
    return Dataset(root="memory", tables={"weapons": table}, unreadable={})


def abilities_dataset(curve):
    table = Table(
        name="abilities",
        path="abilities.json",
        columns=("id", "name", "effect_id", "cooldown_s", "power_curve"),
        rows=(Row(number=1, values={"id": "a", "power_curve": curve}),),
    )
    return Dataset(root="memory", tables={"abilities": table}, unreadable={})


def waves_dataset(weights):
    table = Table(
        name="waves",
        path="waves.json",
        columns=("id", "drop_table"),
        rows=(
            Row(
                number=1,
                values={
                    "id": "w1",
                    "drop_table": [{"item": f"i{n}", "weight": w} for n, w in enumerate(weights)],
                },
            ),
        ),
    )
    return Dataset(root="memory", tables={"waves": table}, unreadable={})


# --- DQ006, range -----------------------------------------------------------------------


@given(damage=st.integers(min_value=-10_000, max_value=1_000_000))
def test_range_check_fires_exactly_when_the_value_is_outside_the_bounds(damage):
    data = weapons_dataset([{"id": "w", "damage": str(damage)}])
    fired = bool(check_out_of_range(data, SCHEMA))
    outside = damage < DAMAGE.min or damage > DAMAGE.max
    assert fired == outside


@given(damage=st.integers(min_value=int(DAMAGE.min), max_value=int(DAMAGE.max)))
def test_an_in_range_value_is_never_a_type_error_either(damage):
    data = weapons_dataset([{"id": "w", "damage": str(damage)}])
    assert check_out_of_range(data, SCHEMA) == []
    assert check_wrong_type(data, SCHEMA) == []


# --- DQ011, positivity --------------------------------------------------------------


@given(cooldown=st.floats(min_value=-1000, max_value=1000, allow_nan=False, allow_infinity=False))
def test_positivity_check_fires_exactly_when_the_value_is_not_positive(cooldown):
    data = weapons_dataset([{"id": "w", "cooldown_s": repr(cooldown)}])
    fired = bool(check_cooldown_not_positive(data, SCHEMA))
    assert fired == (cooldown <= 0)


# --- DQ010, monotonicity ------------------------------------------------------------


@given(curve=st.lists(st.integers(min_value=0, max_value=1000), min_size=1, max_size=12))
def test_a_sorted_curve_never_fires(curve):
    assert check_curve_decreases(abilities_dataset(sorted(curve)), SCHEMA) == []


@given(curve=st.lists(st.integers(min_value=0, max_value=1000), min_size=2, max_size=12))
def test_a_curve_fires_exactly_when_some_step_goes_down(curve):
    fired = bool(check_curve_decreases(abilities_dataset(curve), SCHEMA))
    descends = any(b < a for a, b in zip(curve, curve[1:], strict=False))
    assert fired == descends


@given(curve=st.lists(st.integers(min_value=0, max_value=1000), min_size=2, max_size=12))
def test_reversing_a_strictly_increasing_curve_always_fires(curve):
    strictly = sorted(set(curve))
    assume(len(strictly) >= 2)
    assert check_curve_decreases(abilities_dataset(strictly[::-1]), SCHEMA) != []


# --- DQ012, weights -----------------------------------------------------------------


@given(
    weights=st.lists(
        st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=8,
    )
)
def test_weight_check_fires_exactly_when_the_sum_leaves_tolerance(weights):
    column = SCHEMA.tables["waves"].columns["drop_table"]
    fired = bool(check_weights_do_not_sum(waves_dataset(weights), SCHEMA))
    outside = abs(sum(weights) - column.weights_sum_to) > column.tolerance
    assert fired == outside


@given(parts=st.integers(min_value=1, max_value=50))
def test_an_even_split_always_sums_within_tolerance(parts):
    """The floating-point case the tolerance exists for: 1/3, 1/7, 1/49."""
    assert check_weights_do_not_sum(waves_dataset([1 / parts] * parts), SCHEMA) == []


# --- DQ007, duplicates ----------------------------------------------------------------


@given(ids=st.lists(st.sampled_from(["a", "b", "c", "d"]), min_size=1, max_size=10))
def test_duplicate_findings_equal_the_number_of_repeats(ids):
    data = weapons_dataset([{"id": i, "damage": "1"} for i in ids])
    findings = check_duplicate_id(data, SCHEMA)
    assert len(findings) == len(ids) - len(set(ids))


# --- coercion -------------------------------------------------------------------------


@given(value=st.integers())
def test_an_integer_survives_the_csv_round_trip(value):
    assert as_integer(str(value)) == value


@given(value=st.floats(allow_nan=False, allow_infinity=False, width=32))
def test_a_float_survives_the_csv_round_trip(value):
    assert as_number(repr(value)) == value


@given(st.text())
@settings(max_examples=200)
def test_coercion_never_raises_on_arbitrary_text(text):
    """Cells come from spreadsheets. Every coercer answers rather than throwing."""
    for coercer in (as_integer, as_number, as_number_list, as_string_list):
        coercer(text)


@given(
    items=st.lists(
        st.text(alphabet=st.characters(blacklist_characters="|"), min_size=1), max_size=6
    )
)
def test_a_pipe_separated_cell_round_trips_to_a_list(items):
    assume(all(item.strip() == item and item.strip() for item in items))
    assert as_string_list("|".join(items)) == (items if items else [])
