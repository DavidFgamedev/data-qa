"""Validation for gameplay data tables.

Detection is a set of pure functions over a loaded dataset; reporting and exit codes live
in the CLI. Nothing in this package prints or exits.
"""

from .model import Dataset, Finding, Row, Table
from .rules import RULES, Rule, rule

__version__ = "1.0.0"
__all__ = ["Dataset", "Finding", "Row", "Table", "RULES", "Rule", "rule", "__version__"]
