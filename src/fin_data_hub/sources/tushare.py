"""Tushare 数据源适配器。

- 代码：canonical（``600000.SH`` / ``000001.OF``）直通 ``ts_code``；
- 单位统一：``volume`` 股（Tushare 手 ×100）、``amount`` 元（Tushare 千元 ×1000）；
- 复权：``None`` 用 ``daily``；``qfq`` / ``hfq`` 用 ``adj_factor`` 计算
  （``qfq = price * factor / latest_factor``，``hfq = price * factor``）；
- 因子接口按资产类型选择：股票 ``adj_factor``、ETF/LOF ``fund_adj``；
  场外基金/指数无因子（实测，见 doc-8 §3.1）；
- 快照（snapshot）不在能力范围（Tushare 免费接口无稳定实时快照）。
"""

from __future__ import annotations

import time
from typing import Any

import pandas as pd

from fin_data_hub.codes import SecCode
from fin_data_hub.config import TushareConfig
from fin_data_hub.enums import Capability, SecType, Source
from fin_data_hub.errors import MissingCredentialError, SourceError, UnsupportedCapability
from fin_data_hub.mapping import get_mapper
from fin_data_hub.ratelimit import default_rate_limiter_set
from fin_data_hub.sources.base import BaseAdapter
from fin_data_hub.specs import load_spec, normalize

_FACTOR_ENDPOINTS: dict[SecType, str] = {
    SecType.STOCK: "adj_factor",
    SecType.ETF: "fund_adj",
    SecType.LOF: "fund_adj",
}


def _to_ts_date(value: str) -> str:
    """``YYYY-MM-DD`` / ``YYYYMMDD`` → ``YYYYMMDD``。"""
    text = str(value).strip().replace("-", "")
    if len(text) != 8 or not text.isdigit():
        raise ValueError(f"日期格式应为 YYYYMMDD 或 YYYY-MM-DD: {value!r}")
    return text


def _from_ts_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(
        series.astype(str), format="%Y%m%d", errors="coerce"
    ).astype("datetime64[ns]")


class TushareAdapter(BaseAdapter):
    source = Source.TUSHARE
    capabilities = frozenset(
        {
            Capability.BARS,
            Capability.FUND_NAV,
            Capability.REFERENCE,
            Capability.TRADE_CALENDAR,
            Capability.ADJUST_FACTORS,
        }
    )

    def __init__(
        self,
        config: TushareConfig | None = None,
        *,
        api: Any | None = None,
    ) -> None:
        self._mapper = get_mapper(self.source)
        self._rate_limits = default_rate_limiter_set(self.source)
        self._spec = load_spec(self.source)
        if api is not None:
            self._api = api
            return
        token = (config or TushareConfig()).token
        if not token:
            raise MissingCredentialError(
                "Tushare 需要 token（通过 TushareConfig(token=...) 注入）"
            )
        self._api = _default_api(token)

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
            raise UnsupportedCapability(f"Tushare 适配器暂不支持 freq={freq!r}（仅 1d）")
        if adjust not in (None, "qfq", "hfq"):
            raise ValueError(f"adjust 仅支持 None/qfq/hfq: {adjust!r}")

        ts_codes = [self._mapper.to_source(c) for c in codes]
        raw = self._query(
            "daily",
            ts_code=",".join(ts_codes),
            start_date=_to_ts_date(start),
            end_date=_to_ts_date(end),
        )
        if raw.empty:
            return _empty_bars()

        bars = normalize(
            raw,
            self._spec.responses["bars"],
            source=self.source,
            mapper=self._mapper,
        )

        if adjust in ("qfq", "hfq"):
            factors_raw = self._query(
                "adj_factor",
                ts_code=",".join(ts_codes),
                start_date=_to_ts_date(start),
                end_date=_to_ts_date(end),
            )
            if factors_raw.empty:
                raise SourceError("Tushare adj_factor 缺失，无法计算复权价")
            factors = normalize(
                factors_raw,
                self._spec.responses["adjust_factors"],
                source=self.source,
                mapper=self._mapper,
            )
            bars = self._apply_adjust(bars, factors, adjust)

        return bars.sort_values(["code", "date"]).reset_index(drop=True)

    def _apply_adjust(
        self, bars: pd.DataFrame, factors: pd.DataFrame, adjust: str
    ) -> pd.DataFrame:
        merged = bars.merge(factors, on=["code", "date"], how="left")
        if merged["adj_factor"].isna().any():
            raise SourceError("Tushare adj_factor 缺失，无法计算复权价")
        if adjust == "qfq":
            latest = merged.groupby("code")["adj_factor"].transform("last")
            ratio = merged["adj_factor"] / latest
        else:
            ratio = merged["adj_factor"]
        for column in ("open", "high", "low", "close"):
            merged[column] = merged[column] * ratio
        return merged.drop(columns=["adj_factor"])

    # -------------------------------------------------------------- 基金净值
    def fetch_fund_nav(
        self,
        codes: list[SecCode],
        *,
        start: str | None,
        end: str | None,
    ) -> pd.DataFrame:
        ts_codes = [self._mapper.to_source(c) for c in codes]
        kwargs: dict[str, Any] = {"ts_code": ",".join(ts_codes)}
        if start:
            kwargs["start_date"] = _to_ts_date(start)
        if end:
            kwargs["end_date"] = _to_ts_date(end)
        raw = self._query("fund_nav", **kwargs)
        if raw.empty:
            return pd.DataFrame(
                {
                    "code": [],
                    "date": pd.Series([], dtype="datetime64[ns]"),
                    "unit_nav": [],
                    "accum_nav": [],
                    "daily_return": [],
                }
            )
        nav = normalize(
            raw,
            self._spec.responses["fund_nav"],
            source=self.source,
            mapper=self._mapper,
        ).sort_values(["code", "date"])
        nav["daily_return"] = nav.groupby("code")["unit_nav"].pct_change() * 100
        return nav.reset_index(drop=True)

    # -------------------------------------------------------------- 参考数据
    def fetch_reference(self, kind: str) -> pd.DataFrame:
        if kind == "stock_list":
            raw = self._query("stock_basic", fields="ts_code,name,list_date,market,industry")
            return pd.DataFrame(
                {
                    "code": raw["ts_code"],
                    "name": raw["name"],
                    "list_date": _from_ts_date(raw["list_date"]),
                    "market": raw.get("market"),
                    "industry": raw.get("industry"),
                }
            )
        if kind == "fund_list":
            raw = self._query(
                "fund_basic", fields="ts_code,name,fund_type,management,list_date,market"
            )
            return pd.DataFrame(
                {
                    "code": raw["ts_code"],
                    "name": raw["name"],
                    "fund_type": raw.get("fund_type"),
                    "management": raw.get("management"),
                    "list_date": _from_ts_date(raw["list_date"]),
                    "market": raw.get("market"),
                }
            )
        if kind == "index_list":
            raw = self._query(
                "index_basic",
                fields="ts_code,name,market,category,publisher,list_date",
            )
            return pd.DataFrame(
                {
                    "code": raw["ts_code"],
                    "name": raw["name"],
                    "market": raw.get("market"),
                    "category": raw.get("category"),
                    "publisher": raw.get("publisher"),
                    "list_date": _from_ts_date(raw["list_date"]),
                }
            )
        raise UnsupportedCapability(f"Tushare 不支持 reference kind={kind!r}")

    # ------------------------------------------------------------ 复权因子
    def fetch_adjust_factors(
        self, codes: list[SecCode], *, start: str, end: str
    ) -> pd.DataFrame:
        """复权因子（``code/date/adj_factor``）：按资产类型选择接口。

        - 股票 → ``adj_factor``；ETF/LOF → ``fund_adj``；
        - 场外基金/指数无因子 → ``UnsupportedCapability``（不静默回退）。
        """
        unsupported = [
            code.canonical
            for code in codes
            if code.sec_type not in _FACTOR_ENDPOINTS
        ]
        if unsupported:
            raise UnsupportedCapability(
                "Tushare 无复权因子（仅股票/ETF/LOF，实测见 doc-8 §3.1）："
                + ", ".join(unsupported)
            )
        frames = []
        groups: dict[str, list[SecCode]] = {}
        for code in codes:
            groups.setdefault(_FACTOR_ENDPOINTS[code.sec_type], []).append(code)
        for endpoint, group in groups.items():
            raw = self._query(
                endpoint,
                ts_code=",".join(self._mapper.to_source(code) for code in group),
                start_date=_to_ts_date(start),
                end_date=_to_ts_date(end),
            )
            if raw.empty:
                continue
            frames.append(
                normalize(
                    raw,
                    self._spec.responses["adjust_factors"],
                    source=self.source,
                    mapper=self._mapper,
                )
            )
        if not frames:
            return _empty_factors()
        return (
            pd.concat(frames, ignore_index=True)
            .sort_values(["code", "date"])
            .reset_index(drop=True)
        )

    # ---------------------------------------------------------------- 日历
    def fetch_trade_calendar(self, *, start: str, end: str) -> pd.DataFrame:
        raw = self._query(
            "trade_cal",
            exchange="SSE",
            start_date=_to_ts_date(start),
            end_date=_to_ts_date(end),
        )
        return normalize(
            raw, self._spec.responses["trade_calendar"], source=self.source
        ).sort_values("date")

    # ------------------------------------------------------------------ 内部
    def _query(self, endpoint: str, **kwargs: Any) -> pd.DataFrame:
        fn = getattr(self._api, endpoint, None)
        if fn is None:
            raise SourceError(f"Tushare API 缺少接口 {endpoint!r}")
        self._acquire(endpoint)
        start = time.monotonic()
        try:
            result = fn(**kwargs)
        except Exception as exc:  # noqa: BLE001 - 统一映射源端异常
            raise SourceError(f"Tushare {endpoint} 调用失败: {exc}") from exc
        finally:
            self._record(endpoint, latency_ms=(time.monotonic() - start) * 1000)
        if result is None:
            return pd.DataFrame()
        return pd.DataFrame(result)


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


def _empty_factors() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "code": [],
            "date": pd.Series([], dtype="datetime64[ns]"),
            "adj_factor": [],
        }
    )


def _default_api(token: str) -> Any:
    try:
        import tushare
    except ImportError as exc:  # pragma: no cover - 依赖缺失分支
        raise SourceError(
            "未安装 tushare 包：请安装 fin-data-hub[tushare]"
        ) from exc
    return tushare.pro_api(token)
