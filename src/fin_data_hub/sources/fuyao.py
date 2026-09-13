"""Fuyao（同花顺金融数据API）REST 适配器。

- 鉴权：请求头 ``X-api-key``（配置注入）；
- 代码：完整 ``thscode``（与 canonical 一致，直通）；
- 响应信封：``{code, message, request_id, data:{timestamp, item[]}}``；
- 一期能力：``bars``（单标的、窗口 ≤10 年自动分块）、``snapshot``（thscodes 批量）、
  ``reference``（标的列表分页）、``trade_calendar``（近一年窗口）。
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx
import pandas as pd

from fin_data_hub.codes import SecCode
from fin_data_hub.config import FuyaoConfig
from fin_data_hub.enums import Capability, Source
from fin_data_hub.errors import (
    MissingCredentialError,
    NetworkError,
    RateLimitError,
    ResponseParseError,
    SourceError,
    UnsupportedCapability,
)
from fin_data_hub.ratelimit import default_rate_limiter_set, retry_call
from fin_data_hub.sources.base import BaseAdapter

_REFERENCE_ASSET_TYPES = {
    "stock_list": "a-share",
    "fund_list": "fund-otc,fund-etf,fund-lof,fund-reits",
    "index_list": "a-share-index",
}
_MAX_WINDOW_DAYS = 3650  # ≈10 年
_MAX_PAGES = 50
_REFERENCE_PAGE_SIZE = 10000


def _date_to_ms(value: str) -> int:
    ts = pd.Timestamp(str(value).strip())
    ts = (
        ts.tz_localize("Asia/Shanghai")
        if ts.tzinfo is None
        else ts.tz_convert("Asia/Shanghai")
    )
    return int(ts.timestamp() * 1000)


def _iso_date(value: str) -> str:
    text = str(value).strip().replace("-", "")
    if len(text) != 8 or not text.isdigit():
        raise ValueError(f"日期格式应为 YYYYMMDD 或 YYYY-MM-DD: {value!r}")
    return f"{text[:4]}-{text[4:6]}-{text[6:]}"


def _ms_to_date(series: pd.Series) -> pd.Series:
    parsed = (
        pd.to_datetime(series, unit="ms", utc=True)
        .dt.tz_convert("Asia/Shanghai")
        .dt.normalize()
        .dt.tz_localize(None)
    )
    return parsed.astype("datetime64[ns]")


def _split_windows(start: str, end: str) -> list[tuple[str, str]]:
    start_ts = pd.Timestamp(str(start).strip())
    end_ts = pd.Timestamp(str(end).strip())
    if start_ts > end_ts:
        raise ValueError("start 不能晚于 end")
    windows: list[tuple[str, str]] = []
    cursor = start_ts
    while cursor <= end_ts:
        chunk_end = min(cursor + pd.Timedelta(days=_MAX_WINDOW_DAYS - 1), end_ts)
        windows.append((cursor.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")))
        cursor = chunk_end + pd.Timedelta(days=1)
    return windows


def _raise_for_code(code: int, message: str) -> None:
    if code == 0:
        return
    if code in (1001, 1002, 1003, 1004):
        raise ValueError(f"Fuyao 参数错误[{code}]: {message}")
    if code == 2001:
        raise MissingCredentialError(f"Fuyao 认证失败: {message}")
    if code == 2003:
        raise UnsupportedCapability(f"Fuyao 权限不足: {message}")
    if code == 4001:
        raise RateLimitError(f"Fuyao 限流: {message}")
    raise SourceError(f"Fuyao 错误[{code}]: {message}")


class FuyaoAdapter(BaseAdapter):
    source = Source.FUYAO
    capabilities = frozenset(
        {
            Capability.BARS,
            Capability.SNAPSHOT,
            Capability.REFERENCE,
            Capability.TRADE_CALENDAR,
            Capability.ADJUSTMENT_EVENTS,
        }
    )

    #: 参考数据分页大小（测试可覆盖）
    reference_page_size = _REFERENCE_PAGE_SIZE

    def __init__(
        self,
        config: FuyaoConfig | None = None,
        *,
        http_client: httpx.Client | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config or FuyaoConfig()
        self._sleep_fn = sleep_fn
        if http_client is not None:
            self._client = http_client
            self._owns_client = False
        else:
            api_key = self._config.api_key
            if not api_key:
                raise MissingCredentialError(
                    "Fuyao 需要 api_key（通过 FuyaoConfig(api_key=...) 注入）"
                )
            self._client = httpx.Client(
                base_url=self._config.base_url,
                timeout=30.0,
                headers={"X-api-key": api_key},
            )
            self._owns_client = True
        self._rate_limits = default_rate_limiter_set(self.source)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> FuyaoAdapter:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

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
            raise UnsupportedCapability(f"Fuyao 适配器暂不支持 freq={freq!r}（仅 1d）")
        if adjust is not None:
            raise UnsupportedCapability(
                "Fuyao 预计算复权序列经对账异常（doc-4：日收益衰减/同日 OHLC 比值不一致），"
                "v0 不支持复权；请使用 Tushare/Wind 复权，或 adjust=None 取原始价后自行按因子计算"
            )
        if len(codes) != 1:
            raise UnsupportedCapability(
                "Fuyao 历史 K 线每次仅支持一个 thscode（多标的请由门面分块）"
            )
        code = codes[0]
        items: list[dict] = []
        for window_start, window_end in _split_windows(start, end):
            data = self._get(
                "/api/a-share/prices/historical",
                {
                    "thscode": code.canonical,
                    "interval": "1d",
                    "start": _date_to_ms(window_start),
                    "end": _date_to_ms(window_end),
                    "adjust": "none",
                },
            )
            items.extend(data.get("item") or [])
        if not items:
            return _empty_bars()
        raw = pd.DataFrame(items)
        return pd.DataFrame(
            {
                "code": code.canonical,
                "date": _ms_to_date(raw["date_ms"]),
                "open": pd.to_numeric(raw["open_price"]),
                "high": pd.to_numeric(raw["high_price"]),
                "low": pd.to_numeric(raw["low_price"]),
                "close": pd.to_numeric(raw["close_price"]),
                "volume": pd.to_numeric(raw["volume"]),
                "amount": pd.to_numeric(raw["turnover"]),
            }
        ).sort_values("date").reset_index(drop=True)

    # ---------------------------------------------------------------- 快照
    def fetch_snapshot(
        self,
        codes: list[SecCode],
        *,
        fields: tuple[str, ...] | None,
    ) -> pd.DataFrame:
        if not codes:
            return _empty_snapshot()
        data = self._get(
            "/api/a-share/prices/snapshot",
            {"thscodes": ",".join(code.canonical for code in codes)},
        )
        items = data.get("item") or []
        if not items:
            return _empty_snapshot()
        raw = pd.DataFrame(items)
        timestamp = data.get("timestamp")
        date_value: Any = (
            pd.NaT if timestamp is None else _ms_to_date(pd.Series([timestamp])).iloc[0]
        )
        return pd.DataFrame(
            {
                "code": raw["thscode"],
                "date": date_value,
                "last": pd.to_numeric(raw["last_price"]),
                "open": pd.to_numeric(raw["open_price"]),
                "high": pd.to_numeric(raw["high_price"]),
                "low": pd.to_numeric(raw["low_price"]),
                "prev_close": pd.to_numeric(raw["prev_price"]),
                "volume": pd.to_numeric(raw["volume"]),
                "amount": pd.to_numeric(raw["turnover"]),
            }
        )

    # -------------------------------------------------------------- 参考数据
    def fetch_reference(self, kind: str) -> pd.DataFrame:
        asset_type = _REFERENCE_ASSET_TYPES.get(kind)
        if asset_type is None:
            raise UnsupportedCapability(f"Fuyao 不支持 reference kind={kind!r}")
        items: list[dict] = []
        offset = 0
        for _ in range(_MAX_PAGES):
            data = self._get(
                "/api/meta/tickers/list",
                {
                    "asset_type": asset_type,
                    "limit": self.reference_page_size,
                    "offset": offset,
                },
            )
            batch = data.get("item") or []
            items.extend(batch)
            if len(batch) < self.reference_page_size:
                break
            offset += len(batch)
        if not items:
            return _empty_reference(kind)
        raw = pd.DataFrame(items)
        list_date = pd.to_datetime(raw["list_date"]).astype("datetime64[ns]")
        if kind == "stock_list":
            return pd.DataFrame(
                {
                    "code": raw["thscode"],
                    "name": raw["name"],
                    "list_date": list_date,
                    "market": raw.get("exchange"),
                    "industry": None,
                }
            )
        if kind == "fund_list":
            return pd.DataFrame(
                {
                    "code": raw["thscode"],
                    "name": raw["name"],
                    "fund_type": None,
                    "management": None,
                    "list_date": list_date,
                    "market": raw.get("exchange"),
                }
            )
        return pd.DataFrame(
            {
                "code": raw["thscode"],
                "name": raw["name"],
                "market": raw.get("exchange"),
                "category": raw.get("asset_type"),
                "publisher": None,
                "list_date": list_date,
            }
        )

    # ---------------------------------------------------- 复权事件（推导用）
    def fetch_adjustment_events(
        self,
        codes: list[SecCode],
        *,
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        """公司行为事件流（复权因子推导输入；接口每次仅一个 thscode）。

        返回 ``code / ex_date / dividend_per_share / per_share_bonus``。
        因子推导需原始价（P_prev）与统一锚点，并须与 Tushare 逐事件对账
        （doc-4、doc-2 §6.16）；本方法不注册为 Router 的 factor_source。
        """
        if not codes:
            raise ValueError("codes 不能为空")
        rows: list[dict] = []
        for code in codes:
            params: dict[str, Any] = {"thscode": code.canonical}
            if start:
                params["from"] = _iso_date(start)
            if end:
                params["to"] = _iso_date(end)
            data = self._get(
                "/api/a-share/corporate-actions/adjustment-factors", params
            )
            for item in data.get("item") or []:
                rows.append(
                    {
                        "code": code.canonical,
                        "ex_date": item["ex_date_ms"],
                        "dividend_per_share": item.get("dividend_per_share", 0.0),
                        "per_share_bonus": item.get("per_share_bonus", 0.0),
                    }
                )
        if not rows:
            return _empty_adjustment_events()
        frame = pd.DataFrame(rows)
        frame["ex_date"] = _ms_to_date(frame["ex_date"])
        frame["dividend_per_share"] = pd.to_numeric(frame["dividend_per_share"])
        frame["per_share_bonus"] = pd.to_numeric(frame["per_share_bonus"])
        return frame.sort_values(["code", "ex_date"]).reset_index(drop=True)

    # ---------------------------------------------------------------- 日历
    def fetch_trade_calendar(self, *, start: str, end: str) -> pd.DataFrame:
        data = self._get("/api/a-share/calendar/trading-days")
        items = data.get("item") or []
        if not items:
            raise SourceError("Fuyao 交易日历为空")
        open_dates = set(
            pd.to_datetime(
                pd.Series([item["date"] for item in items]), format="%Y%m%d"
            ).dt.normalize()
        )
        start_ts = pd.Timestamp(str(start).strip())
        end_ts = pd.Timestamp(str(end).strip())
        if start_ts < min(open_dates) or end_ts > max(open_dates):
            raise SourceError(
                "Fuyao 交易日历仅覆盖近一年（[今日-1年, 今日]），"
                "超出窗口的区间请使用其他 source"
            )
        days = pd.date_range(start_ts, end_ts, freq="D")
        return pd.DataFrame(
            {"date": days, "is_open": [day in open_dates for day in days]}
        )

    # ------------------------------------------------------------------ 内部
    def _get(self, path: str, params: dict | None = None) -> dict:
        def attempt() -> dict:
            self._acquire(path)
            start = time.monotonic()
            try:
                response = self._client.get(path, params=params or {})
            except httpx.HTTPError as exc:
                raise NetworkError(f"Fuyao 请求失败: {exc}") from exc
            finally:
                self._record(path, latency_ms=(time.monotonic() - start) * 1000)
            if response.status_code == 429:
                raise RateLimitError(f"Fuyao 限流: {response.text[:200]}")
            if response.status_code >= 400:
                raise SourceError(
                    f"Fuyao HTTP {response.status_code}: {response.text[:200]}"
                )
            try:
                payload = response.json()
            except ValueError as exc:
                raise ResponseParseError(
                    f"Fuyao 响应不是 JSON: {response.text[:200]}"
                ) from exc
            if not isinstance(payload, dict):
                raise ResponseParseError(f"Fuyao 响应结构异常: {str(payload)[:200]}")
            _raise_for_code(
                int(payload.get("code", -1)), str(payload.get("message", ""))
            )
            data = payload.get("data")
            if not isinstance(data, dict):
                raise ResponseParseError(f"Fuyao 响应缺少 data: {str(payload)[:200]}")
            return data

        return retry_call(
            attempt,
            attempts=max(1, self._config.max_attempts),
            retry_on=(NetworkError, RateLimitError),
            sleep_fn=self._sleep_fn,
        )


def _empty_adjustment_events() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "code": [],
            "ex_date": pd.Series([], dtype="datetime64[ns]"),
            "dividend_per_share": [],
            "per_share_bonus": [],
        }
    )


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


def _empty_reference(kind: str) -> pd.DataFrame:
    columns = {
        "stock_list": ("code", "name", "list_date", "market", "industry"),
        "fund_list": ("code", "name", "fund_type", "management", "list_date", "market"),
        "index_list": ("code", "name", "market", "category", "publisher", "list_date"),
    }[kind]
    return pd.DataFrame(
        {
            column: pd.Series(
                [], dtype="datetime64[ns]" if column == "list_date" else object
            )
            for column in columns
        }
    )
