import pandas as pd
import pytest

from fin_data_hub import FinDataHub, HubConfig, RoutingConfig, SecCode, Source
from fin_data_hub.errors import SourceError, UnsupportedCapability
from fin_data_hub.sources import BaseAdapter, SourceRegistry
from fin_data_hub.sources.tushare import TushareAdapter

DATES = ("2026-01-05", "2026-01-06")


class RawBarsAdapter(BaseAdapter):
    """模拟 Fuyao：只有原始价，且可配置缺失字段/失败。"""

    source = Source.FUYAO
    capabilities = frozenset({BaseAdapter.CAP_BARS})

    def __init__(self, *, missing: tuple[str, ...] = (), fail: bool = False) -> None:
        self.missing = missing
        self.fail = fail
        self.adjust_seen: list[str | None] = []

    def fetch_bars(self, codes, *, start, end, freq, adjust, fields):
        self.adjust_seen.append(adjust)
        if self.fail:
            raise SourceError("primary down")
        rows = []
        for code in codes:
            for index, day in enumerate(DATES):
                row = {
                    "code": code.canonical,
                    "date": day,
                    "open": 10.0 * (index + 1),
                    "high": 10.0 * (index + 1),
                    "low": 10.0 * (index + 1),
                    "close": 10.0 * (index + 1),
                    "volume": 100,
                    "amount": 1000.0,
                }
                for column in self.missing:
                    row.pop(column, None)
                rows.append(row)
        return pd.DataFrame(rows)


class FillBarsAdapter(BaseAdapter):
    """模拟 AkShare 等补充源：提供完整字段。"""

    source = Source.AKSHARE
    capabilities = frozenset({BaseAdapter.CAP_BARS})

    def fetch_bars(self, codes, *, start, end, freq, adjust, fields):
        return pd.DataFrame(
            [
                {
                    "code": code.canonical,
                    "date": day,
                    "open": 1.0,
                    "high": 1.0,
                    "low": 1.0,
                    "close": 1.0,
                    "volume": 1,
                    "amount": 7.0,
                }
                for code in codes
                for day in DATES
            ]
        )


class FactorAdapter(BaseAdapter):
    """模拟 Tushare：复权因子。"""

    source = Source.TUSHARE
    capabilities = frozenset(
        {BaseAdapter.CAP_BARS, BaseAdapter.CAP_ADJUST_FACTORS}
    )

    def __init__(self, factors=(("2026-01-05", 1.0), ("2026-01-06", 2.0))) -> None:
        self.factors = factors
        self.calls = 0
        self.adjust_seen: list[str | None] = []

    def fetch_adjust_factors(self, codes, *, start, end):
        self.calls += 1
        return pd.DataFrame(
            {
                "code": [code.canonical for code in codes for _ in self.factors],
                "date": pd.to_datetime(
                    [day for _ in codes for day, _ in self.factors]
                ).astype("datetime64[ns]"),
                "adj_factor": [factor for _ in codes for _, factor in self.factors],
            }
        )

    def fetch_bars(self, codes, *, start, end, freq, adjust, fields):
        self.adjust_seen.append(adjust)
        return RawBarsAdapter().fetch_bars(
            codes, start=start, end=end, freq=freq, adjust=adjust, fields=fields
        )


def make_hub(*adapters, config: HubConfig | None = None) -> FinDataHub:
    return FinDataHub(config or HubConfig(), registry=SourceRegistry(list(adapters)))


def test_routing_defaults() -> None:
    routing = RoutingConfig()
    assert routing.factor_source is Source.TUSHARE
    assert Source.FUYAO not in routing.trusted_native_adjust
    assert routing.field_fill is True


def test_composed_hfq_uses_raw_plus_factor() -> None:
    raw = RawBarsAdapter()
    factor = FactorAdapter()
    hub = make_hub(raw, factor)
    df = hub.get_bars(
        ["600519.SH"], start="20260101", end="20260131", adjust="hfq", source="fuyao"
    )
    # hfq = raw × factor：10×1=10；20×2=40
    assert df["close"].tolist() == [10.0, 40.0]
    assert raw.adjust_seen == [None]  # 主源取原始价
    assert factor.calls == 1
    assert df.attrs["factor_source"] == "tushare"
    assert df.attrs["requested_source"] == "fuyao"


def test_composed_qfq_uses_latest_factor() -> None:
    hub = make_hub(RawBarsAdapter(), FactorAdapter())
    df = hub.get_bars(
        ["600519.SH"], start="20260101", end="20260131", adjust="qfq", source="fuyao"
    )
    # qfq = raw × f / f_latest（f_latest=2.0）：10×0.5=5；20×1=20
    assert df["close"].tolist() == [5.0, 20.0]


def test_trusted_source_uses_native_adjust() -> None:
    factor = FactorAdapter()
    hub = make_hub(factor)
    df = hub.get_bars(
        ["600519.SH"], start="20260101", end="20260131", adjust="qfq", source="tushare"
    )
    assert factor.adjust_seen == ["qfq"]  # 原生复权，不组合
    assert "factor_source" not in df.attrs


def test_field_fill_from_fallback() -> None:
    raw = RawBarsAdapter(missing=("amount",))
    fill = FillBarsAdapter()
    config = HubConfig(routing=RoutingConfig(fallbacks=(Source.AKSHARE,)))
    hub = make_hub(raw, fill, config=config)
    df = hub.get_bars(
        ["600519.SH"], start="20260101", end="20260131", source="fuyao"
    )
    assert df["amount"].tolist() == [7.0, 7.0]
    assert df.attrs["filled_from"] == {"amount": "akshare"}
    assert df.attrs["source"] == "fuyao"


def test_primary_failure_falls_back() -> None:
    raw = RawBarsAdapter(fail=True)
    fill = FillBarsAdapter()
    config = HubConfig(routing=RoutingConfig(fallbacks=(Source.AKSHARE,)))
    hub = make_hub(raw, fill, config=config)
    df = hub.get_bars(
        ["600519.SH"], start="20260101", end="20260131", source="fuyao"
    )
    assert not df.empty
    assert df.attrs["source"] == "akshare"


def test_no_factor_source_raises() -> None:
    config = HubConfig(routing=RoutingConfig(factor_source=None))
    hub = make_hub(RawBarsAdapter(), config=config)
    with pytest.raises(UnsupportedCapability, match="因子源"):
        hub.get_bars(
            ["600519.SH"], start="20260101", end="20260131", adjust="hfq", source="fuyao"
        )


def test_missing_factor_raises() -> None:
    hub = make_hub(RawBarsAdapter(), FactorAdapter(factors=()))
    with pytest.raises(SourceError, match="复权因子缺失"):
        hub.get_bars(
            ["600519.SH"], start="20260101", end="20260131", adjust="hfq", source="fuyao"
        )


class MiniTushareApi:
    def adj_factor(self, **kwargs):
        return pd.DataFrame(
            {
                "ts_code": ["600519.SH", "600519.SH"],
                "trade_date": ["20260105", "20260106"],
                "adj_factor": [1.5, 2.0],
            }
        )


def test_tushare_fetch_adjust_factors() -> None:
    adapter = TushareAdapter(api=MiniTushareApi())
    df = adapter.fetch_adjust_factors(
        [SecCode.parse("600519.SH")], start="20260101", end="20260131"
    )
    assert list(df.columns) == ["code", "date", "adj_factor"]
    assert df["adj_factor"].tolist() == [1.5, 2.0]
    assert str(df["date"].dtype) == "datetime64[ns]"
    assert adapter.capabilities == frozenset(
        {"bars", "fund_nav", "reference", "trade_calendar", "adjust_factors"}
    )
