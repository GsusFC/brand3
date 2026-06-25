"""Thin SQLite access helpers for web requests and scan jobs."""

from __future__ import annotations

from src.config import BRAND3_DB_PATH  # public compatibility symbol for legacy callers/tests

from web.storage_impl import *  # noqa: F401,F403
