"""Reading the schema that describes one game's tables.

A broken schema is a usage error, not a finding: the tool was pointed at something it
cannot work from, so it exits 2 and checks nothing. A broken *data table* is a finding.
Keeping those two apart is the whole point of having a third exit code.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

TYPES = ("string", "integer", "number", "string_list", "number_list", "weight_table")

DEFAULT_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schemas", "default.json")


class SchemaError(Exception):
    """The schema itself is unusable. Always exit 2."""


@dataclass(frozen=True)
class Column:
    name: str
    type: str
    required: bool = True
    min: float | None = None
    max: float | None = None
    one_of: tuple[str, ...] | None = None
    positive: bool = False
    non_decreasing: bool = False
    references: str | None = None
    weights_sum_to: float | None = None
    tolerance: float = 0.001


@dataclass(frozen=True)
class TableSpec:
    name: str
    file: str
    id_column: str
    columns: Mapping[str, Column]


@dataclass(frozen=True)
class Schema:
    path: str
    tables: Mapping[str, TableSpec]


def _column(table: str, name: str, raw: Any) -> Column:
    if not isinstance(raw, dict):
        raise SchemaError(f"{table}.{name}: column definition must be an object")
    ctype = raw.get("type")
    if ctype not in TYPES:
        raise SchemaError(f"{table}.{name}: type must be one of {', '.join(TYPES)}, got {ctype!r}")
    one_of = raw.get("one_of")
    if one_of is not None:
        if not isinstance(one_of, list) or not one_of:
            raise SchemaError(f"{table}.{name}: one_of must be a non-empty list")
        one_of = tuple(str(v) for v in one_of)
    references = raw.get("references")
    if references is not None and str(references).count(".") != 1:
        raise SchemaError(
            f"{table}.{name}: references must read 'table.column', got {references!r}"
        )
    return Column(
        name=name,
        type=ctype,
        required=bool(raw.get("required", True)),
        min=raw.get("min"),
        max=raw.get("max"),
        one_of=one_of,
        positive=bool(raw.get("positive", False)),
        non_decreasing=bool(raw.get("non_decreasing", False)),
        references=references,
        weights_sum_to=raw.get("weights_sum_to"),
        tolerance=float(raw.get("tolerance", 0.001)),
    )


def load_schema(path: str = DEFAULT_SCHEMA_PATH) -> Schema:
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except FileNotFoundError:
        raise SchemaError(f"no schema at {path}") from None
    except json.JSONDecodeError as err:
        raise SchemaError(f"{path} is not valid JSON: {err}") from None

    tables_raw = raw.get("tables")
    if not isinstance(tables_raw, dict) or not tables_raw:
        raise SchemaError(f"{path}: 'tables' must be a non-empty object")

    tables: dict[str, TableSpec] = {}
    for name, spec in tables_raw.items():
        if not isinstance(spec, dict):
            raise SchemaError(f"{name}: table definition must be an object")
        columns_raw = spec.get("columns")
        if not isinstance(columns_raw, dict) or not columns_raw:
            raise SchemaError(f"{name}: 'columns' must be a non-empty object")
        columns = {cn: _column(name, cn, cr) for cn, cr in columns_raw.items()}
        id_column = spec.get("id", "id")
        if id_column not in columns:
            raise SchemaError(f"{name}: id column {id_column!r} is not a declared column")
        file_name = spec.get("file")
        if not file_name:
            raise SchemaError(f"{name}: 'file' is required")
        tables[name] = TableSpec(
            name=name, file=str(file_name), id_column=str(id_column), columns=columns
        )

    # A reference must point at a column that exists, or the reference check would be
    # comparing against an empty set and passing everything.
    for table in tables.values():
        for column in table.columns.values():
            if column.references is None:
                continue
            target_table, target_column = column.references.split(".")
            if target_table not in tables:
                raise SchemaError(
                    f"{table.name}.{column.name}: references unknown table {target_table!r}"
                )
            if target_column not in tables[target_table].columns:
                raise SchemaError(
                    f"{table.name}.{column.name}: references unknown column "
                    f"{target_table}.{target_column}"
                )

    return Schema(path=path, tables=tables)
