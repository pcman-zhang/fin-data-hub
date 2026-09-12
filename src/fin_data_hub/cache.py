"""进程内内存缓存：TTL + LRU + 字节预算 + single-flight。

设计要点（见 doc-1 §7）：
- 仅进程内内存，不落盘、不跨进程共享；
- 字节预算为主（``max_bytes``），条数（``max_entries``）与单条上限
  （``max_entry_bytes``）兜底；
- ``force=True`` 跳过读取并覆盖写入；
- single-flight：同一 key 并发未命中时仅一个线程真正执行 loader；
- 线程安全；pandas>=3.0 CoW 下默认直接返回缓存对象（``copy_on_return=True``
  可强制深拷贝隔离）。
"""

from __future__ import annotations

import sys
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from typing import Any, TypeVar

import pandas as pd

T = TypeVar("T")

Missing = object()

_SWEEP_EVERY = 128


def default_size_fn(value: Any) -> int:
    """估算对象占用字节数（DataFrame 用 deep memory_usage）。"""
    if isinstance(value, pd.DataFrame):
        return int(value.memory_usage(deep=True, index=True).sum())
    if isinstance(value, pd.Series):
        return int(value.memory_usage(deep=True, index=True))
    return sys.getsizeof(value)


@dataclass(frozen=True, slots=True)
class CacheStats:
    entries: int
    bytes: int
    hits: int
    misses: int
    evictions: int


@dataclass(slots=True)
class _Entry:
    value: Any
    expires_at: float | None


class _Flight:
    __slots__ = ("event", "value", "error")

    def __init__(self) -> None:
        self.event = threading.Event()
        self.value: Any = None
        self.error: BaseException | None = None


class MemoryCache:
    """线程安全的 TTL + LRU 内存缓存。"""

    def __init__(
        self,
        *,
        max_bytes: int = 512 * 1024 * 1024,
        max_entries: int = 4096,
        max_entry_bytes: int = 64 * 1024 * 1024,
        ttl: float | None = 6 * 3600,
        size_safety_factor: float = 1.2,
        size_fn: Callable[[Any], int] | None = None,
        copy_on_return: bool = False,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_bytes <= 0 or max_entries <= 0 or max_entry_bytes <= 0:
            raise ValueError("cache 上限必须为正数")
        if size_safety_factor < 1:
            raise ValueError("size_safety_factor 必须 >= 1")
        self.max_bytes = int(max_bytes)
        self.max_entries = int(max_entries)
        self.max_entry_bytes = int(max_entry_bytes)
        self.ttl = ttl
        self._size_fn = size_fn or default_size_fn
        self._size_safety_factor = size_safety_factor
        self.copy_on_return = copy_on_return
        self._time_fn = time_fn

        self._entries: OrderedDict[Hashable, _Entry] = OrderedDict()
        self._sizes: dict[Hashable, int] = {}
        self._total_bytes = 0
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._stores = 0
        self._flights: dict[Hashable, _Flight] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ 读取
    def get(self, key: Hashable, default: Any = None) -> Any:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self._misses += 1
                return default
            if entry.expires_at is not None and self._time_fn() >= entry.expires_at:
                self._remove(key)
                self._misses += 1
                return default
            self._entries.move_to_end(key)
            self._hits += 1
            return self._copy(entry.value)

    def contains(self, key: Hashable) -> bool:
        """key 是否存在且未过期（不改变命中统计）。"""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return False
            if entry.expires_at is not None and self._time_fn() >= entry.expires_at:
                self._remove(key)
                return False
            return True

    def put(self, key: Hashable, value: Any, *, ttl: float | None = None) -> bool:
        """写入缓存；超过 ``max_entry_bytes`` 时跳过并返回 False。"""
        effective_ttl = self.ttl if ttl is None else ttl
        size = int(self._size_fn(value) * self._size_safety_factor)
        if size > self.max_entry_bytes:
            return False
        with self._lock:
            if key in self._entries:
                self._remove(key)
            expires_at = None if effective_ttl is None else self._time_fn() + effective_ttl
            self._entries[key] = _Entry(value=value, expires_at=expires_at)
            self._sizes[key] = size
            self._total_bytes += size
            self._evict()
            self._stores += 1
            if self._stores % _SWEEP_EVERY == 0:
                self._sweep_expired()
            return True

    def get_or_load(
        self,
        key: Hashable,
        loader: Callable[[], T],
        *,
        force: bool = False,
        ttl: float | None = None,
    ) -> T:
        """命中返回缓存；未命中时 single-flight 执行 loader 并写入。"""
        if not force:
            cached = self.get(key, Missing)
            if cached is not Missing:
                return cached
            flight, is_leader = self._join_flight(key)
            if not is_leader:
                flight.event.wait()
                if flight.error is not None:
                    raise flight.error
                return flight.value
            cached = self.get(key, Missing)
            if cached is not Missing:
                self._finish_flight(key, value=cached)
                return cached

        try:
            value = loader()
        except BaseException as exc:
            self._finish_flight(key, error=exc)
            raise
        self.put(key, value, ttl=ttl)
        self._finish_flight(key, value=value)
        return value

    def invalidate(self, key: Hashable) -> None:
        with self._lock:
            self._remove(key)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._sizes.clear()
            self._total_bytes = 0

    def stats(self) -> CacheStats:
        with self._lock:
            return CacheStats(
                entries=len(self._entries),
                bytes=self._total_bytes,
                hits=self._hits,
                misses=self._misses,
                evictions=self._evictions,
            )

    # ------------------------------------------------------------------ 内部
    def _copy(self, value: Any) -> Any:
        if self.copy_on_return and isinstance(value, (pd.DataFrame, pd.Series)):
            return value.copy(deep=True)
        return value

    def _remove(self, key: Hashable) -> None:
        if self._entries.pop(key, None) is not None:
            self._total_bytes -= self._sizes.pop(key, 0)

    def _evict(self) -> None:
        while self._entries and (
            self._total_bytes > self.max_bytes or len(self._entries) > self.max_entries
        ):
            evicted_key, _ = self._entries.popitem(last=False)
            self._total_bytes -= self._sizes.pop(evicted_key, 0)
            self._evictions += 1

    def _sweep_expired(self) -> None:
        now = self._time_fn()
        expired = [
            key
            for key, entry in self._entries.items()
            if entry.expires_at is not None and now >= entry.expires_at
        ]
        for key in expired:
            self._remove(key)

    def _join_flight(self, key: Hashable) -> tuple[_Flight, bool]:
        with self._lock:
            flight = self._flights.get(key)
            if flight is None:
                flight = _Flight()
                self._flights[key] = flight
                return flight, True
            return flight, False

    def _finish_flight(
        self, key: Hashable, *, value: Any = Missing, error: BaseException | None = None
    ) -> None:
        with self._lock:
            flight = self._flights.pop(key, None)
        if flight is None:
            return
        flight.value = value
        flight.error = error
        flight.event.set()
