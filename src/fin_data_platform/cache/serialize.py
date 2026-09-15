"""缓存值序列化：Arrow IPC（DataFrame）/ JSON（小对象）+ 版本头。

格式：``<header json>\\n<payload bytes>``；``header`` 含 ``v``（格式版本）与 ``type``。
版本不匹配 → :class:`CacheFormatError`（调用方按 miss 处理，fail-open）。
"""

from __future__ import annotations

import json
from typing import Any

try:  # pragma: no cover - 依赖缺失路径由 factory 负责提示
    import pyarrow as pa  # type: ignore[import-untyped]
    import pyarrow.ipc as pa_ipc  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    pa = None  # type: ignore[assignment]
    pa_ipc = None  # type: ignore[assignment]

import pandas as pd

#: 缓存值格式版本（不兼容变更时 +1；旧值按 miss 处理）
CACHE_FORMAT_VERSION = 1

_SEPARATOR = b"\n"


class CacheFormatError(ValueError):
    """缓存值格式非法或版本不兼容。"""


def _reject_unsupported(obj: Any) -> Any:
    """JSON 无法表达且未列入白名单的类型：直接失败（调用方按“不缓存”处理）。"""
    raise TypeError(
        f"缓存值包含不支持的类型 {type(obj).__name__}；"
        "请返回 DataFrame 或 JSON 可表达的对象（dict/list/str/int/float/bool/None）"
    )


def encode(value: Any) -> bytes:
    """序列化缓存值（DataFrame → Arrow IPC；其余 → JSON）。

    不支持的类型直接抛错（由 :meth:`LayeredCache._store` 吞掉 → 不缓存），
    避免静默字符串化导致「命中类型与首次返回不一致」。
    """
    if isinstance(value, pd.DataFrame):
        if pa is None or pa_ipc is None:  # pragma: no cover - 依赖提示
            raise ImportError(
                "Arrow 序列化需要 pyarrow：pip install 'fin-data-platform[cache]'"
            )
        table = pa.Table.from_pandas(value, preserve_index=True)
        sink = pa.BufferOutputStream()
        with pa_ipc.new_stream(sink, table.schema) as writer:
            writer.write_table(table)
        header = {"v": CACHE_FORMAT_VERSION, "type": "arrow"}
        payload = sink.getvalue().to_pybytes()
    else:
        header = {"v": CACHE_FORMAT_VERSION, "type": "json"}
        payload = json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), default=_reject_unsupported
        ).encode("utf-8")
    return json.dumps(header, separators=(",", ":")).encode("utf-8") + _SEPARATOR + payload


def decode(data: bytes) -> Any:
    """反序列化缓存值；格式/版本不兼容抛 :class:`CacheFormatError`。"""
    head, sep, payload = data.partition(_SEPARATOR)
    if not sep:
        raise CacheFormatError("缓存值缺少头部")
    try:
        header = json.loads(head.decode("utf-8"))
        version = int(header["v"])
        value_type = str(header["type"])
    except (ValueError, KeyError, TypeError) as exc:
        raise CacheFormatError(f"缓存值头部非法: {head!r}") from exc
    if version != CACHE_FORMAT_VERSION:
        raise CacheFormatError(
            f"缓存值版本不兼容: {version} != {CACHE_FORMAT_VERSION}"
        )
    if value_type == "arrow":
        if pa is None or pa_ipc is None:  # pragma: no cover - 依赖提示
            raise ImportError(
                "Arrow 反序列化需要 pyarrow：pip install 'fin-data-platform[cache]'"
            )
        table = pa_ipc.open_stream(payload).read_all()
        return table.to_pandas()
    if value_type == "json":
        return json.loads(payload.decode("utf-8"))
    raise CacheFormatError(f"未知缓存值类型: {value_type!r}")
