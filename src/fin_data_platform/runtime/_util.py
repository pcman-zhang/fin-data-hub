"""Runtime 内部工具：统一使用 naive UTC（SQLite / PostgreSQL 跨方言一致）。"""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """naive UTC 当前时间（存储层时间列统一口径）。"""
    return datetime.now(UTC).replace(tzinfo=None)
