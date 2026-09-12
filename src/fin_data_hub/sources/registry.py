"""数据源适配器注册表。"""

from __future__ import annotations

from collections.abc import Iterable

from fin_data_hub.enums import Source
from fin_data_hub.errors import UnsupportedCapability
from fin_data_hub.sources.base import BaseAdapter


class SourceRegistry:
    """``Source`` → adapter 实例的注册表。"""

    def __init__(self, adapters: Iterable[BaseAdapter] = ()) -> None:
        self._adapters: dict[Source, BaseAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: BaseAdapter) -> None:
        self._adapters[adapter.source] = adapter

    def get(self, source: Source | str) -> BaseAdapter:
        resolved = Source(source)
        adapter = self._adapters.get(resolved)
        if adapter is None:
            raise UnsupportedCapability(
                f"未注册数据源 {resolved}；可用 source: {self.available()}"
            )
        return adapter

    def get_for_capability(self, source: Source | str, capability: str) -> BaseAdapter:
        adapter = self.get(source)
        if capability not in adapter.capabilities:
            raise UnsupportedCapability(
                f"{Source(source)} 不支持 {capability}；可用 source: {self.available()}"
            )
        return adapter

    def available(self) -> tuple[str, ...]:
        return tuple(sorted(str(s) for s in self._adapters))
