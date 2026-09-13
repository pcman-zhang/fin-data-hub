import threading

import pandas as pd

from fin_data_hub import Capability, FinDataHub, HubConfig, Source
from fin_data_hub.sources import BaseAdapter, SourceRegistry
from fin_data_hub.sources.tushare import TushareAdapter
from fin_data_hub.usage import BudgetConfig, UsageLedger

DAY = 86_400.0


class FakeClock:
    def __init__(self, start: float = 1_700_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class MiniTushareApi:
    def trade_cal(self, **kwargs):
        return pd.DataFrame({"cal_date": ["20260105"], "is_open": [1]})


def test_record_and_summary_with_cost_table() -> None:
    budget = BudgetConfig(
        cost_table={"wind.get_stock_kline": 0.5, "tushare": 1.0}
    )
    ledger = UsageLedger(budget, clock=FakeClock())
    ledger.record("wind", "get_stock_kline", codes=("600519.SH",), latency_ms=12.5)
    ledger.record("tushare", "daily", calls=2)

    summary = ledger.summary()
    assert summary["sources"]["wind"] == {"calls": 1, "cost": 0.5}
    assert summary["sources"]["tushare"] == {"calls": 2, "cost": 2.0}
    assert summary["records"] == 2
    assert ledger.records[0].latency_ms == 12.5
    assert ledger.records[0].codes == ("600519.SH",)


def test_day_rollover_resets_counters() -> None:
    clock = FakeClock()
    ledger = UsageLedger(clock=clock)
    ledger.record("tushare", "daily")
    clock.advance(DAY)
    assert ledger.summary()["sources"] == {}
    ledger.record("tushare", "daily")
    assert ledger.summary()["sources"]["tushare"]["calls"] == 1


def test_budget_warn_then_exceeded_dedup() -> None:
    alerts = []
    budget = BudgetConfig(
        calls_per_day={"wind": 10}, warn_ratio=0.8, on_alert=alerts.append
    )
    ledger = UsageLedger(budget, clock=FakeClock())
    for _ in range(8):
        ledger.record("wind", "get_stock_kline")
    assert [alert.level for alert in alerts] == ["warn"]

    for _ in range(2):
        ledger.record("wind", "get_stock_kline")
    assert [alert.level for alert in alerts] == ["warn", "exceeded"]

    for _ in range(3):
        ledger.record("wind", "get_stock_kline")
    assert len(alerts) == 2  # 同阈值同一天只告警一次
    assert ledger.summary()["alerts"][0]["level"] == "warn"


def test_cost_budget_alert() -> None:
    alerts = []
    budget = BudgetConfig(
        cost_per_day={"wind": 1.0},
        cost_table={"wind.get_economic_data": 10.0},
        warn_ratio=0.5,
        on_alert=alerts.append,
    )
    ledger = UsageLedger(budget, clock=FakeClock())
    ledger.record("wind", "get_economic_data")
    assert alerts[0].metric == "cost"
    assert alerts[0].level == "exceeded"


def test_thread_safety() -> None:
    ledger = UsageLedger(clock=FakeClock())

    def worker() -> None:
        for _ in range(100):
            ledger.record("akshare", "stock_zh_a_hist")

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert ledger.summary()["sources"]["akshare"]["calls"] == 800


def test_records_ring_buffer_bounded() -> None:
    ledger = UsageLedger(max_records=3, clock=FakeClock())
    for index in range(5):
        ledger.record("tushare", f"endpoint-{index}")
    assert len(ledger.records) == 3
    assert ledger.summary()["records"] == 3


def test_on_record_callback_is_cross_process_hook() -> None:
    seen = []
    ledger = UsageLedger(BudgetConfig(on_record=seen.append), clock=FakeClock())
    record = ledger.record("tushare", "daily", calls=2)
    assert seen == [record]
    assert seen[0].calls == 2


def test_on_record_callback_exception_does_not_break_record() -> None:
    def broken(_record) -> None:
        raise RuntimeError("sink down")

    ledger = UsageLedger(BudgetConfig(on_record=broken), clock=FakeClock())
    ledger.record("tushare", "daily")
    assert ledger.summary()["sources"]["tushare"]["calls"] == 1


def test_adapter_records_usage_at_call_boundary() -> None:
    adapter = TushareAdapter(api=MiniTushareApi())
    ledger = UsageLedger(clock=FakeClock())
    adapter.bind_usage(ledger)

    adapter.fetch_trade_calendar(start="20260105", end="20260105")
    summary = ledger.summary()
    assert summary["sources"]["tushare"]["calls"] == 1
    assert ledger.records[0].endpoint == "trade_cal"


class TrackingAdapter(BaseAdapter):
    source = Source.TUSHARE
    capabilities = frozenset({Capability.BARS})

    def fetch_bars(self, codes, *, start, end, freq, adjust, fields):
        self._record("daily", codes=[code.canonical for code in codes])
        return pd.DataFrame(
            {
                "code": [code.canonical for code in codes],
                "date": ["2026-01-05"] * len(codes),
                "open": [1.0] * len(codes),
                "high": [1.0] * len(codes),
                "low": [1.0] * len(codes),
                "close": [1.0] * len(codes),
                "volume": [1] * len(codes),
                "amount": [1.0] * len(codes),
            }
        )


def test_facade_stats_include_cache_and_usage() -> None:
    hub = FinDataHub(HubConfig(), registry=SourceRegistry([TrackingAdapter()]))
    hub.get_bars(["600000.SH"], start="20260101", end="20260131", source="tushare")
    stats = hub.stats()
    assert stats["usage"]["sources"]["tushare"]["calls"] == 1
    assert stats["cache"]["entries"] == 1
    assert stats["cache"]["hits"] + stats["cache"]["misses"] >= 1
