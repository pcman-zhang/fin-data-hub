"""Wind MCP 适配器（get 优先）。

v0 覆盖：
- ``bars``：``get_{stock,fund,index}_kline``（单代码逐次调用；日线省略 ``period``
  —— 实测后端不接受 ``period=1d``；复权映射 ``None→2 / qfq→0 / hfq→1``）；
- ``snapshot``：``get_{stock,fund,index}_price_indicators``（单次 ≤50 代码）；
- ``fetch_economic_indicators``：``get_economic_data``（精确代码逗号批量）；
- ``fetch_bond_market_data``：``get_bond_market_data``（长区间按 ≤90 天分块，
  问句用中文日期）。

Wind 返回为 JSON 文本：``{"data": {"columns": [...], "rows": [...], "unit": {...}}}``
（``columns`` 元素形如 ``{"name", "type"}``），本模块统一解析并换算单位。
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any

import pandas as pd

from fin_data_hub.codes import SecCode, SecType
from fin_data_hub.config import WindConfig
from fin_data_hub.enums import Capability, Source
from fin_data_hub.errors import (
    MissingCredentialError,
    ResponseParseError,
    SourceError,
    UnsupportedCapability,
)
from fin_data_hub.mcp import McpHttpClient, McpServerConfig, unwrap_content
from fin_data_hub.ratelimit import default_rate_limiter_set
from fin_data_hub.sources.base import BaseAdapter

WIND_BASE_URL = "https://mcp.wind.com.cn"
WIND_SERVERS: dict[str, str] = {
    name: f"{WIND_BASE_URL}/vserver_{name}/mcp/"
    for name in (
        "stock_data",
        "fund_data",
        "index_data",
        "bond_data",
        "financial_docs",
        "economic_data",
        "analytics_data",
    )
}

_KLINE_FIELDS = {
    "TIME": "date",
    "OPEN": "open",
    "MATCH": "close",
    "HIGH": "high",
    "LOW": "low",
    "VOLUME": "volume",
    "TURNOVER": "amount",
}
_KLINE_TOOL = {
    SecType.STOCK: ("stock_data", "get_stock_kline"),
    SecType.ETF: ("fund_data", "get_fund_kline"),
    SecType.LOF: ("fund_data", "get_fund_kline"),
    SecType.INDEX: ("index_data", "get_index_kline"),
}
_ADJUST_TO_AFTYPE = {None: "2", "qfq": "0", "hfq": "1"}

_SNAPSHOT_FIELDS = {
    "最新交易日": "date",
    "最新成交价": "last",
    "前收盘价": "prev_close",
    "今日开盘价": "open",
    "今日最高价": "high",
    "今日最低价": "low",
    "成交量": "volume",
    "成交额": "amount",
    "Wind代码": "code",
}
_SNAPSHOT_INDEXES = (
    "最新交易日,最新成交价,前收盘价,今日开盘价,今日最高价,今日最低价,成交量,成交额"
)
_SNAPSHOT_TOOL = {
    SecType.STOCK: ("stock_data", "get_stock_price_indicators"),
    SecType.ETF: ("fund_data", "get_fund_price_indicators"),
    SecType.LOF: ("fund_data", "get_fund_price_indicators"),
    SecType.INDEX: ("index_data", "get_index_price_indicators"),
}
_MAX_WINDCODES_PER_CALL = 50

_UNIT_FACTORS: tuple[tuple[str, float], ...] = (
    ("亿元", 1e8),
    ("万元", 1e4),
    ("千元", 1e3),
    ("元", 1.0),
    ("手", 100.0),
    ("股", 1.0),
)


def _iso_date(value: str) -> str:
    text = str(value).strip().replace("-", "")
    if len(text) != 8 or not text.isdigit():
        raise ValueError(f"日期格式应为 YYYYMMDD 或 YYYY-MM-DD: {value!r}")
    return f"{text[:4]}-{text[4:6]}-{text[6:]}"


def _to_naive_ns(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series)
    if getattr(parsed.dtype, "tz", None) is not None:
        parsed = parsed.dt.tz_localize(None)
    return parsed.astype("datetime64[ns]")


def _unit_factor(label: str) -> float:
    text = str(label).strip()
    for suffix, factor in _UNIT_FACTORS:
        if text.endswith(suffix):
            return factor
    return 1.0


class WindAdapter(BaseAdapter):
    source = Source.WIND
    capabilities = frozenset({Capability.BARS, Capability.SNAPSHOT})

    def __init__(
        self,
        config: WindConfig | None = None,
        *,
        clients: Mapping[str, Any] | None = None,
    ) -> None:
        self._config = config or WindConfig()
        self._clients: dict[str, Any] = dict(clients or {})
        self._owns_clients = clients is None
        self._rate_limits = default_rate_limiter_set(self.source)

    def close(self) -> None:
        if not self._owns_clients:
            return
        for client in self._clients.values():
            close = getattr(client, "close", None)
            if callable(close):
                close()
        self._clients.clear()

    # ------------------------------------------------------------------ 行情
    def fetch_bars(
        self,
        codes: list[SecCode],
        *,
        start: str,
        end: str,
        freq: str,
        adjust: str | None,
        fields: tuple[str, ...] | None,
    ) -> pd.DataFrame:
        if freq not in ("1d", "d", "D"):
            raise UnsupportedCapability(
                "Wind 适配器 v0 仅支持日线（实测后端不接受 period=1d，日线需省略）"
            )
        if adjust not in _ADJUST_TO_AFTYPE:
            raise ValueError(f"adjust 仅支持 None/qfq/hfq: {adjust!r}")
        frames = [self._fetch_bars_one(code, start=start, end=end, adjust=adjust) for code in codes]
        if not frames:
            return _empty_bars()
        return pd.concat(frames, ignore_index=True)

    def _fetch_bars_one(
        self, code: SecCode, *, start: str, end: str, adjust: str | None
    ) -> pd.DataFrame:
        route = _KLINE_TOOL.get(code.sec_type)
        if route is None:
            raise UnsupportedCapability(
                f"Wind K 线不支持 {code.sec_type}（场外基金请用基金净值）"
            )
        service, tool = route
        arguments: dict[str, Any] = {
            "windcode": code.canonical,
            "begin_date": _iso_date(start),
            "end_date": _iso_date(end),
            "aftype": _ADJUST_TO_AFTYPE[adjust],
        }
        data = self._call_data(service, tool, arguments)
        frame = _wind_table(data)
        if frame.empty:
            return _empty_bars()
        return _map_kline(frame, code, data.get("unit") or {})

    # ---------------------------------------------------------------- 快照
    def fetch_snapshot(
        self,
        codes: list[SecCode],
        *,
        fields: tuple[str, ...] | None,
    ) -> pd.DataFrame:
        if not codes:
            return _empty_snapshot()
        groups: dict[tuple[str, str], list[SecCode]] = {}
        for code in codes:
            route = _SNAPSHOT_TOOL.get(code.sec_type)
            if route is None:
                raise UnsupportedCapability(f"Wind 快照不支持 {code.sec_type}")
            groups.setdefault(route, []).append(code)

        frames = []
        for (service, tool), group in groups.items():
            for start_index in range(0, len(group), _MAX_WINDCODES_PER_CALL):
                chunk = group[start_index : start_index + _MAX_WINDCODES_PER_CALL]
                windcodes = ",".join(code.canonical for code in chunk)
                data = self._call_data(
                    service,
                    tool,
                    {"windcode": windcodes, "indexes": _SNAPSHOT_INDEXES},
                )
                frames.append(
                    _map_snapshot(_wind_table(data), chunk, data.get("unit") or {})
                )
        return pd.concat(frames, ignore_index=True)

    # ---------------------------------------------------------------- EDB
    def fetch_economic_indicators(
        self,
        metric_ids: Sequence[str],
        *,
        start: str,
        end: str,
        magnitude: str | None = None,
        currency: str | None = None,
    ) -> pd.DataFrame:
        """精确 EDB 代码批量取数（get_economic_data）。"""
        ids = [str(m).strip().upper() for m in metric_ids if str(m).strip()]
        if not ids:
            raise ValueError("metric_ids 不能为空")
        if not start or not end:
            raise ValueError("必须显式提供 start 与 end（beginDate/endDate 成对）")
        arguments: dict[str, Any] = {
            "metricIdsStr": ",".join(ids),
            "beginDate": _iso_date(start),
            "endDate": _iso_date(end),
        }
        if magnitude:
            arguments["magnitude"] = magnitude
        if currency:
            arguments["currency"] = currency
        data = self._call_data("economic_data", "get_economic_data", arguments)
        return _map_economic(data)

    # --------------------------------------------------------------- 债券
    def fetch_bond_market_data(
        self,
        symbols: Sequence[str],
        *,
        start: str,
        end: str,
        chunk_days: int = 90,
        indicators: str = "收盘价、到期收益率、久期、凸性",
    ) -> pd.DataFrame:
        """债券行情（NL 问句）：长区间自动按 ``chunk_days`` 分块，中文日期。"""
        names = [str(s).strip() for s in symbols if str(s).strip()]
        if not names:
            raise ValueError("symbols 不能为空")
        if chunk_days <= 0 or chunk_days > 90:
            raise ValueError("chunk_days 必须在 1~90 之间（后端约 100 行截断）")
        start_date = pd.to_datetime(_iso_date(start)).date()
        end_date = pd.to_datetime(_iso_date(end)).date()
        if start_date > end_date:
            raise ValueError("start 不能晚于 end")

        frames: list[pd.DataFrame] = []
        cursor = start_date
        while cursor <= end_date:
            chunk_end = min(cursor + timedelta(days=chunk_days - 1), end_date)
            question = (
                f"查询 {'、'.join(names)} 在 {_zh_date(cursor)}至{_zh_date(chunk_end)} "
                f"的行情数据，包括{indicators}"
            )
            data = self._call_data(
                "bond_data", "get_bond_market_data", {"question": question}
            )
            frames.append(_wind_table(data))
            cursor = chunk_end + timedelta(days=1)
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    # ------------------------------------------------------------------ 内部
    def _client(self, service: str) -> Any:
        if service not in WIND_SERVERS:
            raise SourceError(f"未知 Wind 服务: {service!r}")
        client = self._clients.get(service)
        if client is not None:
            return client
        api_key = self._config.api_key
        if not api_key:
            raise MissingCredentialError(
                "Wind 需要 api_key（通过 WindConfig(api_key=...) 注入）"
            )
        client = McpHttpClient(
            McpServerConfig(
                name=f"wind-{service}",
                url=WIND_SERVERS[service],
                token=api_key,
                auth_scheme="bearer",
            )
        )
        self._clients[service] = client
        return client

    def _call_data(self, service: str, tool: str, arguments: dict) -> dict:
        client = self._client(service)
        self._acquire(tool)
        start = time.monotonic()
        try:
            result = client.call_tool(tool, arguments)
        finally:
            self._record(tool, latency_ms=(time.monotonic() - start) * 1000)
        payload = unwrap_content(result)
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except ValueError as exc:
                raise ResponseParseError(
                    f"Wind {tool} 响应不是合法 JSON: {payload[:200]}"
                ) from exc
        if not isinstance(payload, dict):
            raise ResponseParseError(f"Wind {tool} 响应结构异常: {str(payload)[:200]}")
        if payload.get("error"):
            raise SourceError(f"Wind {tool} 返回错误: {str(payload['error'])[:200]}")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ResponseParseError(f"Wind {tool} 缺少 data: {str(payload)[:200]}")
        return data


def _wind_table(data: dict) -> pd.DataFrame:
    columns = data.get("columns")
    rows = data.get("rows")
    if columns is None and rows is None:
        return pd.DataFrame()
    names: list[str] = []
    for column in columns or []:
        if isinstance(column, dict):
            names.append(str(column.get("name", "")))
        else:
            names.append(str(column))
    return pd.DataFrame(rows or [], columns=names, dtype=object)


def _unit_map(unit: Any) -> dict[str, float]:
    if not isinstance(unit, dict):
        return {}
    result: dict[str, float] = {}
    for key, value in unit.items():
        name = (
            str(key)
            .replace("单位：", "")
            .replace("单位:", "")
            .strip()
        )
        result[name] = _unit_factor(str(value))
    return result


def _factors_for(column: str, units: dict[str, float]) -> float:
    if column in units:
        return units[column]
    upper = column.upper()
    for name, factor in units.items():
        if name.upper() == upper:
            return factor
    return 1.0


def _map_kline(frame: pd.DataFrame, code: SecCode, unit: Any) -> pd.DataFrame:
    units = _unit_map(unit)
    result: dict[str, pd.Series] = {}
    for column in frame.columns:
        field = _KLINE_FIELDS.get(str(column).upper())
        if field is None:
            continue
        values: pd.Series = frame[column]
        if field == "date":
            values = _to_naive_ns(values)
        else:
            values = pd.to_numeric(values, errors="coerce") * _factors_for(
                str(column), units
            )
        result[field] = values
    missing = [
        name
        for name in ("date", "open", "high", "low", "close", "volume", "amount")
        if name not in result
    ]
    if missing:
        raise ResponseParseError(f"Wind K 线缺少列 {missing}: {list(frame.columns)}")
    order = ("date", "open", "high", "low", "close", "volume", "amount")
    out = pd.DataFrame({name: result[name] for name in order})
    out.insert(0, "code", code.canonical)
    return out.sort_values("date").reset_index(drop=True)


def _map_snapshot(
    frame: pd.DataFrame, codes: list[SecCode], unit: Any
) -> pd.DataFrame:
    units = _unit_map(unit)
    result: dict[str, pd.Series] = {}
    for column in frame.columns:
        field = _SNAPSHOT_FIELDS.get(str(column))
        if field is None:
            continue
        values: pd.Series = frame[column]
        if field == "date":
            values = _to_naive_ns(values)
        elif field != "code":
            values = pd.to_numeric(values, errors="coerce") * _factors_for(
                str(column), units
            )
        result[field] = values
    if "code" not in result:
        if len(codes) != 1:
            raise ResponseParseError(
                "Wind 快照缺少 Wind代码 列，无法匹配多标的"
            )
        result["code"] = pd.Series([codes[0].canonical] * len(frame))
    missing = [
        name
        for name in ("date", "last", "open", "high", "low", "prev_close", "volume")
        if name not in result
    ]
    if missing:
        raise ResponseParseError(f"Wind 快照缺少列 {missing}: {list(frame.columns)}")
    amount = result.get("amount", pd.Series([pd.NA] * len(frame)))
    out = pd.DataFrame(
        {
            "code": result["code"],
            "date": result["date"],
            "last": result["last"],
            "open": result["open"],
            "high": result["high"],
            "low": result["low"],
            "prev_close": result["prev_close"],
            "volume": result["volume"],
            "amount": amount,
        }
    )
    return out


def _map_economic(data: dict) -> pd.DataFrame:
    dates = data.get("date") or []
    infos = data.get("indicatorInfo") or []
    if not dates or not infos:
        raise ResponseParseError(f"Wind EDB 响应缺少 date/indicatorInfo: {str(data)[:200]}")
    obs_dates = _to_naive_ns(pd.Series(dates))
    frames = []
    for info in infos:
        code = str(info.get("code", "")).strip()
        values = info.get("data") or []
        frames.append(
            pd.DataFrame(
                {
                    "indicator": code,
                    "obs_date": obs_dates,
                    "value": pd.to_numeric(pd.Series(values), errors="coerce"),
                }
            )
        )
    return pd.concat(frames, ignore_index=True).sort_values(
        ["indicator", "obs_date"]
    ).reset_index(drop=True)


def _zh_date(value: date) -> str:
    return f"{value.year}年{value.month}月{value.day}日"


def _empty_bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "code": [],
            "date": pd.Series([], dtype="datetime64[ns]"),
            "open": [],
            "high": [],
            "low": [],
            "close": [],
            "volume": [],
            "amount": [],
        }
    )


def _empty_snapshot() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "code": [],
            "date": pd.Series([], dtype="datetime64[ns]"),
            "last": [],
            "open": [],
            "high": [],
            "low": [],
            "prev_close": [],
            "volume": [],
            "amount": [],
        }
    )
