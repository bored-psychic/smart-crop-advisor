"""
core/utils.py — Translation entry point.

Re-exports T() and activate() from core.language so callers can import from
either module. The BUNDLES dict lives in language.py; this file is intentionally
thin.
"""
from core.language import T, activate, LANGUAGES, BUNDLES  # noqa: F401

__all__ = ["T", "activate", "LANGUAGES", "BUNDLES"]
