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
    BAOSTOCK = "baostock"


class SecType(StrEnum):
    """证券类型。"""

    STOCK = "stock"
    ETF = "etf"
    LOF = "lof"
    FUND = "fund"
    INDEX = "index"


class Venue(StrEnum):
    """canonical 市场后缀（Wind 标准）。"""

    SH = "SH"
    SZ = "SZ"
    BJ = "BJ"
    OF = "OF"
    CSI = "CSI"
    HK = "HK"
    O = "O"  # noqa: E741 - Wind 标准后缀
    N = "N"
    A = "A"
    GI = "GI"
    TI = "TI"
    WI = "WI"


class Currency(StrEnum):
    """ISO 4217 货币代码（按需扩展）。"""

    CNY = "CNY"
    HKD = "HKD"
    USD = "USD"
    EUR = "EUR"
    JPY = "JPY"


class Adjust(StrEnum):
    """复权方式；``None`` 表示不复权。"""

    QFQ = "qfq"
    HFQ = "hfq"


class Freq(StrEnum):
    """数据频率（v0 仅支持 ``1d``，其余预留）。"""

    D1 = "1d"
    W1 = "1w"
    MO1 = "1mo"
    Q1 = "1q"
    Y1 = "1y"
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    M60 = "60m"


class ReferenceKind(StrEnum):
    """``get_reference`` 的数据种类。"""

    STOCK_LIST = "stock_list"
    FUND_LIST = "fund_list"
    INDEX_LIST = "index_list"


class Capability(StrEnum):
    """适配器能力标识（取代散落的字符串常量）。"""

    BARS = "bars"
    SNAPSHOT = "snapshot"
    FUND_NAV = "fund_nav"
    REFERENCE = "reference"
    TRADE_CALENDAR = "trade_calendar"
    SECURITY_INFO = "security_info"
    ADJUST_FACTORS = "adjust_factors"
    ADJUSTMENT_EVENTS = "adjustment_events"
    EDB = "edb"
