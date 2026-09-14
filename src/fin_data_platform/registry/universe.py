"""PIT Universe 推导（doc-10 §3.3）：由交易状态数据集（``listing_lifecycle``）推导。

交易状态不在注册表：universe 的权威来源是数据集行（PIT 区间 + 知识时间），
注册表只提供身份属性（as-of SCD2）。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace
from typing import Any

from fin_data_platform.registry._util import EPOCH, to_date
from fin_data_platform.registry.models import (
    EntityRecord,
    LifecycleRecord,
    LifecycleStatus,
)
from fin_data_platform.registry.service import EntityRegistry

#: 在市状态（停牌仍属 universe；退市不在）
_IN_UNIVERSE = frozenset({LifecycleStatus.LISTED, LifecycleStatus.SUSPENDED})


def _as_lifecycle(raw: LifecycleRecord | Mapping[str, Any]) -> LifecycleRecord:
    if isinstance(raw, LifecycleRecord):
        return replace(
            raw,
            start_date=to_date(raw.start_date),
            end_date=to_date(raw.end_date),
        )
    return LifecycleRecord(
        entity_id=int(raw["entity_id"]),
        status=str(raw["status"]),
        start_date=to_date(raw.get("start_date")),
        end_date=to_date(raw.get("end_date")),
        knowledge_time=raw.get("knowledge_time"),
        version=int(raw.get("version") or 1),
    )


def _status(record: LifecycleRecord) -> LifecycleStatus:
    try:
        return LifecycleStatus(record.status)
    except ValueError as exc:
        raise ValueError(f"listing_lifecycle status 非法: {record.status!r}") from exc


def universe(
    registry: EntityRegistry,
    lifecycle: Iterable[LifecycleRecord | Mapping[str, Any]],
    as_of: Any,
    *,
    entity_type: str | None = None,
    market: str | None = None,
) -> list[EntityRecord]:
    """as-of PIT Universe：交易状态行覆盖 ``as_of`` 且状态在市，实体身份 as-of 有效。

    - 生命周期区间语义：``start_date <= as_of <= end_date``（闭区间，``None`` 表示至今）；
    - 同一实体多行覆盖时取 ``(start_date, version)`` 最大者（append-only 修订）；
    - 无生命周期记录的实体不进入 universe（数据不足，防前视）。
    """
    target = to_date(as_of)
    if target is None:
        raise ValueError("as_of 不能为空")
    best: dict[int, LifecycleRecord] = {}
    for raw in lifecycle:
        row = _as_lifecycle(raw)
        start = row.start_date or EPOCH
        if start > target:
            continue
        if row.end_date is not None and target > row.end_date:
            continue
        current = best.get(row.entity_id)
        if current is None or (
            start,
            row.version,
        ) > (
            current.start_date or EPOCH,
            current.version,
        ):
            best[row.entity_id] = row
    result: list[EntityRecord] = []
    for entity_id, row in sorted(best.items()):
        if _status(row) not in _IN_UNIVERSE:
            continue
        record = registry.entity(entity_id, as_of=target)
        if record is None:
            continue
        if entity_type and record.entity_type != entity_type:
            continue
        if market and record.market != market:
            continue
        result.append(record)
    return result
