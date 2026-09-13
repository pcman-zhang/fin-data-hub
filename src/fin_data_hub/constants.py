"""全局常量：attrs 键与 venue → currency 映射。"""

from __future__ import annotations

from fin_data_hub.enums import Currency, Venue

#: DataFrame ``attrs`` 键
ATTR_SOURCE = "source"
ATTR_REQUESTED_SOURCE = "requested_source"
ATTR_FACTOR_SOURCE = "factor_source"
ATTR_FILLED_FROM = "filled_from"
ATTR_CACHED = "cached"
ATTR_FETCHED_AT = "fetched_at"
ATTR_CODE_FORMAT = "code_format"
ATTR_ADJUST = "adjust"

#: venue → 货币（``.GI`` 需参考数据判定，故不在此表，结果为 None）
VENUE_CURRENCY: dict[Venue, Currency] = {
    Venue.SH: Currency.CNY,
    Venue.SZ: Currency.CNY,
    Venue.BJ: Currency.CNY,
    Venue.OF: Currency.CNY,
    Venue.TI: Currency.CNY,
    Venue.WI: Currency.CNY,
    Venue.CSI: Currency.CNY,
    Venue.HK: Currency.HKD,
    Venue.O: Currency.USD,
    Venue.N: Currency.USD,
    Venue.A: Currency.USD,
}


def currency_for_venue(venue: str | Venue) -> Currency | None:
    """按 canonical venue 推导货币；未知或需要参考数据时返回 None。"""
    try:
        resolved = Venue(venue)
    except ValueError:
        return None
    return VENUE_CURRENCY.get(resolved)


def currency_for_code(code: str) -> Currency | None:
    """按 canonical 代码（``symbol.VENUE``）推导货币。"""
    if "." not in code:
        return None
    return currency_for_venue(code.rsplit(".", 1)[1])
