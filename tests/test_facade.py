import pandas as pd
import pytest

from fin_data_hub import (
    Capability,
    FinDataHub,
    HubConfig,
    ResponseParseError,
    Source,
    TushareConfig,
    UnsupportedCapability,
)
from fin_data_hub.schemas import FINANCIAL_COLUMNS, MARKET_EVENT_COLUMNS
from fin_data_hub.sources import BaseAdapter, SourceRegistry


class FakeAdapter(BaseAdapter):
    source = Source.TUSHARE
    capabilities = frozenset(
        {
            Capability.BARS,
            Capability.SNAPSHOT,
            Capability.FUND_NAV,
            Capability.REFERENCE,
            Capability.TRADE_CALENDAR,
            Capability.SECURITY_INFO,
            Capability.INDEX_WEIGHTS,
            Capability.FINANCIALS,
            Capability.MARKET_EVENTS,
        }
    )

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.break_bars = False

    def fetch_bars(self, codes, *, start, end, freq, adjust, fields):
        self.calls.append(
            ("bars", tuple(c.canonical for c in codes), start, end, freq, adjust, fields)
        )
        rows = [
            {
                "code": c.canonical,
                "date": "2026-01-05",
                "open": 1.0,
                "high": 1.1,
                "low": 0.9,
                "close": 1.05,
                "volume": 100,
                "amount": 105.0,
            }
            for c in codes
        ]
        df = pd.DataFrame(rows)
        if self.break_bars:
            df = df.drop(columns=["amount"])
        return df

    def fetch_snapshot(self, codes, *, fields):
        self.calls.append(("snapshot", tuple(c.canonical for c in codes), fields))
        return pd.DataFrame(
            [
                {
                    "code": c.canonical,
                    "date": "2026-01-05",
                    "last": 1.05,
                    "open": 1.0,
                    "high": 1.1,
                    "low": 0.9,
                    "prev_close": 1.0,
                    "volume": 100,
                    "amount": 105.0,
                }
                for c in codes
            ]
        )

    def fetch_fund_nav(self, codes, *, start, end):
        self.calls.append(("fund_nav", tuple(c.canonical for c in codes), start, end))
        return pd.DataFrame(
            [
                {
                    "code": c.canonical,
                    "date": "2026-01-05",
                    "unit_nav": 1.23,
                    "accum_nav": 3.45,
                    "daily_return": 0.1,
                }
                for c in codes
            ]
        )

    def fetch_reference(self, kind):
        self.calls.append(("reference", kind))
        if kind == "stock_list":
            return pd.DataFrame(
                [
                    {
                        "code": "600000.SH",
                        "name": "浦发银行",
                        "list_date": "1999-11-10",
                        "market": "主板",
                        "industry": "银行",
                    }
                ]
            )
        return pd.DataFrame(
            [
                {
                    "code": "000001.OF",
                    "name": "示例基金",
                    "fund_type": "混合型",
                    "management": "示例基金公司",
                    "list_date": None,
                    "market": "O",
                }
            ]
        )

    def fetch_security_info(self, codes):
        self.calls.append(("security_info", tuple(c.canonical for c in codes)))
        return pd.DataFrame(
            [
                {
                    "code": code.canonical,
                    "name": "浦发银行",
                    "sec_type": "stock",
                    "market": "SH",
                    "list_status": "L",
                    "list_date": "1999-11-10",
                    "delist_date": None,
                }
                for code in codes
            ]
        )

    def fetch_index_weights(self, codes, *, start, end):
        self.calls.append(("index_weights", tuple(c.canonical for c in codes), start, end))
        return pd.DataFrame(
            [
                {
                    "code": code.canonical,
                    "date": "2026-08-31",
                    "con_code": "600519.SH",
                    "weight": 3.66,
                }
                for code in codes
            ]
        )

    def fetch_market_events(self, *, kind, start, end, codes=None):
        self.calls.append(("market_events", kind, tuple(c.canonical for c in (codes or []))))
        row = {column: None for column in MARKET_EVENT_COLUMNS[kind]}
        row.update(
            {
                "code": "000004.SZ",
                "name": "示例标的",
                "date": "2026-01-05",
                "ipo_date": "2026-01-05",
                "issue_date": "2026-01-05",
                "st_type": "ST",
                "type_name": "风险警示板",
            }
        )
        return pd.DataFrame([row])

    def fetch_financials(self, codes, *, kind, start, end):
        self.calls.append(("financials", kind, tuple(c.canonical for c in codes)))
        row = {
            column: 1.0
            for column in FINANCIAL_COLUMNS[kind]
            if column not in ("code", "currency")
        }
        row.update(
            {
                "code": codes[0].canonical,
                "ann_date": "2026-04-30",
                "end_date": "2025-12-31",
                "report_type": "1",
            }
        )
        return pd.DataFrame([row])

    def fetch_trade_calendar(self, *, start, end):
        self.calls.append(("calendar", start, end))
        return pd.DataFrame(
            [
                {"date": "2026-01-05", "is_open": True},
                {"date": "2026-01-06", "is_open": False},
            ]
        )


class BarsOnlyAdapter(FakeAdapter):
    capabilities = frozenset({Capability.BARS})


def make_hub(*, adapter: BaseAdapter | None = None, config: HubConfig | None = None) -> FinDataHub:
    registry = SourceRegistry([adapter or FakeAdapter()])
    return FinDataHub(config or HubConfig(), registry=registry)


def test_get_bars_end_to_end() -> None:
    adapter = FakeAdapter()
    hub = make_hub(adapter=adapter)
    df = hub.get_bars(
        ["600000.SH", "000001.OF"],
        start="20260101",
        end="20260131",
        source=Source.TUSHARE,
    )
    assert list(df.columns) == [
        "code",
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount",
        "currency",
    ]
    assert df.attrs["source"] == "tushare"
    assert df.attrs["cached"] is False
    assert df["currency"].tolist() == ["CNY", "CNY"]
    assert df["date"].dtype == "datetime64[ns]"
    # 适配器收到 SecCode 列表
    call = adapter.calls[0]
    assert call[0] == "bars"
    assert call[1] == ("600000.SH", "000001.OF")


def test_cache_hit_and_force_refresh() -> None:
    adapter = FakeAdapter()
    hub = make_hub(adapter=adapter)
    hub.get_bars(["600000.SH"], start="20260101", end="20260131", source="tushare")
    df2 = hub.get_bars(["600000.SH"], start="20260101", end="20260131", source="tushare")
    assert df2.attrs["cached"] is True
    assert len(adapter.calls) == 1

    df3 = hub.get_bars(
        ["600000.SH"], start="20260101", end="20260131", source="tushare", force=True
    )
    assert df3.attrs["cached"] is False
    assert len(adapter.calls) == 2


def test_unsupported_capability_lists_sources() -> None:
    hub = make_hub(adapter=BarsOnlyAdapter())
    with pytest.raises(UnsupportedCapability) as exc_info:
        hub.get_snapshot(["600000.SH"], source="tushare")
    assert "可用 source" in str(exc_info.value)


def test_unregistered_source_lists_available() -> None:
    hub = make_hub()
    with pytest.raises(UnsupportedCapability) as exc_info:
        hub.get_bars(["600000.SH"], start="20260101", end="20260131", source="wind")
    assert "tushare" in str(exc_info.value)


def test_source_required_without_default() -> None:
    hub = make_hub()
    with pytest.raises(ValueError, match="source"):
        hub.get_bars(["600000.SH"], start="20260101", end="20260131")


def test_default_source_used() -> None:
    hub = make_hub(config=HubConfig(default_source=Source.TUSHARE))
    df = hub.get_bars(["600000.SH"], start="20260101", end="20260131")
    assert df.attrs["source"] == "tushare"


def test_fund_nav_reference_calendar() -> None:
    adapter = FakeAdapter()
    hub = make_hub(adapter=adapter)

    nav = hub.get_fund_nav(["000001.OF"], source="tushare")
    assert list(nav.columns) == [
        "code",
        "date",
        "unit_nav",
        "accum_nav",
        "daily_return",
        "currency",
    ]

    stocks = hub.get_reference("stock_list", source="tushare")
    assert stocks.iloc[0]["name"] == "浦发银行"

    calendar = hub.get_trade_calendar(start="20260101", end="20260131", source="tushare")
    assert calendar["is_open"].tolist() == [True, False]


def test_reference_unknown_kind_rejected() -> None:
    hub = make_hub()
    with pytest.raises(ValueError, match="kind"):
        hub.get_reference("unknown_list", source="tushare")


def test_security_info_schema_and_currency() -> None:
    hub = make_hub(adapter=FakeAdapter())
    df = hub.get_security_info(["600000.SH"], source="tushare")
    assert list(df.columns) == [
        "code",
        "name",
        "sec_type",
        "market",
        "list_status",
        "list_date",
        "delist_date",
        "currency",
    ]
    assert df.iloc[0]["currency"] == "CNY"
    assert str(df["list_date"].dtype) == "datetime64[ns]"


def test_index_weights_schema() -> None:
    hub = make_hub(adapter=FakeAdapter())
    df = hub.get_index_weights(
        ["000300.SH"], start="20260701", end="20260911", source="tushare"
    )
    assert list(df.columns) == ["code", "date", "con_code", "weight"]
    assert df.iloc[0]["code"] == "000300.SH"
    assert df.iloc[0]["con_code"] == "600519.SH"
    assert str(df["date"].dtype) == "datetime64[ns]"


def test_market_events_schema_and_kind_validation() -> None:
    hub = make_hub(adapter=FakeAdapter())
    df = hub.get_market_events(
        kind="st", start="20260101", end="20260131", source="tushare"
    )
    assert list(df.columns) == list(MARKET_EVENT_COLUMNS["st"])
    assert df.iloc[0]["currency"] == "CNY"
    nc = hub.get_market_events(
        kind="namechange", start="20000101", end="20261231", source="tushare"
    )
    assert list(nc.columns) == list(MARKET_EVENT_COLUMNS["namechange"])
    with pytest.raises(ValueError, match="event kind"):
        hub.get_market_events(
            kind="dividend", start="20260101", end="20260131", source="tushare"
        )


def test_financials_schema_and_kind_validation() -> None:
    hub = make_hub(adapter=FakeAdapter())
    df = hub.get_financials(
        ["600519.SH"], kind="balance_sheet", start="20260101", end="20260630", source="tushare"
    )
    assert list(df.columns) == list(FINANCIAL_COLUMNS["balance_sheet"])
    assert df.iloc[0]["total_assets"] == 1.0
    assert df.iloc[0]["currency"] == "CNY"
    assert str(df["ann_date"].dtype) == "datetime64[ns]"

    with pytest.raises(ValueError, match="financial kind"):
        hub.get_financials(
            ["600519.SH"], kind="cashflow", start="20260101", end="20260630", source="tushare"
        )


def test_schema_missing_column_raises_parse_error() -> None:
    adapter = FakeAdapter()
    adapter.break_bars = True
    hub = make_hub(adapter=adapter)
    with pytest.raises(ResponseParseError, match="amount"):
        hub.get_bars(["600000.SH"], start="20260101", end="20260131", source="tushare")


def test_credentials_hidden_in_repr() -> None:
    text = repr(TushareConfig(token="super-secret-token"))
    assert "super-secret-token" not in text


def test_cache_key_separates_adjust_and_dates() -> None:
    adapter = FakeAdapter()
    hub = make_hub(adapter=adapter)
    hub.get_bars(["600000.SH"], start="20260101", end="20260131", source="tushare", adjust="qfq")
    hub.get_bars(["600000.SH"], start="20260101", end="20260131", source="tushare", adjust="hfq")
    assert len(adapter.calls) == 2
