"""One named test per check, against tables built in memory.

These construct a Dataset directly rather than reading a file, so a failure points at the
check and not at the fixture, the loader or the CLI.
"""

from __future__ import annotations

import pytest

from data_qa.checks.balance import (
    check_cooldown_not_positive,
    check_curve_decreases,
    check_weights_do_not_sum,
)
from data_qa.checks.identifiers import check_duplicate_id, check_missing_id
from data_qa.checks.references import check_unknown_reference
from data_qa.checks.structure import (
    check_missing_column,
    check_missing_table,
    check_unknown_column,
    check_unreadable_file,
)
from data_qa.checks.values import check_out_of_range, check_wrong_type
from data_qa.model import Dataset, Row, Table


def table(name, columns, rows):
    return Table(
        name=name,
        path=f"{name}.csv",
        columns=tuple(columns),
        rows=tuple(Row(number=i, values=v) for i, v in enumerate(rows, start=1)),
    )


def dataset(*tables, unreadable=None):
    return Dataset(
        root="memory",
        tables={t.name: t for t in tables},
        unreadable=unreadable or {},
    )


def weapons(rows, columns=("id", "name", "damage", "cooldown_s", "rarity")):
    return table("weapons", columns, rows)


def one_weapon(**overrides):
    row = {
        "id": "wpn_pistol",
        "name": "Pistol",
        "damage": "12",
        "cooldown_s": "0.35",
        "rarity": "common",
    }
    row.update(overrides)
    return row


# --- DQ001 ----------------------------------------------------------------------------


def test_unreadable_file_is_a_finding_not_an_exception(schema):
    findings = check_unreadable_file(
        dataset(unreadable={"abilities": "Expecting ',' delimiter"}), schema
    )
    assert [f.rule_id for f in findings] == ["DQ001"]
    assert "abilities.json" in findings[0].where


# --- DQ002 ----------------------------------------------------------------------------


def test_missing_table_names_every_absent_table(schema):
    findings = check_missing_table(dataset(weapons([one_weapon()])), schema)
    assert {f.table for f in findings} == {"enemies", "effects", "abilities", "waves"}


def test_a_table_that_failed_to_parse_is_not_also_reported_missing(schema):
    findings = check_missing_table(
        dataset(weapons([one_weapon()]), unreadable={"enemies": "no header row"}), schema
    )
    assert "enemies" not in {f.table for f in findings}


# --- DQ003 / DQ004 --------------------------------------------------------------------


def test_missing_column_is_caught(schema):
    columns = ("id", "name", "damage", "rarity")
    findings = check_missing_column(dataset(weapons([{}], columns=columns)), schema)
    assert [f.where for f in findings] == ["column cooldown_s"]


def test_unknown_column_is_caught(schema):
    columns = ("id", "name", "damage", "cooldown_s", "rarity", "notes")
    findings = check_unknown_column(dataset(weapons([{}], columns=columns)), schema)
    assert [f.where for f in findings] == ["column notes"]


def test_a_renamed_column_fires_both_shape_rules(schema):
    columns = ("id", "name", "dmg", "cooldown_s", "rarity")
    data = dataset(weapons([{}], columns=columns))
    fired = {f.rule_id for f in check_missing_column(data, schema)} | {
        f.rule_id for f in check_unknown_column(data, schema)
    }
    assert fired == {"DQ003", "DQ004"}


# --- DQ005 ----------------------------------------------------------------------------


def test_wrong_type_is_caught(schema):
    findings = check_wrong_type(dataset(weapons([one_weapon(damage="twelve")])), schema)
    assert [(f.rule_id, f.where) for f in findings] == [("DQ005", "row 1, column damage")]


def test_a_numeric_string_from_a_csv_is_not_a_type_error(schema):
    assert check_wrong_type(dataset(weapons([one_weapon(damage="12")])), schema) == []


def test_a_boolean_in_a_numeric_column_is_a_type_error(schema):
    findings = check_wrong_type(dataset(weapons([one_weapon(damage=True)])), schema)
    assert [f.rule_id for f in findings] == ["DQ005"]


# --- DQ006 ----------------------------------------------------------------------------


def test_out_of_range_is_caught_above_the_maximum(schema):
    findings = check_out_of_range(dataset(weapons([one_weapon(damage="10000")])), schema)
    assert [f.rule_id for f in findings] == ["DQ006"]
    assert "above the maximum" in findings[0].message


def test_bounds_are_inclusive(schema):
    rows = [one_weapon(damage="1"), one_weapon(id="w2", damage="9999")]
    assert check_out_of_range(dataset(weapons(rows)), schema) == []


def test_a_value_outside_one_of_is_caught(schema):
    findings = check_out_of_range(dataset(weapons([one_weapon(rarity="mythic")])), schema)
    assert [f.rule_id for f in findings] == ["DQ006"]


def test_a_type_error_is_not_reported_twice_as_a_range_error(schema):
    data = dataset(weapons([one_weapon(damage="twelve")]))
    assert [f.rule_id for f in check_wrong_type(data, schema)] == ["DQ005"]
    assert check_out_of_range(data, schema) == []


# --- DQ007 / DQ008 --------------------------------------------------------------------


def test_duplicate_id_is_caught_and_names_the_first_row(schema):
    rows = [one_weapon(), one_weapon(name="Pistol Mk II")]
    findings = check_duplicate_id(dataset(weapons(rows)), schema)
    assert [f.rule_id for f in findings] == ["DQ007"]
    assert "row 1" in findings[0].message


def test_missing_id_is_caught(schema):
    findings = check_missing_id(dataset(weapons([one_weapon(id="   ")])), schema)
    assert [f.rule_id for f in findings] == ["DQ008"]


def test_blank_ids_are_not_also_reported_as_duplicates_of_each_other(schema):
    rows = [one_weapon(id=""), one_weapon(id="")]
    assert check_duplicate_id(dataset(weapons(rows)), schema) == []
    assert len(check_missing_id(dataset(weapons(rows)), schema)) == 2


# --- DQ009 ----------------------------------------------------------------------------


def effects(ids):
    return table("effects", ("id", "name", "kind"), [{"id": i} for i in ids])


def abilities(rows):
    return table("abilities", ("id", "name", "effect_id", "cooldown_s", "power_curve"), rows)


def test_unknown_scalar_reference_is_caught(schema):
    data = dataset(effects(["eff_burn"]), abilities([{"id": "a", "effect_id": "eff_gone"}]))
    findings = check_unknown_reference(data, schema)
    assert [f.rule_id for f in findings] == ["DQ009"]
    assert "eff_gone" in findings[0].message


def test_a_known_reference_passes(schema):
    data = dataset(effects(["eff_burn"]), abilities([{"id": "a", "effect_id": "eff_burn"}]))
    assert check_unknown_reference(data, schema) == []


def test_unknown_reference_inside_a_list_column_is_caught(schema):
    enemies = table("enemies", ("id",), [{"id": "enemy_grunt"}])
    waves = table(
        "waves",
        ("id", "enemy_ids", "count", "drop_table"),
        [{"id": "w1", "enemy_ids": ["enemy_grunt", "enemy_ghost"]}],
    )
    findings = check_unknown_reference(dataset(enemies, waves), schema)
    assert [f.rule_id for f in findings] == ["DQ009"]
    assert "enemy_ghost" in findings[0].message


def test_unknown_reference_inside_a_weight_table_is_caught(schema):
    data = dataset(
        weapons([one_weapon()]),
        table(
            "waves",
            ("id", "drop_table"),
            [{"id": "w1", "drop_table": [{"item": "wpn_missing", "weight": 1.0}]}],
        ),
    )
    findings = check_unknown_reference(data, schema)
    assert [f.rule_id for f in findings] == ["DQ009"]
    assert "wpn_missing" in findings[0].message


def test_reference_check_stands_down_when_the_target_table_is_absent(schema):
    """Otherwise one missing file reports every reference in the game as unknown."""
    data = dataset(abilities([{"id": "a", "effect_id": "eff_burn"}]))
    assert check_unknown_reference(data, schema) == []


# --- DQ010 ----------------------------------------------------------------------------


def test_curve_that_decreases_is_caught(schema):
    data = dataset(abilities([{"id": "a", "power_curve": [10, 14, 12, 25]}]))
    findings = check_curve_decreases(data, schema)
    assert [f.rule_id for f in findings] == ["DQ010"]
    assert "level 3" in findings[0].message


def test_a_flat_curve_is_allowed(schema):
    data = dataset(abilities([{"id": "a", "power_curve": [5, 5, 8, 12, 12]}]))
    assert check_curve_decreases(data, schema) == []


def test_one_finding_per_curve_however_many_reversals(schema):
    data = dataset(abilities([{"id": "a", "power_curve": [9, 1, 9, 1, 9, 1]}]))
    assert len(check_curve_decreases(data, schema)) == 1


# --- DQ011 ----------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["0", "0.0", "-0.5", 0, -3])
def test_non_positive_cooldown_is_caught(schema, value):
    findings = check_cooldown_not_positive(dataset(weapons([one_weapon(cooldown_s=value)])), schema)
    assert [f.rule_id for f in findings] == ["DQ011"]


def test_zero_fails_rather_than_passing_as_in_range(schema):
    """A zero cooldown is an ability that fires every frame, not a fast ability."""
    data = dataset(weapons([one_weapon(cooldown_s="0")]))
    assert check_out_of_range(data, schema) == []
    assert len(check_cooldown_not_positive(data, schema)) == 1


# --- DQ012 ----------------------------------------------------------------------------


def waves_with(drop_table):
    return table("waves", ("id", "drop_table"), [{"id": "w1", "drop_table": drop_table}])


def test_weights_that_do_not_sum_are_caught(schema):
    data = dataset(waves_with([{"item": "a", "weight": 0.7}, {"item": "b", "weight": 0.5}]))
    findings = check_weights_do_not_sum(data, schema)
    assert [f.rule_id for f in findings] == ["DQ012"]
    assert "1.2" in findings[0].message


def test_thirds_pass_within_tolerance(schema):
    """0.333 three times is 0.999 and must not fail: the values are floating point."""
    data = dataset(waves_with([{"item": x, "weight": 1 / 3} for x in ("a", "b", "c")]))
    assert check_weights_do_not_sum(data, schema) == []
