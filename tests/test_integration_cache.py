"""缓存真 Redis 集成测试（默认跳过：``pytest -m integration``）。

依赖 docker compose 中的 redis 服务（或 ``FDP_TEST_REDIS_URL`` 指定）；
使用独立 DB（默认 15）并在用例前后清空。
"""

from __future__ import annotations

import os
import threading
import time

import pytest
import redis

from fin_data_platform.cache import (
    InMemoryCache,
    LayeredCache,
    RedisCache,
    bump_generation_of,
    generation_of,
)

pytestmark = pytest.mark.integration


def _redis_url() -> str:
    return os.environ.get("FDP_TEST_REDIS_URL", "redis://127.0.0.1:6379/15")


@pytest.fixture()
def client():
    try:
        client = redis.Redis.from_url(
            _redis_url(), socket_timeout=1.0, decode_responses=False
        )
        client.ping()
    except Exception as exc:  # noqa: BLE001 - 环境缺失则跳过
        pytest.skip(f"Redis 不可用（{_redis_url()}）: {exc}")
    client.flushdb()
    yield client
    client.flushdb()


def test_redis_cache_ttl_lock_and_generation(client) -> None:
    cache = RedisCache(_redis_url(), client=client)

    cache.set("k", b"v", ttl=30)
    assert cache.get("k") == b"v"
    ttl = client.ttl("k")
    assert 0 < ttl <= 30

    assert cache.acquire_lock("lock", "t1", ttl=5) is True
    assert cache.acquire_lock("lock", "t2", ttl=5) is False
    cache.release_lock("lock", "t2")  # token 不匹配 → 不释放
    assert cache.acquire_lock("lock", "t3", ttl=5) is False
    cache.release_lock("lock", "t1")
    assert cache.acquire_lock("lock", "t4", ttl=5) is True

    assert generation_of(cache, "cn_equity") == 0
    assert bump_generation_of(cache, "cn_equity") == 1
    assert generation_of(cache, "cn_equity") == 1

    stats = cache.stats()
    # 代际读取（generation_of）同样走 get，命中数 ≥ 1
    assert stats.hits >= 1
    assert stats.memory_bytes is not None and stats.memory_bytes > 0
    assert "evicted_keys" in stats.extra


def test_layered_cross_instance_single_flight_real_redis(client) -> None:
    """两个 LayeredCache 实例共享真 Redis：并发同一键仅执行一次 loader。"""
    caches = [
        LayeredCache(
            InMemoryCache(),
            RedisCache(_redis_url(), client=client),
            lock_wait=5.0,
            poll_interval=0.02,
        )
        for _ in range(2)
    ]
    key = caches[0].build_key("cn_equity", "daily_bar", as_of="2026-09-14")
    calls = {"n": 0}
    barrier = threading.Barrier(2)
    results: list[str] = []

    def loader() -> str:
        calls["n"] += 1
        time.sleep(0.2)
        return "value"

    def worker(cache: LayeredCache) -> None:
        barrier.wait()
        results.append(cache.get_or_load(key, loader))

    threads = [threading.Thread(target=worker, args=(cache,)) for cache in caches]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results == ["value", "value"]
    assert calls["n"] == 1

    # 域失效：代际推进 → 新键不命中旧值
    caches[0].invalidate_domain("cn_equity")
    assert caches[1].generation("cn_equity") == 1
    new_key = caches[1].build_key("cn_equity", "daily_bar", as_of="2026-09-14")
    assert new_key != key
    assert caches[1].get_or_load(new_key, lambda: "value2") == "value2"
