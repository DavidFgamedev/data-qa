"""The command line. Printing and exit codes live here and nowhere else.

The exit-code contract:

    0   every declared table loaded and every rule held
    1   the data has findings
    2   the tool could not run: bad arguments, missing directory, unusable schema

The third code is the one that matters. A tool that cannot run must never be mistaken for
a clean bill of health, and a pipeline that treats "could not start" as "passed" is the
way a gate quietly stops being a gate.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

from .checks import run_all
from .docs import render_rules_markdown
from .loader import load_dataset
from .report import render_json, render_text
from .schema import DEFAULT_SCHEMA_PATH, SchemaError, load_schema

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2


class _Parser(argparse.ArgumentParser):
    """argparse exits 2 on a parse error, which is already the contract. This makes the
    same true of `--help` on no command, and keeps the message on stderr."""

    def error(self, message: str) -> None:  # pragma: no cover - argparse internals
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="data-qa",
        description="Validate gameplay data tables: schema, ranges, references, balance.",
    )
    sub = parser.add_subparsers(dest="command")

    check = sub.add_parser("check", help="check a directory of data tables")
    check.add_argument("data_dir", help="directory holding the table files")
    check.add_argument(
        "--schema",
        default=DEFAULT_SCHEMA_PATH,
        help="schema describing the tables (default: the example schema that ships here)",
    )
    check.add_argument("--format", choices=("text", "json"), default="text", help="output format")

    sub.add_parser("rules", help="print the rule table")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help(sys.stderr)
        return EXIT_USAGE

    if args.command == "rules":
        print(render_rules_markdown())
        return EXIT_CLEAN

    if not os.path.isdir(args.data_dir):
        print(f"data-qa: not a directory: {args.data_dir}", file=sys.stderr)
        return EXIT_USAGE

    try:
        schema = load_schema(args.schema)
    except SchemaError as err:
        print(f"data-qa: {err}", file=sys.stderr)
        return EXIT_USAGE

    dataset = load_dataset(args.data_dir, schema)
    findings = run_all(dataset, schema)

    if args.format == "json":
        print(render_json(findings, dataset.root, len(dataset.tables)))
    else:
        print(render_text(findings, dataset.root, len(dataset.tables)))

    return EXIT_FINDINGS if findings else EXIT_CLEAN


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
