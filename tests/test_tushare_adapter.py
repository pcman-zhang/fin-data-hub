import pandas as pd
import pytest

from fin_data_hub import SecCode, TushareConfig
from fin_data_hub.errors import (
    MissingCredentialError,
    SourceError,
    UnsupportedCapability,
)
from fin_data_hub.schemas import BALANCE_SHEET_COLUMNS, FINANCIAL_INDICATOR_COLUMNS
from fin_data_hub.sources.tushare import TushareAdapter


def _financial_row(columns: tuple[str, ...], **overrides):
    row = {
        column: 1.0
        for column in columns
        if column not in ("code", "currency")
    }
    row.update(overrides)
    return row


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

    def fund_daily(self, **kwargs):
        self.calls.append(("fund_daily", kwargs))
        return pd.DataFrame(
            {
                "ts_code": ["510300.SH", "510300.SH"],
                "trade_date": ["20260105", "20260106"],
                "open": [4.0, 4.1],
                "high": [4.1, 4.2],
                "low": [3.9, 4.0],
                "close": [4.05, 4.15],
                "vol": [10000.0, 12000.0],
                "amount": [4.05, 4.98],
            }
        )

    def index_daily(self, **kwargs):
        self.calls.append(("index_daily", kwargs))
        return pd.DataFrame(
            {
                "ts_code": ["000300.SH", "000300.SH"],
                "trade_date": ["20260105", "20260106"],
                "open": [4000.0, 4010.0],
                "high": [4020.0, 4030.0],
                "low": [3990.0, 4000.0],
                "close": [4010.0, 4020.0],
                "vol": [1_000_000.0, 1_200_000.0],
                "amount": [4.05e6, 4.98e6],
            }
        )

    def fund_adj(self, **kwargs):
        self.calls.append(("fund_adj", kwargs))
        codes = kwargs["ts_code"].split(",")
        return pd.DataFrame(
            {
                "ts_code": [code for code in codes for _ in range(2)],
                "trade_date": ["20260105", "20260106"] * len(codes),
                "adj_factor": [1.2, 1.5] * len(codes),
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

    def etf_basic(self, **kwargs):
        self.calls.append(("etf_basic", kwargs))
        return pd.DataFrame(
            {
                "ts_code": ["510300.SH"],
                "csname": ["300ETF"],
                "cname": ["华泰柏瑞沪深300ETF"],
                "index_code": ["000300.SH"],
                "index_name": ["沪深300"],
                "setup_date": ["20120504"],
                "list_date": ["20120528"],
                "list_status": ["L"],
                "exchange": ["SH"],
                "mgr_name": ["华泰柏瑞"],
                "custod_name": ["工商银行"],
                "mgt_fee": [0.5],
                "etf_type": ["被动"],
            }
        )

    def index_classify(self, **kwargs):
        self.calls.append(("index_classify", kwargs))
        level = kwargs.get("level", "L1")
        rows = {
            "L1": {
                "index_code": "801010.SI",
                "industry_name": "农林牧渔",
                "level": "L1",
                "industry_code": "110000",
                "is_pub": "1",
                "parent_code": "0",
            },
            "L2": {
                "index_code": "801011.SI",
                "industry_name": "种植业",
                "level": "L2",
                "industry_code": "110100",
                "is_pub": "1",
                "parent_code": "110000",
            },
            "L3": {
                "index_code": "851011.SI",
                "industry_name": "粮食种植",
                "level": "L3",
                "industry_code": "110101",
                "is_pub": "0",
                "parent_code": "110100",
            },
        }
        return pd.DataFrame([{**rows[level], "src": "SW2021"}])

    def index_member_all(self, **kwargs):
        self.calls.append(("index_member_all", kwargs))
        is_new = kwargs.get("is_new", "Y")
        return pd.DataFrame(
            {
                "l1_code": ["801010.SI"],
                "l1_name": ["农林牧渔"],
                "l2_code": ["801011.SI"],
                "l2_name": ["种植业"],
                "l3_code": ["851011.SI"],
                "l3_name": ["粮食种植"],
                "ts_code": ["600000.SH"],
                "name": ["浦发银行"],
                "in_date": ["20200101"],
                "out_date": [None if is_new == "Y" else "20240101"],
                "is_new": [is_new],
            }
        )

    def new_share(self, **kwargs):
        self.calls.append(("new_share", kwargs))
        return pd.DataFrame(
            {
                "ts_code": ["920001.BJ"],
                "sub_code": ["790001"],
                "name": ["示例新股"],
                "ipo_date": ["20260110"],
                "issue_date": ["20260105"],
                "amount": [1000.0],
                "market_amount": [900.0],
                "price": [10.0],
                "pe": [22.5],
                "limit_amount": [15000.0],
                "funds": [9000.0],
                "ballot": [0.03],
            }
        )

    def namechange(self, **kwargs):
        self.calls.append(("namechange", kwargs))
        code = kwargs.get("ts_code", "600519.SH")
        return pd.DataFrame(
            {
                "ts_code": [code, code],
                "name": ["贵州茅台", "G茅台"],
                "start_date": ["20061009", "20060525"],
                "end_date": [None, "20061008"],
                "ann_date": ["20060928", "20060522"],
                "change_reason": ["其他", "其他"],
            }
        )

    def suspend_d(self, **kwargs):
        self.calls.append(("suspend_d", kwargs))
        return pd.DataFrame(
            {
                "ts_code": ["600322.SH"],
                "trade_date": ["20260105"],
                "suspend_timing": [None],
                "suspend_type": ["R"],
            }
        )

    def stock_st(self, **kwargs):
        self.calls.append(("stock_st", kwargs))
        return pd.DataFrame(
            {
                "ts_code": ["000004.SZ"],
                "name": ["*ST国华"],
                "trade_date": ["20260105"],
                "type": ["ST"],
                "type_name": ["风险警示板"],
            }
        )

    def balancesheet(self, **kwargs):
        self.calls.append(("balancesheet", kwargs))
        row = _financial_row(
            BALANCE_SHEET_COLUMNS,
            ts_code=kwargs["ts_code"],
            ann_date="20260430",
            end_date="20251231",
            report_type="1",
        )
        return pd.DataFrame([row])

    def fina_indicator(self, **kwargs):
        self.calls.append(("fina_indicator", kwargs))
        codes = kwargs["ts_code"].split(",")
        return pd.DataFrame(
            [
                _financial_row(
                    FINANCIAL_INDICATOR_COLUMNS,
                    ts_code=code,
                    ann_date="20260430",
                    end_date="20251231",
                )
                for code in codes
            ]
        )

    def index_weight(self, **kwargs):
        self.calls.append(("index_weight", kwargs))
        return pd.DataFrame(
            {
                "index_code": ["000300.SH", "000300.SH"],
                "con_code": ["600519.SH", "300750.SZ"],
                "trade_date": ["20260831", "20260831"],
                "weight": [3.66, 3.20],
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


def test_bars_routes_by_asset_type() -> None:
    adapter, fake = make_adapter()
    df = adapter.fetch_bars(
        [
            SecCode.parse("600000.SH"),
            SecCode.parse("510300.SH"),
            SecCode.parse("000300.SH"),
        ],
        start="20260105",
        end="20260106",
        freq="1d",
        adjust=None,
        fields=None,
    )
    assert [name for name, _ in fake.calls] == ["daily", "fund_daily", "index_daily"]
    assert sorted(df["code"].unique()) == ["000300.SH", "510300.SH", "600000.SH"]
    index_rows = df[df["code"] == "000300.SH"]
    assert index_rows["close"].tolist() == [4010.0, 4020.0]


def test_bars_etf_qfq_uses_fund_adj() -> None:
    adapter, fake = make_adapter()
    df = adapter.fetch_bars(
        [SecCode.parse("510300.SH")],
        start="20260105",
        end="20260106",
        freq="1d",
        adjust="qfq",
        fields=None,
    )
    endpoints = [name for name, _ in fake.calls]
    assert endpoints == ["fund_daily", "fund_adj"]
    # qfq = close × f / f_latest（latest=1.5）：4.05×0.8；4.15×1
    assert df["close"].tolist() == pytest.approx([4.05 * 0.8, 4.15])


def test_bars_index_adjust_rejected() -> None:
    adapter, _ = make_adapter()
    with pytest.raises(UnsupportedCapability, match="无复权因子"):
        adapter.fetch_bars(
            [SecCode.parse("000300.SH")],
            start="20260105",
            end="20260106",
            freq="1d",
            adjust="qfq",
            fields=None,
        )


def test_bars_otc_fund_rejected() -> None:
    adapter, _ = make_adapter()
    with pytest.raises(UnsupportedCapability, match="无日线行情"):
        adapter.fetch_bars(
            [SecCode.parse("000001.OF")],
            start="20260105",
            end="20260106",
            freq="1d",
            adjust=None,
            fields=None,
        )


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


def test_reference_etf_list() -> None:
    adapter, fake = make_adapter()
    df = adapter.fetch_reference("etf_list")
    assert fake.calls[-1][0] == "etf_basic"
    assert df.iloc[0]["code"] == "510300.SH"
    assert df.iloc[0]["name"] == "300ETF"
    assert df.iloc[0]["index_code"] == "000300.SH"
    assert df.iloc[0]["mgt_fee"] == 0.5
    assert str(df["setup_date"].dtype) == "datetime64[ns]"


def test_reference_delist_list() -> None:
    adapter, fake = make_adapter()
    df = adapter.fetch_reference("delist_list")
    name, kwargs = fake.calls[-1]
    assert name == "stock_basic"
    assert kwargs["list_status"] == "D"
    assert df.iloc[0]["code"] == "600000.SH"


def test_fetch_security_info_routes_and_types() -> None:
    adapter, fake = make_adapter()
    df = adapter.fetch_security_info(
        [
            SecCode.parse("600000.SH"),
            SecCode.parse("000001.OF"),
            SecCode.parse("000300.SH"),
        ]
    )
    assert [name for name, _ in fake.calls] == [
        "stock_basic",
        "fund_basic",
        "index_basic",
    ]
    assert list(df.columns) == [
        "code",
        "name",
        "sec_type",
        "market",
        "list_status",
        "list_date",
        "delist_date",
    ]
    assert dict(zip(df["code"], df["sec_type"], strict=True)) == {
        "600000.SH": "stock",
        "000001.OF": "fund",
        "000300.SH": "index",
    }
    assert str(df["list_date"].dtype) == "datetime64[ns]"


def test_fetch_market_events_ipo() -> None:
    adapter, fake = make_adapter()
    df = adapter.fetch_market_events(kind="ipo", start="20260101", end="20260131")
    name, kwargs = fake.calls[-1]
    assert name == "new_share"
    assert kwargs["start_date"] == "20260101"
    assert kwargs["limit"] == 1000
    assert list(df.columns) == [
        "code",
        "name",
        "ipo_date",
        "issue_date",
        "price",
        "pe",
        "amount",
        "market_amount",
        "limit_amount",
        "funds",
        "ballot",
    ]
    assert df.iloc[0]["price"] == 10.0
    assert str(df["ipo_date"].dtype) == "datetime64[ns]"


def test_fetch_market_events_suspension_with_codes() -> None:
    adapter, fake = make_adapter()
    df = adapter.fetch_market_events(
        kind="suspension",
        start="20260101",
        end="20260131",
        codes=[SecCode.parse("600322.SH")],
    )
    assert fake.calls[-1][1]["ts_code"] == "600322.SH"
    assert list(df.columns) == [
        "code",
        "date",
        "suspend_type",
        "suspend_timing",
    ]
    assert df.iloc[0]["suspend_type"] == "R"


def test_fetch_market_events_st_local_filter() -> None:
    adapter, fake = make_adapter()
    df = adapter.fetch_market_events(
        kind="st",
        start="20260101",
        end="20260131",
        codes=[SecCode.parse("000004.SZ")],
    )
    assert df.iloc[0]["st_type"] == "ST"
    empty = adapter.fetch_market_events(
        kind="st",
        start="20260101",
        end="20260131",
        codes=[SecCode.parse("600519.SH")],
    )
    assert empty.empty
    assert list(empty.columns) == [
        "code",
        "name",
        "date",
        "st_type",
        "type_name",
    ]


def test_fetch_market_events_namechange_intervals() -> None:
    adapter, fake = make_adapter()
    df = adapter.fetch_market_events(
        kind="namechange",
        start="20000101",
        end="20261231",
        codes=[SecCode.parse("600519.SH")],
    )
    name, kwargs = fake.calls[-1]
    assert name == "namechange"
    assert kwargs["ts_code"] == "600519.SH"
    assert list(df.columns) == [
        "code",
        "name",
        "start_date",
        "end_date",
        "ann_date",
        "change_reason",
    ]
    first = df.iloc[0]
    assert first["name"] == "G茅台"  # 排序后最早区间在前
    assert first["start_date"] == pd.Timestamp("2006-05-25")
    assert first["end_date"] == pd.Timestamp("2006-10-08")
    assert pd.isna(df.iloc[-1]["end_date"])  # 当前名称区间无结束日
    assert str(df["ann_date"].dtype) == "datetime64[ns]"


def test_fetch_market_events_namechange_per_code_calls() -> None:
    adapter, fake = make_adapter()
    adapter.fetch_market_events(
        kind="namechange",
        start="20000101",
        end="20261231",
        codes=[SecCode.parse("600519.SH"), SecCode.parse("000001.SZ")],
    )
    calls = [k for n, k in fake.calls if n == "namechange"]
    assert len(calls) == 2


def test_fetch_market_events_unknown_kind_rejected() -> None:
    adapter, _ = make_adapter()
    with pytest.raises(UnsupportedCapability, match="event kind"):
        adapter.fetch_market_events(kind="dividend", start="20260101", end="20260131")


def test_fetch_financials_balance_sheet_per_code() -> None:
    adapter, fake = make_adapter()
    df = adapter.fetch_financials(
        [SecCode.parse("600000.SH"), SecCode.parse("000001.SZ")],
        kind="balance_sheet",
        start="20260101",
        end="20260630",
    )
    assert [name for name, _ in fake.calls] == ["balancesheet", "balancesheet"]
    assert df["total_assets"].tolist() == [1.0, 1.0]
    assert str(df["ann_date"].dtype) == "datetime64[ns]"
    assert set(df["code"]) == {"600000.SH", "000001.SZ"}


def test_fetch_financials_indicator_batch() -> None:
    adapter, fake = make_adapter()
    df = adapter.fetch_financials(
        [SecCode.parse("600000.SH"), SecCode.parse("000001.SZ")],
        kind="financial_indicator",
        start="20260101",
        end="20260630",
    )
    name, kwargs = fake.calls[-1]
    assert name == "fina_indicator"
    assert kwargs["ts_code"] == "600000.SH,000001.SZ"
    assert df["roe"].tolist() == [1.0, 1.0]


def test_fetch_financials_unknown_kind_rejected() -> None:
    adapter, _ = make_adapter()
    with pytest.raises(UnsupportedCapability, match="financial kind"):
        adapter.fetch_financials(
            [SecCode.parse("600000.SH")],
            kind="cashflow",
            start="20260101",
            end="20260630",
        )


def test_fetch_index_weights() -> None:
    adapter, fake = make_adapter()
    df = adapter.fetch_index_weights(
        [SecCode.parse("000300.SH")], start="20260701", end="20260911"
    )
    name, kwargs = fake.calls[-1]
    assert name == "index_weight"
    assert kwargs["index_code"] == "000300.SH"
    assert list(df.columns) == ["code", "date", "con_code", "weight"]
    assert df["code"].tolist() == ["000300.SH", "000300.SH"]
    assert df["weight"].tolist() == [3.2, 3.66]
    assert str(df["date"].dtype) == "datetime64[ns]"


def test_fetch_index_weights_rejects_non_index() -> None:
    adapter, _ = make_adapter()
    with pytest.raises(UnsupportedCapability, match="仅支持指数"):
        adapter.fetch_index_weights(
            [SecCode.parse("600000.SH")], start="20260701", end="20260911"
        )


def test_reference_industry_classify_tree() -> None:
    adapter, fake = make_adapter()
    df = adapter.fetch_reference("industry_classify")
    levels = [k["level"] for name, k in fake.calls if name == "index_classify"]
    assert levels == ["L1", "L2", "L3"]
    assert set(df["level"]) == {"L1", "L2", "L3"}
    assert list(df.columns) == [
        "index_code",
        "name",
        "level",
        "industry_code",
        "parent_code",
        "is_pub",
        "src",
    ]
    # parent_code 引用上级 industry_code，可组装三级树
    l1_codes = set(df[df["level"] == "L1"]["industry_code"])
    l2 = df[df["level"] == "L2"]
    assert set(l2["parent_code"]) <= l1_codes
    assert set(df[df["level"] == "L3"]["parent_code"]) <= set(l2["industry_code"])


def test_reference_industry_member_history() -> None:
    adapter, fake = make_adapter()
    df = adapter.fetch_reference("industry_member")
    is_new_calls = [k["is_new"] for name, k in fake.calls if name == "index_member_all"]
    assert is_new_calls == ["Y", "N"]
    assert list(df.columns) == [
        "code",
        "name",
        "l1_code",
        "l1_name",
        "l2_code",
        "l2_name",
        "l3_code",
        "l3_name",
        "in_date",
        "out_date",
        "is_new",
    ]
    assert df["out_date"].notna().sum() == 1  # 已剔除记录带 out_date
    assert str(df["in_date"].dtype) == "datetime64[ns]"


def test_fetch_security_info_fund_endpoints_single_code() -> None:
    # fund_basic / index_basic 不支持逗号多代码 → 逐代码调用
    adapter, fake = make_adapter()
    adapter.fetch_security_info(
        [SecCode.parse("510300.SH"), SecCode.parse("161725.SZ")]
    )
    assert [name for name, _ in fake.calls] == ["fund_basic", "fund_basic"]


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
