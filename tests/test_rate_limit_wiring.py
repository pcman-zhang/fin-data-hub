import json

import pandas as pd
import pytest

from fin_data_hub import FinDataHub, HubConfig, Source
from fin_data_hub.errors import RateLimitTimeout
from fin_data_hub.ratelimit import (
    DEFAULT_RATE_LIMITS,
    RateLimitConfig,
    RateLimiter,
    RateLimiterSet,
    default_rate_limiter_set,
)
from fin_data_hub.sources import BaseAdapter, SourceRegistry
from fin_data_hub.sources.akshare import AkShareAdapter
from fin_data_hub.sources.ifind import IfindAdapter
from fin_data_hub.sources.tushare import TushareAdapter
from fin_data_hub.sources.wind import WindAdapter


class SpyLimiter:
    def __init__(self) -> None:
        self.calls: list[str | None] = []

    def acquire(self, endpoint=None, tokens=1.0, *, timeout=None) -> None:
        self.calls.append(endpoint)


class MiniTushareApi:
    def trade_cal(self, **kwargs):
        return pd.DataFrame({"cal_date": ["20260105"], "is_open": [1]})


class MiniAkModule:
    def tool_trade_date_hist_sina(self, **kwargs):
        return pd.DataFrame({"trade_date": ["2026-01-05"]})


class StubIfindClient:
    def call_tool(self, tool, arguments=None):
        payload = {
            "code": 1,
            "msg": "success",
            "data": {
                "datas": [
                    {
                        "data": {
                            "columns": ["指标名称", "日期", "数值"],
                            "data": [["示例指标", "20260105", 1.0]],
                        }
                    }
                ]
            },
        }
        return {
            "content": [
                {"type": "text", "text": json.dumps(payload, ensure_ascii=False)}
            ]
        }


class StubWindClient:
    def call_tool(self, tool, arguments=None):
        payload = {
            "data": {
                "date": ["20260105"],
                "indicatorInfo": [
                    {"code": "M0000001", "name": "示例指标", "data": [1.0]}
                ],
            },
            "error": None,
        }
        return {
            "content": [
                {"type": "text", "text": json.dumps(payload, ensure_ascii=False)}
            ]
        }


def test_default_table_has_ifind_2_qps() -> None:
    assert DEFAULT_RATE_LIMITS[Source.IFIND].rate == 2.0
    assert DEFAULT_RATE_LIMITS[Source.IFIND].burst == 2.0
    assert default_rate_limiter_set(Source.IFIND).default.rate == 2.0


def test_tushare_acquires_before_call() -> None:
    adapter = TushareAdapter(api=MiniTushareApi())
    spy = SpyLimiter()
    adapter.bind_rate_limits(spy)  # type: ignore[arg-type]
    adapter.fetch_trade_calendar(start="20260105", end="20260105")
    assert spy.calls == ["trade_cal"]


def test_akshare_acquires_before_call() -> None:
    adapter = AkShareAdapter(ak_module=MiniAkModule())
    spy = SpyLimiter()
    adapter.bind_rate_limits(spy)  # type: ignore[arg-type]
    adapter.fetch_trade_calendar(start="20260105", end="20260105")
    assert spy.calls == ["tool_trade_date_hist_sina"]


def test_ifind_acquires_before_call() -> None:
    adapter = IfindAdapter(clients={"edb": StubIfindClient()})
    spy = SpyLimiter()
    adapter.bind_rate_limits(spy)  # type: ignore[arg-type]
    adapter.fetch_edb_series(["示例指标"], start="20260101", end="20260131")
    assert spy.calls == ["get_edb_data"]


def test_wind_acquires_before_call() -> None:
    adapter = WindAdapter(clients={"economic_data": StubWindClient()})
    spy = SpyLimiter()
    adapter.bind_rate_limits(spy)  # type: ignore[arg-type]
    adapter.fetch_economic_indicators(
        ["M0000001"], start="2026-01-01", end="2026-01-31"
    )
    assert spy.calls == ["get_economic_data"]


def test_adapter_has_default_limiter() -> None:
    adapter = TushareAdapter(api=MiniTushareApi())
    assert adapter._rate_limits is not None
    assert adapter._rate_limits.default.rate == DEFAULT_RATE_LIMITS[Source.TUSHARE].rate


class TrackingAdapter(BaseAdapter):
    source = Source.TUSHARE
    capabilities = frozenset({BaseAdapter.CAP_BARS})

    def fetch_bars(self, codes, *, start, end, freq, adjust, fields):
        self._acquire("daily")
        self._record("daily")
        return pd.DataFrame(
            [
                {
                    "code": code.canonical,
                    "date": "2026-01-05",
                    "open": 1.0,
                    "high": 1.0,
                    "low": 1.0,
                    "close": 1.0,
                    "volume": 1,
                    "amount": 1.0,
                }
                for code in codes
            ]
        )


def test_facade_timeout_raises_rate_limit_timeout() -> None:
    config = HubConfig(
        rate_limits={
            "tushare": RateLimitConfig(rate=0.001, burst=1, timeout=0.01)
        }
    )
    hub = FinDataHub(config, registry=SourceRegistry([TrackingAdapter()]))
    hub.get_bars(["600000.SH"], start="20260101", end="20260131", source="tushare")
    # 令牌耗尽：不同请求键（绕过缓存）应因等待限流超时
    with pytest.raises(RateLimitTimeout):
        hub.get_bars(
            ["600001.SH"], start="20260101", end="20260131", source="tushare"
        )


def test_rate_limiter_set_uses_default_timeout() -> None:
    limiter = RateLimiter(rate=0.001, burst=1)
    limiter.acquire()
    limiters = RateLimiterSet(limiter, timeout=0.01)
    with pytest.raises(RateLimitTimeout):
        limiters.acquire("any")
