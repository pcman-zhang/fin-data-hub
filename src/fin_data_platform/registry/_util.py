"""注册表内部值解析工具（日期/代码规整与区间判定）。"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Protocol

import pandas as pd

#: SCD2 默认起始（无更早信息时的知识边界）
EPOCH = date(1990, 1, 1)


class _Validity(Protocol):
    @property
    def valid_from(self) -> date | None: ...

    @property
    def valid_to(self) -> date | None: ...


def to_date(value: Any) -> date | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        parsed = pd.Timestamp(value)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(parsed) else parsed.date()


def clean_code(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return None
    text = str(value).strip()
    return text or None


def now() -> datetime:
    return datetime.now(UTC)


def covers(record: _Validity, target: date | None) -> bool:
    """SCD2 闭区间覆盖判定；``target=None`` 表示当前（仅 open 行）。"""
    if target is None:
        return record.valid_to is None
    return (
        record.valid_from is not None
        and record.valid_from <= target
        and (record.valid_to is None or target <= record.valid_to)
    )
