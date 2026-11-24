"""Values passed between detection and reporting.

Everything here is frozen. A check receives a Dataset and returns Findings; it never
prints, never exits, and never mutates what it was given. That is what lets a test assert
on what a check found without capturing stdout or spawning a process, and it is the same
split the other repositories in this set use.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Row:
    """One record. `number` is 1-based and counts data rows, not file lines.

    For a CSV the header is not a data row, so row 1 is the first record. A reader
    looking at the file in a spreadsheet counts the same way.
    """

    number: int
    values: Mapping[str, Any]


@dataclass(frozen=True)
class Table:
    name: str
    path: str
    columns: tuple[str, ...]
    rows: tuple[Row, ...]


@dataclass(frozen=True)
class Dataset:
    """Tables that loaded, plus the ones that did not.

    A file that cannot be parsed is a defect in the data, not a failure of the tool, so
    it is carried here and reported as a finding rather than raised.
    """

    root: str
    tables: Mapping[str, Table]
    unreadable: Mapping[str, str]

    def table(self, name: str) -> Table | None:
        return self.tables.get(name)


@dataclass(frozen=True)
class Finding:
    """One violation of one rule, at one place.

    `where` is human-addressed: "row 3, column damage". It exists to be pasted into a
    conversation with whoever owns the spreadsheet, so it names the row the way the
    spreadsheet does.
    """

    rule_id: str
    table: str
    where: str
    message: str

    def line(self) -> str:
        return f"{self.rule_id}  {self.table}  {self.where}  {self.message}"
