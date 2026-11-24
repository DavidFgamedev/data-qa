"""DQ005 wrong-type, DQ006 out-of-range.

The order matters and is load-bearing: a value that fails its type check is skipped by
the range check rather than reported by both. One wrong cell should produce one finding,
or a single typo in a large table produces a wall of output and the real defects in it
stop being visible.
"""

from __future__ import annotations

from ..coerce import coerce
from ..model import Dataset, Finding
from ..schema import Column, Schema


def _absent(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def check_wrong_type(dataset: Dataset, schema: Schema) -> list[Finding]:
    findings = []
    for name, spec in schema.tables.items():
        table = dataset.table(name)
        if table is None:
            continue
        for column in spec.columns.values():
            if column.name not in table.columns:
                continue  # DQ003 reports it; this check has nothing to read
            for row in table.rows:
                value = row.values.get(column.name)
                if _absent(value):
                    continue  # blank ids are DQ008; blank elsewhere is not typed
                if coerce(value, column.type) is None:
                    findings.append(
                        Finding(
                            rule_id="DQ005",
                            table=name,
                            where=f"row {row.number}, column {column.name}",
                            message=f"{value!r} is not {column.type}",
                        )
                    )
    return findings


def _range_findings(
    table_name: str, column: Column, row_number: int, value: object
) -> list[Finding]:
    findings = []
    where = f"row {row_number}, column {column.name}"
    if column.one_of is not None and str(value) not in column.one_of:
        findings.append(
            Finding(
                rule_id="DQ006",
                table=table_name,
                where=where,
                message=f"{value!r} is not one of {', '.join(column.one_of)}",
            )
        )
        return findings
    if isinstance(value, (int, float)):
        if column.min is not None and value < column.min:
            findings.append(
                Finding(
                    rule_id="DQ006",
                    table=table_name,
                    where=where,
                    message=f"{value} is below the minimum of {column.min}",
                )
            )
        elif column.max is not None and value > column.max:
            findings.append(
                Finding(
                    rule_id="DQ006",
                    table=table_name,
                    where=where,
                    message=f"{value} is above the maximum of {column.max}",
                )
            )
    return findings


def check_out_of_range(dataset: Dataset, schema: Schema) -> list[Finding]:
    findings = []
    for name, spec in schema.tables.items():
        table = dataset.table(name)
        if table is None:
            continue
        for column in spec.columns.values():
            if column.name not in table.columns:
                continue
            has_bounds = (
                column.min is not None or column.max is not None or column.one_of is not None
            )
            if not has_bounds:
                continue
            for row in table.rows:
                raw = row.values.get(column.name)
                if _absent(raw):
                    continue
                value = coerce(raw, column.type)
                if value is None:
                    continue  # DQ005 owns this cell
                findings.extend(_range_findings(name, column, row.number, value))
    return findings
