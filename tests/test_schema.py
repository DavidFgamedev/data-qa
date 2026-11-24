"""Rejecting a schema the tool cannot work from.

Every case here is exit 2 rather than a finding. The distinction is the point: a defect
in the data is something to report, a defect in the schema means nothing was checked.
"""

from __future__ import annotations

import json

import pytest

from data_qa.schema import DEFAULT_SCHEMA_PATH, SchemaError, load_schema


def write(tmp_path, payload):
    path = tmp_path / "schema.json"
    path.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
    return str(path)


def test_the_shipped_schema_loads():
    schema = load_schema(DEFAULT_SCHEMA_PATH)
    assert set(schema.tables) == {"weapons", "enemies", "effects", "abilities", "waves"}


def test_an_absent_schema_is_a_schema_error(tmp_path):
    with pytest.raises(SchemaError, match="no schema at"):
        load_schema(str(tmp_path / "nope.json"))


def test_malformed_json_is_a_schema_error(tmp_path):
    with pytest.raises(SchemaError, match="not valid JSON"):
        load_schema(write(tmp_path, "{ nope"))


def test_tables_must_be_a_non_empty_object(tmp_path):
    with pytest.raises(SchemaError, match="non-empty object"):
        load_schema(write(tmp_path, {"tables": {}}))


def test_a_table_must_be_an_object(tmp_path):
    with pytest.raises(SchemaError, match="must be an object"):
        load_schema(write(tmp_path, {"tables": {"weapons": "nope"}}))


def test_columns_must_be_a_non_empty_object(tmp_path):
    with pytest.raises(SchemaError, match="'columns' must be"):
        load_schema(write(tmp_path, {"tables": {"weapons": {"file": "w.csv", "columns": {}}}}))


def test_a_column_must_be_an_object(tmp_path):
    payload = {"tables": {"weapons": {"file": "w.csv", "columns": {"id": "string"}}}}
    with pytest.raises(SchemaError, match="column definition must be an object"):
        load_schema(write(tmp_path, payload))


def test_an_unknown_column_type_is_rejected(tmp_path):
    payload = {"tables": {"weapons": {"file": "w.csv", "columns": {"id": {"type": "colour"}}}}}
    with pytest.raises(SchemaError, match="type must be one of"):
        load_schema(write(tmp_path, payload))


def test_one_of_must_be_a_non_empty_list(tmp_path):
    payload = {
        "tables": {
            "weapons": {
                "file": "w.csv",
                "columns": {"id": {"type": "string", "one_of": []}},
            }
        }
    }
    with pytest.raises(SchemaError, match="one_of must be"):
        load_schema(write(tmp_path, payload))


def test_file_is_required(tmp_path):
    payload = {"tables": {"weapons": {"columns": {"id": {"type": "string"}}}}}
    with pytest.raises(SchemaError, match="'file' is required"):
        load_schema(write(tmp_path, payload))


def test_the_id_column_must_be_declared(tmp_path):
    payload = {
        "tables": {"weapons": {"file": "w.csv", "id": "key", "columns": {"id": {"type": "string"}}}}
    }
    with pytest.raises(SchemaError, match="is not a declared column"):
        load_schema(write(tmp_path, payload))


def test_a_reference_must_read_table_dot_column(tmp_path):
    payload = {
        "tables": {
            "waves": {
                "file": "w.json",
                "columns": {"id": {"type": "string", "references": "enemies"}},
            }
        }
    }
    with pytest.raises(SchemaError, match="must read 'table.column'"):
        load_schema(write(tmp_path, payload))


def test_a_reference_to_an_unknown_table_is_rejected(tmp_path):
    """Otherwise the reference check compares against an empty set and passes everything."""
    payload = {
        "tables": {
            "waves": {
                "file": "w.json",
                "columns": {"id": {"type": "string", "references": "goblins.id"}},
            }
        }
    }
    with pytest.raises(SchemaError, match="unknown table"):
        load_schema(write(tmp_path, payload))


def test_a_reference_to_an_unknown_column_is_rejected(tmp_path):
    payload = {
        "tables": {
            "waves": {
                "file": "w.json",
                "columns": {"id": {"type": "string", "references": "waves.nope"}},
            }
        }
    }
    with pytest.raises(SchemaError, match="unknown column"):
        load_schema(write(tmp_path, payload))
