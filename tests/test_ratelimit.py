import time

import pytest

from fin_data_hub.errors import NetworkError, RateLimitError, RateLimitTimeout
from fin_data_hub.ratelimit import (
    RateLimiter,
    RateLimiterSet,
    compute_backoff,
    retry_call,
)


def test_token_bucket_throttles() -> None:
    limiter = RateLimiter(rate=50, burst=1)
    start = time.monotonic()
    limiter.acquire()
    limiter.acquire()
    assert time.monotonic() - start >= 0.015


def test_acquire_timeout_raises() -> None:
    limiter = RateLimiter(rate=0.001, burst=1)
    limiter.acquire()
    with pytest.raises(RateLimitTimeout):
        limiter.acquire(timeout=0.02)


def test_try_acquire_non_blocking() -> None:
    limiter = RateLimiter(rate=10, burst=1)
    assert limiter.try_acquire() is True
    assert limiter.try_acquire() is False


def test_oversized_request_rejected() -> None:
    limiter = RateLimiter(rate=10, burst=1)
    with pytest.raises(ValueError):
        limiter.acquire(tokens=2)


def test_endpoint_override_isolated() -> None:
    default = RateLimiter(rate=1000, burst=10)
    slow = RateLimiter(rate=0.001, burst=1)
    limiters = RateLimiterSet(default, {"stock_basic": slow})

    limiters.acquire("other")
    slow.acquire()  # 消耗 slow 桶的唯一令牌
    with pytest.raises(RateLimitTimeout):
        limiters.acquire("stock_basic", timeout=0.02)
    limiters.acquire("other")  # 默认桶不受影响


def test_compute_backoff() -> None:
    assert compute_backoff(1, base=2.0, jitter=0.0) == 2.0
    assert compute_backoff(3, base=2.0, max_delay=5.0, jitter=0.0) == 5.0
    delay = compute_backoff(2, base=1.0, jitter=0.5, rand=lambda: 0.0)
    assert 0 <= delay < 2.0


def test_retry_call_succeeds_after_failures() -> None:
    attempts = {"n": 0}
    sleeps: list[float] = []

    def fn() -> str:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise NetworkError("boom")
        return "ok"

    result = retry_call(fn, attempts=3, sleep_fn=sleeps.append, base=1.0, jitter=0.0)
    assert result == "ok"
    assert attempts["n"] == 3
    assert sleeps == [1.0, 2.0]


def test_retry_call_exhausts_and_raises() -> None:
    def fn() -> None:
        raise RateLimitError("limit")

    with pytest.raises(RateLimitError):
        retry_call(fn, attempts=2, sleep_fn=lambda _: None, base=1.0, jitter=0.0)


def test_retry_call_does_not_retry_other_errors() -> None:
    calls = {"n": 0}

    def fn() -> None:
        calls["n"] += 1
        raise ValueError("no retry")

    with pytest.raises(ValueError):
        retry_call(fn, attempts=3, sleep_fn=lambda _: None)
    assert calls["n"] == 1


def test_on_retry_callback() -> None:
    events: list[tuple[int, float]] = []

    def fn() -> str:
        raise NetworkError("x")

    with pytest.raises(NetworkError):
        retry_call(
            fn,
            attempts=2,
            sleep_fn=lambda _: None,
            base=1.0,
            jitter=0.0,
            on_retry=lambda attempt, delay, exc: events.append((attempt, delay)),
        )
    assert events == [(1, 1.0)]
