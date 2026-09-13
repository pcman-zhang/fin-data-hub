"""统一标的代码模型（WindCode 风格 ``symbol.VENUE``）。"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from fin_data_hub.enums import SecType, Venue
from fin_data_hub.errors import UnknownSecurityError

#: 已实现类型推断的 CN venue
CN_VENUES = frozenset({Venue.SH, Venue.SZ, Venue.BJ, Venue.OF})
#: 美股交易所（推断为股票）
US_EXCHANGES = frozenset({Venue.O, Venue.N, Venue.A})
#: 指数 venue（推断为指数）
INDEX_VENUES = frozenset({Venue.GI, Venue.TI, Venue.WI, Venue.CSI})
#: 预留 venue（格式层接受，但需显式指定 sec_type）
RESERVED_VENUES = frozenset({Venue.HK})
SUPPORTED_VENUES = (
    CN_VENUES | US_EXCHANGES | INDEX_VENUES | RESERVED_VENUES
)

_NUMERIC_SYMBOL = re.compile(r"^\d{1,6}$")
_ALNUM_SYMBOL = re.compile(r"^[A-Z0-9]{1,10}$")


def infer_sec_type(venue: Venue, symbol: str) -> SecType:
    """按 venue + 代码段推断证券类型；无法识别时抛 ``UnknownSecurityError``。"""
    if venue == Venue.OF:
        return SecType.FUND
    if venue in US_EXCHANGES:
        return SecType.STOCK
    if venue in INDEX_VENUES:
        return SecType.INDEX
    if venue == Venue.SH:
        if symbol.startswith("6"):
            return SecType.STOCK
        if symbol.startswith(("000", "950")):
            return SecType.INDEX
        if symbol.startswith("501"):
            return SecType.LOF
        if symbol.startswith("5"):
            return SecType.ETF
    if venue == Venue.SZ:
        if symbol.startswith(("00", "30")):
            return SecType.STOCK
        if symbol.startswith("15"):
            return SecType.ETF
        if symbol.startswith("16"):
            return SecType.LOF
        if symbol.startswith("39"):
            return SecType.INDEX
    if venue == Venue.BJ and symbol.startswith(("4", "8", "9")):
        return SecType.STOCK
    raise UnknownSecurityError(f"无法推断证券类型: {symbol}.{venue}")


@dataclass(frozen=True, slots=True)
class SecCode:
    """标准化标的代码。

    示例：``600000.SH``、``000001.SZ``、``920002.BJ``、``510300.SH``、
    ``000001.OF``（场外基金）、``000300.SH``（指数）。
    """

    symbol: str
    venue: Venue
    sec_type: SecType

    @classmethod
    def parse(
        cls,
        value: str | SecCode,
        *,
        sec_type: SecType | str | None = None,
    ) -> SecCode:
        """解析并校验代码；``venue`` 大小写不敏感，CN 市场数字代码自动补零。"""
        if isinstance(value, SecCode):
            if sec_type is None:
                return value
            return value.with_sec_type(sec_type)

        if not isinstance(value, str):
            raise UnknownSecurityError(f"代码类型不支持: {type(value).__name__}")

        raw = value.strip()
        if "." not in raw:
            raise UnknownSecurityError(f"代码必须为 symbol.VENUE 形式: {value!r}")

        symbol_part, _, venue_part = raw.rpartition(".")
        try:
            venue = Venue(venue_part.strip().upper())
        except ValueError as exc:
            raise UnknownSecurityError(
                f"未知 venue: {venue_part!r}"
                f"（支持 {sorted(v.value for v in SUPPORTED_VENUES)}）"
            ) from exc

        symbol = symbol_part.strip().upper()
        if venue in CN_VENUES:
            if not _NUMERIC_SYMBOL.match(symbol):
                raise UnknownSecurityError(f"CN 市场代码应为 1-6 位数字: {value!r}")
            symbol = symbol.zfill(6)
        elif not _ALNUM_SYMBOL.match(symbol):
            raise UnknownSecurityError(f"非法代码: {value!r}")

        if sec_type is not None:
            resolved = SecType(sec_type)
        elif venue in RESERVED_VENUES:
            raise UnknownSecurityError(f"venue {venue} 为预留市场，需显式指定 sec_type")
        else:
            resolved = infer_sec_type(venue, symbol)

        return cls(symbol=symbol, venue=venue, sec_type=resolved)

    def with_sec_type(self, sec_type: SecType | str) -> SecCode:
        return replace(self, sec_type=SecType(sec_type))

    @property
    def canonical(self) -> str:
        """canonical 字符串（``symbol.VENUE``）。"""
        return f"{self.symbol}.{self.venue}"

    def __str__(self) -> str:  # pragma: no cover - 直接委托 canonical
        return self.canonical


def parse_codes(values: str | SecCode | list[str | SecCode]) -> list[SecCode]:
    """批量解析代码，保持输入顺序。"""
    if isinstance(values, (str, SecCode)):
        values = [values]
    return [SecCode.parse(v) for v in values]
