"""实体注册表读取面（RegistryReader）真查询测试：SQLite（ATTACH 模拟 schema）。

覆盖：当前态 SCD2 选择、检索过滤、双向关系对端解析、关系/词表当前态过滤。
"""

from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, insert, text
from sqlalchemy.pool import StaticPool

from fin_data_platform.registry.reader import RegistryReader
from fin_data_platform.registry.schema import (
    entity,
    entity_code_history,
    entity_external_id,
    entity_relation,
    relation_type_dict,
)
from fin_data_platform.storage.schema import build_metadata


@pytest.fixture()
def reader() -> RegistryReader:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    with engine.begin() as connection:
        for schema in ("cn_equity", "cn_fund", "ref", "meta"):
            connection.execute(text(f"ATTACH DATABASE ':memory:' AS {schema}"))
        metadata, _ = build_metadata(include_runtime=False)
        metadata.create_all(engine)

        # 实体：10001 股票（旧行闭合 + 当前行）；10002 发行主体（当前行）
        for row in [
                {
                    "entity_id": 10001,
                    "entity_type": "equity",
                    "entity_class": "stock",
                    "market": "cn",
                    "code": "600519.SH",
                    "name": "贵州茅台（旧名）",
                    "valid_from": date(2001, 8, 27),
                    "valid_to": date(2010, 1, 1),
                    "knowledge_time": datetime(2008, 1, 1),
                    "version": 1,
                },
                {
                    "entity_id": 10001,
                    "entity_type": "equity",
                    "entity_class": "stock",
                    "market": "cn",
                    "code": "600519.SH",
                    "name": "贵州茅台",
                    "valid_from": date(2010, 1, 1),
                    "valid_to": None,
                    "knowledge_time": datetime(2026, 9, 1),
                    "version": 2,
                },
                {
                    "entity_id": 10002,
                    "entity_type": "issuer",
                    "market": "cn",
                    "code": "91520000714308124W",
                    "name": "贵州茅台酒股份有限公司",
                    "social_status": "active",
                    "valid_from": date(2001, 1, 1),
                    "valid_to": None,
                    "knowledge_time": datetime(2026, 9, 1),
                    "version": 1,
                },
        ]:
            connection.execute(insert(entity), row)
        connection.execute(
            insert(entity_code_history),
            [
                {
                    "entity_id": 10001,
                    "code": "600519.SH",
                    "valid_from": date(2001, 8, 27),
                    "valid_to": None,
                    "knowledge_time": datetime(2026, 9, 1),
                    "version": 1,
                }
            ],
        )
        connection.execute(
            insert(entity_relation),
            [
                # 历史（已闭合）与当前（open）各一条：读取面只应返回 open
                {
                    "entity_id": 10001,
                    "related_id": 10002,
                    "relation_type": "issued_by",
                    "valid_from": date(2001, 1, 1),
                    "valid_to": date(2002, 1, 1),
                    "knowledge_time": datetime(2002, 1, 1),
                    "version": 1,
                },
                {
                    "entity_id": 10001,
                    "related_id": 10002,
                    "relation_type": "issued_by",
                    "valid_from": date(2002, 1, 2),
                    "valid_to": None,
                    "knowledge_time": datetime(2026, 9, 1),
                    "version": 2,
                },
            ],
        )
        connection.execute(
            insert(entity_external_id),
            [
                {
                    "entity_id": 10001,
                    "id_type": "isin",
                    "id_value": "CNE0000018R8",
                    "valid_from": date(2001, 8, 27),
                    "valid_to": None,
                    "knowledge_time": datetime(2026, 9, 1),
                    "version": 1,
                }
            ],
        )
        connection.execute(
            insert(relation_type_dict),
            [
                {
                    "relation_type": "issued_by",
                    "inverse_relation": "issues",
                    "description": "旧版",
                    "valid_from": date(2001, 1, 1),
                    "valid_to": date(2002, 1, 1),
                    "knowledge_time": datetime(2002, 1, 1),
                    "version": 1,
                },
                {
                    "relation_type": "issued_by",
                    "inverse_relation": "issues",
                    "description": "发行关系",
                    "valid_from": date(2002, 1, 2),
                    "valid_to": None,
                    "knowledge_time": datetime(2026, 9, 1),
                    "version": 2,
                },
            ],
        )
    return RegistryReader(engine)


def test_search_entities_filters_and_current_row(reader: RegistryReader) -> None:
    records, total = reader.search_entities(query="茅台")
    assert total == 2
    equity = next(item for item in records if item.entity_id == 10001)
    assert equity.name == "贵州茅台"  # 当前行，而非历史名

    records, total = reader.search_entities(entity_type="issuer")
    assert total == 1 and records[0].entity_id == 10002

    records, total = reader.search_entities(market="cn", limit=1, offset=1)
    assert total == 2 and len(records) == 1


def test_entity_and_history(reader: RegistryReader) -> None:
    current = reader.entity(10001)
    assert current is not None and current.version == 2 and current.valid_to is None
    history = reader.entity_history(10001)
    assert [row.version for row in history] == [1, 2]
    assert reader.entity(99999) is None


def test_relations_resolve_peer_and_current_state(reader: RegistryReader) -> None:
    relations = reader.relations(10001)
    assert len(relations) == 1  # 已闭合的历史关系被过滤
    out = relations[0]
    assert out.direction == "out" and out.relation_type == "issued_by"
    assert out.related_id == 10002
    assert out.related_code == "91520000714308124W"  # 对端解析（回归：曾取错列）
    assert out.related_name == "贵州茅台酒股份有限公司"

    inverse = reader.relations(10002)
    assert len(inverse) == 1
    assert inverse[0].direction == "in"
    assert inverse[0].relation_type == "issues"  # 词表 inverse
    assert inverse[0].related_id == 10001
    assert inverse[0].related_code == "600519.SH"


def test_relation_types_current_only(reader: RegistryReader) -> None:
    types = reader.relation_types()
    assert len(types) == 1
    assert types[0].description == "发行关系"  # 当前版而非旧版
