"""实体注册表仓储协议与内存实现（持久化由 TASK-3.3 接入）。"""

from __future__ import annotations

from typing import Protocol

from fin_data_platform.registry.models import (
    CodeHistoryRecord,
    EntityRecord,
    ExternalIdRecord,
    RelationRecord,
    RelationTypeRecord,
)


class EntityRegistryRepository(Protocol):
    """仓储协议：内存/数据库实现可互换。"""

    # 身份
    def next_entity_id(self) -> int: ...

    def append_entity(self, record: EntityRecord) -> None: ...

    def entity_rows(self, entity_id: int) -> list[EntityRecord]: ...

    def all_rows(self) -> list[EntityRecord]: ...

    # 代码履历
    def append_code(self, record: CodeHistoryRecord) -> None: ...

    def code_history(self, entity_id: int) -> list[CodeHistoryRecord]: ...

    def find_by_code(self, code: str) -> list[CodeHistoryRecord]: ...

    # 关系
    def append_relation(self, record: RelationRecord) -> None: ...

    def relation_rows(self, entity_id: int) -> list[RelationRecord]: ...

    def find_relations_by_related(self, entity_id: int) -> list[RelationRecord]: ...

    def all_relations(self) -> list[RelationRecord]: ...

    def append_relation_type(self, record: RelationTypeRecord) -> None: ...

    def relation_types(self) -> list[RelationTypeRecord]: ...

    # 外部标识
    def append_external_id(self, record: ExternalIdRecord) -> None: ...

    def external_id_rows(self, entity_id: int) -> list[ExternalIdRecord]: ...

    def find_external_ids(self, id_type: str, id_value: str) -> list[ExternalIdRecord]: ...


class InMemoryEntityRegistryRepository:
    """内存实现（测试与本地构建；权威存储见 TASK-3.3）。"""

    def __init__(self, *, id_start: int = 10001) -> None:
        self._next_id = id_start
        self._rows: dict[int, list[EntityRecord]] = {}
        self._codes: list[CodeHistoryRecord] = []
        self._relations: list[RelationRecord] = []
        self._relation_types: dict[str, RelationTypeRecord] = {}
        self._external_ids: list[ExternalIdRecord] = []

    # 身份
    def next_entity_id(self) -> int:
        value = self._next_id
        self._next_id += 1
        return value

    def append_entity(self, record: EntityRecord) -> None:
        self._rows.setdefault(record.entity_id, []).append(record)

    def entity_rows(self, entity_id: int) -> list[EntityRecord]:
        return list(self._rows.get(entity_id, []))

    def all_rows(self) -> list[EntityRecord]:
        return [row for rows in self._rows.values() for row in rows]

    # 代码履历
    def append_code(self, record: CodeHistoryRecord) -> None:
        self._codes.append(record)

    def code_history(self, entity_id: int) -> list[CodeHistoryRecord]:
        return [item for item in self._codes if item.entity_id == entity_id]

    def find_by_code(self, code: str) -> list[CodeHistoryRecord]:
        return [item for item in self._codes if item.code == code]

    # 关系
    def append_relation(self, record: RelationRecord) -> None:
        self._relations.append(record)

    def relation_rows(self, entity_id: int) -> list[RelationRecord]:
        return [item for item in self._relations if item.entity_id == entity_id]

    def find_relations_by_related(self, entity_id: int) -> list[RelationRecord]:
        return [item for item in self._relations if item.related_id == entity_id]

    def all_relations(self) -> list[RelationRecord]:
        return list(self._relations)

    def append_relation_type(self, record: RelationTypeRecord) -> None:
        self._relation_types[record.relation_type] = record

    def relation_types(self) -> list[RelationTypeRecord]:
        return list(self._relation_types.values())

    # 外部标识
    def append_external_id(self, record: ExternalIdRecord) -> None:
        self._external_ids.append(record)

    def external_id_rows(self, entity_id: int) -> list[ExternalIdRecord]:
        return [item for item in self._external_ids if item.entity_id == entity_id]

    def find_external_ids(self, id_type: str, id_value: str) -> list[ExternalIdRecord]:
        return [
            item
            for item in self._external_ids
            if item.id_type == id_type and item.id_value == id_value
        ]
