"""Security Master 服务：注册、别名解析、as-of 宇宙、SCD2 属性还原（doc-10 §3.3）。

存储落地（DDL/迁移/持久化仓储）由 TASK-3.3 接入；本模块为存储无关核心逻辑。

区间语义约定：
- ``universe``：半开区间——``list_date <= as_of < delist_date``（退市日当日已不可交易）；
- ``name_as_of`` / ``status_as_of``：闭区间——``start <= as_of <= end``（NULL=至今）；
  目标日不被任何区间覆盖时返回 ``None``（无区间记录时才回退当前值，防前视）。

增量刷新：``build_from_hub`` 可重复调用；已注册标的的退市/状态/名称变化会更新记录
并补写状态区间（见 :meth:`SecurityMaster.register`）。
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from fin_data_hub.errors import UnsupportedCapability
from fin_data_platform.security_master.models import (
    AliasRecord,
    AttributeInterval,
    BuildStats,
    SecurityRecord,
    StatusInterval,
)
from fin_data_platform.security_master.repository import (
    InMemorySecurityMasterRepository,
    SecurityMasterRepository,
)

_DEFAULT_SOURCES = ("tushare", "baostock", "akshare")
#: 别名生效兜底起点（list_date 缺失时；早于 A 股最早上市日）
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


def _bump(
    stats: BuildStats,
    *,
    registered: int = 0,
    updated: int = 0,
    aliases: int = 0,
    attributes: int = 0,
    skipped: int = 0,
) -> BuildStats:
    return BuildStats(
        registered=stats.registered + registered,
        updated=stats.updated + updated,
        aliases=stats.aliases + aliases,
        attributes=stats.attributes + attributes,
        skipped=stats.skipped + skipped,
    )


class SecurityMaster:
    """标的注册与 PIT 查询（含退市永久保留）。"""

    def __init__(self, repository: SecurityMasterRepository | None = None) -> None:
        self._repo = repository or InMemorySecurityMasterRepository()

    # ------------------------------------------------------------ 注册
    def register(
        self,
        *,
        canonical_code: str,
        sec_type: str,
        name: str,
        currency: str | None = None,
        list_date: Any = None,
        delist_date: Any = None,
        status: str = "L",
        aliases: tuple[tuple[str, str], ...] = (),
        standard_sources: tuple[str, ...] = _DEFAULT_SOURCES,
    ) -> SecurityRecord:
        """注册或刷新标的（按 canonical 幂等）。

        已存在时仅应用可观测变化（退市、状态、名称、补全上市日），不重复建别名。
        """
        record, _, _, _ = self._register_or_refresh(
            canonical_code=canonical_code,
            sec_type=sec_type,
            name=name,
            currency=currency,
            list_date=list_date,
            delist_date=delist_date,
            status=status,
            aliases=aliases,
            standard_sources=standard_sources,
        )
        return record

    def _register_or_refresh(
        self, **kwargs: Any
    ) -> tuple[SecurityRecord, bool, bool, int]:
        """返回 ``(record, created, updated, aliases_added)``。"""
        code = str(kwargs["canonical_code"])
        existing = self._repo.find_by_canonical(code)
        if existing is None:
            record = self._create(**kwargs)
            return record, True, False, self._repo.count_aliases(record.security_id)
        updated = self._refresh_existing(existing, **kwargs)
        record = self._repo.get_security(existing.security_id) or existing
        return record, False, updated, 0

    def _create(
        self,
        *,
        canonical_code: str,
        sec_type: str,
        name: str,
        currency: str | None = None,
        list_date: Any = None,
        delist_date: Any = None,
        status: str = "L",
        aliases: tuple[tuple[str, str], ...] = (),
        standard_sources: tuple[str, ...] = _DEFAULT_SOURCES,
    ) -> SecurityRecord:
        record = SecurityRecord(
            security_id=self._repo.next_security_id(),
            canonical_code=canonical_code,
            sec_type=sec_type,
            name=name,
            currency=currency,
            list_date=_to_date(list_date),
            delist_date=_to_date(delist_date),
            status=status,
            valid_from=_to_date(list_date),
        )
        self._repo.add_security(record)
        self._repo.add_alias(
            AliasRecord(
                security_id=record.security_id,
                source="canonical",
                source_code=canonical_code,
                valid_from=record.list_date or _EPOCH,
            )
        )
        for source, source_code in aliases:
            self._repo.add_alias(
                AliasRecord(
                    security_id=record.security_id,
                    source=str(source),
                    source_code=str(source_code),
                    valid_from=record.list_date or _EPOCH,
                )
            )
        self._add_standard_aliases(record, standard_sources)
        self._add_initial_status(record)
        return record

    def _refresh_existing(self, existing: SecurityRecord, **kwargs: Any) -> bool:
        """应用增量变化：退市、状态、名称、补全上市日。"""
        name = str(kwargs.get("name") or "")
        status = str(kwargs.get("status") or existing.status)
        list_date = _to_date(kwargs.get("list_date"))
        delist_date = _to_date(kwargs.get("delist_date"))
        updated = existing
        if list_date is not None and existing.list_date is None:
            updated = replace(updated, list_date=list_date, valid_from=list_date)
        if name and name != updated.name:
            updated = replace(updated, name=name)
        if delist_date is not None and updated.delist_date is None:
            updated = replace(updated, delist_date=delist_date, status="D")
            self._repo.add_security(updated)
            self._add_delist_status(updated)
            return True
        if status != updated.status:
            updated = replace(updated, status=status)
        if updated != existing:
            self._repo.add_security(updated)
            return True
        return False

    def _add_delist_status(self, record: SecurityRecord) -> None:
        if record.delist_date is None:
            return
        if record.list_date is not None and not self._has_status(
            record.security_id, "L", record.list_date
        ):
            self.add_status(
                record.security_id,
                status="L",
                start_date=record.list_date,
                end_date=record.delist_date - timedelta(days=1),
            )
        if not self._has_status(record.security_id, "D", record.delist_date):
            self.add_status(
                record.security_id, status="D", start_date=record.delist_date
            )

    def _has_status(self, security_id: int, status: str, start: date) -> bool:
        return any(
            item.status == status and item.start_date == start
            for item in self._repo.statuses_of(security_id)
        )

    def _add_initial_status(self, record: SecurityRecord) -> None:
        if record.status == "D" and record.delist_date is not None:
            self._add_delist_status(record)
        elif record.list_date is not None:
            self.add_status(
                record.security_id, status=record.status, start_date=record.list_date
            )

    def add_status(
        self, security_id: int, *, status: str, start_date: Any, end_date: Any = None
    ) -> None:
        start = _to_date(start_date)
        if start is None:
            raise ValueError(f"status start_date 无效: {start_date!r}")
        self._repo.add_status(
            StatusInterval(
                security_id=security_id,
                status=status,
                start_date=start,
                end_date=_to_date(end_date),
            )
        )

    def add_attribute(
        self,
        security_id: int,
        *,
        attribute: str,
        value: str,
        start_date: Any,
        end_date: Any = None,
        ann_date: Any = None,
    ) -> None:
        start = _to_date(start_date)
        if start is None:
            raise ValueError(f"attribute start_date 无效: {start_date!r}")
        self._repo.add_attribute(
            AttributeInterval(
                security_id=security_id,
                attribute=attribute,
                value=str(value),
                start_date=start,
                end_date=_to_date(end_date),
                ann_date=_to_date(ann_date),
            )
        )

    # ------------------------------------------------------------ 查询
    def resolve(
        self, source: str, source_code: str, *, as_of: Any = None
    ) -> int | None:
        """多源代码 → security_id（按有效期过滤）。"""
        target = _to_date(as_of)
        for alias in self._repo.aliases_by_code(source, source_code):
            if target is not None:
                if alias.valid_from is not None and target < alias.valid_from:
                    continue
                if alias.valid_to is not None and target > alias.valid_to:
                    continue
            return alias.security_id
        return None

    def aliases(self, security_id: int) -> list[AliasRecord]:
        return self._repo.aliases_of(security_id)

    def security(self, security_id: int) -> SecurityRecord | None:
        return self._repo.get_security(security_id)

    def universe(
        self, as_of: Any, *, sec_types: tuple[str, ...] | None = None
    ) -> list[SecurityRecord]:
        """as-of 宇宙：``list_date <= as_of < delist_date``（含退市，半开区间）。"""
        target = _to_date(as_of)
        if target is None:
            raise ValueError("as_of 不能为空")
        result = []
        for security in self._repo.all_securities():
            if sec_types and security.sec_type not in sec_types:
                continue
            if security.list_date is not None and target < security.list_date:
                continue
            if security.delist_date is not None and target >= security.delist_date:
                continue
            result.append(security)
        return sorted(result, key=lambda item: item.security_id)

    def name_as_of(self, security_id: int, as_of: Any) -> str | None:
        """SCD2 名称还原（闭区间）。

        有区间记录但目标日不被覆盖 → ``None``（防前视）；无任何区间记录时回退当前名称。
        """
        value = self._attribute_as_of(security_id, "name", as_of)
        if value is not None:
            return value
        if self._repo.attributes_of(security_id, "name"):
            return None
        security = self._repo.get_security(security_id)
        return security.name if security else None

    def status_as_of(self, security_id: int, as_of: Any) -> str | None:
        """SCD2 状态还原（闭区间）；语义同 :meth:`name_as_of`。"""
        target = _to_date(as_of)
        if target is None:
            return None
        intervals = self._repo.statuses_of(security_id)
        for interval in sorted(
            intervals, key=lambda item: item.start_date, reverse=True
        ):
            if interval.start_date <= target and (
                interval.end_date is None or target <= interval.end_date
            ):
                return interval.status
        if intervals:
            return None
        security = self._repo.get_security(security_id)
        return security.status if security else None

    def _attribute_as_of(
        self, security_id: int, attribute: str, as_of: Any
    ) -> str | None:
        target = _to_date(as_of)
        if target is None:
            return None
        intervals = self._repo.attributes_of(security_id, attribute)
        for interval in sorted(
            intervals, key=lambda item: item.start_date, reverse=True
        ):
            if interval.start_date <= target and (
                interval.end_date is None or target <= interval.end_date
            ):
                return interval.value
        return None

    # ------------------------------------------------------------ Hub 构建
    def build_from_hub(
        self,
        hub: Any,
        *,
        namechange_start: str | None = None,
        namechange_end: str | None = None,
        standard_sources: tuple[str, ...] = _DEFAULT_SOURCES,
    ) -> BuildStats:
        """从 FinDataHub 基础信息构建/刷新（可重复调用；含退市与名称变更）。

        ``etf_list`` 先于 ``fund_list``（源基金列表常含 ETF，避免类型被泛化为 fund）。
        """
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
            stats = self._register_frame(
                frame, sec_type, stats, standard_sources=standard_sources
            )
        try:
            delisted = hub.get_reference("delist_list")
        except (UnsupportedCapability, ValueError):
            delisted = None
        if delisted is not None and not delisted.empty:
            for row in delisted.to_dict("records"):
                code = _clean_code(row.get("code"))
                if code is None:
                    continue
                _, created, updated, alias_count = self._register_or_refresh(
                    canonical_code=code,
                    sec_type="stock",
                    name=str(row.get("name") or ""),
                    list_date=row.get("list_date"),
                    delist_date=row.get("delist_date"),
                    status="D",
                    standard_sources=standard_sources,
                )
                stats = _bump(
                    stats,
                    registered=int(created),
                    updated=int(updated),
                    aliases=alias_count,
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
                    security = self._repo.find_by_canonical(code) if code else None
                    if security is None:
                        stats = _bump(stats, skipped=1)
                        continue
                    self.add_attribute(
                        security.security_id,
                        attribute="name",
                        value=str(row["name"]),
                        start_date=row["start_date"],
                        end_date=row.get("end_date"),
                        ann_date=row.get("ann_date"),
                    )
                    stats = _bump(stats, attributes=1)
        return stats

    def _register_frame(
        self,
        frame: pd.DataFrame,
        sec_type: str,
        stats: BuildStats,
        *,
        standard_sources: tuple[str, ...],
    ) -> BuildStats:
        if frame is None or frame.empty:
            return stats
        for row in frame.to_dict("records"):
            code = _clean_code(row.get("code"))
            if code is None:
                continue
            _, created, updated, alias_count = self._register_or_refresh(
                canonical_code=code,
                sec_type=sec_type,
                name=str(row.get("name") or ""),
                list_date=row.get("list_date"),
                delist_date=row.get("delist_date"),
                status=str(row.get("list_status") or row.get("status") or "L"),
                standard_sources=standard_sources,
            )
            stats = _bump(
                stats,
                registered=int(created),
                updated=int(updated),
                aliases=alias_count,
                skipped=int(not created and not updated),
            )
        return stats

    def _add_standard_aliases(
        self, record: SecurityRecord, sources: tuple[str, ...]
    ) -> None:
        from fin_data_hub.codes import SecCode
        from fin_data_hub.enums import Source
        from fin_data_hub.mapping import get_mapper

        try:
            code = SecCode.parse(record.canonical_code)
        except Exception:  # noqa: BLE001 - 无法解析的代码仅保留 canonical 别名
            return
        for source in sources:
            try:
                source_code = get_mapper(Source(source)).to_source(code)
            except Exception:  # noqa: BLE001 - 源不支持该市场时跳过
                continue
            self._repo.add_alias(
                AliasRecord(
                    security_id=record.security_id,
                    source=str(source),
                    source_code=source_code,
                    valid_from=record.list_date or _EPOCH,
                )
            )
