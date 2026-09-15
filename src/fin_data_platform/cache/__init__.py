"""平台共享缓存（doc-10 §3.4：缓存非权威）。

- **L1 进程内 + L2 Redis** 分层（:class:`LayeredCache`）；
- **PIT 安全键**：``as_of`` / ``knowledge_time`` 互斥必填 + 参数哈希 + 域代际；
- **代际失效**：同步完成后按域 +1，旧键自然失效（免 SCAN）；
- **跨进程 single-flight**：L2 锁防击穿；等待超时回退自算；
- **fail-open**：后端异常按 miss 处理，直查权威层，不阻塞数据链路；
- **观测**：命中率 / 字节 / 淘汰 / 锁等待快照。

v0 接入层（fin_data_hub）的进程内缓存保持不变，本模块仅服务平台侧。
"""

from fin_data_platform.cache.backend import (
    CacheBackend,
    CacheStats,
    InMemoryCache,
    NullCache,
    RedisCache,
)
from fin_data_platform.cache.factory import (
    cache_from_env,
    ttl_for_domain,
)
from fin_data_platform.cache.keys import (
    KEY_PREFIX,
    bump_generation_of,
    cache_key,
    generation_of,
    lock_key,
    params_hash,
    pit_token,
)
from fin_data_platform.cache.layered import DEFAULT_TTL, LayeredCache
from fin_data_platform.cache.serialize import (
    CACHE_FORMAT_VERSION,
    CacheFormatError,
    decode,
    encode,
)

__all__ = [
    "CACHE_FORMAT_VERSION",
    "DEFAULT_TTL",
    "KEY_PREFIX",
    "CacheBackend",
    "CacheFormatError",
    "CacheStats",
    "InMemoryCache",
    "LayeredCache",
    "NullCache",
    "RedisCache",
    "bump_generation_of",
    "cache_from_env",
    "cache_key",
    "decode",
    "encode",
    "generation_of",
    "lock_key",
    "params_hash",
    "pit_token",
    "ttl_for_domain",
]
