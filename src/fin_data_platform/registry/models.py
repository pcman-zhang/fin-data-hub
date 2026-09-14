"""引用注册表领域模型（doc-10 §3.3 冻结稿修订）。

- :class:`EntityRecord`：实体 SCD2 行（身份 + 属性 + 生命周期）；
- :class:`CodeHistoryRecord`：canonical 代码履历（替代多源别名表）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class EntityRecord:
    entity_id: int
    entity_type: str  # instrument / series / basket
    code: str  # canonical（WindCode 风格）
    name: str
    status: str = "L"  # instrument: L/P/D；series/basket: active/paused
    sec_type: str | None = None
    currency: str | None = None
    exchange: str | None = None
    frequency: str | None = None
    unit: str | None = None
    list_date: date | None = None
    delist_date: date | None = None
    algorithm_id: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    knowledge_time: datetime | None = None
    version: int = 1
    attrs: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class CodeHistoryRecord:
    entity_id: int
    code: str
    valid_from: date | None = None
    valid_to: date | None = None
    knowledge_time: datetime | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class BuildStats:
    registered: int = 0
    updated: int = 0
    attributes: int = 0
    skipped: int = 0
