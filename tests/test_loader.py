"""Loading, and the defects that must survive loading rather than crash it."""

from __future__ import annotations

from data_qa.loader import load_dataset


def write(tmp_path, name, text):
    (tmp_path / name).write_text(text, encoding="utf-8")


def test_malformed_json_is_carried_not_raised(tmp_path, schema):
    write(tmp_path, "abilities.json", '[{"id": "a",')
    dataset = load_dataset(str(tmp_path), schema)
    assert "abilities" in dataset.unreadable
    assert "abilities" not in dataset.tables


def test_json_that_is_not_an_array_is_carried_not_raised(tmp_path, schema):
    write(tmp_path, "effects.json", '{"id": "eff_burn"}')
    dataset = load_dataset(str(tmp_path), schema)
    assert "expected a JSON array" in dataset.unreadable["effects"]


def test_a_csv_with_no_header_is_carried_not_raised(tmp_path, schema):
    write(tmp_path, "weapons.csv", "")
    dataset = load_dataset(str(tmp_path), schema)
    assert "no header row" in dataset.unreadable["weapons"]


def test_rows_are_numbered_from_one_ignoring_the_header(tmp_path, schema):
    write(tmp_path, "weapons.csv", "id,name\nwpn_a,A\nwpn_b,B\n")
    dataset = load_dataset(str(tmp_path), schema)
    assert [row.number for row in dataset.tables["weapons"].rows] == [1, 2]


def test_json_columns_are_the_union_in_first_seen_order(tmp_path, schema):
    write(tmp_path, "effects.json", '[{"id":"a","kind":"x"},{"id":"b","name":"B"}]')
    dataset = load_dataset(str(tmp_path), schema)
    assert dataset.tables["effects"].columns == ("id", "kind", "name")


def test_an_absent_file_is_neither_loaded_nor_unreadable(tmp_path, schema):
    dataset = load_dataset(str(tmp_path), schema)
    assert dataset.tables == {}
    assert dataset.unreadable == {}


def test_a_nan_in_a_json_table_is_reported_as_a_type_error(tmp_path, schema):
    """Python's json parses the bare literal `NaN`, and NaN passes a range check by
    comparing false against both bounds. It must be caught as a type error instead."""
    from data_qa.checks.values import check_out_of_range, check_wrong_type

    write(tmp_path, "abilities.json", '[{"id": "a", "cooldown_s": NaN}]')
    dataset = load_dataset(str(tmp_path), schema)
    assert "abilities" not in dataset.unreadable  # it parses; that is the problem
    assert [f.rule_id for f in check_wrong_type(dataset, schema)] == ["DQ005"]
    assert check_out_of_range(dataset, schema) == []
