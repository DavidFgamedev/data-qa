"""DQ001 unreadable-file, DQ002 missing-table, DQ003 missing-column, DQ004 unknown-column.

Shape, before any value is looked at. These run first because everything after them
assumes a table that parsed and has the columns it claims.
"""

from __future__ import annotations

from ..model import Dataset, Finding
from ..schema import Schema


def check_unreadable_file(dataset: Dataset, schema: Schema) -> list[Finding]:
    findings = []
    for name in sorted(dataset.unreadable):
        findings.append(
            Finding(
                rule_id="DQ001",
                table=name,
                where=schema.tables[name].file,
                message=f"could not be parsed: {dataset.unreadable[name]}",
            )
        )
    return findings


def check_missing_table(dataset: Dataset, schema: Schema) -> list[Finding]:
    findings = []
    for name, spec in schema.tables.items():
        if name in dataset.tables or name in dataset.unreadable:
            continue
        findings.append(
            Finding(
                rule_id="DQ002",
                table=name,
                where=spec.file,
                message="declared by the schema and not present in the data directory",
            )
        )
    return sorted(findings, key=lambda f: f.table)


def check_missing_column(dataset: Dataset, schema: Schema) -> list[Finding]:
    findings = []
    for name, spec in schema.tables.items():
        table = dataset.table(name)
        if table is None:
            continue
        for column in spec.columns.values():
            if not column.required or column.name in table.columns:
                continue
            findings.append(
                Finding(
                    rule_id="DQ003",
                    table=name,
                    where=f"column {column.name}",
                    message="required by the schema and absent from the table",
                )
            )
    return findings


def check_unknown_column(dataset: Dataset, schema: Schema) -> list[Finding]:
    findings = []
    for name, spec in schema.tables.items():
        table = dataset.table(name)
        if table is None:
            continue
        for column in table.columns:
            if column in spec.columns:
                continue
            findings.append(
                Finding(
                    rule_id="DQ004",
                    table=name,
                    where=f"column {column}",
                    message="present in the table and not declared by the schema",
                )
            )
    return findings
