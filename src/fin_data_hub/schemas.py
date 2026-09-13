"""统一输出 schema（各端点规范列与归一化）。"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pandas as pd

from fin_data_hub.constants import currency_for_code
from fin_data_hub.errors import ResponseParseError

#: K 线/行情
BARS_COLUMNS = (
    "code",
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "currency",
)
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
    "currency",
)
#: 场外基金净值
NAV_COLUMNS = ("code", "date", "unit_nav", "accum_nav", "daily_return", "currency")
#: 交易日历
CALENDAR_COLUMNS = ("date", "is_open")
#: 参考数据（按 kind）
REFERENCE_COLUMNS: dict[str, tuple[str, ...]] = {
    "stock_list": ("code", "name", "list_date", "market", "industry", "currency"),
    "fund_list": (
        "code",
        "name",
        "fund_type",
        "management",
        "list_date",
        "market",
        "currency",
    ),
    "etf_list": (
        "code",
        "name",
        "fullname",
        "index_code",
        "index_name",
        "setup_date",
        "list_date",
        "list_status",
        "exchange",
        "manager",
        "custodian",
        "mgt_fee",
        "etf_type",
        "currency",
    ),
    "delist_list": (
        "code",
        "name",
        "list_date",
        "delist_date",
        "market",
        "currency",
    ),
    "industry_classify": (
        "index_code",
        "name",
        "level",
        "industry_code",
        "parent_code",
        "is_pub",
        "src",
    ),
    "industry_member": (
        "code",
        "name",
        "l1_code",
        "l1_name",
        "l2_code",
        "l2_name",
        "l3_code",
        "l3_name",
        "in_date",
        "out_date",
        "is_new",
        "currency",
    ),
    "index_list": (
        "code",
        "name",
        "market",
        "category",
        "publisher",
        "list_date",
        "currency",
    ),
}

#: 标的基础信息（get_security_info）
SECURITY_INFO_COLUMNS = (
    "code",
    "name",
    "sec_type",
    "market",
    "list_status",
    "list_date",
    "delist_date",
    "currency",
)

ADJUST_FACTOR_COLUMNS = ("code", "date", "adj_factor")
#: 指数成分与权重（快照型 PIT：as-of 取最近一期）
INDEX_WEIGHT_COLUMNS = ("code", "date", "con_code", "weight")

#: 财务数据（核心 curated 列；公共 PIT 键 ann_date/end_date/report_type）
BALANCE_SHEET_COLUMNS = (
    "code",
    "ann_date",
    "end_date",
    "report_type",
    "total_assets",
    "total_cur_assets",
    "money_cap",
    "accounts_receiv",
    "inventories",
    "fix_assets",
    "cip",
    "intan_assets",
    "goodwill",
    "total_liab",
    "total_cur_liab",
    "st_borr",
    "lt_borr",
    "acct_payable",
    "notes_payable",
    "contract_liab",
    "total_hldr_eqy_exc_min_int",
    "minority_int",
    "currency",
)
FINANCIAL_INDICATOR_COLUMNS = (
    "code",
    "ann_date",
    "end_date",
    "report_type",
    "eps",
    "dt_eps",
    "bps",
    "ocfps",
    "roe",
    "roe_waa",
    "roe_dt",
    "roa",
    "roic",
    "grossprofit_margin",
    "netprofit_margin",
    "debt_to_assets",
    "current_ratio",
    "quick_ratio",
    "or_yoy",
    "netprofit_yoy",
    "dt_netprofit_yoy",
    "currency",
)
FINANCIAL_COLUMNS: dict[str, tuple[str, ...]] = {
    "balance_sheet": BALANCE_SHEET_COLUMNS,
    "financial_indicator": FINANCIAL_INDICATOR_COLUMNS,
}


def financial_columns(kind: str) -> tuple[str, ...]:
    try:
        return FINANCIAL_COLUMNS[kind]
    except KeyError as exc:
        raise ValueError(
            f"未知 financial kind: {kind!r}（可选 {sorted(FINANCIAL_COLUMNS)}）"
        ) from exc


#: 市场事件（get_market_events）：ipo / suspension / st
IPO_COLUMNS = (
    "code",
    "name",
    "ipo_date",
    "issue_date",
    "price",
    "pe",
    "amount",
    "market_amount",
    "limit_amount",
    "funds",
    "ballot",
    "currency",
)
SUSPENSION_COLUMNS = ("code", "date", "suspend_type", "suspend_timing", "currency")
ST_COLUMNS = ("code", "name", "date", "st_type", "type_name", "currency")
NAMECHANGE_COLUMNS = (
    "code",
    "name",
    "start_date",
    "end_date",
    "ann_date",
    "change_reason",
    "currency",
)
MARKET_EVENT_COLUMNS: dict[str, tuple[str, ...]] = {
    "ipo": IPO_COLUMNS,
    "suspension": SUSPENSION_COLUMNS,
    "st": ST_COLUMNS,
    "namechange": NAMECHANGE_COLUMNS,
}


def market_event_columns(kind: str) -> tuple[str, ...]:
    try:
        return MARKET_EVENT_COLUMNS[kind]
    except KeyError as exc:
        raise ValueError(
            f"未知 event kind: {kind!r}（可选 {sorted(MARKET_EVENT_COLUMNS)}）"
        ) from exc
ADJUSTMENT_EVENT_COLUMNS = (
    "code",
    "ex_date",
    "dividend_per_share",
    "per_share_bonus",
)
_DATE_COLUMNS = (
    "date",
    "ex_date",
    "obs_date",
    "list_date",
    "delist_date",
    "setup_date",
    "ann_date",
    "end_date",
    "ipo_date",
    "issue_date",
)


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
    required = [c for c in columns if c != "currency"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ResponseParseError(
            f"响应缺少字段 {missing}；实际字段: {list(df.columns)}"
        )
    out = df.loc[:, [c for c in columns if c in df.columns]].copy(deep=False)
    for column in _DATE_COLUMNS:
        if column not in out.columns:
            continue
        try:
            out[column] = pd.to_datetime(out[column]).astype("datetime64[ns]")
        except (ValueError, TypeError) as exc:
            raise ResponseParseError(f"日期列 {column} 解析失败: {exc}") from exc
    if "currency" in columns and "code" in out.columns:
        derived = out["code"].map(lambda value: currency_for_code(str(value)))
        if "currency" in out.columns:
            out["currency"] = out["currency"].where(out["currency"].notna(), derived)
        else:
            out["currency"] = derived
        out = out.reindex(columns=list(columns))
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
