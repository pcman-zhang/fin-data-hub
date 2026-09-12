import pandas as pd
import pytest

from fin_data_hub import DataHub, HubConfig, SecCode, Source
from fin_data_hub.capabilities import EndpointCapability, get_capability, split_codes
from fin_data_hub.sources import BaseAdapter, SourceRegistry


# 能力表：iFinD EDB 一次一指标、Wind 快照单次 ≤50
def test_capability_table_facts() -> None:
    edb = get_capability(Source.IFIND, "edb")
    assert edb.max_indicators_per_call == 1
    assert edb.cost_class == "metered"

    snapshot = get_capability(Source.WIND, "snapshot")
    assert snapshot.max_codes_per_call == 50
    assert snapshot.cost_class == "premium"

    tushare_bars = get_capability(Source.TUSHARE, "bars")
    assert tushare_bars.max_codes_per_call is None
    assert tushare_bars.cost_class == "free"


def test_get_capability_default_for_unknown() -> None:
    default = get_capability(Source.AKSHARE, "unknown-capability")
    assert default == EndpointCapability(max_codes_per_call=None)


def test_split_codes_boundaries() -> None:
    codes = [SecCode.parse(f"{600000 + i}.SH") for i in range(3)]
    tushare_chunks = split_codes(Source.TUSHARE, "bars", codes)
    assert [len(chunk) for chunk in tushare_chunks] == [3]

    akshare_chunks = split_codes(Source.AKSHARE, "bars", codes)
    assert [len(chunk) for chunk in akshare_chunks] == [1, 1, 1]

    many = [SecCode.parse(f"{600000 + i}.SH") for i in range(120)]
    wind_chunks = split_codes(Source.WIND, "snapshot", many)
    assert [len(chunk) for chunk in wind_chunks] == [50, 50, 20]

    wind_bars = split_codes(Source.WIND, "bars", codes)
    assert [len(chunk) for chunk in wind_bars] == [1, 1, 1]


class AkshareLikeBarsAdapter(BaseAdapter):
    source = Source.AKSHARE
    capabilities = frozenset({BaseAdapter.CAP_BARS})

    def __init__(self) -> None:
        self.chunks: list[list[str]] = []

    def fetch_bars(self, codes, *, start, end, freq, adjust, fields):
        self.chunks.append([code.canonical for code in codes])
        rows = []
        for code in codes:
            row = {
                "code": code.canonical,
                "date": "2026-01-05",
                "open": 1.0,
                "high": 1.0,
                "low": 1.0,
                "close": 1.0,
                "volume": 1,
                "amount": 1.0,
            }
            rows.append(row)
            rows.append(dict(row))  # 重复行，验证门面去重
        return pd.DataFrame(rows)


def test_facade_chunks_per_capability_and_merges() -> None:
    adapter = AkshareLikeBarsAdapter()
    hub = DataHub(HubConfig(), registry=SourceRegistry([adapter]))
    df = hub.get_bars(
        ["600002.SH", "600000.SH", "600001.SH"],
        start="20260101",
        end="20260131",
        source="akshare",
    )
    # 单标的源：3 个代码 → 3 次调用，每次 1 个
    assert [len(chunk) for chunk in adapter.chunks] == [1, 1, 1]
    # 合并去重 + 按 code 排序
    assert df["code"].tolist() == ["600000.SH", "600001.SH", "600002.SH"]
    assert len(df) == 3


class WindLikeSnapshotAdapter(BaseAdapter):
    source = Source.WIND
    capabilities = frozenset({BaseAdapter.CAP_SNAPSHOT})

    def __init__(self) -> None:
        self.chunks: list[int] = []

    def fetch_snapshot(self, codes, *, fields):
        self.chunks.append(len(codes))
        return pd.DataFrame(
            [
                {
                    "code": code.canonical,
                    "date": "2026-01-05",
                    "last": 1.0,
                    "open": 1.0,
                    "high": 1.0,
                    "low": 1.0,
                    "prev_close": 1.0,
                    "volume": 1,
                    "amount": 1.0,
                }
                for code in codes
            ]
        )


def test_facade_snapshot_chunks_at_50() -> None:
    adapter = WindLikeSnapshotAdapter()
    hub = DataHub(HubConfig(), registry=SourceRegistry([adapter]))
    codes = [f"{600000 + i}.SH" for i in range(51)]
    df = hub.get_snapshot(codes, source="wind")
    assert adapter.chunks == [50, 1]
    assert len(df) == 51
    assert df["code"].is_monotonic_increasing


def test_facade_rejects_empty_codes() -> None:
    hub = DataHub(
        HubConfig(), registry=SourceRegistry([AkshareLikeBarsAdapter()])
    )
    with pytest.raises(ValueError, match="codes"):
        hub.get_bars([], start="20260101", end="20260131", source="akshare")
