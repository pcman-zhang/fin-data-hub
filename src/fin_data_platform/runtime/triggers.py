"""APScheduler 触发入口（TASK-3.6 切片 2）。

调度注册持久化在 APScheduler job store（PostgreSQL）；**运行状态权威仍在
``meta.job_runs``**。job store 只序列化模块级 :func:`fire` 与 ``job_id``，
真正的处理器在进程启动时登记（内存查找），避免序列化闭包。
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)

_HANDLERS: dict[str, Callable[[str], None]] = {}
_LOCK = threading.Lock()


def register_handler(job_id: str, handler: Callable[[str], None]) -> None:
    with _LOCK:
        _HANDLERS[job_id] = handler


def unregister_handler(job_id: str) -> None:
    with _LOCK:
        _HANDLERS.pop(job_id, None)


def clear_handlers() -> None:
    with _LOCK:
        _HANDLERS.clear()


def fire(job_id: str) -> None:
    """APScheduler 调度入口：按 job_id 分发到进程内处理器。"""
    with _LOCK:
        handler = _HANDLERS.get(job_id)
    if handler is None:
        logger.warning("触发时未注册处理器（任务已移除或进程未初始化）: %s", job_id)
        return
    handler(job_id)
