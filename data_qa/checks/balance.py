"""DQ010 curve-decreases, DQ011 cooldown-not-positive, DQ012 weights-do-not-sum.

The invariants that are not type errors and not range errors. Every value here is
individually legal; what fails is the relationship between values, which is why a schema
validator alone does not catch any of them.
"""

from __future__ import annotations

from ..coerce import coerce
from ..model import Dataset, Finding
from ..schema import Schema


def check_curve_decreases(dataset: Dataset, schema: Schema) -> list[Finding]:
    findings = []
    for name, spec in schema.tables.items():
        table = dataset.table(name)
        if table is None:
            continue
        for column in spec.columns.values():
            if not column.non_decreasing or column.name not in table.columns:
                continue
            for row in table.rows:
                values = coerce(row.values.get(column.name), column.type)
                if not values:
                    continue
                for index in range(1, len(values)):
                    if values[index] >= values[index - 1]:
                        continue
                    findings.append(
                        Finding(
                            rule_id="DQ010",
                            table=name,
                            where=f"row {row.number}, column {column.name}",
                            message=(
                                f"level {index + 1} is {values[index]}, below level "
                                f"{index} at {values[index - 1]}"
                            ),
                        )
                    )
                    break  # one finding per curve: the first reversal is the report
    return findings


def check_cooldown_not_positive(dataset: Dataset, schema: Schema) -> list[Finding]:
    findings = []
    for name, spec in schema.tables.items():
        table = dataset.table(name)
        if table is None:
            continue
        for column in spec.columns.values():
            if not column.positive or column.name not in table.columns:
                continue
            for row in table.rows:
                value = coerce(row.values.get(column.name), column.type)
                if value is None or not isinstance(value, (int, float)):
                    continue
                if value > 0:
                    continue
                findings.append(
                    Finding(
                        rule_id="DQ011",
                        table=name,
                        where=f"row {row.number}, column {column.name}",
                        message=f"{value} is not positive",
                    )
                )
    return findings


def check_weights_do_not_sum(dataset: Dataset, schema: Schema) -> list[Finding]:
    findings = []
    for name, spec in schema.tables.items():
        table = dataset.table(name)
        if table is None:
            continue
        for column in spec.columns.values():
            if column.weights_sum_to is None or column.name not in table.columns:
                continue
            for row in table.rows:
                entries = coerce(row.values.get(column.name), column.type)
                if not entries:
                    continue
                total = sum(weight for _item, weight in entries)
                if abs(total - column.weights_sum_to) <= column.tolerance:
                    continue
                findings.append(
                    Finding(
                        rule_id="DQ012",
                        table=name,
                        where=f"row {row.number}, column {column.name}",
                        message=(
                            f"weights sum to {total:g}, not {column.weights_sum_to:g} "
                            f"(tolerance {column.tolerance:g})"
                        ),
                    )
                )
    return findings
