import pandas as pd
import pytest

from fin_data_hub import Capability, FinDataHub, HubConfig, RoutingConfig, SecCode, Source
from fin_data_hub.errors import SourceError, UnsupportedCapability
from fin_data_hub.sources import BaseAdapter, SourceRegistry
from fin_data_hub.sources.tushare import TushareAdapter

DATES = ("2026-01-05", "2026-01-06")


class RawBarsAdapter(BaseAdapter):
    """模拟 Fuyao：只有原始价，且可配置缺失字段/失败。"""

    source = Source.FUYAO
    capabilities = frozenset({Capability.BARS})

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
    capabilities = frozenset({Capability.BARS})

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
        {Capability.BARS, Capability.ADJUST_FACTORS}
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


class SparseFactorAdapter(BaseAdapter):
    """模拟 BaoStock：事件步进因子 + 窗口基准行（start 可为非交易日）。"""

    source = Source.TUSHARE
    capabilities = frozenset({Capability.ADJUST_FACTORS})

    def fetch_adjust_factors(self, codes, *, start, end):
        return pd.DataFrame(
            {
                "code": [code.canonical for code in codes for _ in range(2)],
                "date": pd.to_datetime(["2026-01-01", "2026-01-06"] * len(codes)),
                "adj_factor": [1.0, 2.0] * len(codes),
            }
        )


@pytest.mark.parametrize(
    ("adjust", "expected"),
    [("hfq", [10.0, 40.0]), ("qfq", [5.0, 20.0])],
)
def test_sparse_factors_backward_align(adjust: str, expected: list[float]) -> None:
    # 因子仅有 2026-01-01（非交易日）基准行与 2026-01-06 事件行；
    # backward 对齐：01-05 用 f=1.0，01-06 用 f=2.0
    hub = make_hub(RawBarsAdapter(), SparseFactorAdapter())
    df = hub.get_bars(
        ["600519.SH"], start="20260101", end="20260131", adjust=adjust, source="fuyao"
    )
    assert df["close"].tolist() == expected


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
        {
            "bars",
            "fund_nav",
            "reference",
            "trade_calendar",
            "security_info",
            "index_weights",
            "financials",
            "market_events",
            "adjust_factors",
        }
    )


class MultiEndpointApi:
    """按 ts_code 返回 adj_factor / fund_adj 两个接口。"""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def adj_factor(self, **kwargs):
        self.calls.append("adj_factor")
        codes = kwargs["ts_code"].split(",")
        return pd.DataFrame(
            {
                "ts_code": codes,
                "trade_date": ["20260105"] * len(codes),
                "adj_factor": [1.5] * len(codes),
            }
        )

    def fund_adj(self, **kwargs):
        self.calls.append("fund_adj")
        codes = kwargs["ts_code"].split(",")
        return pd.DataFrame(
            {
                "ts_code": codes,
                "trade_date": ["20260105"] * len(codes),
                "adj_factor": [1.2] * len(codes),
            }
        )


def test_tushare_factor_endpoint_by_asset_type() -> None:
    api = MultiEndpointApi()
    adapter = TushareAdapter(api=api)
    df = adapter.fetch_adjust_factors(
        [
            SecCode.parse("600519.SH"),
            SecCode.parse("510300.SH"),
            SecCode.parse("161725.SZ"),
        ],
        start="20260101",
        end="20260131",
    )
    assert api.calls == ["adj_factor", "fund_adj"]  # 股票 → adj_factor；ETF/LOF → fund_adj
    assert sorted(df["code"].unique()) == ["161725.SZ", "510300.SH", "600519.SH"]
    assert df["adj_factor"].tolist() == [1.2, 1.2, 1.5]


def test_tushare_factor_unsupported_asset_raises() -> None:
    adapter = TushareAdapter(api=MultiEndpointApi())
    with pytest.raises(UnsupportedCapability, match="无复权因子"):
        adapter.fetch_adjust_factors(
            [SecCode.parse("000001.OF")], start="20260101", end="20260131"
        )


def test_get_adjust_factors_defaults_to_factor_source() -> None:
    factor = FactorAdapter()
    hub = make_hub(RawBarsAdapter(), factor)
    df = hub.get_adjust_factors(["600519.SH"], start="20260101", end="20260131")
    assert list(df.columns) == ["code", "date", "adj_factor"]
    assert df["adj_factor"].tolist() == [1.0, 2.0]
    assert df.attrs["source"] == "tushare"


class EventsAdapter(BaseAdapter):
    source = Source.FUYAO
    capabilities = frozenset({Capability.ADJUSTMENT_EVENTS})

    def fetch_adjustment_events(self, codes, *, start=None, end=None):
        return pd.DataFrame(
            {
                "code": [code.canonical for code in codes],
                "ex_date": ["2026-06-26"],
                "dividend_per_share": [28.024],
                "per_share_bonus": [0.0],
            }
        )


def test_get_adjustment_events_via_fuyao() -> None:
    hub = make_hub(EventsAdapter())
    df = hub.get_adjustment_events(["600519.SH"], source="fuyao")
    assert list(df.columns) == [
        "code",
        "ex_date",
        "dividend_per_share",
        "per_share_bonus",
    ]
    assert str(df["ex_date"].dtype) == "datetime64[ns]"
    assert df.attrs["source"] == "fuyao"


def test_reserved_interfaces_raise_unsupported() -> None:
    hub = make_hub()
    with pytest.raises(UnsupportedCapability, match="预留接口"):
        hub.get_intraday_bars(
            ["600519.SH"], start="20260101", end="20260102"
        )
    with pytest.raises(UnsupportedCapability, match="预留接口"):
        hub.get_edb_series(["M0000001"], start="20260101", end="20260228")
