"""引用注册表领域模型（doc-10 §3.3 冻结稿修订）。

- 分类面：``entity_type``（本体）/ ``entity_class``（产品细分）/ ``market``（市场面），
  替代旧 ``sec_type``；交易状态不在注册表（由 ``listing_lifecycle`` 数据集承载）；
- :class:`EntityRecord`：实体 SCD2 行（身份 + 属性 + 生命周期）；
- :class:`RelationRecord` / :class:`RelationTypeRecord`：关系（单向存储 + 词表驱动双向查询）；
- :class:`ExternalIdRecord`：外部标识（isin/figi/…，不含 ticker）；
- :class:`LifecycleRecord`：交易状态数据集行（PIT Universe 推导输入）。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any


class EntityType(StrEnum):
    """实体本体（粗分类；doc-10 §3.3）。"""

    ISSUER = "issuer"
    EQUITY = "equity"
    ETF = "etf"
    LOF = "lof"
    FUND = "fund"
    INDEX = "index"
    BOND = "bond"
    FUTURE = "future"
    OPTION = "option"
    RATE = "rate"
    FX = "fx"
    MACRO = "macro"
    BASKET = "basket"


class EntityClass(StrEnum):
    """产品细分（``entity_type`` 之下的 ``entity_class``）。"""

    BOND_ETF = "bond_etf"
    MONEY_ETF = "money_etf"
    REIT = "reit"
    EQUITY_INDEX = "equity_index"
    COMMODITY_FUTURE = "commodity_future"


class Market(StrEnum):
    """市场面。"""

    CN = "cn"
    HK = "hk"
    US = "us"
    GLOBAL = "global"


class SocialStatus(StrEnum):
    """社会实体状态（issuer 专用）。"""

    OPERATING = "operating"
    DEFUNCT = "defunct"
    RESTRUCTURING = "restructuring"


class IdType(StrEnum):
    """外部标识类型（不含 ticker）。"""

    ISIN = "isin"
    FIGI = "figi"
    CUSIP = "cusip"
    SEDOL = "sedol"
    LEI = "lei"
    USCC = "uscc"
    OTHER = "other"


class LifecycleStatus(StrEnum):
    """交易状态（``cn_equity.listing_lifecycle``）。"""

    LISTED = "listed"
    SUSPENDED = "suspended"
    DELISTED = "delisted"


@dataclass(frozen=True, slots=True)
class EntityRecord:
    entity_id: int
    entity_type: str  # EntityType
    code: str  # canonical（WindCode 风格）
    name: str
    entity_class: str | None = None  # EntityClass（产品细分；可缺省）
    market: str | None = None  # Market
    currency: str | None = None
    exchange: str | None = None
    frequency: str | None = None  # series 使用
    unit: str | None = None  # series 使用
    algorithm_id: str | None = None  # basket 使用
    social_status: str | None = None  # issuer 专用（SocialStatus）
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
class RelationRecord:
    """实体关系（单向存储；双向查询由词表 ``inverse_relation`` 驱动）。"""

    entity_id: int
    related_id: int
    relation_type: str
    valid_from: date | None = None
    valid_to: date | None = None
    knowledge_time: datetime | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class RelationTypeRecord:
    """关系词表条目（``ref.relation_type_dict``；新增关系词必须先登记）。"""

    relation_type: str
    inverse_relation: str
    description: str = ""
    valid_from: date | None = None
    valid_to: date | None = None
    knowledge_time: datetime | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class ExternalIdRecord:
    """外部标识（不含 ticker；ticker/canonical code 归代码履历）。"""

    entity_id: int
    id_type: str  # IdType
    id_value: str
    valid_from: date | None = None
    valid_to: date | None = None
    knowledge_time: datetime | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class LifecycleRecord:
    """交易状态数据集行（``cn_equity.listing_lifecycle``；PIT Universe 输入）。"""

    entity_id: int
    status: str  # LifecycleStatus
    start_date: date | None = None
    end_date: date | None = None
    knowledge_time: datetime | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class BuildStats:
    registered: int = 0
    updated: int = 0
    attributes: int = 0
    skipped: int = 0
