"""iFinD（同花顺）MCP 适配器。

v0 覆盖：
- ``fund_nav``：``get_fund_market_performance``（NL 聚合，一次请求多只基金）；
- ``bars``：``index_data``（仅指数；股票/基金 K 线暂不支持）；
- ``fetch_edb_series``：``get_edb_data``（**一次仅一个指标**，时间范围可合并）。

NL 响应为 markdown 文本表，解析见 :mod:`fin_data_hub.mcp.parsers`。
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from fin_data_hub.codes import SecCode, SecType
from fin_data_hub.config import IfindConfig
from fin_data_hub.enums import Source
from fin_data_hub.errors import (
    MissingCredentialError,
    ResponseParseError,
    SourceError,
    UnsupportedCapability,
)
from fin_data_hub.mcp import McpHttpClient, McpServerConfig, unwrap_content
from fin_data_hub.mcp.parsers import find_table, parse_markdown_tables, split_unit
from fin_data_hub.sources.base import BaseAdapter

IFIND_BASE_URL = "https://api-mcp.51ifind.com:8643/ds-mcp-servers"
IFIND_SERVERS: dict[str, str] = {
    "stock": f"{IFIND_BASE_URL}/hexin-ifind-ds-stock-mcp",
    "fund": f"{IFIND_BASE_URL}/hexin-ifind-ds-fund-mcp",
    "edb": f"{IFIND_BASE_URL}/hexin-ifind-ds-edb-mcp",
    "index": f"{IFIND_BASE_URL}/hexin-ifind-ds-index-mcp",
    "bond": f"{IFIND_BASE_URL}/hexin-ifind-ds-bond-mcp",
    "news": f"{IFIND_BASE_URL}/hexin-ifind-ds-news-mcp",
    "global_stock": f"{IFIND_BASE_URL}/hexin-ifind-ds-global-stock-mcp",
    "futures": f"{IFIND_BASE_URL}/hexin-ifind-ds-futures-mcp",
}

_BARS_FIELDS = {
    "证券代码": "code",
    "日期": "date",
    "开盘价": "open",
    "最高价": "high",
    "最低价": "low",
    "收盘价": "close",
    "成交量": "volume",
    "成交额": "amount",
}
_BARS_NUMERIC = ("open", "high", "low", "close", "volume", "amount")

_NAV_FIELDS = {
    "证券代码": "code",
    "日期": "date",
    "单位净值": "unit_nav",
    "累计单位净值": "accum_nav",
    "单位净值增长率": "daily_return",
}
_NAV_NUMERIC = ("unit_nav", "accum_nav", "daily_return")


def _iso_date(value: str) -> str:
    text = str(value).strip().replace("-", "")
    if len(text) != 8 or not text.isdigit():
        raise ValueError(f"日期格式应为 YYYYMMDD 或 YYYY-MM-DD: {value!r}")
    return f"{text[:4]}-{text[4:6]}-{text[6:]}"


class IfindAdapter(BaseAdapter):
    source = Source.IFIND
    capabilities = frozenset({BaseAdapter.CAP_BARS, BaseAdapter.CAP_FUND_NAV})

    def __init__(
        self,
        config: IfindConfig | None = None,
        *,
        clients: Mapping[str, Any] | None = None,
    ) -> None:
        self._config = config or IfindConfig()
        self._clients: dict[str, Any] = dict(clients or {})
        self._owns_clients = clients is None

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
            raise UnsupportedCapability(f"iFinD 适配器暂不支持 freq={freq!r}（仅 1d）")
        if adjust:
            raise UnsupportedCapability("iFinD v0 不支持复权行情")
        if any(code.sec_type is not SecType.INDEX for code in codes):
            raise UnsupportedCapability(
                "iFinD v0 的 K 线仅支持指数（index_data）；股票/基金请使用其他 source"
            )
        query = (
            f"{'、'.join(code.canonical for code in codes)} 在 {_iso_date(start)} 至 "
            f"{_iso_date(end)} 的开盘价、最高价、最低价、收盘价、成交量、成交额"
        )
        data = self._call_service("index", "index_data", {"query": query})
        answer = _answer_of(data)
        table = find_table(
            parse_markdown_tables(answer), ("证券代码", "日期", "收盘价")
        )
        if table is None:
            raise ResponseParseError(
                f"iFinD 指数行情无法解析（answer 截断）: {answer[:200]}"
            )
        extracted = _extract(table, _BARS_FIELDS, _BARS_NUMERIC)
        missing = [
            name
            for name in ("code", "date", "open", "high", "low", "close", "volume", "amount")
            if name not in extracted
        ]
        if missing:
            raise ResponseParseError(f"iFinD 指数行情缺少列 {missing}")
        frame = pd.DataFrame(extracted)
        frame["code"] = _canonicalize(frame["code"])
        return frame.sort_values(["code", "date"]).reset_index(drop=True)

    # -------------------------------------------------------------- 基金净值
    def fetch_fund_nav(
        self,
        codes: list[SecCode],
        *,
        start: str | None,
        end: str | None,
    ) -> pd.DataFrame:
        if any(code.sec_type is not SecType.FUND for code in codes):
            raise UnsupportedCapability("iFinD 净值仅支持场外基金（.OF）")
        if not codes:
            return _empty_nav()
        period = (
            f"{_iso_date(start)} 至 {_iso_date(end)}"
            if start and end
            else "最新"
        )
        query = (
            f"{'、'.join(code.canonical for code in codes)} 在 {period} 的单位净值、"
            "累计单位净值、单位净值增长率"
        )
        data = self._call_service(
            "fund", "get_fund_market_performance", {"query": query}
        )
        answer = _answer_of(data)
        table = find_table(
            parse_markdown_tables(answer), ("证券代码", "日期", "单位净值")
        )
        if table is None:
            raise ResponseParseError(
                f"iFinD 基金净值无法解析（answer 截断）: {answer[:200]}"
            )
        extracted = _extract(table, _NAV_FIELDS, _NAV_NUMERIC)
        missing = [name for name in ("code", "date", "unit_nav") if name not in extracted]
        if missing:
            raise ResponseParseError(f"iFinD 基金净值缺少列 {missing}")
        frame = pd.DataFrame(extracted)
        frame["code"] = _canonicalize(frame["code"])
        for optional in ("accum_nav", "daily_return"):
            if optional not in frame.columns:
                frame[optional] = pd.NA
        if start:
            frame = frame[frame["date"] >= pd.to_datetime(_iso_date(start))]
        if end:
            frame = frame[frame["date"] <= pd.to_datetime(_iso_date(end))]
        return frame.sort_values(["code", "date"]).reset_index(drop=True)

    # ---------------------------------------------------------------- EDB
    def fetch_edb_series(
        self, indicators: Sequence[str], *, start: str, end: str
    ) -> pd.DataFrame:
        """查询单个 EDB 指标（iFinD 限制：一次一个，时间范围可合并）。"""
        if len(indicators) != 1:
            raise ValueError(
                f"iFinD EDB 一次只能查询一个指标，收到 {len(indicators)} 个"
                "（时间范围可合并，指标不可合并）"
            )
        indicator = str(indicators[0]).strip()
        if not indicator:
            raise ValueError("indicator 不能为空")
        query = f"{indicator}（{start.strip()} - {end.strip()}）"
        data = self._call_service("edb", "get_edb_data", {"query": query})
        return _edb_frame(data, indicator)

    # ------------------------------------------------------------------ 内部
    def _client(self, service: str) -> Any:
        if service not in IFIND_SERVERS:
            raise SourceError(f"未知 iFinD 服务: {service!r}")
        client = self._clients.get(service)
        if client is not None:
            return client
        token = self._config.authorization
        if not token:
            raise MissingCredentialError(
                "iFinD 需要 authorization（通过 IfindConfig(authorization=...) 注入）"
            )
        client = McpHttpClient(
            McpServerConfig(
                name=f"ifind-{service}",
                url=IFIND_SERVERS[service],
                token=token,
                auth_scheme="raw",
            )
        )
        self._clients[service] = client
        return client

    def _call_service(self, service: str, tool: str, arguments: dict) -> Any:
        client = self._client(service)
        start = time.monotonic()
        try:
            result = client.call_tool(tool, arguments)
        finally:
            self._record(tool, latency_ms=(time.monotonic() - start) * 1000)
        payload = unwrap_content(result)
        if not isinstance(payload, dict):
            raise ResponseParseError(f"iFinD 响应结构异常: {str(payload)[:200]}")
        if payload.get("code") != 1:
            raise SourceError(
                f"iFinD {service}.{tool} 返回错误: {str(payload)[:200]}"
            )
        data = payload.get("data")
        if isinstance(data, str):
            try:
                return json.loads(data)
            except ValueError as exc:
                raise ResponseParseError(
                    f"iFinD data 不是合法 JSON: {data[:200]}"
                ) from exc
        return data


def _answer_of(data: Any) -> str:
    if isinstance(data, dict) and isinstance(data.get("answer"), str):
        return data["answer"]
    raise ResponseParseError(f"iFinD 响应缺少 answer: {str(data)[:200]}")


def _extract(
    table: pd.DataFrame, mapping: dict[str, str], numeric_fields: tuple[str, ...]
) -> dict[str, pd.Series]:
    extracted: dict[str, pd.Series] = {}
    for column in table.columns:
        base, factor = split_unit(str(column))
        field = mapping.get(base)
        if field is None:
            continue
        values: pd.Series = table[column]
        if field in numeric_fields:
            values = pd.to_numeric(values, errors="coerce") * factor
        elif field == "date":
            values = pd.to_datetime(values, errors="coerce").astype("datetime64[ns]")
        extracted[field] = values
    return extracted


def _canonicalize(series: pd.Series) -> pd.Series:
    def convert(value: Any) -> str:
        try:
            return SecCode.parse(str(value)).canonical
        except Exception:  # noqa: BLE001 - 保留原值，交由上层校验
            return str(value)

    return series.map(convert)


def _edb_frame(data: Any, indicator: str) -> pd.DataFrame:
    datas = data.get("datas") if isinstance(data, dict) else None
    if not datas:
        raise ResponseParseError(f"iFinD EDB 响应缺少 datas: {str(data)[:200]}")
    container = datas[0].get("data") if isinstance(datas[0], dict) else None
    if not isinstance(container, dict):
        raise ResponseParseError(f"iFinD EDB data 结构异常: {str(datas[0])[:200]}")
    columns = container.get("columns")
    rows = container.get("data")
    if not columns or rows is None:
        raise ResponseParseError(f"iFinD EDB 缺少 columns/data: {str(container)[:200]}")
    frame = pd.DataFrame(rows, columns=columns)
    date_column = next(
        (c for c in frame.columns if "日期" in str(c) or "时间" in str(c)), None
    )
    value_column = None
    for column in frame.columns:
        if column == date_column or "指标" in str(column):
            continue
        numeric = pd.to_numeric(frame[column], errors="coerce")
        if numeric.notna().all():
            value_column = column
            break
    if date_column is None or value_column is None:
        raise ResponseParseError(
            f"iFinD EDB 无法识别日期/数值列: {list(frame.columns)}"
        )
    return pd.DataFrame(
        {
            "indicator": indicator,
            "obs_date": pd.to_datetime(frame[date_column]).astype("datetime64[ns]"),
            "value": pd.to_numeric(frame[value_column]),
        }
    ).sort_values("obs_date").reset_index(drop=True)


def _empty_nav() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "code": [],
            "date": pd.Series([], dtype="datetime64[ns]"),
            "unit_nav": [],
            "accum_nav": [],
            "daily_return": [],
        }
    )
