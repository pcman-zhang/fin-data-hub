"""缓存装配：环境变量 → :class:`LayeredCache`（未配置 Redis 时返回 ``None``）。

```
FDP_REDIS_URL             Redis 连接串（如 redis://redis:6379/0）；未设置则不启用缓存
FDP_CACHE_TTL             默认 TTL（秒，默认 21600 = 6h）
FDP_CACHE_TTL_<DOMAIN>    按域覆盖（域名大写，如 FDP_CACHE_TTL_CN_EQUITY）
FDP_CACHE_L1_ENTRIES      L1 条数上限（默认 4096）
FDP_CACHE_L1_BYTES        L1 字节上限（默认 256 MiB）
```

缓存非权威：后端不可用时 fail-open（直查权威层）。
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from fin_data_platform.cache.backend import InMemoryCache, RedisCache
from fin_data_platform.cache.layered import DEFAULT_TTL, LayeredCache

ENV_REDIS_URL = "FDP_REDIS_URL"
ENV_CACHE_TTL = "FDP_CACHE_TTL"
ENV_L1_ENTRIES = "FDP_CACHE_L1_ENTRIES"
ENV_L1_BYTES = "FDP_CACHE_L1_BYTES"

_DEFAULT_L1_ENTRIES = 4096
_DEFAULT_L1_BYTES = 256 * 1024 * 1024


def _float_env(env: Mapping[str, str], name: str, default: float) -> float:
    raw = (env.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} 非法（应为数值）: {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"{name} 必须为正数: {raw!r}")
    return value


def _int_env(env: Mapping[str, str], name: str, default: int) -> int:
    return int(_float_env(env, name, float(default)))


def _domain_env_name(domain: str) -> str:
    return f"FDP_CACHE_TTL_{domain.upper().replace('.', '_')}"


def ttl_for_domain(
    domain: str, *, env: Mapping[str, str] | None = None, default: float = DEFAULT_TTL
) -> float:
    """按域 TTL：``FDP_CACHE_TTL_<DOMAIN>`` > ``FDP_CACHE_TTL`` > 默认。"""
    source = env if env is not None else os.environ
    name = _domain_env_name(domain)
    override = source.get(name)
    if override:
        return _float_env(source, name, default)
    return _float_env(source, ENV_CACHE_TTL, default)


def cache_from_env(env: Mapping[str, str] | None = None) -> LayeredCache | None:
    """构建分层缓存；未配置 ``FDP_REDIS_URL`` 时返回 ``None``（不启用）。"""
    source = env if env is not None else os.environ
    url = (source.get(ENV_REDIS_URL) or "").strip()
    if not url:
        return None
    l1 = InMemoryCache(
        max_entries=_int_env(source, ENV_L1_ENTRIES, _DEFAULT_L1_ENTRIES),
        max_bytes=_int_env(source, ENV_L1_BYTES, _DEFAULT_L1_BYTES),
    )
    default_ttl = _float_env(source, ENV_CACHE_TTL, DEFAULT_TTL)
    return LayeredCache(
        l1,
        RedisCache(url),
        default_ttl=default_ttl,
        ttl_resolver=lambda domain: ttl_for_domain(
            domain, env=source, default=default_ttl
        ),
    )
