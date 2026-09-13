"""各数据源代码映射（canonical = :class:`SecCode`）。

- Tushare / Wind / iFinD：直接使用 canonical（``symbol.VENUE``）；
- AkShare：多数接口只接受 6 位裸代码，指数接口还分“6 位”与“市场前缀”两种形式，
  由 :class:`AkShareMapper` 按 ``endpoint`` 处理。
"""

from __future__ import annotations

from typing import Protocol

from fin_data_hub.codes import SecCode, SecType
from fin_data_hub.enums import Source
from fin_data_hub.errors import UnknownSecurityError, UnsupportedCapability


class CodeMapper(Protocol):
    """源代码映射协议。"""

    def to_source(self, code: SecCode, endpoint: str | None = None) -> str:
        """canonical → 源端代码。"""
        ...

    def from_source(
        self,
        raw: str,
        *,
        venue: str | None = None,
        endpoint: str | None = None,
    ) -> SecCode:
        """源端代码 → canonical（``venue`` 可选，用于无后缀的裸代码）。"""
        ...


class PassthroughMapper:
    """Tushare / Wind / iFinD：canonical 即源端代码。"""

    def to_source(self, code: SecCode, endpoint: str | None = None) -> str:
        return code.canonical

    def from_source(
        self,
        raw: str,
        *,
        venue: str | None = None,
        endpoint: str | None = None,
    ) -> SecCode:
        if venue and "." not in raw:
            return SecCode.parse(f"{raw}.{venue}")
        return SecCode.parse(raw)


#: AkShare 指数接口中使用市场前缀（sh/sz/csi）的 endpoint。
AKSHARE_INDEX_PREFIXED_ENDPOINTS = frozenset(
    {
        "stock_zh_index_daily_em",
        "stock_zh_index_daily",
    }
)

_PREFIX_BY_VENUE = {"SH": "sh", "SZ": "sz", "CSI": "csi"}
_VENUE_BY_PREFIX = {"sh": "SH", "sz": "SZ", "csi": "CSI"}


class AkShareMapper:
    """AkShare：按 endpoint 转为 6 位裸代码或带市场前缀的指数代码。"""

    def to_source(self, code: SecCode, endpoint: str | None = None) -> str:
        if code.venue not in {"SH", "SZ", "BJ", "OF"}:
            raise UnsupportedCapability(
                f"AkShare 不支持 venue {code.venue}（仅 CN 市场）；{code.canonical}"
            )
        if code.sec_type is SecType.INDEX and endpoint in AKSHARE_INDEX_PREFIXED_ENDPOINTS:
            prefix = _PREFIX_BY_VENUE.get(code.venue)
            if prefix is None:
                raise UnknownSecurityError(
                    f"AkShare 指数接口 {endpoint!r} 不支持 venue {code.venue}"
                )
            return f"{prefix}{code.symbol}"
        return code.symbol

    def from_source(
        self,
        raw: str,
        *,
        venue: str | None = None,
        endpoint: str | None = None,
    ) -> SecCode:
        text = raw.strip().lower()
        for prefix, resolved_venue in _VENUE_BY_PREFIX.items():
            body = text[len(prefix) :]
            if text.startswith(prefix) and body.isdigit():
                return SecCode.parse(
                    f"{body}.{resolved_venue}", sec_type=SecType.INDEX
                )
        if venue:
            return SecCode.parse(f"{text}.{venue.upper()}")
        raise UnknownSecurityError(f"AkShare 代码缺少 venue，无法还原 canonical: {raw!r}")


class BaoStockMapper:
    """BaoStock：canonical ↔ ``sh.600000`` 形式（仅 SH/SZ，含指数）。"""

    _PREFIX_BY_VENUE = {"SH": "sh", "SZ": "sz"}
    _VENUE_BY_PREFIX = {"sh": "SH", "sz": "SZ"}

    def to_source(self, code: SecCode, endpoint: str | None = None) -> str:
        prefix = self._PREFIX_BY_VENUE.get(str(code.venue))
        if prefix is None:
            raise UnsupportedCapability(
                f"BaoStock 仅支持 SH/SZ（含指数），不支持 {code.canonical}"
            )
        return f"{prefix}.{code.symbol}"

    def from_source(
        self,
        raw: str,
        *,
        venue: str | None = None,
        endpoint: str | None = None,
    ) -> SecCode:
        text = raw.strip().lower()
        if "." not in text:
            if venue:
                return SecCode.parse(f"{text}.{venue.upper()}")
            raise UnknownSecurityError(f"BaoStock 代码缺少前缀: {raw!r}")
        prefix, _, symbol = text.partition(".")
        resolved = self._VENUE_BY_PREFIX.get(prefix)
        if resolved is None:
            raise UnknownSecurityError(f"未知 BaoStock 前缀: {raw!r}")
        return SecCode.parse(f"{symbol}.{resolved}")


_MAPPERS: dict[Source, CodeMapper] = {
    Source.TUSHARE: PassthroughMapper(),
    Source.WIND: PassthroughMapper(),
    Source.IFIND: PassthroughMapper(),
    Source.AKSHARE: AkShareMapper(),
    Source.BAOSTOCK: BaoStockMapper(),
}


def get_mapper(source: Source | str) -> CodeMapper:
    """获取指定数据源的代码映射器。"""
    resolved = Source(source)
    return _MAPPERS[resolved]
