"""统一输出 schema（各端点规范列与归一化）。"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pandas as pd

from fin_data_hub.errors import ResponseParseError

#: K 线/行情
BARS_COLUMNS = ("code", "date", "open", "high", "low", "close", "volume", "amount")
#: 快照（当日/实时）
SNAPSHOT_COLUMNS = (
    "code",
    "date",
    "last",
    "open",
    "high",
    "low",
    "prev_close",
    "volume",
    "amount",
)
#: 场外基金净值
NAV_COLUMNS = ("code", "date", "unit_nav", "accum_nav", "daily_return")
#: 交易日历
CALENDAR_COLUMNS = ("date", "is_open")
#: 参考数据（按 kind）
REFERENCE_COLUMNS: dict[str, tuple[str, ...]] = {
    "stock_list": ("code", "name", "list_date", "market", "industry"),
    "fund_list": ("code", "name", "fund_type", "management", "list_date", "market"),
    "index_list": ("code", "name", "market", "category", "publisher", "list_date"),
}

_DATE_COLUMN = "date"


def finalize_frame(
    df: pd.DataFrame,
    *,
    columns: tuple[str, ...],
    source: str,
    cached: bool,
    fetched_at: dt.datetime | None = None,
) -> pd.DataFrame:
    """校验规范列、统一日期类型并写入 ``attrs`` 元信息。"""
    if not isinstance(df, pd.DataFrame):
        raise ResponseParseError(f"期望 DataFrame，实际为 {type(df).__name__}")
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ResponseParseError(
            f"响应缺少字段 {missing}；实际字段: {list(df.columns)}"
        )
    out = df.loc[:, list(columns)].copy(deep=False)
    if _DATE_COLUMN in out.columns:
        try:
            out[_DATE_COLUMN] = pd.to_datetime(out[_DATE_COLUMN]).astype(
                "datetime64[ns]"
            )
        except (ValueError, TypeError) as exc:
            raise ResponseParseError(f"日期列解析失败: {exc}") from exc
    timestamp = fetched_at or dt.datetime.now(dt.UTC)
    out.attrs["source"] = str(source)
    out.attrs["cached"] = bool(cached)
    out.attrs["fetched_at"] = timestamp.isoformat()
    out.attrs["code_format"] = "canonical"
    return out


def reference_columns(kind: str) -> tuple[str, ...]:
    try:
        return REFERENCE_COLUMNS[kind]
    except KeyError as exc:
        raise ValueError(
            f"未知 reference kind: {kind!r}（可选 {sorted(REFERENCE_COLUMNS)}）"
        ) from exc


def as_frame(value: Any) -> pd.DataFrame:
    """适配器返回值兜底转换（list[dict] / dict / DataFrame）。"""
    if isinstance(value, pd.DataFrame):
        return value
    return pd.DataFrame(value)
