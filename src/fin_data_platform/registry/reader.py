"""实体注册表读取面（SQL）：检索、当前态、历史时间轴、履历/关系/外部标识。

面向 WebUI/REST 的**只读**查询；写路径仍归 ``service.py`` / ``store.py``。
当前态口径与读模型一致：每个实体取「open 区间优先、生效日次之、版本最后」的行。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import Engine, func, or_, select

from fin_data_platform.registry.models import (
    CodeHistoryRecord,
    EntityRecord,
    ExternalIdRecord,
    RelationTypeRecord,
)
from fin_data_platform.registry.schema import (
    entity,
    entity_code_history,
    entity_external_id,
    entity_relation,
    relation_type_dict,
)
from fin_data_platform.registry.store import _to_record


@dataclass(frozen=True, slots=True)
class RelationView:
    """关系视图（含词表反查：``direction`` 为 out/in）。"""

    relation_type: str
    direction: str
    entity_id: int
    related_id: int
    related_code: str | None
    related_name: str | None
    valid_from: date | None = None
    valid_to: date | None = None


def _current_rank():  # type: ignore[no-untyped-def]
    return func.row_number().over(
        partition_by=entity.c.entity_id,
        order_by=[
            (entity.c.valid_to.is_(None)).desc(),
            entity.c.valid_from.desc(),
            entity.c.version.desc(),
        ],
    )


class RegistryReader:
    """实体注册表只读查询（跨方言：SQLite 单测 / PostgreSQL 生产）。"""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    # -------------------------------------------------------------- 检索
    def search_entities(
        self,
        *,
        query: str | None = None,
        entity_type: str | None = None,
        market: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[EntityRecord], int]:
        rank = _current_rank()
        ranked = select(*entity.c, rank.label("_rank"))
        filters = []
        if entity_type:
            filters.append(entity.c.entity_type == entity_type)
        if market:
            filters.append(entity.c.market == market)
        if query:
            pattern = f"%{query.strip()}%"
            filters.append(
                or_(
                    entity.c.code.ilike(pattern),
                    entity.c.name.ilike(pattern),
                )
            )
        if filters:
            ranked = ranked.where(*filters)
        subquery = ranked.subquery()
        current = select(*[subquery.c[column.name] for column in entity.c]).where(
            subquery.c._rank == 1
        )
        statement = current.order_by(
            subquery.c.entity_type, subquery.c.code, subquery.c.entity_id
        )
        with self._engine.connect() as connection:
            total = int(
                connection.execute(
                    select(func.count()).select_from(current.subquery())
                ).scalar_one()
            )
            rows = (
                connection.execute(statement.limit(limit).offset(offset))
                .mappings()
                .all()
            )
        return [_to_record(row) for row in rows], total

    def entity(self, entity_id: int) -> EntityRecord | None:
        """当前态（open 区间优先）。"""
        statement = (
            select(*entity.c)
            .where(entity.c.entity_id == entity_id)
            .order_by(
                (entity.c.valid_to.is_(None)).desc(),
                entity.c.valid_from.desc(),
                entity.c.version.desc(),
            )
            .limit(1)
        )
        with self._engine.connect() as connection:
            row = connection.execute(statement).mappings().first()
        return _to_record(row) if row is not None else None

    def entity_history(self, entity_id: int) -> list[EntityRecord]:
        """属性时间轴（SCD2 全部行，按生效日/版本升序）。"""
        statement = (
            select(*entity.c)
            .where(entity.c.entity_id == entity_id)
            .order_by(entity.c.valid_from, entity.c.version)
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_to_record(row) for row in rows]

    def code_history(self, entity_id: int) -> list[CodeHistoryRecord]:
        statement = (
            select(*entity_code_history.c)
            .where(entity_code_history.c.entity_id == entity_id)
            .order_by(
                entity_code_history.c.valid_from, entity_code_history.c.version
            )
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [
            CodeHistoryRecord(
                entity_id=int(row["entity_id"]),
                code=str(row["code"]),
                valid_from=row["valid_from"],
                valid_to=row["valid_to"],
                knowledge_time=row["knowledge_time"],
                version=int(row["version"]),
            )
            for row in rows
        ]

    def external_ids(self, entity_id: int) -> list[ExternalIdRecord]:
        statement = (
            select(*entity_external_id.c)
            .where(entity_external_id.c.entity_id == entity_id)
            .order_by(entity_external_id.c.id_type, entity_external_id.c.id_value)
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [
            ExternalIdRecord(
                entity_id=int(row["entity_id"]),
                id_type=str(row["id_type"]),
                id_value=str(row["id_value"]),
                valid_from=row["valid_from"],
                valid_to=row["valid_to"],
                knowledge_time=row["knowledge_time"],
                version=int(row["version"]),
            )
            for row in rows
        ]

    def relations(self, entity_id: int) -> list[RelationView]:
        """双向关系视图（出边 + 入边，含词表 inverse 名称与对端代码/名称）。"""
        inverse = {
            str(row["relation_type"]): str(row["inverse_relation"])
            for row in self._relation_types()
        }
        out_rows = self._relation_rows(entity_id, column=entity_relation.c.entity_id)
        in_rows = self._relation_rows(entity_id, column=entity_relation.c.related_id)

        peer_ids = {int(row["entity_id"]) for row in out_rows} | {
            int(row["related_id"]) for row in in_rows
        }
        peers = self._peer_names(peer_ids)

        views: list[RelationView] = []
        for row in out_rows:
            related_id = int(row["related_id"])
            views.append(
                RelationView(
                    relation_type=str(row["relation_type"]),
                    direction="out",
                    entity_id=int(row["entity_id"]),
                    related_id=related_id,
                    related_code=peers.get(related_id, (None, None))[0],
                    related_name=peers.get(related_id, (None, None))[1],
                    valid_from=row["valid_from"],
                    valid_to=row["valid_to"],
                )
            )
        for row in in_rows:
            relation_type = str(row["relation_type"])
            views.append(
                RelationView(
                    relation_type=inverse.get(relation_type, relation_type),
                    direction="in",
                    entity_id=int(row["entity_id"]),
                    related_id=int(row["entity_id"]),
                    related_code=peers.get(int(row["entity_id"]), (None, None))[0],
                    related_name=peers.get(int(row["entity_id"]), (None, None))[1],
                    valid_from=row["valid_from"],
                    valid_to=row["valid_to"],
                )
            )
        return views

    def relation_types(self) -> list[RelationTypeRecord]:
        statement = select(*relation_type_dict.c).order_by(
            relation_type_dict.c.relation_type
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).mappings().all()
        return [
            RelationTypeRecord(
                relation_type=str(row["relation_type"]),
                inverse_relation=str(row["inverse_relation"]),
                description=str(row["description"] or ""),
                valid_from=row["valid_from"],
                valid_to=row["valid_to"],
                knowledge_time=row["knowledge_time"],
                version=int(row["version"]),
            )
            for row in rows
        ]

    # -------------------------------------------------------------- 内部
    def _relation_rows(self, entity_id: int, *, column):  # type: ignore[no-untyped-def]
        statement = (
            select(*entity_relation.c)
            .where(column == entity_id)
            .order_by(entity_relation.c.relation_type, entity_relation.c.version)
        )
        with self._engine.connect() as connection:
            return connection.execute(statement).mappings().all()

    def _relation_types(self):  # type: ignore[no-untyped-def]
        statement = select(*relation_type_dict.c)
        with self._engine.connect() as connection:
            return connection.execute(statement).mappings().all()

    def _peer_names(self, entity_ids: set[int]) -> dict[int, tuple[str | None, str | None]]:
        if not entity_ids:
            return {}
        rank = func.row_number().over(
            partition_by=entity.c.entity_id,
            order_by=[
                (entity.c.valid_to.is_(None)).desc(),
                entity.c.valid_from.desc(),
                entity.c.version.desc(),
            ],
        )
        ranked = (
            select(entity.c.entity_id, entity.c.code, entity.c.name, rank.label("_rank"))
            .where(entity.c.entity_id.in_(entity_ids))
            .subquery()
        )
        statement = select(ranked.c.entity_id, ranked.c.code, ranked.c.name).where(
            ranked.c._rank == 1
        )
        with self._engine.connect() as connection:
            rows = connection.execute(statement).all()
        return {int(row[0]): (row[1], row[2]) for row in rows}
