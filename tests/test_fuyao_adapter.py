
import httpx
import pandas as pd
import pytest

from fin_data_hub import FuyaoConfig, SecCode, Source
from fin_data_hub.errors import (
    MissingCredentialError,
    RateLimitError,
    ResponseParseError,
    SourceError,
    UnsupportedCapability,
)
from fin_data_hub.ratelimit import DEFAULT_RATE_LIMITS, RateLimiter
from fin_data_hub.sources.fuyao import FuyaoAdapter, _date_to_ms, _ms_to_date
from fin_data_hub.usage import UsageLedger

BASE = "https://fuyao.test"


def envelope(data: dict, *, code: int = 0, message: str = "success") -> httpx.Response:
    return httpx.Response(
        200,
        json={"code": code, "message": message, "request_id": "req-1", "data": data},
    )


def make_adapter(handler, *, api_key: str | None = "test-key"):
    client = httpx.Client(transport=httpx.MockTransport(handler), base_url=BASE)
    config = FuyaoConfig(api_key=api_key, base_url=BASE)
    return FuyaoAdapter(config, http_client=client), client


def bars_handler(requests: list[httpx.Request]):
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return envelope(
            {
                "timestamp": 1757347200000,
                "item": [
                    {
                        "date_ms": 1757260800000,
                        "open_price": 10.0,
                        "high_price": 10.5,
                        "low_price": 9.9,
                        "close_price": 10.3,
                        "volume": 1_000_000,
                        "turnover": 10_300_000.0,
                    },
                    {
                        "date_ms": 1757347200000,
                        "open_price": 10.2,
                        "high_price": 10.4,
                        "low_price": 10.0,
                        "close_price": 10.1,
                        "volume": 1_200_000,
                        "turnover": 12_100_000.0,
                    },
                ],
            }
        )

    return handler


def test_bars_mapping_and_default_adjust() -> None:
    requests: list[httpx.Request] = []
    adapter, client = make_adapter(bars_handler(requests))
    df = adapter.fetch_bars(
        [SecCode.parse("600519.SH")],
        start="2026-09-01",
        end="2026-09-11",
        freq="1d",
        adjust=None,
        fields=None,
    )
    assert len(requests) == 1
    params = requests[0].url.params
    assert params["thscode"] == "600519.SH"
    assert params["interval"] == "1d"
    assert params["adjust"] == "none"
    assert list(df.columns) == [
        "code",
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
    ]
    assert str(df["date"].dtype) == "datetime64[ns]"
    assert df["close"].tolist() == [10.3, 10.1]
    assert df["amount"].tolist() == [10_300_000.0, 12_100_000.0]
    client.close()


@pytest.mark.parametrize("adjust", ["qfq", "hfq"])
def test_bars_adjust_rejected_after_reconciliation(adjust: str) -> None:
    adapter, client = make_adapter(bars_handler([]))
    with pytest.raises(UnsupportedCapability, match="复权"):
        adapter.fetch_bars(
            [SecCode.parse("600519.SH")],
            start="20260901",
            end="20260911",
            freq="1d",
            adjust=adjust,
            fields=None,
        )
    client.close()


def test_bars_window_chunking_over_10_years() -> None:
    requests: list[httpx.Request] = []
    adapter, client = make_adapter(bars_handler(requests))
    adapter.fetch_bars(
        [SecCode.parse("600519.SH")],
        start="2000-01-01",
        end="2026-01-01",
        freq="1d",
        adjust=None,
        fields=None,
    )
    assert len(requests) == 3
    for request in requests:
        start_ms = int(request.url.params["start"])
        end_ms = int(request.url.params["end"])
        assert (end_ms - start_ms) / 86_400_000 <= 3650
    client.close()


def test_bars_rejects_multi_code_and_invalid_params() -> None:
    adapter, client = make_adapter(bars_handler([]))
    with pytest.raises(UnsupportedCapability):
        adapter.fetch_bars(
            [SecCode.parse("600519.SH"), SecCode.parse("600000.SH")],
            start="20260901",
            end="20260911",
            freq="1d",
            adjust=None,
            fields=None,
        )
    with pytest.raises(UnsupportedCapability):
        adapter.fetch_bars(
            [SecCode.parse("600519.SH")],
            start="20260901",
            end="20260911",
            freq="1w",
            adjust=None,
            fields=None,
        )
    with pytest.raises(UnsupportedCapability):
        adapter.fetch_bars(
            [SecCode.parse("600519.SH")],
            start="20260901",
            end="20260911",
            freq="1d",
            adjust="raw",
            fields=None,
        )
    client.close()


def test_snapshot_mapping_and_batch_param() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return envelope(
            {
                "timestamp": 1757558400000,
                "total": 2,
                "item": [
                    {
                        "thscode": "600519.SH",
                        "ticker": "600519",
                        "last_price": 1277.8,
                        "price_change": 21.8,
                        "price_change_ratio_pct": 1.74,
                        "open_price": 1252.08,
                        "high_price": 1282.0,
                        "low_price": 1250.21,
                        "prev_price": 1256.0,
                        "volume": 3_098_875,
                        "turnover": 3_937_375_200.0,
                    }
                ],
            }
        )

    adapter, client = make_adapter(handler)
    df = adapter.fetch_snapshot(
        [SecCode.parse("600519.SH"), SecCode.parse("000001.SZ")], fields=None
    )
    assert requests[0].url.params["thscodes"] == "600519.SH,000001.SZ"
    assert list(df.columns) == [
        "code",
        "date",
        "last",
        "open",
        "high",
        "low",
        "prev_close",
        "volume",
        "amount",
    ]
    row = df.iloc[0]
    assert row["code"] == "600519.SH"
    assert row["last"] == pytest.approx(1277.8)
    assert row["amount"] == pytest.approx(3_937_375_200.0)
    assert str(df["date"].dtype) == "datetime64[ns]"
    client.close()


def test_reference_pagination_and_mapping() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        offset = int(request.url.params["offset"])
        items = [
            {
                "thscode": f"60000{offset + i}.SH",
                "ticker": f"60000{offset + i}",
                "name": f"示例{offset + i}",
                "exchange": "SH",
                "asset_type": "a-share",
                "currency": "CNY",
                "list_date": "2001-08-27",
                "end_date": None,
                "last_trade_date": None,
                "last_delivery_date": None,
            }
            for i in range(2 if offset == 0 else 1)
        ]
        return envelope({"timestamp": 1757558400000, "item": items})

    adapter, client = make_adapter(handler)
    adapter.reference_page_size = 2
    df = adapter.fetch_reference("stock_list")
    assert len(requests) == 2
    assert [request.url.params["asset_type"] for request in requests] == [
        "a-share",
        "a-share",
    ]
    assert len(df) == 3
    assert list(df.columns) == ["code", "name", "list_date", "market", "industry"]
    assert str(df["list_date"].dtype) == "datetime64[ns]"
    client.close()


def test_reference_unknown_kind() -> None:
    adapter, client = make_adapter(bars_handler([]))
    with pytest.raises(UnsupportedCapability):
        adapter.fetch_reference("bond_list")
    client.close()


def test_trade_calendar_and_window_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return envelope(
            {
                "timestamp": 1757558400000,
                "item": [
                    {"date_ms": 1757260800000, "date": "20250908"},
                    {"date_ms": 1757347200000, "date": "20250909"},
                ],
            }
        )

    adapter, client = make_adapter(handler)
    df = adapter.fetch_trade_calendar(start="2025-09-08", end="2025-09-09")
    assert df["is_open"].tolist() == [True, True]

    with pytest.raises(SourceError, match="近一年"):
        adapter.fetch_trade_calendar(start="2020-01-01", end="2020-01-10")
    client.close()


@pytest.mark.parametrize(
    ("code", "exception"),
    [
        (1001, ValueError),
        (2001, MissingCredentialError),
        (2003, UnsupportedCapability),
        (4001, RateLimitError),
        (3001, SourceError),
        (5001, SourceError),
    ],
)
def test_error_code_mapping(code: int, exception: type[Exception]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return envelope({"item": []}, code=code, message="boom")

    adapter, client = make_adapter(handler)
    with pytest.raises(exception):
        adapter.fetch_trade_calendar(start="2025-09-08", end="2025-09-09")
    client.close()


def test_http_429_and_500_mapping() -> None:
    def handler_429(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="too many requests")

    adapter, client = make_adapter(handler_429)
    with pytest.raises(RateLimitError):
        adapter.fetch_snapshot([SecCode.parse("600519.SH")], fields=None)
    client.close()

    def handler_500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="server error")

    adapter, client = make_adapter(handler_500)
    with pytest.raises(SourceError, match="500"):
        adapter.fetch_snapshot([SecCode.parse("600519.SH")], fields=None)
    client.close()


def test_unparseable_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>not json</html>")

    adapter, client = make_adapter(handler)
    with pytest.raises(ResponseParseError):
        adapter.fetch_snapshot([SecCode.parse("600519.SH")], fields=None)
    client.close()


def test_missing_credential_raises() -> None:
    with pytest.raises(MissingCredentialError):
        FuyaoAdapter(FuyaoConfig(api_key=None))


def test_capabilities_and_default_rate_limit() -> None:
    adapter, client = make_adapter(bars_handler([]))
    assert adapter.capabilities == frozenset(
        {"bars", "snapshot", "reference", "trade_calendar", "adjustment_events"}
    )
    assert DEFAULT_RATE_LIMITS[Source.FUYAO].rate == 2.0
    client.close()


def test_usage_and_rate_limit_wired() -> None:
    class SpyLimiter:
        def __init__(self) -> None:
            self.calls: list[str | None] = []

        def acquire(self, endpoint=None, tokens=1.0, *, timeout=None) -> None:
            self.calls.append(endpoint)

    def handler(request: httpx.Request) -> httpx.Response:
        return envelope(
            {
                "timestamp": 1757558400000,
                "item": [
                    {
                        "thscode": "600519.SH",
                        "last_price": 1.0,
                        "open_price": 1.0,
                        "high_price": 1.0,
                        "low_price": 1.0,
                        "prev_price": 1.0,
                        "volume": 1,
                        "turnover": 1.0,
                    }
                ],
            }
        )

    adapter, client = make_adapter(handler)
    spy = SpyLimiter()
    adapter.bind_rate_limits(spy)  # type: ignore[arg-type]
    ledger = UsageLedger()
    adapter.bind_usage(ledger)
    adapter.fetch_snapshot([SecCode.parse("600519.SH")], fields=None)
    assert spy.calls == ["/api/a-share/prices/snapshot"]
    assert ledger.summary()["sources"]["fuyao"]["calls"] == 1
    client.close()


def test_date_helpers_roundtrip() -> None:
    assert _ms_to_date(pd.Series([0])).iloc[0] == pd.Timestamp("1970-01-01")
    expected = int(pd.Timestamp("2026-09-01", tz="Asia/Shanghai").timestamp() * 1000)
    assert _date_to_ms("2026-09-01") == expected


def test_rate_limiter_default_set() -> None:
    from fin_data_hub.ratelimit import default_rate_limiter_set

    limiter = default_rate_limiter_set(Source.FUYAO)
    assert isinstance(limiter.default, RateLimiter)
    assert limiter.default.rate == 2.0


def test_rate_limit_error_retried() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return envelope({"item": []}, code=4001, message="rate limited")
        return envelope(
            {
                "timestamp": 1757558400000,
                "item": [
                    {
                        "thscode": "600519.SH",
                        "last_price": 1.0,
                        "open_price": 1.0,
                        "high_price": 1.0,
                        "low_price": 1.0,
                        "prev_price": 1.0,
                        "volume": 1,
                        "turnover": 1.0,
                    }
                ],
            }
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url=BASE)
    adapter = FuyaoAdapter(
        FuyaoConfig(api_key="test-key", base_url=BASE, max_attempts=2),
        http_client=client,
        sleep_fn=lambda _: None,
    )
    df = adapter.fetch_snapshot([SecCode.parse("600519.SH")], fields=None)
    assert len(df) == 1
    assert calls["n"] == 2
    client.close()


def test_adjustment_events_mapping_and_per_code_calls() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return envelope(
            {
                "thscode": "600519.SH",
                "ticker": "600519",
                "item": [
                    {
                        "ticker": "600519",
                        "ex_date_ms": 1782403200000,
                        "dividend_per_share": 28.02423,
                        "per_share_bonus": 0,
                    },
                    {
                        "ticker": "600519",
                        "ex_date_ms": 1766073600000,
                        "dividend_per_share": 23.957,
                        "per_share_bonus": 0,
                    },
                ],
            }
        )

    adapter, client = make_adapter(handler)
    df = adapter.fetch_adjustment_events(
        [SecCode.parse("600519.SH"), SecCode.parse("000001.SZ")],
        start="2026-01-01",
        end="2026-09-11",
    )
    assert len(requests) == 2  # 单标的接口 → 逐代码调用
    assert requests[0].url.params["thscode"] == "600519.SH"
    assert requests[0].url.params["from"] == "2026-01-01"
    assert requests[0].url.params["to"] == "2026-09-11"
    assert list(df.columns) == [
        "code",
        "ex_date",
        "dividend_per_share",
        "per_share_bonus",
    ]
    assert str(df["ex_date"].dtype) == "datetime64[ns]"
    assert len(df) == 4
    client.close()


def test_adjustment_events_empty_and_missing_codes() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return envelope({"thscode": "600519.SH", "ticker": "600519", "item": []})

    adapter, client = make_adapter(handler)
    df = adapter.fetch_adjustment_events([SecCode.parse("600519.SH")])
    assert df.empty
    assert list(df.columns) == [
        "code",
        "ex_date",
        "dividend_per_share",
        "per_share_bonus",
    ]
    with pytest.raises(ValueError):
        adapter.fetch_adjustment_events([])
    client.close()


def test_fuyao_is_not_router_factor_source() -> None:
    adapter, client = make_adapter(bars_handler([]))
    assert "adjust_factors" not in adapter.capabilities
    client.close()
