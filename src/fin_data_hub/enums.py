"""公共枚举。"""

from __future__ import annotations

from enum import StrEnum


class Source(StrEnum):
    """数据源标识（对外接口 source 参数的取值）。"""

    TUSHARE = "tushare"
    WIND = "wind"
    IFIND = "ifind"
    AKSHARE = "akshare"
    FUYAO = "fuyao"
