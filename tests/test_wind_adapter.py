import json

import pandas as pd
import pytest

from fin_data_hub import SecCode
from fin_data_hub.errors import (
    MissingCredentialError,
    SourceError,
    UnsupportedCapability,
)
from fin_data_hub.sources.wind import WindAdapter

# fixture 由 Wind 实测响应整理并脱敏（数值为构造/截断值）。
KLINE_DATA = {
    "data": {
        "columns": [
            {"name": "TIME", "type": "string"},
            {"name": "OPEN", "type": "string"},
            {"name": "MATCH", "type": "string"},
            {"name": "HIGH", "type": "string"},
            {"name": "LOW", "type": "string"},
            {"name": "TURNOVER", "type": "string"},
            {"name": "VOLUME", "type": "string"},
            {"name": "CHANGEHANDRATE", "type": "string"},
            {"name": "AVPRICE", "type": "string"},
        ],
        "rows": [
            [
                "2026-09-09T00:00:00.000+08:00",
                "1305.01",
                "1290.88",
                "1309.30",
                "1286.68",
                "4168500462",
                "3222611",
                "0.2578",
                "1293.52",
            ],
            [
                "2026-09-10T00:00:00.000+08:00",
                "1291.00",
                "1285.13",
                "1294.99",
                "1282.00",
                "2428698784",
                "1890022",
                "0.1512",
                "1285.01",
            ],
        ],
        "unit": {
            "VOLUME 单位：": "股",
            "TURNOVER 单位：": "元",
            "OPEN 单位：": "元",
        },
    },
    "error": None,
}

SNAPSHOT_DATA = {
    "data": {
        "columns": [
            {"name": "最新交易日", "type": "string"},
            {"name": "交易时间", "type": "string"},
            {"name": "最新成交价", "type": "string"},
            {"name": "前收盘价", "type": "string"},
            {"name": "今日开盘价", "type": "string"},
            {"name": "今日最高价", "type": "string"},
            {"name": "今日最低价", "type": "string"},
            {"name": "成交量", "type": "string"},
            {"name": "成交额", "type": "string"},
            {"name": "Wind代码", "type": "string"},
        ],
        "rows": [
            [
                "20260911",
                "2026-09-11T15:31:21.000+08:00",
                "1275.16",
                "1285.13",
                "1285.15",
                "1286.15",
                "1263.01",
                "3480142",
                "4430841445",
                "600519.SH",
            ],
            [
                "20260911",
                "2026-09-11T15:31:21.000+08:00",
                "10.50",
                "10.40",
                "10.45",
                "10.60",
                "10.30",
                "1000000",
                "10500000",
                "600000.SH",
            ],
        ],
        "unit": {"成交量": "股", "成交额": "元", "最新成交价": "元"},
    },
    "error": None,
}

EDB_DATA = {
    "data": {
        "date": ["20260131", "20260228"],
        "indicatorInfo": [
            {"code": "M0000001", "name": "示例指标A", "data": [100.0, 120.0]},
            {"code": "M0000002", "name": "示例指标B", "data": [1.0, 2.0]},
        ],
    },
    "error": None,
}

BOND_DATA = {
    "data": {
        "columns": [{"name": "日期"}, {"name": "收盘价"}],
        "rows": [["2026-09-09", "1.02"], ["2026-09-10", "1.03"]],
        "unit": {},
    },
    "error": None,
}


class StubWindClient:
    def __init__(self, payload) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict]] = []

    def call_tool(self, tool, arguments=None):
        self.calls.append((tool, dict(arguments or {})))
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(self.payload, ensure_ascii=False),
                }
            ]
        }


def test_stock_kline_mapping_and_backend_quirk() -> None:
    stub = StubWindClient(KLINE_DATA)
    adapter = WindAdapter(clients={"stock_data": stub})
    df = adapter.fetch_bars(
        [SecCode.parse("600519.SH")],
        start="2026-09-09",
        end="2026-09-10",
        freq="1d",
        adjust=None,
        fields=None,
    )
    assert len(stub.calls) == 1
    tool, arguments = stub.calls[0]
    assert tool == "get_stock_kline"
    assert "period" not in arguments  # 实测后端不接受 period=1d
    assert arguments["aftype"] == "2"
    assert arguments["begin_date"] == "2026-09-09"
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
    assert df.iloc[0]["date"] == pd.Timestamp("2026-09-09")
    assert df.iloc[0]["close"] == pytest.approx(1290.88)
    assert df.iloc[0]["volume"] == pytest.approx(3_222_611)


def test_kline_adjust_mapping() -> None:
    for adjust, aftype in (("qfq", "0"), ("hfq", "1")):
        stub = StubWindClient(KLINE_DATA)
        adapter = WindAdapter(clients={"stock_data": stub})
        adapter.fetch_bars(
            [SecCode.parse("600519.SH")],
            start="2026-09-09",
            end="2026-09-10",
            freq="1d",
            adjust=adjust,
            fields=None,
        )
        assert stub.calls[0][1]["aftype"] == aftype


def test_kline_unit_conversion() -> None:
    payload = json.loads(json.dumps(KLINE_DATA))
    payload["data"]["unit"] = {"VOLUME 单位：": "手", "TURNOVER 单位：": "元"}
    stub = StubWindClient(payload)
    adapter = WindAdapter(clients={"stock_data": stub})
    df = adapter.fetch_bars(
        [SecCode.parse("600519.SH")],
        start="2026-09-09",
        end="2026-09-10",
        freq="1d",
        adjust=None,
        fields=None,
    )
    assert df.iloc[0]["volume"] == pytest.approx(322_261_100)


def test_kline_routing_and_rejections() -> None:
    fund_stub = StubWindClient(KLINE_DATA)
    adapter = WindAdapter(clients={"fund_data": fund_stub})
    adapter.fetch_bars(
        [SecCode.parse("510300.SH")],
        start="2026-09-09",
        end="2026-09-10",
        freq="1d",
        adjust=None,
        fields=None,
    )
    assert fund_stub.calls[0][0] == "get_fund_kline"

    index_stub = StubWindClient(KLINE_DATA)
    adapter = WindAdapter(clients={"index_data": index_stub})
    adapter.fetch_bars(
        [SecCode.parse("000300.SH")],
        start="2026-09-09",
        end="2026-09-10",
        freq="1d",
        adjust=None,
        fields=None,
    )
    assert index_stub.calls[0][0] == "get_index_kline"

    with pytest.raises(UnsupportedCapability):
        adapter.fetch_bars(
            [SecCode.parse("000001.OF")],
            start="2026-09-09",
            end="2026-09-10",
            freq="1d",
            adjust=None,
            fields=None,
        )
    with pytest.raises(UnsupportedCapability):
        adapter.fetch_bars(
            [SecCode.parse("000300.SH")],
            start="2026-09-09",
            end="2026-09-10",
            freq="1w",
            adjust=None,
            fields=None,
        )


def test_snapshot_batch_single_call() -> None:
    stub = StubWindClient(SNAPSHOT_DATA)
    adapter = WindAdapter(clients={"stock_data": stub})
    df = adapter.fetch_snapshot(
        [SecCode.parse("600519.SH"), SecCode.parse("600000.SH")], fields=None
    )
    assert len(stub.calls) == 1
    tool, arguments = stub.calls[0]
    assert tool == "get_stock_price_indicators"
    assert arguments["windcode"] == "600519.SH,600000.SH"
    assert "成交额" in arguments["indexes"]
    assert set(df["code"]) == {"600519.SH", "600000.SH"}
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
    row = df[df["code"] == "600519.SH"].iloc[0]
    assert row["last"] == pytest.approx(1275.16)
    assert str(df["date"].dtype) == "datetime64[ns]"


def test_snapshot_groups_by_sec_type() -> None:
    index_payload = json.loads(json.dumps(SNAPSHOT_DATA))
    index_payload["data"]["rows"][0][-1] = "000300.SH"
    index_payload["data"]["rows"] = index_payload["data"]["rows"][:1]
    stock_payload = json.loads(json.dumps(SNAPSHOT_DATA))
    stock_payload["data"]["rows"] = stock_payload["data"]["rows"][:1]
    stock_stub = StubWindClient(stock_payload)
    index_stub = StubWindClient(index_payload)
    adapter = WindAdapter(
        clients={"stock_data": stock_stub, "index_data": index_stub}
    )
    df = adapter.fetch_snapshot(
        [SecCode.parse("000300.SH"), SecCode.parse("600519.SH")], fields=None
    )
    assert len(stock_stub.calls) == 1
    assert len(index_stub.calls) == 1
    assert index_stub.calls[0][0] == "get_index_price_indicators"
    assert set(df["code"]) == {"000300.SH", "600519.SH"}


def test_snapshot_chunks_over_50_codes() -> None:
    stub = StubWindClient(SNAPSHOT_DATA)
    adapter = WindAdapter(clients={"stock_data": stub})
    codes = [SecCode.parse(f"{600000 + i}.SH") for i in range(51)]
    adapter.fetch_snapshot(codes, fields=None)
    assert len(stub.calls) == 2
    first = stub.calls[0][1]["windcode"].split(",")
    second = stub.calls[1][1]["windcode"].split(",")
    assert len(first) == 50
    assert len(second) == 1


def test_economic_batch_and_range_required() -> None:
    stub = StubWindClient(EDB_DATA)
    adapter = WindAdapter(clients={"economic_data": stub})
    df = adapter.fetch_economic_indicators(
        ["M0000001", "M0000002"],
        start="2026-01-01",
        end="2026-02-28",
    )
    assert len(stub.calls) == 1
    tool, arguments = stub.calls[0]
    assert tool == "get_economic_data"
    assert arguments["metricIdsStr"] == "M0000001,M0000002"
    assert arguments["beginDate"] == "2026-01-01"
    assert len(df) == 4
    assert list(df.columns) == ["indicator", "obs_date", "value"]
    assert df["value"].tolist() == [100.0, 120.0, 1.0, 2.0]
    assert all(tool.startswith("get_") for tool, _ in stub.calls)

    with pytest.raises(ValueError):
        adapter.fetch_economic_indicators(["M1"], start="", end="2026-02-28")


def test_bond_chunking_uses_chinese_dates() -> None:
    stub = StubWindClient(BOND_DATA)
    adapter = WindAdapter(clients={"bond_data": stub})
    df = adapter.fetch_bond_market_data(
        ["26国债01"], start="2026-01-01", end="2026-06-30"
    )
    assert len(stub.calls) == 3
    first_question = stub.calls[0][1]["question"]
    assert "2026年1月1日至2026年3月31日" in first_question
    assert all(call[1]["question"] for call in stub.calls)
    assert all(tool.startswith("get_") for tool, _ in stub.calls)
    assert len(df) == 6

    with pytest.raises(ValueError):
        adapter.fetch_bond_market_data(
            ["26国债01"], start="2026-01-01", end="2026-06-30", chunk_days=120
        )


def test_payload_error_maps_to_source_error() -> None:
    stub = StubWindClient({"data": None, "error": {"code": 1, "message": "boom"}})
    adapter = WindAdapter(clients={"stock_data": stub})
    with pytest.raises(SourceError, match="boom"):
        adapter.fetch_bars(
            [SecCode.parse("600519.SH")],
            start="2026-09-09",
            end="2026-09-10",
            freq="1d",
            adjust=None,
            fields=None,
        )


def test_missing_credential_raises_on_use() -> None:
    adapter = WindAdapter()
    with pytest.raises(MissingCredentialError):
        adapter.fetch_bars(
            [SecCode.parse("600519.SH")],
            start="2026-09-09",
            end="2026-09-10",
            freq="1d",
            adjust=None,
            fields=None,
        )


def test_capabilities() -> None:
    adapter = WindAdapter(clients={})
    assert adapter.capabilities == frozenset({"bars", "snapshot"})
