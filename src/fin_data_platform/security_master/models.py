"""Security Master 领域模型（doc-10 §3.3）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class SecurityRecord:
    security_id: int
    canonical_code: str
    sec_type: str
    name: str
    currency: str | None = None
    list_date: date | None = None
    delist_date: date | None = None
    status: str = "L"
    valid_from: date | None = None
    valid_to: date | None = None
    knowledge_time: datetime | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class AliasRecord:
    security_id: int
    source: str
    source_code: str
    valid_from: date | None = None
    valid_to: date | None = None
    knowledge_time: datetime | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class StatusInterval:
    security_id: int
    status: str  # L 上市 / P 暂停 / D 退市
    start_date: date
    end_date: date | None = None
    knowledge_time: datetime | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class AttributeInterval:
    security_id: int
    attribute: str  # name / st_type / sec_type ...
    value: str
    start_date: date
    end_date: date | None = None  # 闭区间终点（None=至今）
    ann_date: date | None = None  # 官方发布时间（publish_time）
    knowledge_time: datetime | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class BuildStats:
    registered: int = 0
    updated: int = 0
    aliases: int = 0
    attributes: int = 0
    skipped: int = 0
