"""Turning cell values into the type a column declares.

CSV has no types: every value arrives as text, so `12` and `"12"` are the same cell and
the type check is a coercion. JSON has types and they are taken as given. One function
per declared type, each returning `None` when the value is not of that type, so a caller
never has to catch.

`None` means "not this type". It never means "absent": absence is handled before these
are called, by the required-column check.
"""

from __future__ import annotations

from typing import Any

TRUE_INTEGER = (int,)


def as_integer(value: Any) -> int | None:
    # bool is a subclass of int in Python, and `True` in a damage column is a defect,
    # not the number one.
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        text = value.strip()
        try:
            return int(text)
        except ValueError:
            return None
    return None


def _finite(number: float) -> float | None:
    """NaN and the infinities are not usable values, whichever path they arrived by.

    This guard was on the string path only, and the gap was real rather than theoretical:
    Python's `json` module parses the bare literals `NaN`, `Infinity` and `-Infinity` by
    default, so a JSON table could carry a NaN into a damage column. It would then pass
    every range check, because NaN compares false against both the minimum and the
    maximum and the check asks only whether it is outside them.
    """
    if number != number:  # NaN is the only value unequal to itself
        return None
    if number in (float("inf"), float("-inf")):
        return None
    return number


def as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return _finite(float(value))
    if isinstance(value, str):
        text = value.strip()
        try:
            number = float(text)
        except ValueError:
            return None
        return _finite(number)
    return None


def as_string(value: Any) -> str | None:
    if isinstance(value, (bool, list, dict)):
        return None
    if value is None:
        return None
    return str(value)


def as_string_list(value: Any) -> list[str] | None:
    if isinstance(value, list):
        out = []
        for item in value:
            text = as_string(item)
            if text is None:
                return None
            out.append(text)
        return out
    if isinstance(value, str):
        # A CSV cell holding a list is written pipe-separated, because a comma is the
        # delimiter and quoting a comma-separated list inside a CSV is how these files
        # get corrupted by the next tool that opens them.
        text = value.strip()
        if not text:
            return []
        return [part.strip() for part in text.split("|")]
    return None


def as_number_list(value: Any) -> list[float] | None:
    if isinstance(value, list):
        out = []
        for item in value:
            number = as_number(item)
            if number is None:
                return None
            out.append(number)
        return out
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        out = []
        for part in text.split("|"):
            number = as_number(part)
            if number is None:
                return None
            out.append(number)
        return out
    return None


def as_weight_table(value: Any) -> list[tuple[str, float]] | None:
    """A list of {item, weight} objects, in declaration order."""
    if not isinstance(value, list):
        return None
    out: list[tuple[str, float]] = []
    for entry in value:
        if not isinstance(entry, dict):
            return None
        item = as_string(entry.get("item"))
        weight = as_number(entry.get("weight"))
        if item is None or weight is None:
            return None
        out.append((item, weight))
    return out


COERCERS = {
    "string": as_string,
    "integer": as_integer,
    "number": as_number,
    "string_list": as_string_list,
    "number_list": as_number_list,
    "weight_table": as_weight_table,
}


def coerce(value: Any, declared_type: str) -> Any:
    return COERCERS[declared_type](value)
