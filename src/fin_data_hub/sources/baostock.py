"""BaoStock 免费源适配器（A 股）。

线程安全：baostock 使用模块级全局会话（login/socket），**不是线程安全的**。
本适配器用模块级 ``RLock`` 串行化所有登录/查询/登出操作。

**会话恢复**：会话以「代际（generation）+ 引用计数」管理；网络异常/会话失效时
递增代际并失效会话，下一次调用检测到代际不一致会**重新 login**；查询失败会
自动失效会话并按退避重试（``BaostockConfig.max_attempts``）。

- 代码：canonical ↔ ``sh.600000`` / ``sz.399006``（映射层转换，仅 SH/SZ）；
- 复权：原生 ``adjustflag``（None→3 / qfq→2 / hfq→1）；默认不在 Router
  ``trusted_native_adjust`` 内（复权走 raw + factor 合成）；
- 单位：``volume``=股、``amount``=元（与 canonical 一致）；
- 能力：bars（单代码）、reference（stock_list）、trade_calendar、
  adjust_factors（``query_adjust_factor``，**仅股票**，事件步进 + 窗口基准行）。
"""

from __future__ import annotations

import contextlib
import threading
import time
from collections.abc import Callable
from typing import Any

import pandas as pd

from fin_data_hub.codes import SecCode
from fin_data_hub.config import BaostockConfig
from fin_data_hub.enums import Capability, SecType, Source
from fin_data_hub.errors import SourceError, UnsupportedCapability
from fin_data_hub.mapping import get_mapper
from fin_data_hub.ratelimit import compute_backoff, default_rate_limiter_set
from fin_data_hub.sources.base import BaseAdapter
from fin_data_hub.specs import load_spec, normalize

_BAOSTOCK_LOCK = threading.RLock()
_LOGIN_COUNT = 0
_SESSION_GENERATION = 0
_ADJUST_FLAGS = {None: "3", "qfq": "2", "hfq": "1"}
_BARS_FIELDS = "date,code,open,high,low,close,volume,amount"
_FACTOR_LOOKBACK_START = "1990-01-01"  # A 股最早上市日之前，确保取全历史事件
_CONNECTION_HINTS = (
    "网络",
    "连接",
    "超时",
    "登录",
    "login",
    "socket",
    "timeout",
    "断开",
    "重连",
)


def _reset_session_state() -> None:  # pragma: no cover - 测试辅助
    """重置全局会话状态（仅测试使用）。"""
    global _LOGIN_COUNT, _SESSION_GENERATION
    with _BAOSTOCK_LOCK:
        _LOGIN_COUNT = 0
        _SESSION_GENERATION = 0


def _invalidate_session() -> None:
    """标记当前会话失效（连接/登录异常），下次调用将重新 login。"""
    global _LOGIN_COUNT, _SESSION_GENERATION
    with _BAOSTOCK_LOCK:
        _SESSION_GENERATION += 1
        _LOGIN_COUNT = 0


def _is_connection_error(message: str) -> bool:
    text = message.lower()
    return any(hint in text for hint in _CONNECTION_HINTS)


def _iso_date(value: str) -> str:
    text = str(value).strip().replace("-", "")
    if len(text) != 8 or not text.isdigit():
        raise ValueError(f"日期格式应为 YYYYMMDD 或 YYYY-MM-DD: {value!r}")
    return f"{text[:4]}-{text[4:6]}-{text[6:]}"


class BaoStockAdapter(BaseAdapter):
    source = Source.BAOSTOCK
    capabilities = frozenset(
        {
            Capability.BARS,
            Capability.REFERENCE,
            Capability.TRADE_CALENDAR,
            Capability.ADJUST_FACTORS,
        }
    )

    def __init__(
        self,
        config: BaostockConfig | None = None,
        *,
        bs_module: Any | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config or BaostockConfig()
        self._bs = bs_module if bs_module is not None else _default_module()
        self._mapper = get_mapper(self.source)
        self._rate_limits = default_rate_limiter_set(self.source)
        self._spec = load_spec(self.source)
        self._sleep_fn = sleep_fn
        self._closed = False
        self._login_acquired = False
        self._session_generation: int | None = None

    def close(self) -> None:
        global _LOGIN_COUNT
        with _BAOSTOCK_LOCK:
            if self._closed:
                return
            self._closed = True
            if (
                self._login_acquired
                and self._session_generation == _SESSION_GENERATION
            ):
                self._login_acquired = False
                if _LOGIN_COUNT > 0:
                    _LOGIN_COUNT -= 1
                if _LOGIN_COUNT == 0:
                    with contextlib.suppress(Exception):
                        self._bs.logout()
            self._session_generation = None

    def __enter__(self) -> BaoStockAdapter:
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
            raise UnsupportedCapability(f"BaoStock 适配器暂不支持 freq={freq!r}（仅 1d）")
        if adjust not in _ADJUST_FLAGS:
            raise ValueError(f"adjust 仅支持 None/qfq/hfq: {adjust!r}")
        if len(codes) != 1:
            raise UnsupportedCapability(
                "BaoStock K 线每次仅支持一个代码（多标的请由门面分块）"
            )
        code = codes[0]
        started = time.monotonic()
        self._acquire("query_history_k_data_plus")
        try:
            rows, columns = self._query(
                "query_history_k_data_plus",
                code=self._mapper.to_source(code),
                fields=_BARS_FIELDS,
                start_date=_iso_date(start),
                end_date=_iso_date(end),
                frequency="d",
                adjustflag=_ADJUST_FLAGS[adjust],
            )
        finally:
            self._record(
                "query_history_k_data_plus",
                latency_ms=(time.monotonic() - started) * 1000,
            )
        if not rows:
            return _empty_bars()
        raw = pd.DataFrame(rows, columns=columns)
        frame = normalize(
            raw,
            self._spec.responses["bars"],
            source=self.source,
            code=code.canonical,
        )
        return frame.sort_values("date").reset_index(drop=True)

    # -------------------------------------------------------------- 参考数据
    def fetch_reference(self, kind: str) -> pd.DataFrame:
        if kind != "stock_list":
            raise UnsupportedCapability(f"BaoStock 不支持 reference kind={kind!r}")
        started = time.monotonic()
        self._acquire("query_stock_basic")
        try:
            rows, columns = self._query("query_stock_basic")
        finally:
            self._record(
                "query_stock_basic", latency_ms=(time.monotonic() - started) * 1000
            )
        if not rows:
            return _empty_stock_list()
        raw = pd.DataFrame(rows, columns=columns)
        codes = [
            self._mapper.from_source(str(value)).canonical for value in raw["code"]
        ]
        return pd.DataFrame(
            {
                "code": codes,
                "name": raw["code_name"],
                "list_date": pd.to_datetime(raw["ipoDate"], errors="coerce").astype(
                    "datetime64[ns]"
                ),
                "market": [code.rsplit(".", 1)[1] for code in codes],
                "industry": None,
            }
        )

    # ------------------------------------------------------------ 复权因子
    def fetch_adjust_factors(
        self, codes: list[SecCode], *, start: str, end: str
    ) -> pd.DataFrame:
        """复权因子（``query_adjust_factor``，仅股票；事件步进 + 窗口基准行）。

        输出 ``code/date/adj_factor``：``adj_factor`` 为累计后复权因子
        （``backAdjustFactor``），首个事件前恒为 1.0。窗口内事件日逐行给出，
        并在 ``start`` 处补一行窗口基准因子（自 ``1990-01-01`` 取最近事件），
        供事件步进式对齐（Router ``apply_adjustment``）使用；对账与覆盖范围见
        doc-8 / doc-9。
        """
        if len(codes) != 1:
            raise UnsupportedCapability(
                "BaoStock 复权因子每次仅支持一个代码（多标的请由门面分块）"
            )
        code = codes[0]
        if code.sec_type is not SecType.STOCK:
            raise UnsupportedCapability(
                "BaoStock 复权因子仅覆盖股票（实测，见 doc-9）："
                f"{code.canonical} 为 {code.sec_type}"
            )
        started = time.monotonic()
        self._acquire("query_adjust_factor")
        try:
            rows, columns = self._query(
                "query_adjust_factor",
                code=self._mapper.to_source(code),
                start_date=_FACTOR_LOOKBACK_START,
                end_date=_iso_date(end),
            )
        finally:
            self._record(
                "query_adjust_factor",
                latency_ms=(time.monotonic() - started) * 1000,
            )
        if rows:
            parsed = (
                normalize(
                    pd.DataFrame(rows, columns=columns),
                    self._spec.responses["adjust_factors"],
                    source=self.source,
                )
                .sort_values("date")
                .dropna(subset=["date", "adj_factor"])
                .drop_duplicates(subset=["date"], keep="last")
                .reset_index(drop=True)
            )
        else:
            parsed = pd.DataFrame(
                {
                    "date": pd.Series([], dtype="datetime64[ns]"),
                    "adj_factor": pd.Series([], dtype=float),
                }
            )
        return _factors_frame(
            code, parsed, start=_iso_date(start), end=_iso_date(end)
        )

    # ---------------------------------------------------------------- 日历
    def fetch_trade_calendar(self, *, start: str, end: str) -> pd.DataFrame:
        started = time.monotonic()
        self._acquire("query_trade_dates")
        try:
            rows, columns = self._query(
                "query_trade_dates",
                start_date=_iso_date(start),
                end_date=_iso_date(end),
            )
        finally:
            self._record(
                "query_trade_dates", latency_ms=(time.monotonic() - started) * 1000
            )
        if not rows:
            return pd.DataFrame(
                {
                    "date": pd.Series([], dtype="datetime64[ns]"),
                    "is_open": pd.Series([], dtype=bool),
                }
            )
        raw = pd.DataFrame(rows, columns=columns)
        return (
            normalize(
                raw, self._spec.responses["trade_calendar"], source=self.source
            )
            .sort_values("date")
            .reset_index(drop=True)
        )

    # ------------------------------------------------------------------ 内部
    def _ensure_login(self) -> None:
        global _LOGIN_COUNT
        if (
            self._login_acquired
            and self._session_generation == _SESSION_GENERATION
        ):
            return
        if _LOGIN_COUNT == 0:
            result = self._bs.login()
            if getattr(result, "error_code", "0") != "0":
                raise ConnectionError(
                    f"BaoStock 登录失败: {getattr(result, 'error_msg', '')}"
                )
        _LOGIN_COUNT += 1
        self._login_acquired = True
        self._session_generation = _SESSION_GENERATION

    def _query(self, method: str, **kwargs: Any) -> tuple[list[list[str]], list[str]]:
        """在全局锁内执行查询；连接类失败会失效会话并按退避重试（会重新 login）。"""
        attempts = max(1, self._config.max_attempts)
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            with _BAOSTOCK_LOCK:
                try:
                    self._ensure_login()
                    result = getattr(self._bs, method)(**kwargs)
                    error_code = getattr(result, "error_code", "0")
                    message = str(getattr(result, "error_msg", ""))
                    if error_code != "0":
                        if _is_connection_error(message):
                            _invalidate_session()
                            self._session_generation = None
                            raise ConnectionError(message or error_code)
                        raise SourceError(
                            f"BaoStock {method} 错误[{error_code}]: {message}"
                        )
                    rows: list[list[str]] = []
                    while result.next():
                        rows.append(result.get_row_data())
                    return rows, list(getattr(result, "fields", []))
                except SourceError:
                    raise
                except Exception as exc:  # noqa: BLE001 - 网络/会话异常 → 重登录重试
                    _invalidate_session()
                    self._session_generation = None
                    last_error = exc
            if attempt < attempts:
                self._sleep_fn(compute_backoff(attempt, base=1.0, jitter=0.0))
        raise SourceError(
            f"BaoStock {method} 调用失败（{attempts} 次尝试）: {last_error}"
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


def _empty_stock_list() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "code": [],
            "name": [],
            "list_date": pd.Series([], dtype="datetime64[ns]"),
            "market": [],
            "industry": [],
        }
    )


def _factors_frame(
    code: SecCode,
    parsed: pd.DataFrame,
    *,
    start: str,
    end: str,
) -> pd.DataFrame:
    """事件步进因子 → 规范因子帧（基准行 + 窗口内事件行）。"""
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    before = parsed[parsed["date"] < start_ts]
    base = float(before.iloc[-1]["adj_factor"]) if not before.empty else 1.0
    window = parsed[(parsed["date"] >= start_ts) & (parsed["date"] <= end_ts)]
    frames = []
    if window.empty or window["date"].iloc[0] != start_ts:
        frames.append(
            pd.DataFrame(
                {
                    "code": [code.canonical],
                    "date": [start_ts],
                    "adj_factor": [base],
                }
            )
        )
    if not window.empty:
        frames.append(
            pd.DataFrame(
                {
                    "code": [code.canonical] * len(window),
                    "date": window["date"].to_numpy(),
                    "adj_factor": window["adj_factor"].to_numpy(),
                }
            )
        )
    out = pd.concat(frames, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"]).astype("datetime64[ns]")
    return out.sort_values("date").reset_index(drop=True)


def _default_module() -> Any:
    try:
        import baostock
    except ImportError as exc:  # pragma: no cover - 依赖缺失分支
        raise SourceError(
            "未安装 baostock 包：请安装 fin-data-hub[baostock]"
        ) from exc
    return baostock
