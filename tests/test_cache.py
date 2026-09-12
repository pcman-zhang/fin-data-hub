import threading
import time

import pandas as pd

from fin_data_hub.cache import MemoryCache


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_ttl_expiry() -> None:
    clock = FakeClock()
    cache = MemoryCache(ttl=10, time_fn=clock)
    cache.put("a", 1)
    assert cache.get("a", None) == 1
    clock.advance(11)
    assert cache.get("a", None) is None
    assert cache.stats().misses >= 1


def test_force_bypasses_and_overwrites() -> None:
    cache = MemoryCache(ttl=100)
    cache.put("k", "old")
    calls: list[int] = []

    def loader() -> str:
        calls.append(1)
        return "new"

    assert cache.get_or_load("k", loader) == "old"
    assert calls == []
    assert cache.get_or_load("k", loader, force=True) == "new"
    assert calls == [1]
    assert cache.get("k") == "new"


def test_lru_eviction_by_entries() -> None:
    cache = MemoryCache(
        max_entries=2, max_bytes=10**9, ttl=None, size_fn=lambda v: 1
    )
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == 1  # a 变为最近使用
    cache.put("c", 3)
    assert cache.get("b", "missing") == "missing"
    assert cache.get("a") == 1
    assert cache.get("c") == 3
    assert cache.stats().evictions == 1


def test_byte_budget_eviction() -> None:
    cache = MemoryCache(
        max_bytes=250,
        max_entries=100,
        ttl=None,
        size_fn=lambda v: 100,
        size_safety_factor=1.0,
    )
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)
    stats = cache.stats()
    assert stats.entries == 2
    assert stats.bytes == 200
    assert cache.get("a", "missing") == "missing"


def test_max_entry_bytes_skips_store() -> None:
    cache = MemoryCache(max_entry_bytes=50, size_fn=lambda v: 100, ttl=None)
    assert cache.put("big", 1) is False
    assert cache.get("big", "missing") == "missing"
    assert cache.stats().bytes == 0


def test_overwrite_deducts_old_size() -> None:
    sizes = {"old": 100, "new": 40}
    cache = MemoryCache(
        max_bytes=10**6,
        ttl=None,
        size_safety_factor=1.0,
        size_fn=lambda v: sizes[v],
    )
    cache.put("k", "old")
    cache.put("k", "new")
    assert cache.stats().bytes == 40
    assert cache.stats().entries == 1


def test_single_flight_runs_loader_once() -> None:
    cache = MemoryCache(ttl=None)
    calls: list[int] = []
    barrier = threading.Barrier(4)

    def loader() -> str:
        calls.append(threading.get_ident())
        time.sleep(0.05)
        return "value"

    results: list[str] = []

    def worker() -> None:
        barrier.wait()
        results.append(cache.get_or_load("k", loader))

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results == ["value"] * 4
    assert len(calls) == 1


def test_single_flight_propagates_error() -> None:
    cache = MemoryCache(ttl=None)

    def loader() -> str:
        raise RuntimeError("boom")

    try:
        cache.get_or_load("k", loader)
    except RuntimeError:
        pass
    else:  # pragma: no cover
        raise AssertionError("应向上抛出 loader 异常")
    # 失败后缓存未写入，flight 已清理，可重试
    assert cache.get_or_load("k", lambda: "ok") == "ok"


def test_dataframe_size_counted() -> None:
    cache = MemoryCache(ttl=None)
    df = pd.DataFrame({"x": range(1000)})
    cache.put("df", df)
    raw = int(df.memory_usage(deep=True, index=True).sum())
    assert cache.stats().bytes >= raw
