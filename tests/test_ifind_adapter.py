import json

import pytest

from fin_data_hub import SecCode
from fin_data_hub.errors import (
    MissingCredentialError,
    ResponseParseError,
    SourceError,
    UnsupportedCapability,
)
from fin_data_hub.mcp.parsers import parse_markdown_tables, split_unit
from fin_data_hub.sources.ifind import IfindAdapter

# 以下 fixture 由实测 iFinD 响应整理并脱敏（数值/日期为构造值）。
FUND_ANSWER = """|证券代码|证券简称|净值日期|单位净值币种|
|---|---|---|---|
|000001.OF|华夏成长混合|20260911|人民币元|

|证券代码|证券简称|日期|单位净值（单位：元）|累计单位净值（单位：元）|单位净值增长率（单位：%）|
|---|---|---|---|---|---|
|000001.OF|华夏成长混合|20260910|1.262|3.835|-0.4732|
|000001.OF|华夏成长混合|20260911|1.250|3.823|-0.9508|
|000159.OF|华安宝利配置|20260910|2.100|4.500|0.1000|
"""

INDEX_ANSWER = (
    "|证券代码|证券简称|日期|开盘价（单位：元）|最高价（单位：元）|最低价（单位：元）|"
    "收盘价（单位：元）|成交量（单位：手）|成交额（单位：元）|\n"
    "|---|---|---|---|---|---|---|---|---|\n"
    "|000300.SH|沪深300|20260910|4500.1|4520.5|4480.2|4510.0|100000|451000000|\n"
    "|000300.SH|沪深300|20260911|4510.0|4530.0|4490.0|4510.1554|110000|496000000|\n"
    "|399006.SZ|创业板指|20260910|2300.0|2310.0|2290.0|2305.0|80000|184000000|\n"
)

EDB_DATA = {
    "datas": [
        {
            "data": {
                "columns": ["指标名称", "日期", "数值"],
                "data": [
                    ["光伏电池产量", "20260131", 100.0],
                    ["光伏电池产量", "20260228", 120.0],
                ],
            }
        }
    ]
}


class StubIfindClient:
    def __init__(self, data, *, as_string: bool = True) -> None:
        self.data = data
        self.as_string = as_string
        self.calls: list[tuple[str, dict]] = []

    def call_tool(self, tool, arguments=None):
        self.calls.append((tool, dict(arguments or {})))
        payload = {
            "code": 1,
            "msg": "success",
            "data": (
                json.dumps(self.data, ensure_ascii=False)
                if self.as_string
                else self.data
            ),
        }
        return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}]}


class ErrorIfindClient:
    def call_tool(self, tool, arguments=None):
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {"code": -1, "msg": "bad query", "data": None},
                        ensure_ascii=False,
                    ),
                }
            ]
        }


def test_fund_nav_multicode_single_call() -> None:
    stub = StubIfindClient({"answer": FUND_ANSWER})
    adapter = IfindAdapter(clients={"fund": stub})
    df = adapter.fetch_fund_nav(
        [SecCode.parse("000001.OF"), SecCode.parse("000159.OF")],
        start="2026-09-01",
        end="2026-09-11",
    )
    assert len(stub.calls) == 1  # 多标的合并为一次 NL 调用
    tool, arguments = stub.calls[0]
    assert tool == "get_fund_market_performance"
    assert "000001.OF" in arguments["query"]
    assert "000159.OF" in arguments["query"]
    assert set(df["code"]) == {"000001.OF", "000159.OF"}
    assert list(df.columns) == [
        "code",
        "date",
        "unit_nav",
        "accum_nav",
        "daily_return",
    ]
    assert str(df["date"].dtype) == "datetime64[ns]"
    row = df[(df["code"] == "000001.OF") & (df["date"] == "2026-09-11")].iloc[0]
    assert row["unit_nav"] == pytest.approx(1.25)
    assert row["accum_nav"] == pytest.approx(3.823)
    assert row["daily_return"] == pytest.approx(-0.9508)


def test_fund_nav_date_filter() -> None:
    stub = StubIfindClient({"answer": FUND_ANSWER})
    adapter = IfindAdapter(clients={"fund": stub})
    df = adapter.fetch_fund_nav(
        [SecCode.parse("000001.OF")], start="2026-09-11", end="2026-09-11"
    )
    assert len(df) == 1
    assert df.iloc[0]["unit_nav"] == pytest.approx(1.25)


def test_fund_nav_rejects_non_fund() -> None:
    adapter = IfindAdapter(clients={"fund": StubIfindClient({"answer": ""})})
    with pytest.raises(UnsupportedCapability):
        adapter.fetch_fund_nav([SecCode.parse("600000.SH")], start=None, end=None)


def test_index_bars_multicode_and_units() -> None:
    stub = StubIfindClient({"answer": INDEX_ANSWER})
    adapter = IfindAdapter(clients={"index": stub})
    df = adapter.fetch_bars(
        [SecCode.parse("000300.SH"), SecCode.parse("399006.SZ")],
        start="2026-09-01",
        end="2026-09-11",
        freq="1d",
        adjust=None,
        fields=None,
    )
    assert len(stub.calls) == 1
    tool, arguments = stub.calls[0]
    assert tool == "index_data"
    assert "000300.SH" in arguments["query"]
    assert "399006.SZ" in arguments["query"]
    assert len(df) == 3
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
    # 手 → 股
    assert df.iloc[0]["volume"] == pytest.approx(10_000_000)
    assert df.iloc[0]["amount"] == pytest.approx(451_000_000)
    assert str(df["date"].dtype) == "datetime64[ns]"


def test_bars_rejects_non_index_and_adjust() -> None:
    adapter = IfindAdapter(clients={"index": StubIfindClient({"answer": INDEX_ANSWER})})
    with pytest.raises(UnsupportedCapability):
        adapter.fetch_bars(
            [SecCode.parse("600000.SH")],
            start="20260901",
            end="20260902",
            freq="1d",
            adjust=None,
            fields=None,
        )
    with pytest.raises(UnsupportedCapability):
        adapter.fetch_bars(
            [SecCode.parse("000300.SH")],
            start="20260901",
            end="20260902",
            freq="1d",
            adjust="qfq",
            fields=None,
        )


def test_parse_failure_has_truncated_snippet() -> None:
    stub = StubIfindClient({"answer": "抱歉，没有找到相关数据"})
    adapter = IfindAdapter(clients={"index": stub})
    with pytest.raises(ResponseParseError, match="无法解析"):
        adapter.fetch_bars(
            [SecCode.parse("000300.SH")],
            start="20260901",
            end="20260902",
            freq="1d",
            adjust=None,
            fields=None,
        )


def test_payload_error_code_raises_source_error() -> None:
    adapter = IfindAdapter(clients={"index": ErrorIfindClient()})
    with pytest.raises(SourceError, match="bad query"):
        adapter.fetch_bars(
            [SecCode.parse("000300.SH")],
            start="20260901",
            end="20260902",
            freq="1d",
            adjust=None,
            fields=None,
        )


def test_missing_credential_raises_on_use() -> None:
    adapter = IfindAdapter()
    with pytest.raises(MissingCredentialError):
        adapter.fetch_fund_nav([SecCode.parse("000001.OF")], start=None, end=None)


def test_edb_single_indicator_enforced() -> None:
    stub = StubIfindClient(EDB_DATA, as_string=False)
    adapter = IfindAdapter(clients={"edb": stub})
    with pytest.raises(ValueError, match="一个指标"):
        adapter.fetch_edb_series(["A", "B"], start="20260101", end="20260228")


def test_edb_series_parsed() -> None:
    stub = StubIfindClient(EDB_DATA, as_string=False)
    adapter = IfindAdapter(clients={"edb": stub})
    df = adapter.fetch_edb_series(["光伏电池产量"], start="20260101", end="20260228")
    assert list(df.columns) == ["indicator", "obs_date", "value"]
    assert df["value"].tolist() == [100.0, 120.0]
    assert str(df["obs_date"].dtype) == "datetime64[ns]"
    tool, arguments = stub.calls[0]
    assert tool == "get_edb_data"
    assert "光伏电池产量" in arguments["query"]


def test_capabilities() -> None:
    adapter = IfindAdapter(clients={})
    assert adapter.capabilities == frozenset({"bars", "fund_nav"})


def test_parse_markdown_tables_handles_multiple_tables() -> None:
    tables = parse_markdown_tables(FUND_ANSWER)
    assert len(tables) == 2
    assert tables[1].columns.tolist()[-1] == "单位净值增长率（单位：%）"
    assert len(tables[1]) == 3


def test_split_unit() -> None:
    assert split_unit("收盘价（单位：元）") == ("收盘价", 1.0)
    assert split_unit("成交额（单位：万元）") == ("成交额", 1e4)
    assert split_unit("成交量（单位：手）") == ("成交量", 100.0)
    assert split_unit("单位净值增长率（单位：%）") == ("单位净值增长率", 1.0)
    assert split_unit("证券代码") == ("证券代码", 1.0)
