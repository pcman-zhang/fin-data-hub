"""引用注册表仓储协议与内存实现（持久化由 TASK-3.3 接入）。"""

from __future__ import annotations

from typing import Protocol

from fin_data_platform.registry.models import CodeHistoryRecord, EntityRecord


class EntityRegistryRepository(Protocol):
    """仓储协议：内存/数据库实现可互换。"""

    def next_entity_id(self) -> int: ...

    def append_entity(self, record: EntityRecord) -> None: ...

    def append_code(self, record: CodeHistoryRecord) -> None: ...

    def entity_rows(self, entity_id: int) -> list[EntityRecord]: ...

    def code_history(self, entity_id: int) -> list[CodeHistoryRecord]: ...

    def find_by_code(self, code: str) -> list[CodeHistoryRecord]: ...

    def all_rows(self) -> list[EntityRecord]: ...


class InMemoryEntityRegistryRepository:
    """内存实现（测试与本地构建；权威存储见 TASK-3.3）。"""

    def __init__(self, *, id_start: int = 10001) -> None:
        self._next_id = id_start
        self._rows: dict[int, list[EntityRecord]] = {}
        self._codes: list[CodeHistoryRecord] = []

    def next_entity_id(self) -> int:
        value = self._next_id
        self._next_id += 1
        return value

    def append_entity(self, record: EntityRecord) -> None:
        self._rows.setdefault(record.entity_id, []).append(record)

    def append_code(self, record: CodeHistoryRecord) -> None:
        self._codes.append(record)

    def entity_rows(self, entity_id: int) -> list[EntityRecord]:
        return list(self._rows.get(entity_id, []))

    def code_history(self, entity_id: int) -> list[CodeHistoryRecord]:
        return [item for item in self._codes if item.entity_id == entity_id]

    def find_by_code(self, code: str) -> list[CodeHistoryRecord]:
        return [item for item in self._codes if item.code == code]

    def all_rows(self) -> list[EntityRecord]:
        return [row for rows in self._rows.values() for row in rows]
