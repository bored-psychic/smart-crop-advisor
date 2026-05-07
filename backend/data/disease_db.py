"""Backward-compatible re-export. Source of truth is core/disease_db.py."""

from core.disease_db import DISEASE_DB  # noqa: F401

__all__ = ["DISEASE_DB"]
