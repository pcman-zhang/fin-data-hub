"""引用注册表服务：注册/刷新、代码解析、as-of 宇宙与属性还原（doc-10 §3.3）。

存储落地（DDL/迁移/持久化仓储）由 TASK-3.3 接入；本模块为存储无关核心逻辑。
区间语义：SCD2 行 ``valid_from <= as_of <= valid_to``（闭区间，``valid_to=None`` 表示至今）；
``universe`` 以生命周期过滤：``list_date <= as_of < delist_date``（退市日不含）。
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pandas as pd

from fin_data_hub.errors import UnsupportedCapability
from fin_data_platform.registry.models import (
    BuildStats,
    CodeHistoryRecord,
    EntityRecord,
)
from fin_data_platform.registry.repository import (
    EntityRegistryRepository,
    InMemoryEntityRegistryRepository,
)

_EPOCH = date(1990, 1, 1)


def _to_date(value: Any) -> date | None:
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


def _clean_code(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return None
    text = str(value).strip()
    return text or None


def _now() -> datetime:
    return datetime.now(UTC)


def _bump(
    stats: BuildStats,
    *,
    registered: int = 0,
    updated: int = 0,
    attributes: int = 0,
    skipped: int = 0,
) -> BuildStats:
    return BuildStats(
        registered=stats.registered + registered,
        updated=stats.updated + updated,
        attributes=stats.attributes + attributes,
        skipped=stats.skipped + skipped,
    )


class EntityRegistry:
    """实体身份与 PIT 履历（instrument / series / basket）。"""

    def __init__(self, repository: EntityRegistryRepository | None = None) -> None:
        self._repo = repository or InMemoryEntityRegistryRepository()

    # ------------------------------------------------------------ 注册/刷新
    def register(self, **kwargs: Any) -> EntityRecord:
        """注册或刷新实体（按 canonical code 幂等；变化以 SCD2 新行表达）。"""
        record, _, _ = self._register_or_refresh(**kwargs)
        return record

    def _register_or_refresh(
        self, **kwargs: Any
    ) -> tuple[EntityRecord, bool, bool]:
        """返回 ``(record, created, updated)``。"""
        entity_id = self.resolve(str(kwargs["code"]))
        if entity_id is None:
            return self._create(**kwargs), True, False
        updated = self._refresh(entity_id, **kwargs)
        return self._current_row(entity_id), False, updated

    def _create(self, **kwargs: Any) -> EntityRecord:
        list_date = _to_date(kwargs.get("list_date"))
        delist_date = _to_date(kwargs.get("delist_date"))
        status = str(kwargs.get("status") or "L")
        base = EntityRecord(
            entity_id=self._repo.next_entity_id(),
            entity_type=str(kwargs.get("entity_type") or "instrument"),
            code=str(kwargs["code"]),
            name=str(kwargs.get("name") or ""),
            status=status,
            sec_type=kwargs.get("sec_type"),
            currency=kwargs.get("currency"),
            exchange=kwargs.get("exchange"),
            frequency=kwargs.get("frequency"),
            unit=kwargs.get("unit"),
            list_date=list_date,
            delist_date=delist_date,
            algorithm_id=kwargs.get("algorithm_id"),
            valid_from=list_date or _EPOCH,
            knowledge_time=_now(),
            attrs=kwargs.get("attrs"),
        )
        self._repo.append_code(
            CodeHistoryRecord(
                entity_id=base.entity_id,
                code=base.code,
                valid_from=base.valid_from,
                knowledge_time=base.knowledge_time,
            )
        )
        if delist_date is not None and status == "D":
            # 初始即退市：拆为 L 区间 + D 区间（SCD2）
            listed = replace(
                base,
                status="L",
                valid_to=delist_date - timedelta(days=1),
            )
            self._repo.append_entity(listed)
            delisted = replace(
                base,
                status="D",
                valid_from=delist_date,
            )
            self._repo.append_entity(delisted)
            return delisted
        self._repo.append_entity(base)
        return base

    def _refresh(self, entity_id: int, **kwargs: Any) -> bool:
        current = self._current_row(entity_id)
        name = str(kwargs.get("name") or "")
        status = str(kwargs.get("status") or current.status)
        list_date = _to_date(kwargs.get("list_date"))
        delist_date = _to_date(kwargs.get("delist_date"))
        updated = current
        if list_date is not None and current.list_date is None:
            updated = replace(updated, list_date=list_date)
            if current.valid_from == _EPOCH:
                updated = replace(updated, valid_from=list_date)
        if name and name != current.name:
            updated = replace(updated, name=name)
        if delist_date is not None and current.delist_date is None:
            self._close_row(current, delist_date - timedelta(days=1))
            self._append_row(
                updated,
                status="D",
                delist_date=delist_date,
                valid_from=delist_date,
            )
            return True
        if status != updated.status:
            updated = replace(updated, status=status)
        if updated != current:
            self._append_row(updated, valid_from=current.valid_from)
            return True
        return False

    def add_name_change(
        self,
        entity_id: int,
        *,
        name: str,
        start_date: Any,
        end_date: Any = None,
        ann_date: Any = None,
    ) -> None:
        """名称变更：闭合覆盖行 + 追加新名称行（SCD2）。"""
        start = _to_date(start_date)
        if start is None:
            raise ValueError(f"名称变更 start_date 无效: {start_date!r}")
        end = _to_date(end_date)
        day_before = start - timedelta(days=1)
        previous = self._covering_row(entity_id, day_before)
        resume_name = previous.name if previous is not None else self._current_row(entity_id).name
        if previous is not None and (
            previous.valid_to is None or previous.valid_to > day_before
        ):
            self._close_row(previous, day_before)
        current = self._current_row(entity_id)
        self._append_row(
            current,
            name=str(name),
            valid_from=start,
            valid_to=end,
            attrs_extra={"ann_date": ann_date} if ann_date else None,
        )
        if end is not None:
            self._append_row(
                current,
                name=resume_name,
                valid_from=end + timedelta(days=1),
            )

    def _close_row(self, row: EntityRecord, valid_to: date | None) -> None:
        self._repo.append_entity(
            replace(
                row,
                valid_to=valid_to,
                knowledge_time=_now(),
                version=self._next_version(row.entity_id),
            )
        )

    def _append_row(
        self,
        base: EntityRecord,
        *,
        code: str | None = None,
        name: str | None = None,
        status: str | None = None,
        delist_date: date | None = None,
        valid_from: date | None = None,
        valid_to: date | None = None,
        attrs_extra: dict[str, Any] | None = None,
    ) -> EntityRecord:
        attrs = dict(base.attrs or {})
        if attrs_extra:
            attrs.update(attrs_extra)
        record = replace(
            base,
            code=code if code is not None else base.code,
            name=name if name is not None else base.name,
            status=status if status is not None else base.status,
            delist_date=delist_date if delist_date is not None else base.delist_date,
            valid_from=valid_from if valid_from is not None else base.valid_from,
            valid_to=valid_to,
            knowledge_time=_now(),
            version=self._next_version(base.entity_id),
            attrs=attrs or None,
        )
        self._repo.append_entity(record)
        return record

    def _current_row(self, entity_id: int) -> EntityRecord:
        """当前有效行：优先 open 区间（valid_to=None），版本单调递增。"""
        rows = self._repo.entity_rows(entity_id)
        if not rows:
            raise KeyError(f"entity_id 不存在: {entity_id}")
        open_rows = [row for row in rows if row.valid_to is None]
        pool = open_rows or rows
        return max(pool, key=lambda row: (row.valid_from or _EPOCH, row.version))

    def _next_version(self, entity_id: int) -> int:
        return max(row.version for row in self._repo.entity_rows(entity_id)) + 1

    def _covering_row(
        self, entity_id: int, as_of: date | None
    ) -> EntityRecord | None:
        rows = self._repo.entity_rows(entity_id)
        if not rows:
            return None
        if as_of is None:
            return self._current_row(entity_id)
        candidates = [
            row
            for row in rows
            if row.valid_from is not None
            and row.valid_from <= as_of
            and (row.valid_to is None or as_of <= row.valid_to)
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda row: (row.valid_from or _EPOCH, row.version))

    # ------------------------------------------------------------ 查询
    def resolve(self, code: str, *, as_of: Any = None) -> int | None:
        """canonical 代码（含历史代码）→ entity_id。

        append-only 仓储可能保留同键旧版本；按 ``(entity_id, code, valid_from)``
        取最新 version 后再做有效期过滤。
        """
        target = _to_date(as_of)
        latest: dict[tuple[int, str, date | None], CodeHistoryRecord] = {}
        for entry in self._repo.find_by_code(code):
            key = (entry.entity_id, entry.code, entry.valid_from)
            if key not in latest or entry.version > latest[key].version:
                latest[key] = entry
        entries = sorted(
            latest.values(),
            key=lambda item: (item.valid_from or _EPOCH, item.version),
            reverse=True,
        )
        for entry in entries:
            if target is None:
                return entry.entity_id
            if entry.valid_from is not None and target < entry.valid_from:
                continue
            if entry.valid_to is not None and target > entry.valid_to:
                continue
            return entry.entity_id
        return None

    def entity(self, entity_id: int, *, as_of: Any = None) -> EntityRecord | None:
        target = _to_date(as_of)
        if target is None:
            rows = self._repo.entity_rows(entity_id)
            return self._current_row(entity_id) if rows else None
        return self._covering_row(entity_id, target)

    def code_history(self, entity_id: int) -> list[CodeHistoryRecord]:
        return self._repo.code_history(entity_id)

    def add_code_change(
        self, entity_id: int, *, new_code: str, start_date: Any
    ) -> None:
        """canonical 代码变更：闭合旧代码条目 + 追加新代码（历史码仍可解析）。"""
        start = _to_date(start_date)
        if start is None:
            raise ValueError(f"代码变更 start_date 无效: {start_date!r}")
        for entry in self._repo.code_history(entity_id):
            if entry.valid_to is None:
                self._repo.append_code(
                    replace(
                        entry,
                        valid_to=start - timedelta(days=1),
                        knowledge_time=_now(),
                        version=entry.version + 1,
                    )
                )
        current = self._current_row(entity_id)
        self._close_row(current, start - timedelta(days=1))
        self._repo.append_code(
            CodeHistoryRecord(
                entity_id=entity_id,
                code=str(new_code),
                valid_from=start,
                knowledge_time=_now(),
            )
        )
        self._append_row(current, code=str(new_code), valid_from=start)

    def universe(
        self,
        as_of: Any,
        *,
        entity_type: str | None = None,
        sec_type: str | None = None,
    ) -> list[EntityRecord]:
        """as-of 宇宙：``list_date <= as_of < delist_date``（退市日不含）。"""
        target = _to_date(as_of)
        if target is None:
            raise ValueError("as_of 不能为空")
        result = []
        seen: set[int] = set()
        for entity_id in sorted({row.entity_id for row in self._repo.all_rows()}):
            row = self._covering_row(entity_id, target)
            if row is None or row.entity_id in seen:
                continue
            seen.add(row.entity_id)
            if entity_type and row.entity_type != entity_type:
                continue
            if sec_type and row.sec_type != sec_type:
                continue
            if row.list_date is not None and target < row.list_date:
                continue
            if row.delist_date is not None and target >= row.delist_date:
                continue
            result.append(row)
        return sorted(result, key=lambda item: item.entity_id)

    def name_as_of(self, entity_id: int, as_of: Any) -> str | None:
        row = self._covering_row(entity_id, _to_date(as_of))
        return row.name if row else None

    def status_as_of(self, entity_id: int, as_of: Any) -> str | None:
        row = self._covering_row(entity_id, _to_date(as_of))
        return row.status if row else None

    # ------------------------------------------------------------ Hub 构建
    def build_from_hub(
        self,
        hub: Any,
        *,
        namechange_start: str | None = None,
        namechange_end: str | None = None,
    ) -> BuildStats:
        """从 FinDataHub 基础信息构建/刷新（可重复调用；含退市与名称变更）。"""
        stats = BuildStats()
        for kind, sec_type in (
            ("stock_list", "stock"),
            ("etf_list", "etf"),
            ("fund_list", "fund"),
            ("index_list", "index"),
        ):
            try:
                frame = hub.get_reference(kind)
            except (UnsupportedCapability, ValueError):
                continue
            stats = self._register_frame(frame, sec_type, stats)
        try:
            delisted = hub.get_reference("delist_list")
        except (UnsupportedCapability, ValueError):
            delisted = None
        if delisted is not None and not delisted.empty:
            for row in delisted.to_dict("records"):
                code = _clean_code(row.get("code"))
                if code is None:
                    continue
                _, created, updated = self._register_or_refresh(
                    code=code,
                    name=str(row.get("name") or ""),
                    list_date=row.get("list_date"),
                    delist_date=row.get("delist_date"),
                    status="D",
                )
                stats = _bump(
                    stats,
                    registered=int(created),
                    updated=int(updated),
                    skipped=int(not created and not updated),
                )
        if namechange_start and namechange_end:
            try:
                events = hub.get_market_events(
                    kind="namechange", start=namechange_start, end=namechange_end
                )
            except (UnsupportedCapability, ValueError):
                events = None
            if events is not None and not events.empty:
                for row in events.to_dict("records"):
                    code = _clean_code(row.get("code"))
                    entity_id = self.resolve(code) if code else None
                    if entity_id is None:
                        stats = _bump(stats, skipped=1)
                        continue
                    self.add_name_change(
                        entity_id,
                        name=str(row["name"]),
                        start_date=row["start_date"],
                        end_date=row.get("end_date"),
                        ann_date=row.get("ann_date"),
                    )
                    stats = _bump(stats, attributes=1)
        return stats

    def _register_frame(
        self, frame: pd.DataFrame, sec_type: str, stats: BuildStats
    ) -> BuildStats:
        if frame is None or frame.empty:
            return stats
        for row in frame.to_dict("records"):
            code = _clean_code(row.get("code"))
            if code is None:
                continue
            _, created, updated = self._register_or_refresh(
                code=code,
                name=str(row.get("name") or ""),
                sec_type=sec_type,
                status=str(row.get("list_status") or row.get("status") or "L"),
                list_date=row.get("list_date"),
                delist_date=row.get("delist_date"),
            )
            stats = _bump(
                stats,
                registered=int(created),
                updated=int(updated),
                skipped=int(not created and not updated),
            )
        return stats
