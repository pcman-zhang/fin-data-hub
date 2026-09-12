import pandas as pd
import pytest

from fin_data_hub import SecCode, TushareConfig
from fin_data_hub.errors import (
    MissingCredentialError,
    SourceError,
    UnsupportedCapability,
)
from fin_data_hub.sources.tushare import TushareAdapter


class FakeTushareApi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.adj_factors = [1.5, 2.0]
        self.fail_daily = False

    def daily(self, **kwargs):
        self.calls.append(("daily", kwargs))
        if self.fail_daily:
            raise RuntimeError("tushare exploded")
        return pd.DataFrame(
            {
                "ts_code": ["600000.SH", "600000.SH"],
                "trade_date": ["20260105", "20260106"],
                "open": [10.0, 10.2],
                "high": [10.5, 10.4],
                "low": [9.9, 10.0],
                "close": [10.3, 10.1],
                "vol": [1000.0, 1200.0],
                "amount": [1.03, 1.21],
            }
        )

    def adj_factor(self, **kwargs):
        self.calls.append(("adj_factor", kwargs))
        return pd.DataFrame(
            {
                "ts_code": ["600000.SH", "600000.SH"],
                "trade_date": ["20260105", "20260106"],
                "adj_factor": self.adj_factors,
            }
        )

    def fund_nav(self, **kwargs):
        self.calls.append(("fund_nav", kwargs))
        return pd.DataFrame(
            {
                "ts_code": ["000001.OF", "000001.OF", "000001.OF"],
                "nav_date": ["20260105", "20260106", "20260107"],
                "unit_nav": [1.0, 1.1, 1.21],
                "accum_nav": [3.0, 3.1, 3.21],
            }
        )

    def stock_basic(self, **kwargs):
        self.calls.append(("stock_basic", kwargs))
        return pd.DataFrame(
            {
                "ts_code": ["600000.SH"],
                "name": ["浦发银行"],
                "list_date": ["19991110"],
                "market": ["主板"],
                "industry": ["银行"],
            }
        )

    def fund_basic(self, **kwargs):
        self.calls.append(("fund_basic", kwargs))
        return pd.DataFrame(
            {
                "ts_code": ["000001.OF"],
                "name": ["华夏成长"],
                "fund_type": ["混合型"],
                "management": ["华夏基金"],
                "list_date": [None],
                "market": ["O"],
            }
        )

    def index_basic(self, **kwargs):
        self.calls.append(("index_basic", kwargs))
        return pd.DataFrame(
            {
                "ts_code": ["000300.SH"],
                "name": ["沪深300"],
                "market": ["SSE"],
                "category": ["规模指数"],
                "publisher": ["中证指数"],
                "list_date": ["20050408"],
            }
        )

    def trade_cal(self, **kwargs):
        self.calls.append(("trade_cal", kwargs))
        return pd.DataFrame(
            {
                "cal_date": ["20260105", "20260106"],
                "is_open": [1, 0],
            }
        )


def make_adapter(api: FakeTushareApi | None = None) -> tuple[TushareAdapter, FakeTushareApi]:
    fake = api or FakeTushareApi()
    return TushareAdapter(api=fake), fake


def test_bars_basic_mapping_and_units() -> None:
    adapter, fake = make_adapter()
    df = adapter.fetch_bars(
        [SecCode.parse("600000.SH")],
        start="2026-01-05",
        end="2026-01-06",
        freq="1d",
        adjust=None,
        fields=None,
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
    ]
    assert df["code"].tolist() == ["600000.SH", "600000.SH"]
    assert str(df["date"].dtype) == "datetime64[ns]"
    # Tushare 手 → 股，千元 → 元
    assert df["volume"].tolist() == [100_000.0, 120_000.0]
    assert df["amount"].tolist() == [1030.0, 1210.0]
    # start/end 归一化为 YYYYMMDD
    assert fake.calls[0][1]["start_date"] == "20260105"
    assert fake.calls[0][1]["end_date"] == "20260106"
    assert "adj_factor" not in [name for name, _ in fake.calls]


def test_bars_qfq_and_hfq() -> None:
    adapter, fake = make_adapter()
    qfq = adapter.fetch_bars(
        [SecCode.parse("600000.SH")],
        start="20260105",
        end="20260106",
        freq="1d",
        adjust="qfq",
        fields=None,
    )
    # qfq = price * factor / latest_factor（latest=2.0）
    assert qfq["close"].tolist() == pytest.approx([10.3 * 0.75, 10.1])
    assert "adj_factor" in [name for name, _ in fake.calls]

    adapter2, _ = make_adapter()
    hfq = adapter2.fetch_bars(
        [SecCode.parse("600000.SH")],
        start="20260105",
        end="20260106",
        freq="1d",
        adjust="hfq",
        fields=None,
    )
    assert hfq["close"].tolist() == pytest.approx([10.3 * 1.5, 10.1 * 2.0])


def test_bars_unsupported_freq() -> None:
    adapter, _ = make_adapter()
    with pytest.raises(UnsupportedCapability):
        adapter.fetch_bars(
            [SecCode.parse("600000.SH")],
            start="20260101",
            end="20260131",
            freq="1w",
            adjust=None,
            fields=None,
        )


def test_bars_invalid_adjust() -> None:
    adapter, _ = make_adapter()
    with pytest.raises(ValueError):
        adapter.fetch_bars(
            [SecCode.parse("600000.SH")],
            start="20260101",
            end="20260131",
            freq="1d",
            adjust="raw",
            fields=None,
        )


def test_bars_api_error_wrapped() -> None:
    fake = FakeTushareApi()
    fake.fail_daily = True
    adapter = TushareAdapter(api=fake)
    with pytest.raises(SourceError, match="daily"):
        adapter.fetch_bars(
            [SecCode.parse("600000.SH")],
            start="20260101",
            end="20260131",
            freq="1d",
            adjust=None,
            fields=None,
        )


def test_fund_nav_daily_return() -> None:
    adapter, _ = make_adapter()
    df = adapter.fetch_fund_nav([SecCode.parse("000001.OF")], start=None, end=None)
    assert df["code"].tolist() == ["000001.OF"] * 3
    assert pd.isna(df["daily_return"].iloc[0])
    assert df["daily_return"].iloc[1:].tolist() == pytest.approx([10.0, 10.0])


def test_reference_stock_list() -> None:
    adapter, _ = make_adapter()
    df = adapter.fetch_reference("stock_list")
    assert df.iloc[0]["code"] == "600000.SH"
    assert df.iloc[0]["name"] == "浦发银行"
    assert str(df["list_date"].dtype) == "datetime64[ns]"


def test_reference_fund_and_index() -> None:
    adapter, _ = make_adapter()
    funds = adapter.fetch_reference("fund_list")
    assert funds.iloc[0]["fund_type"] == "混合型"
    indexes = adapter.fetch_reference("index_list")
    assert indexes.iloc[0]["publisher"] == "中证指数"


def test_reference_unknown_kind() -> None:
    adapter, _ = make_adapter()
    with pytest.raises(UnsupportedCapability):
        adapter.fetch_reference("bond_list")


def test_trade_calendar() -> None:
    adapter, _ = make_adapter()
    df = adapter.fetch_trade_calendar(start="20260105", end="20260106")
    assert df["is_open"].tolist() == [True, False]
    assert str(df["date"].dtype) == "datetime64[ns]"


def test_missing_token_raises() -> None:
    with pytest.raises(MissingCredentialError):
        TushareAdapter(TushareConfig(token=None))


def test_capabilities_exclude_snapshot() -> None:
    adapter, _ = make_adapter()
    assert "snapshot" not in adapter.capabilities
    assert "bars" in adapter.capabilities


def test_invalid_date_rejected() -> None:
    adapter, _ = make_adapter()
    with pytest.raises(ValueError):
        adapter.fetch_bars(
            [SecCode.parse("600000.SH")],
            start="2026/01/05",
            end="20260106",
            freq="1d",
            adjust=None,
            fields=None,
        )
