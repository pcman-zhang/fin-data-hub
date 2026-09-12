"""统一门面：:class:`DataHub`。

调用链：``normalize codes → capability check → cache lookup → adapter fetch
→ schema normalize → cache store → return``。
"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from fin_data_hub.cache import MemoryCache
from fin_data_hub.codes import SecCode, parse_codes
from fin_data_hub.config import HubConfig
from fin_data_hub.enums import Source
from fin_data_hub.schemas import (
    BARS_COLUMNS,
    CALENDAR_COLUMNS,
    NAV_COLUMNS,
    SNAPSHOT_COLUMNS,
    finalize_frame,
    reference_columns,
)
from fin_data_hub.sources.base import BaseAdapter
from fin_data_hub.sources.registry import SourceRegistry

_Fields = Sequence[str] | None


def _with_cached_flag(df: pd.DataFrame, cached: bool) -> pd.DataFrame:
    """返回浅拷贝并更新 ``cached``（避免并发下互相污染缓存对象的 attrs）。"""
    out = df.copy(deep=False)
    out.attrs = {**df.attrs, "cached": bool(cached)}
    return out


class DataHub:
    """多源金融数据统一入口。"""

    def __init__(
        self,
        config: HubConfig | None = None,
        *,
        registry: SourceRegistry | None = None,
    ) -> None:
        self.config = config or HubConfig()
        self.registry = registry if registry is not None else SourceRegistry()
        cc = self.config.cache
        self.cache = MemoryCache(
            max_bytes=cc.max_bytes,
            max_entries=cc.max_entries,
            max_entry_bytes=cc.max_entry_bytes,
            ttl=cc.ttl,
            copy_on_return=cc.copy_on_return,
        )

    # ------------------------------------------------------------------ 行情
    def get_bars(
        self,
        codes: str | SecCode | Sequence[str | SecCode],
        *,
        start: str,
        end: str,
        freq: str = "1d",
        adjust: str | None = None,
        source: Source | str | None = None,
        fields: _Fields = None,
        force: bool = False,
        ttl: float | None = None,
    ) -> pd.DataFrame:
        resolved = self._resolve_source(source)
        scodes = parse_codes(list(codes) if not isinstance(codes, (str, SecCode)) else codes)
        adapter = self.registry.get_for_capability(resolved, BaseAdapter.CAP_BARS)
        key = (
            "bars",
            str(resolved),
            tuple(sorted(c.canonical for c in scodes)),
            start,
            end,
            freq,
            adjust,
            tuple(fields) if fields else (),
        )
        was_cached = (not force) and self.cache.contains(key)

        def load() -> pd.DataFrame:
            raw = adapter.fetch_bars(
                scodes,
                start=start,
                end=end,
                freq=freq,
                adjust=adjust,
                fields=tuple(fields) if fields else None,
            )
            return finalize_frame(
                raw, columns=BARS_COLUMNS, source=resolved, cached=was_cached
            )

        df = self.cache.get_or_load(key, load, force=force, ttl=ttl)
        return _with_cached_flag(df, was_cached)

    # ---------------------------------------------------------------- 快照
    def get_snapshot(
        self,
        codes: str | SecCode | Sequence[str | SecCode],
        *,
        fields: _Fields = None,
        source: Source | str | None = None,
        force: bool = False,
        ttl: float | None = None,
    ) -> pd.DataFrame:
        resolved = self._resolve_source(source)
        scodes = parse_codes(list(codes) if not isinstance(codes, (str, SecCode)) else codes)
        adapter = self.registry.get_for_capability(resolved, BaseAdapter.CAP_SNAPSHOT)
        key = (
            "snapshot",
            str(resolved),
            tuple(sorted(c.canonical for c in scodes)),
            tuple(fields) if fields else (),
        )
        was_cached = (not force) and self.cache.contains(key)

        def load() -> pd.DataFrame:
            raw = adapter.fetch_snapshot(
                scodes, fields=tuple(fields) if fields else None
            )
            return finalize_frame(
                raw, columns=SNAPSHOT_COLUMNS, source=resolved, cached=was_cached
            )

        df = self.cache.get_or_load(key, load, force=force, ttl=ttl)
        return _with_cached_flag(df, was_cached)

    # -------------------------------------------------------------- 基金净值
    def get_fund_nav(
        self,
        codes: str | SecCode | Sequence[str | SecCode],
        *,
        start: str | None = None,
        end: str | None = None,
        source: Source | str | None = None,
        force: bool = False,
        ttl: float | None = None,
    ) -> pd.DataFrame:
        resolved = self._resolve_source(source)
        scodes = parse_codes(list(codes) if not isinstance(codes, (str, SecCode)) else codes)
        adapter = self.registry.get_for_capability(resolved, BaseAdapter.CAP_FUND_NAV)
        key = (
            "fund_nav",
            str(resolved),
            tuple(sorted(c.canonical for c in scodes)),
            start,
            end,
        )
        was_cached = (not force) and self.cache.contains(key)

        def load() -> pd.DataFrame:
            raw = adapter.fetch_fund_nav(scodes, start=start, end=end)
            return finalize_frame(
                raw, columns=NAV_COLUMNS, source=resolved, cached=was_cached
            )

        df = self.cache.get_or_load(key, load, force=force, ttl=ttl)
        return _with_cached_flag(df, was_cached)

    # -------------------------------------------------------------- 参考数据
    def get_reference(
        self,
        kind: str,
        *,
        source: Source | str | None = None,
        force: bool = False,
        ttl: float | None = None,
    ) -> pd.DataFrame:
        columns = reference_columns(kind)
        resolved = self._resolve_source(source)
        adapter = self.registry.get_for_capability(resolved, BaseAdapter.CAP_REFERENCE)
        key = ("reference", str(resolved), kind)
        was_cached = (not force) and self.cache.contains(key)

        def load() -> pd.DataFrame:
            raw = adapter.fetch_reference(kind)
            return finalize_frame(
                raw, columns=columns, source=resolved, cached=was_cached
            )

        df = self.cache.get_or_load(key, load, force=force, ttl=ttl)
        return _with_cached_flag(df, was_cached)

    # ---------------------------------------------------------------- 日历
    def get_trade_calendar(
        self,
        *,
        start: str,
        end: str,
        source: Source | str | None = None,
        force: bool = False,
        ttl: float | None = None,
    ) -> pd.DataFrame:
        resolved = self._resolve_source(source)
        adapter = self.registry.get_for_capability(
            resolved, BaseAdapter.CAP_TRADE_CALENDAR
        )
        key = ("trade_calendar", str(resolved), start, end)
        was_cached = (not force) and self.cache.contains(key)

        def load() -> pd.DataFrame:
            raw = adapter.fetch_trade_calendar(start=start, end=end)
            return finalize_frame(
                raw, columns=CALENDAR_COLUMNS, source=resolved, cached=was_cached
            )

        df = self.cache.get_or_load(key, load, force=force, ttl=ttl)
        return _with_cached_flag(df, was_cached)

    # ------------------------------------------------------------------ 内部
    def _resolve_source(self, source: Source | str | None) -> Source:
        if source is not None:
            return Source(source)
        if self.config.default_source is not None:
            return Source(self.config.default_source)
        raise ValueError(
            "必须显式指定 source（或通过 HubConfig.default_source 配置默认值）"
        )
