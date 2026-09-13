"""Security Master 仓储协议与内存实现（存储落地由 TASK-3.3 接入）。"""

from __future__ import annotations

from typing import Protocol

from fin_data_platform.security_master.models import (
    AliasRecord,
    AttributeInterval,
    SecurityRecord,
    StatusInterval,
)


class SecurityMasterRepository(Protocol):
    """仓储协议：内存/数据库实现可互换。"""

    def next_security_id(self) -> int: ...

    def add_security(self, record: SecurityRecord) -> None: ...

    def add_alias(self, record: AliasRecord) -> None: ...

    def add_status(self, record: StatusInterval) -> None: ...

    def add_attribute(self, record: AttributeInterval) -> None: ...

    def get_security(self, security_id: int) -> SecurityRecord | None: ...

    def find_by_canonical(self, canonical_code: str) -> SecurityRecord | None: ...

    def all_securities(self) -> list[SecurityRecord]: ...

    def aliases_of(self, security_id: int) -> list[AliasRecord]: ...

    def aliases_by_code(self, source: str, source_code: str) -> list[AliasRecord]: ...

    def count_aliases(self, security_id: int) -> int: ...

    def statuses_of(self, security_id: int) -> list[StatusInterval]: ...

    def attributes_of(
        self, security_id: int, attribute: str | None = None
    ) -> list[AttributeInterval]: ...


class InMemorySecurityMasterRepository:
    """内存实现（测试与本地构建；权威存储见 TASK-3.3）。"""

    def __init__(self, *, id_start: int = 10001) -> None:
        self._next_id = id_start
        self._securities: dict[int, SecurityRecord] = {}
        self._by_canonical: dict[str, int] = {}
        self._aliases: list[AliasRecord] = []
        self._alias_counts: dict[int, int] = {}
        self._statuses: list[StatusInterval] = []
        self._attributes: list[AttributeInterval] = []

    def next_security_id(self) -> int:
        value = self._next_id
        self._next_id += 1
        return value

    def add_security(self, record: SecurityRecord) -> None:
        self._securities[record.security_id] = record
        self._by_canonical[record.canonical_code] = record.security_id

    def add_alias(self, record: AliasRecord) -> None:
        self._aliases.append(record)
        self._alias_counts[record.security_id] = (
            self._alias_counts.get(record.security_id, 0) + 1
        )

    def add_status(self, record: StatusInterval) -> None:
        self._statuses.append(record)

    def add_attribute(self, record: AttributeInterval) -> None:
        self._attributes.append(record)

    def get_security(self, security_id: int) -> SecurityRecord | None:
        return self._securities.get(security_id)

    def find_by_canonical(self, canonical_code: str) -> SecurityRecord | None:
        security_id = self._by_canonical.get(canonical_code)
        return self._securities.get(security_id) if security_id else None

    def all_securities(self) -> list[SecurityRecord]:
        return list(self._securities.values())

    def aliases_of(self, security_id: int) -> list[AliasRecord]:
        return [alias for alias in self._aliases if alias.security_id == security_id]

    def aliases_by_code(self, source: str, source_code: str) -> list[AliasRecord]:
        return [
            alias
            for alias in self._aliases
            if alias.source == source and alias.source_code == source_code
        ]

    def count_aliases(self, security_id: int) -> int:
        return self._alias_counts.get(security_id, 0)

    def statuses_of(self, security_id: int) -> list[StatusInterval]:
        return [item for item in self._statuses if item.security_id == security_id]

    def attributes_of(
        self, security_id: int, attribute: str | None = None
    ) -> list[AttributeInterval]:
        return [
            item
            for item in self._attributes
            if item.security_id == security_id
            and (attribute is None or item.attribute == attribute)
        ]
