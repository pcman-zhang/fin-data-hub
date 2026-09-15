"""缓存键与域代际（PIT 安全）。

键结构：``fdh:{domain}:{panel}:g{generation}:{pit}:{params_hash}``

- **PIT 维度必填**：``as_of``（知识时间视角）与 ``knowledge_time``（数据知识时点）
  **互斥且必须二选一**——禁止无时间维度键，防前视与陈旧混用；
- **域代际**：``fdh:gen:{domain}`` 计数；同步完成后 +1，旧键自然失效（免 SCAN）；
- **参数哈希**：规范化 JSON（排序键）取 SHA-256 前 16 位。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

from fin_data_platform.cache.backend import CacheBackend

KEY_PREFIX = "fdh"

#: 域代际键模板（``incr`` 自增）
GENERATION_KEY = KEY_PREFIX + ":gen:{domain}"

#: 跨进程 single-flight 锁键模板
LOCK_KEY = KEY_PREFIX + ":lock:{key}"

#: 参数哈希长度（hex 字符）
PARAMS_HASH_LENGTH = 16


def _iso(value: date | datetime | str) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def generation_of(backend: CacheBackend, domain: str) -> int:
    """读取域代际（不存在视为 0）。"""
    raw = backend.get(GENERATION_KEY.format(domain=domain))
    if raw is None:
        return 0
    try:
        return int(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
    except (TypeError, ValueError, UnicodeDecodeError):
        return 0


def bump_generation_of(backend: CacheBackend, domain: str) -> int:
    """推进域代际并返回新值（同步完成后的按域失效）。"""
    return backend.incr(GENERATION_KEY.format(domain=domain))


def set_generation_of(backend: CacheBackend, domain: str, value: int) -> None:
    """写入域代际（用于失败恢复后的单调同步；不递减）。"""
    backend.set(GENERATION_KEY.format(domain=domain), str(value).encode("utf-8"))


def pit_token(
    *, as_of: date | datetime | str | None, knowledge_time: date | datetime | str | None
) -> str:
    """构造 PIT 维度 token；两者互斥且必须二选一。"""
    if as_of is not None and knowledge_time is not None:
        raise ValueError("as_of 与 knowledge_time 互斥（禁止混用时间轴）")
    if as_of is not None:
        return f"asof:{_iso(as_of)}"
    if knowledge_time is not None:
        return f"kt:{_iso(knowledge_time)}"
    raise ValueError("缓存键必须携带 PIT 时间语义（as_of 或 knowledge_time 之一）")


def params_hash(params: Mapping[str, Any] | None) -> str:
    """参数规范化哈希（排序键 JSON → SHA-256 前 16 位）。"""
    payload = json.dumps(
        dict(params or {}),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:PARAMS_HASH_LENGTH]


def cache_key(
    domain: str,
    panel: str,
    *,
    generation: int,
    as_of: date | datetime | str | None = None,
    knowledge_time: date | datetime | str | None = None,
    params: Mapping[str, Any] | None = None,
) -> str:
    """构造 PIT 安全缓存键（纯函数；代际由调用方提供）。"""
    if not domain or not panel:
        raise ValueError("domain / panel 不能为空")
    token = pit_token(as_of=as_of, knowledge_time=knowledge_time)
    return (
        f"{KEY_PREFIX}:{domain}:{panel}:g{generation}:{token}:{params_hash(params)}"
    )


def lock_key(key: str) -> str:
    """由缓存键派生锁键。"""
    return LOCK_KEY.format(key=key)
