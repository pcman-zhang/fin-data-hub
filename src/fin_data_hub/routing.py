"""Router：统一输出与跨源路由（策略见 doc-5）。

职责：主源执行 → 完整性检测 → 按需补充（字段补全 / 复权合成 / 失败回退）→ 溯源。
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from fin_data_hub.enums import Source
from fin_data_hub.errors import SourceError, UnsupportedCapability


@dataclass(frozen=True, slots=True)
class RoutingConfig:
    """跨源路由配置（doc-5 §4）。"""

    factor_source: Source | None = Source.TUSHARE
    trusted_native_adjust: frozenset[Source] = frozenset(
        {Source.TUSHARE, Source.WIND, Source.AKSHARE}
    )
    fallbacks: tuple[Source, ...] = ()
    field_fill: bool = True


@dataclass(frozen=True, slots=True)
class BarsPlan:
    """bars 请求的执行计划。"""

    primary: Source
    adapter_adjust: str | None
    factor_source: Source | None
    fallbacks: tuple[Source, ...]


def build_bars_plan(
    source: Source, adjust: str | None, routing: RoutingConfig
) -> BarsPlan:
    """按 doc-5 §3 生成 bars 执行计划。"""
    if adjust is None or source in routing.trusted_native_adjust:
        return BarsPlan(source, adjust, None, routing.fallbacks)
    if routing.factor_source is None:
        raise UnsupportedCapability(
            f"{source} 不支持原生复权，且未配置因子源（RoutingConfig.factor_source）"
        )
    return BarsPlan(source, None, routing.factor_source, routing.fallbacks)


def missing_columns(df: pd.DataFrame, columns: tuple[str, ...]) -> list[str]:
    """返回缺失或全空的规范列。"""
    return [
        column
        for column in columns
        if column not in df.columns or df[column].isna().all()
    ]


def fill_missing_fields(
    primary: pd.DataFrame,
    fill_frames: list[tuple[str, pd.DataFrame]],
    columns: tuple[str, ...],
) -> tuple[pd.DataFrame, dict[str, str]]:
    """字段级补全：first-non-null，不覆盖主源已有值（doc-5 §3）。

    返回 ``(合并后的 DataFrame, {列: 补充源标签})``。
    """
    result = primary.copy()
    filled: dict[str, str] = {}
    for column in columns:
        if column not in result.columns:
            result[column] = pd.NA
        if not result[column].isna().all():
            continue
        for label, frame in fill_frames:
            if column not in frame.columns or frame[column].isna().all():
                continue
            if all(key in result.columns for key in ("code", "date")) and all(
                key in frame.columns for key in ("code", "date")
            ):
                patch = frame[["code", "date", column]].rename(
                    columns={column: f"{column}__fill"}
                )
                result = result.merge(patch, on=["code", "date"], how="left")
                result[column] = result[column].where(
                    result[column].notna(), result[f"{column}__fill"]
                )
                result = result.drop(columns=[f"{column}__fill"])
            else:
                result[column] = frame[column].reindex(result.index)
            filled[column] = label
            break
    return result, filled


def apply_adjustment(
    bars: pd.DataFrame, factors: pd.DataFrame, adjust: str
) -> pd.DataFrame:
    """按 raw + factor 计算复权价（doc-5 §3）。"""
    if adjust not in ("qfq", "hfq"):
        raise ValueError(f"adjust 仅支持 qfq/hfq: {adjust!r}")
    if bars.empty:
        return bars
    bars = bars.copy()
    factors = factors.copy()
    bars["date"] = pd.to_datetime(bars["date"]).astype("datetime64[ns]")
    factors["date"] = pd.to_datetime(factors["date"]).astype("datetime64[ns]")
    merged = bars.merge(factors, on=["code", "date"], how="left").sort_values(
        ["code", "date"]
    )
    merged["adj_factor"] = merged.groupby("code")["adj_factor"].ffill()
    if merged["adj_factor"].isna().any():
        raise SourceError("复权因子缺失（对齐后仍为 NaN），无法计算复权价")
    if adjust == "qfq":
        latest = merged.groupby("code")["adj_factor"].transform("last")
        ratio = merged["adj_factor"] / latest
    else:
        ratio = merged["adj_factor"]
    for column in ("open", "high", "low", "close"):
        if column in merged.columns:
            merged[column] = merged[column] * ratio
    return merged.drop(columns=["adj_factor"]).reset_index(drop=True)
