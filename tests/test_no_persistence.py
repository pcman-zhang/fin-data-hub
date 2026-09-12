import pandas as pd

from fin_data_hub import DataHub, HubConfig, Source
from fin_data_hub.sources import BaseAdapter, SourceRegistry


class _BarsAdapter(BaseAdapter):
    source = Source.TUSHARE
    capabilities = frozenset({BaseAdapter.CAP_BARS})

    def fetch_bars(self, codes, *, start, end, freq, adjust, fields):
        self._record("daily", codes=[code.canonical for code in codes])
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


def test_library_writes_no_files(tmp_path, monkeypatch) -> None:
    """AC：库无任何持久化写盘（缓存/计量均仅在内存）。"""
    monkeypatch.chdir(tmp_path)
    hub = DataHub(HubConfig(), registry=SourceRegistry([_BarsAdapter()]))

    hub.get_bars(
        ["600000.SH"], start="20260101", end="20260131", source="tushare"
    )
    hub.get_bars(  # 命中缓存路径
        ["600000.SH"], start="20260101", end="20260131", source="tushare"
    )
    hub.stats()  # 计量统计

    assert list(tmp_path.iterdir()) == []
