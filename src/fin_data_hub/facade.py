"""统一门面：:class:`FinDataHub`。

调用链：``normalize codes → capability check → cache lookup → adapter fetch
→ schema normalize → cache store → return``。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict

import pandas as pd

from fin_data_hub.cache import MemoryCache
from fin_data_hub.capabilities import split_codes
from fin_data_hub.codes import SecCode, parse_codes
from fin_data_hub.config import HubConfig
from fin_data_hub.enums import Source
from fin_data_hub.errors import MissingCredentialError, SourceError
from fin_data_hub.ratelimit import (
    RateLimiter,
    RateLimiterSet,
    default_rate_limiter_set,
)
from fin_data_hub.routing import (
    apply_adjustment,
    build_bars_plan,
    fill_missing_fields,
    missing_columns,
)
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
from fin_data_hub.usage import UsageLedger

_Fields = Sequence[str] | None


def _with_cached_flag(df: pd.DataFrame, cached: bool) -> pd.DataFrame:
    """返回浅拷贝并更新 ``cached``（避免并发下互相污染缓存对象的 attrs）。"""
    out = df.copy(deep=False)
    out.attrs = {**df.attrs, "cached": bool(cached)}
    return out


def _merge_frames(
    frames: list[pd.DataFrame],
    *,
    dedupe_on: tuple[str, ...] | None = None,
    sort_by: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """合并分块结果并去重、排序（保证顺序稳定）。"""
    if not frames:
        return pd.DataFrame()
    merged = pd.concat(frames, ignore_index=True)
    if dedupe_on and all(column in merged.columns for column in dedupe_on):
        merged = merged.drop_duplicates(subset=list(dedupe_on))
    if sort_by and all(column in merged.columns for column in sort_by):
        merged = merged.sort_values(list(sort_by)).reset_index(drop=True)
    return merged


class FinDataHub:
    """多源金融数据统一入口（v0 对外接口）。"""

    def __init__(
        self,
        config: HubConfig | None = None,
        *,
        registry: SourceRegistry | None = None,
    ) -> None:
        self.config = config or HubConfig()
        self.registry = registry if registry is not None else SourceRegistry()
        self.usage = UsageLedger(self.config.budget)
        self._rate_limiters: dict[Source, RateLimiterSet] = {}
        cc = self.config.cache
        self.cache = MemoryCache(
            max_bytes=cc.max_bytes,
            max_entries=cc.max_entries,
            max_entry_bytes=cc.max_entry_bytes,
            ttl=cc.ttl,
            copy_on_return=cc.copy_on_return,
        )

    @classmethod
    def from_config(cls, config: HubConfig) -> FinDataHub:
        """按配置自动构建适配器注册表（缺凭证/依赖的源会被跳过）。"""
        from fin_data_hub.sources.factory import build_registry

        return cls(config, registry=build_registry(config))

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
        if not scodes:
            raise ValueError("codes 不能为空")
        plan = build_bars_plan(resolved, adjust, self.config.routing)
        primary_adapter = self._adapter(plan.primary, BaseAdapter.CAP_BARS)
        factor_adapter = (
            self._adapter(plan.factor_source, BaseAdapter.CAP_ADJUST_FACTORS)
            if plan.factor_source is not None
            else None
        )
        fallback_adapters = [
            (str(fallback), self._adapter(fallback, BaseAdapter.CAP_BARS))
            for fallback in plan.fallbacks
            if fallback != plan.primary
        ]
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

        def fetch_frames(adapter: BaseAdapter) -> list[pd.DataFrame]:
            return [
                adapter.fetch_bars(
                    chunk,
                    start=start,
                    end=end,
                    freq=freq,
                    adjust=plan.adapter_adjust,
                    fields=tuple(fields) if fields else None,
                )
                for chunk in split_codes(adapter.source, "bars", scodes)
            ]

        def load() -> pd.DataFrame:
            used_source = str(plan.primary)
            frames: list[pd.DataFrame] = []
            errors: list[str] = []
            for label, adapter in [
                (str(plan.primary), primary_adapter),
                *fallback_adapters,
            ]:
                try:
                    frames = fetch_frames(adapter)
                    used_source = label
                    break
                except (SourceError, MissingCredentialError) as exc:  # 回退链
                    errors.append(f"{label}: {exc}")
            if not frames:
                raise SourceError("所有数据源均失败: " + "; ".join(errors))

            merged = _merge_frames(
                frames, dedupe_on=("code", "date"), sort_by=("code", "date")
            )

            filled: dict[str, str] = {}
            if (
                self.config.routing.field_fill
                and fallback_adapters
                and missing_columns(merged, BARS_COLUMNS)
            ):
                fill_frames: list[tuple[str, pd.DataFrame]] = []
                for label, adapter in fallback_adapters:
                    try:
                        fill_frames.append(
                            (
                                label,
                                _merge_frames(
                                    fetch_frames(adapter),
                                    dedupe_on=("code", "date"),
                                    sort_by=("code", "date"),
                                ),
                            )
                        )
                    except (SourceError, MissingCredentialError):
                        continue
                merged, filled = fill_missing_fields(
                    merged, fill_frames, BARS_COLUMNS
                )

            if (
                factor_adapter is not None
                and plan.factor_source is not None
                and adjust is not None
            ):
                factor_frames = [
                    factor_adapter.fetch_adjust_factors(
                        chunk, start=start, end=end
                    )
                    for chunk in split_codes(
                        plan.factor_source, "adjust_factors", scodes
                    )
                ]
                factors = _merge_frames(
                    factor_frames, dedupe_on=("code", "date"), sort_by=("code", "date")
                )
                merged = apply_adjustment(merged, factors, adjust)

            out = finalize_frame(
                merged, columns=BARS_COLUMNS, source=used_source, cached=was_cached
            )
            out.attrs["requested_source"] = str(resolved)
            if plan.factor_source is not None:
                out.attrs["factor_source"] = str(plan.factor_source)
            if filled:
                out.attrs["filled_from"] = filled
            return out

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
        if not scodes:
            raise ValueError("codes 不能为空")
        adapter = self._adapter(resolved, BaseAdapter.CAP_SNAPSHOT)
        key = (
            "snapshot",
            str(resolved),
            tuple(sorted(c.canonical for c in scodes)),
            tuple(fields) if fields else (),
        )
        was_cached = (not force) and self.cache.contains(key)

        def load() -> pd.DataFrame:
            frames = [
                adapter.fetch_snapshot(chunk, fields=tuple(fields) if fields else None)
                for chunk in split_codes(resolved, "snapshot", scodes)
            ]
            merged = _merge_frames(frames, dedupe_on=("code",), sort_by=("code",))
            return finalize_frame(
                merged, columns=SNAPSHOT_COLUMNS, source=resolved, cached=was_cached
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
        if not scodes:
            raise ValueError("codes 不能为空")
        adapter = self._adapter(resolved, BaseAdapter.CAP_FUND_NAV)
        key = (
            "fund_nav",
            str(resolved),
            tuple(sorted(c.canonical for c in scodes)),
            start,
            end,
        )
        was_cached = (not force) and self.cache.contains(key)

        def load() -> pd.DataFrame:
            frames = [
                adapter.fetch_fund_nav(chunk, start=start, end=end)
                for chunk in split_codes(resolved, "fund_nav", scodes)
            ]
            merged = _merge_frames(
                frames, dedupe_on=("code", "date"), sort_by=("code", "date")
            )
            return finalize_frame(
                merged, columns=NAV_COLUMNS, source=resolved, cached=was_cached
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
        adapter = self._adapter(resolved, BaseAdapter.CAP_REFERENCE)
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
        adapter = self._adapter(
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
    def _limiter_for(self, source: Source) -> RateLimiterSet:
        limiter = self._rate_limiters.get(source)
        if limiter is None:
            override = self.config.rate_limits.get(str(source))
            if override is None:
                limiter = default_rate_limiter_set(source)
            else:
                limiter = RateLimiterSet(
                    RateLimiter(override.rate, override.burst),
                    timeout=override.timeout,
                )
            self._rate_limiters[source] = limiter
        return limiter

    def _adapter(self, source: Source, capability: str) -> BaseAdapter:
        adapter = self.registry.get_for_capability(source, capability)
        adapter.bind_usage(self.usage)
        adapter.bind_rate_limits(self._limiter_for(source))
        return adapter

    def stats(self) -> dict:
        """缓存与用量统计（内存）。"""
        return {"cache": asdict(self.cache.stats()), "usage": self.usage.summary()}

    def _resolve_source(self, source: Source | str | None) -> Source:
        if source is not None:
            return Source(source)
        if self.config.default_source is not None:
            return Source(self.config.default_source)
        raise ValueError(
            "必须显式指定 source（或通过 HubConfig.default_source 配置默认值）"
        )

