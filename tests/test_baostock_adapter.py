import sys
import threading
import time
import types

import pandas as pd
import pytest

from fin_data_hub import Capability, HubConfig, SecCode, Source
from fin_data_hub.errors import SourceError, UnknownSecurityError, UnsupportedCapability
from fin_data_hub.mapping import get_mapper
from fin_data_hub.ratelimit import RateLimiter, RateLimiterSet
from fin_data_hub.sources import BaseAdapter, SourceRegistry
from fin_data_hub.sources import baostock as baostock_module
from fin_data_hub.sources.baostock import BaoStockAdapter
from fin_data_hub.sources.factory import build_registry


class FakeResult:
    def __init__(self, fields, rows, error_code="0", error_msg=""):
        self.fields = fields
        self._rows = rows
        self._index = -1
        self.error_code = error_code
        self.error_msg = error_msg

    def next(self) -> bool:
        self._index += 1
        return self._index < len(self._rows)

    def get_row_data(self):
        return self._rows[self._index]


class FakeBaoStock:
    def __init__(self) -> None:
        self.logins = 0
        self.logouts = 0
        self.calls: list[tuple[str, dict]] = []
        self.active = 0
        self.max_active = 0
        self.error_code = "0"

    def login(self):
        self.logins += 1
        return FakeResult([], [])

    def logout(self):
        self.logouts += 1
        return FakeResult([], [])

    def _serve(self, name, fields, rows, **kwargs):
        self.calls.append((name, kwargs))
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            time.sleep(0.001)
            return FakeResult(fields, rows, error_code=self.error_code)
        finally:
            self.active -= 1

    def query_history_k_data_plus(
        self,
        code,
        fields,
        start_date=None,
        end_date=None,
        frequency=None,
        adjustflag=None,
        **kwargs,
    ):
        rows = [
            [
                "2026-09-01",
                "sh.600000",
                "1295.0",
                "1307.99",
                "1286.10",
                "1299.56",
                "3266402",
                "4242441000",
            ]
        ]
        return self._serve(
            "query_history_k_data_plus",
            fields.split(","),
            rows,
            code=code,
            adjustflag=adjustflag,
            start_date=start_date,
            end_date=end_date,
        )

    def query_stock_basic(self, **kwargs):
        rows = [["sh.600000", "浦发银行", "1999-11-10", "", "1", "1"]]
        return self._serve(
            "query_stock_basic",
            ["code", "code_name", "ipoDate", "outDate", "type", "status"],
            rows,
        )

    def query_trade_dates(self, **kwargs):
        rows = [["2026-09-01", "1"], ["2026-09-02", "0"]]
        return self._serve(
            "query_trade_dates",
            ["calendar_date", "is_trading_day"],
            rows,
            **kwargs,
        )

    def query_adjust_factor(self, code, start_date=None, end_date=None, **kwargs):
        rows = [
            ["sh.600000", "2024-07-18", "0.967359", "12.388310", "12.388310"],
            ["sh.600000", "2025-07-16", "0.976909", "12.763991", "12.763991"],
            ["sh.600000", "2026-07-15", "1.000000", "13.138046", "13.138046"],
        ]
        return self._serve(
            "query_adjust_factor",
            [
                "code",
                "dividOperateDate",
                "foreAdjustFactor",
                "backAdjustFactor",
                "adjustFactor",
            ],
            rows,
            code=code,
            start_date=start_date,
            end_date=end_date,
        )


@pytest.fixture(autouse=True)
def _reset_session() -> None:
    baostock_module._reset_session_state()
    yield
    baostock_module._reset_session_state()


def make_adapter(fake: FakeBaoStock | None = None) -> tuple[BaoStockAdapter, FakeBaoStock]:
    fake = fake or FakeBaoStock()
    adapter = BaoStockAdapter(bs_module=fake)
    adapter.bind_rate_limits(
        RateLimiterSet(RateLimiter(rate=10_000, burst=10_000))
    )
    return adapter, fake


def test_mapper_roundtrip_and_rejections() -> None:
    mapper = get_mapper(Source.BAOSTOCK)
    assert mapper.to_source(SecCode.parse("600000.SH")) == "sh.600000"
    assert mapper.to_source(SecCode.parse("399006.SZ")) == "sz.399006"
    assert mapper.from_source("sh.600000").canonical == "600000.SH"
    assert mapper.from_source("sz.399006").canonical == "399006.SZ"
    with pytest.raises(UnsupportedCapability):
        mapper.to_source(SecCode.parse("920002.BJ"))
    with pytest.raises(UnknownSecurityError):
        mapper.from_source("xx.600000")


def test_bars_mapping_and_adjust_flags() -> None:
    adapter, fake = make_adapter()
    df = adapter.fetch_bars(
        [SecCode.parse("600000.SH")],
        start="2026-09-01",
        end="2026-09-02",
        freq="1d",
        adjust=None,
        fields=None,
    )
    assert fake.calls[0][1]["code"] == "sh.600000"
    assert fake.calls[0][1]["adjustflag"] == "3"
    assert fake.calls[0][1]["start_date"] == "2026-09-01"
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
    assert df["close"].tolist() == [1299.56]
    assert df["volume"].tolist() == [3_266_402.0]  # 股
    assert df["amount"].tolist() == [4_242_441_000.0]  # 元

    adapter_qfq, fake_qfq = make_adapter()
    adapter_qfq.fetch_bars(
        [SecCode.parse("600000.SH")],
        start="20260901",
        end="20260902",
        freq="1d",
        adjust="qfq",
        fields=None,
    )
    assert fake_qfq.calls[0][1]["adjustflag"] == "2"


def test_bars_rejections() -> None:
    adapter, _ = make_adapter()
    with pytest.raises(UnsupportedCapability):
        adapter.fetch_bars(
            [SecCode.parse("600000.SH"), SecCode.parse("000001.SZ")],
            start="20260901",
            end="20260902",
            freq="1d",
            adjust=None,
            fields=None,
        )
    with pytest.raises(UnsupportedCapability):
        adapter.fetch_bars(
            [SecCode.parse("600000.SH")],
            start="20260901",
            end="20260902",
            freq="1w",
            adjust=None,
            fields=None,
        )


def test_login_refcount_shared_session() -> None:
    fake = FakeBaoStock()
    first = BaoStockAdapter(bs_module=fake)
    second = BaoStockAdapter(bs_module=fake)
    first.fetch_trade_calendar(start="20260901", end="20260902")
    second.fetch_trade_calendar(start="20260901", end="20260902")
    assert fake.logins == 1  # 共享同一进程级会话

    first.close()
    assert fake.logouts == 0  # 仍有使用者
    second.close()
    assert fake.logouts == 1


def test_calls_are_serialized_across_threads() -> None:
    adapter, fake = make_adapter()

    def worker() -> None:
        adapter.fetch_trade_calendar(start="20260901", end="20260902")

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert fake.max_active == 1  # 全局锁串行化


def test_reference_stock_list() -> None:
    adapter, _ = make_adapter()
    df = adapter.fetch_reference("stock_list")
    assert df.iloc[0]["code"] == "600000.SH"
    assert df.iloc[0]["name"] == "浦发银行"
    assert df.iloc[0]["market"] == "SH"
    assert str(df["list_date"].dtype) == "datetime64[ns]"

    with pytest.raises(UnsupportedCapability):
        adapter.fetch_reference("fund_list")


def test_trade_calendar_and_error_mapping() -> None:
    adapter, fake = make_adapter()
    df = adapter.fetch_trade_calendar(start="2026-09-01", end="2026-09-02")
    assert df["is_open"].tolist() == [True, False]

    failing, failing_fake = make_adapter()
    failing_fake.error_code = "10001"
    with pytest.raises(SourceError, match="10001"):
        failing.fetch_trade_calendar(start="20260901", end="20260902")


def test_adjust_factors_event_steps_with_base_row() -> None:
    adapter, fake = make_adapter()
    df = adapter.fetch_adjust_factors(
        [SecCode.parse("600000.SH")], start="2026-01-01", end="2026-12-31"
    )
    call = fake.calls[-1]
    assert call[0] == "query_adjust_factor"
    assert call[1]["code"] == "sh.600000"
    assert call[1]["start_date"] == "1990-01-01"  # 回看取窗口基准
    assert list(df.columns) == ["code", "date", "adj_factor"]
    # 基准行（取最近事件 2025-07-16 的累计因子）+ 2026-07-15 事件行
    assert df["date"].tolist() == [
        pd.Timestamp("2026-01-01"),
        pd.Timestamp("2026-07-15"),
    ]
    assert df["adj_factor"].tolist() == [12.763991, 13.138046]


def test_adjust_factors_compose_qfq_and_hfq() -> None:
    from fin_data_hub.routing import apply_adjustment

    adapter, _ = make_adapter()
    factors = adapter.fetch_adjust_factors(
        [SecCode.parse("600000.SH")], start="2026-07-15", end="2026-08-31"
    )
    bars = pd.DataFrame(
        {
            "code": ["600000.SH"],
            "date": pd.to_datetime(["2026-07-15"]),
            "open": [10.0],
            "high": [10.0],
            "low": [10.0],
            "close": [10.0],
            "volume": [100],
            "amount": [1000.0],
        }
    )
    hfq = apply_adjustment(bars, factors, "hfq")
    qfq = apply_adjustment(bars, factors, "qfq")
    assert hfq["close"].tolist() == [10.0 * 13.138046]  # raw × f
    assert qfq["close"].tolist() == [10.0]  # raw × f / f_last（事件当日=f_last）


def test_adjust_factors_rejections() -> None:
    adapter, _ = make_adapter()
    with pytest.raises(UnsupportedCapability):
        adapter.fetch_adjust_factors(
            [SecCode.parse("600000.SH"), SecCode.parse("000001.SZ")],
            start="20260101",
            end="20261231",
        )
    with pytest.raises(UnsupportedCapability, match="仅覆盖股票"):
        adapter.fetch_adjust_factors(
            [SecCode.parse("510300.SH")], start="20260101", end="20261231"
        )


def test_capabilities_and_factory_registration(monkeypatch) -> None:
    adapter, _ = make_adapter()
    assert adapter.capabilities == frozenset(
        {"bars", "reference", "trade_calendar", "adjust_factors"}
    )

    monkeypatch.setitem(sys.modules, "baostock", types.ModuleType("baostock"))
    registry = build_registry(HubConfig(), sources=[Source.BAOSTOCK])
    assert registry.available() == ("baostock",)
    assert isinstance(registry.get(Source.BAOSTOCK), BaseAdapter)


def test_registry_capability_gate() -> None:
    adapter, _ = make_adapter()
    registry = SourceRegistry([adapter])
    assert registry.get_for_capability(Source.BAOSTOCK, Capability.BARS) is adapter
    with pytest.raises(UnsupportedCapability):
        registry.get_for_capability(Source.BAOSTOCK, Capability.SNAPSHOT)


class FlakyBaoStock(FakeBaoStock):
    """模拟网络异常：前 N 次查询失败（异常或连接类错误码）。"""

    def __init__(self, fail_times: int = 1, mode: str = "raise") -> None:
        super().__init__()
        self.fail_times = fail_times
        self.mode = mode

    def query_trade_dates(self, **kwargs):
        if self.fail_times > 0:
            self.fail_times -= 1
            if self.mode == "raise":
                raise OSError("网络连接断开")
            return FakeResult(
                [], [], error_code="10002007", error_msg="网络连接失败"
            )
        return super().query_trade_dates(**kwargs)


def test_relogin_after_network_exception() -> None:
    fake = FlakyBaoStock(fail_times=1)
    adapter, _ = make_adapter(fake)
    df = adapter.fetch_trade_calendar(start="20260901", end="20260902")
    assert df["is_open"].tolist() == [True, False]
    assert fake.logins == 2  # 初次 + 断线重登录


def test_relogin_on_connection_error_code() -> None:
    fake = FlakyBaoStock(fail_times=1, mode="code")
    adapter, _ = make_adapter(fake)
    df = adapter.fetch_trade_calendar(start="20260901", end="20260902")
    assert not df.empty
    assert fake.logins == 2


def test_persistent_failure_then_recovery() -> None:
    fake = FlakyBaoStock(fail_times=99)
    adapter = BaoStockAdapter(bs_module=fake, sleep_fn=lambda _: None)
    adapter.bind_rate_limits(RateLimiterSet(RateLimiter(rate=10_000, burst=10_000)))
    with pytest.raises(SourceError, match="调用失败"):
        adapter.fetch_trade_calendar(start="20260901", end="20260902")

    fake.fail_times = 0
    df = adapter.fetch_trade_calendar(start="20260901", end="20260902")
    assert not df.empty
    assert fake.logins >= 3  # 失败期每次重登录 + 恢复后重新登录


def test_non_connection_error_not_retried() -> None:
    fake = FakeBaoStock()
    fake.error_code = "10001"
    adapter, _ = make_adapter(fake)
    with pytest.raises(SourceError, match="10001"):
        adapter.fetch_trade_calendar(start="20260901", end="20260902")
    assert fake.logins == 1  # 非连接错误不重登录
