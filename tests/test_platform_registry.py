"""实体注册表（doc-10 §3.3）测试：分类面/issuer、代码履历、关系/外部标识、PIT Universe。"""

from __future__ import annotations

import pandas as pd
import pytest

from fin_data_platform.registry import (
    EntityRegistry,
    LifecycleRecord,
    load_relation_types,
    universe,
    validate_relation_types,
)
from fin_data_platform.registry.schema import TABLES


def _registry() -> EntityRegistry:
    registry = EntityRegistry()
    registry.register(
        code="600519.SH", entity_type="equity", name="贵州茅台", market="cn"
    )
    registry.register(code="510300.SH", entity_type="etf", name="300ETF", market="cn")
    registry.register(
        code="000300.SH", entity_type="index", name="沪深300", market="cn"
    )
    return registry


def test_register_and_resolve() -> None:
    registry = _registry()
    entity_id = registry.resolve("600519.SH")
    assert entity_id is not None
    assert registry.resolve("000300.SH") is not None
    assert registry.resolve("600000.SH") is None


def test_classification_face_persisted() -> None:
    registry = EntityRegistry()
    etf = registry.register(
        code="511010.SH",
        entity_type="etf",
        entity_class="bond_etf",
        market="cn",
        name="国债ETF",
    )
    current = registry.entity(etf.entity_id)
    assert current is not None
    assert current.entity_type == "etf"
    assert current.entity_class == "bond_etf"
    assert current.market == "cn"


def test_issuer_social_status() -> None:
    registry = EntityRegistry()
    issuer = registry.register_issuer(code="91520000714308124W", name="茅台股份")
    assert issuer.entity_type == "issuer"
    assert issuer.social_status == "operating"
    # 非 issuer 不得携带 social_status
    with pytest.raises(ValueError, match="social_status"):
        registry.register(code="600519.SH", entity_type="equity", social_status="defunct")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("entity_type", "stock"),
        ("entity_class", "stock"),
        ("market", "sh"),
        ("social_status", "alive"),
    ],
)
def test_facet_validation(field: str, value: str) -> None:
    registry = EntityRegistry()
    kwargs = {"code": "600519.SH", "entity_type": "equity", field: value}
    if field == "social_status":
        kwargs["entity_type"] = "issuer"
    with pytest.raises(ValueError, match=field):
        registry.register(**kwargs)


def test_code_history_resolution() -> None:
    registry = _registry()
    entity_id = registry.resolve("600519.SH")
    assert entity_id is not None
    registry.add_code_change(entity_id, new_code="920519.BJ", start_date="2026-01-01")
    # 新代码可解析
    assert registry.resolve("920519.BJ") == entity_id
    # 旧代码在变更前有效、变更后失效
    assert registry.resolve("600519.SH", as_of="2025-12-31") == entity_id
    assert registry.resolve("600519.SH", as_of="2026-06-01") is None
    # 当前属性行代码已更新
    current = registry.entity(entity_id)
    assert current is not None and current.code == "920519.BJ"


def test_register_name_refresh_applies() -> None:
    registry = EntityRegistry()
    registry.register(code="600519.SH", entity_type="equity", name="贵州茅台")
    registry.register(code="600519.SH", entity_type="equity", name="茅台股份")
    entity_id = registry.resolve("600519.SH")
    assert entity_id is not None
    current = registry.entity(entity_id)
    assert current is not None and current.name == "茅台股份"
    assert registry.name_as_of(entity_id, "2025-01-01") == "茅台股份"


def test_entity_type_first_seen_wins_on_refresh() -> None:
    registry = EntityRegistry()
    registry.register(code="510300.SH", entity_type="etf", name="300ETF")
    registry.register(code="510300.SH", entity_type="fund", name="300ETF")
    entity_id = registry.resolve("510300.SH")
    assert entity_id is not None
    current = registry.entity(entity_id)
    assert current is not None and current.entity_type == "etf"


def test_entity_current_excludes_expired_temporary_name() -> None:
    registry = _registry()
    entity_id = registry.resolve("600519.SH")
    assert entity_id is not None
    registry.add_name_change(
        entity_id, name="ST茅台", start_date="2010-01-01", end_date="2011-12-31"
    )
    current = registry.entity(entity_id)
    assert current is not None and current.name == "贵州茅台"  # 当前行非临时行
    assert registry.name_as_of(entity_id, "2010-06-01") == "ST茅台"
    assert registry.name_as_of(entity_id, "2013-06-01") == "贵州茅台"  # 恢复行


def test_name_as_of_scd2() -> None:
    registry = _registry()
    entity_id = registry.resolve("600519.SH")
    assert entity_id is not None
    registry.add_name_change(
        entity_id, name="G茅台", start_date="2006-05-25", end_date="2006-10-08"
    )
    assert registry.name_as_of(entity_id, "2006-06-01") == "G茅台"
    # 名称区间结束后回到后续行名称
    assert registry.name_as_of(entity_id, "2007-01-01") == "贵州茅台"
    # 早于实体行生效起点 → None（防前视）
    assert registry.name_as_of(entity_id, "1989-01-01") is None


def test_relation_type_vocabulary_symmetric() -> None:
    records = load_relation_types()
    assert validate_relation_types(records) == []
    assert records["issued_by"].inverse_relation == "issues"
    assert records["tracks"].inverse_relation == "tracked_by"


def test_relation_bidirectional_via_inverse() -> None:
    registry = _registry()
    listing = registry.resolve("600519.SH")
    issuer = registry.register_issuer(code="91520000714308124W", name="茅台股份")
    assert listing is not None
    registry.link_issuer(listing, issuer.entity_id)
    # 正向查询：listing → issuer
    assert registry.issuer_of(listing) == issuer.entity_id
    # 反向查询：issuer → listings（经由 inverse 词表，无硬编码）
    assert registry.listings_of(issuer.entity_id) == [listing]
    assert registry.related_ids(issuer.entity_id, "issues") == [listing]
    # 幂等登记
    again = registry.link_issuer(listing, issuer.entity_id)
    assert again.entity_id == listing
    assert len(registry.relations_of(issuer.entity_id)) == 1


def test_relation_requires_registered_word_and_entities() -> None:
    registry = _registry()
    listing = registry.resolve("600519.SH")
    assert listing is not None
    with pytest.raises(ValueError, match="关系词未登记"):
        registry.add_relation(listing, listing, "unknown_rel")
    with pytest.raises(KeyError):
        registry.add_relation(99999, listing, "tracks")


def test_link_issuer_rejects_non_issuer() -> None:
    registry = _registry()
    listing = registry.resolve("600519.SH")
    other = registry.resolve("510300.SH")
    assert listing is not None and other is not None
    with pytest.raises(ValueError, match="不是 issuer"):
        registry.link_issuer(listing, other)


def test_external_id_registration_and_lookup() -> None:
    registry = _registry()
    listing = registry.resolve("600519.SH")
    assert listing is not None
    registry.add_external_id(listing, "isin", "CNE0000018R8")
    assert registry.find_by_external_id("isin", "CNE0000018R8") == listing
    assert registry.find_by_external_id("figi", "BBG000BLNQ16") is None
    assert [row.id_type for row in registry.external_ids(listing)] == ["isin"]
    # as-of：早于标识生效期不可解析
    assert registry.find_by_external_id("isin", "CNE0000018R8", as_of="1989-01-01") is None


def test_external_id_type_validation() -> None:
    registry = _registry()
    listing = registry.resolve("600519.SH")
    assert listing is not None
    with pytest.raises(ValueError, match="id_type"):
        registry.add_external_id(listing, "ticker", "600519")


def test_universe_from_lifecycle() -> None:
    registry = _registry()
    maotai = registry.resolve("600519.SH")
    etf = registry.resolve("510300.SH")
    index = registry.resolve("000300.SH")
    assert maotai is not None and etf is not None and index is not None
    lifecycle = [
        LifecycleRecord(entity_id=maotai, status="listed", start_date="2001-08-27"),
        LifecycleRecord(entity_id=etf, status="listed", start_date="2012-05-28"),
        LifecycleRecord(entity_id=index, status="listed", start_date="2005-04-08"),
    ]
    assert {item.code for item in universe(registry, lifecycle, "2020-01-01")} == {
        "600519.SH",
        "510300.SH",
        "000300.SH",
    }
    # 上市前不在 universe（防前视）
    assert {item.code for item in universe(registry, lifecycle, "2004-01-01")} == {
        "600519.SH"
    }
    # 暂停上市仍在 universe；退市不在
    lifecycle.append(
        LifecycleRecord(
            entity_id=maotai, status="delisted", start_date="2026-07-14", version=2
        )
    )
    assert {item.code for item in universe(registry, lifecycle, "2026-07-14")} == {
        "510300.SH",
        "000300.SH",
    }
    # 无生命周期记录的实体不进入 universe
    registry.register(code="000001.SZ", entity_type="equity", name="平安银行")
    assert "000001.SZ" not in {
        item.code for item in universe(registry, lifecycle, "2020-01-01")
    }


def test_universe_filters() -> None:
    registry = _registry()
    maotai = registry.resolve("600519.SH")
    assert maotai is not None
    lifecycle = [LifecycleRecord(entity_id=maotai, status="listed", start_date="2001-08-27")]
    only_index = universe(registry, lifecycle, "2020-01-01", entity_type="index")
    assert only_index == []
    assert universe(registry, lifecycle, "2020-01-01", market="hk") == []
    with pytest.raises(ValueError, match="as_of"):
        universe(registry, lifecycle, None)


def test_universe_respects_knowledge_time() -> None:
    registry = _registry()
    maotai = registry.resolve("600519.SH")
    assert maotai is not None
    # 2026 年才录入的退市更正（knowledge=2026）不得影响 2020 年的 as-of
    lifecycle = [
        LifecycleRecord(entity_id=maotai, status="listed", start_date="2001-08-27"),
        LifecycleRecord(
            entity_id=maotai,
            status="delisted",
            start_date="2010-01-01",
            knowledge_time="2026-01-01",
            version=2,
        ),
    ]
    # 2026 年才录入的退市更正（knowledge=2026）不得影响更正前的 as-of
    assert [
        item.code
        for item in universe(registry, lifecycle, "2020-01-01", knowledge_as_of="2025-12-31")
    ] == ["600519.SH"]
    # 更正已知晓后，2020 年按更正后的状态判定（退市）
    assert universe(registry, lifecycle, "2020-01-01", knowledge_as_of="2026-01-02") == []
    # 未提供 knowledge_as_of 时假定调用方已预过滤：行直接参与判定
    assert universe(registry, lifecycle, "2020-01-01") == []


class FakeHub:
    def __init__(self) -> None:
        self._frames = {
            "stock_list": pd.DataFrame(
                [
                    {
                        "code": "600519.SH",
                        "name": "贵州茅台",
                        "list_date": "2001-08-27",
                        "list_status": "L",
                    },
                    {
                        "code": "000001.SZ",
                        "name": "平安银行",
                        "list_date": "1991-04-03",
                        "list_status": "L",
                    },
                ]
            ),
            "etf_list": pd.DataFrame(
                [{"code": "510300.SH", "name": "300ETF", "list_date": "2012-05-28"}]
            ),
            "fund_list": pd.DataFrame(
                [
                    {"code": "510300.SH", "name": "300ETF", "list_date": "2012-05-28"},
                    {"code": "000001.OF", "name": "华夏成长", "list_date": pd.NaT},
                    {"code": "161725.SZ", "name": "白酒LOF", "list_date": "2015-05-06"},
                ]
            ),
            "index_list": pd.DataFrame(
                [{"code": "000300.SH", "name": "沪深300", "list_date": "2005-04-08"}]
            ),
            "delist_list": pd.DataFrame(
                [
                    {
                        "code": "000004.SZ",
                        "name": "国华退",
                        "list_date": "1991-01-14",
                        "delist_date": "2026-07-14",
                    }
                ]
            ),
        }
        self._events = {
            "namechange": pd.DataFrame(
                [
                    {
                        "code": "600519.SH",
                        "name": "G茅台",
                        "start_date": "2006-05-25",
                        "end_date": "2006-10-08",
                        "ann_date": "2006-05-22",
                    }
                ]
            )
        }

    def get_reference(self, kind: str) -> pd.DataFrame:
        if kind not in self._frames:
            raise ValueError(kind)
        return self._frames[kind]

    def get_market_events(self, *, kind: str, start: str, end: str) -> pd.DataFrame:
        if kind not in self._events:
            raise ValueError(kind)
        return self._events[kind]


def test_build_from_hub_classification() -> None:
    registry = EntityRegistry()
    stats = registry.build_from_hub(
        FakeHub(), namechange_start="2000-01-01", namechange_end="2026-12-31"
    )
    # 2 股票 + 1 ETF + 1 场外基金 + 1 LOF + 1 指数 + 1 退市身份（delist_list）
    assert stats.registered == 7
    assert stats.attributes == 1

    expected = {
        "600519.SH": ("equity", "cn"),
        "000001.SZ": ("equity", "cn"),
        "510300.SH": ("etf", "cn"),  # 先见优先：ETF 列表命中
        "000001.OF": ("fund", "cn"),
        "161725.SZ": ("lof", "cn"),
        "000300.SH": ("index", "cn"),
        # 退市标的保留实体身份（stock_basic 默认只返上市；身份供 listing_lifecycle 挂接）
        "000004.SZ": ("equity", "cn"),
    }
    for code, (entity_type, market) in expected.items():
        entity_id = registry.resolve(code)
        assert entity_id is not None, code
        row = registry.entity(entity_id)
        assert row is not None
        assert (row.entity_type, row.market) == (entity_type, market)

    entity_id = registry.resolve("600519.SH")
    assert entity_id is not None
    assert registry.name_as_of(entity_id, "2006-06-01") == "G茅台"


def test_schema_tables_defined() -> None:
    names = {table.key for table in TABLES}
    assert names == {
        "ref.entity",
        "ref.entity_code_history",
        "ref.entity_relation",
        "ref.entity_external_id",
        "ref.relation_type_dict",
    }
    pk = {column.name for column in TABLES[0].primary_key}
    assert pk == {"entity_id", "valid_from", "knowledge_time", "version"}
    relation_pk = {column.name for column in TABLES[2].primary_key}
    assert relation_pk == {
        "entity_id",
        "related_id",
        "relation_type",
        "valid_from",
        "knowledge_time",
        "version",
    }
    external_pk = {column.name for column in TABLES[3].primary_key}
    assert external_pk == {
        "entity_id",
        "id_type",
        "id_value",
        "valid_from",
        "knowledge_time",
        "version",
    }
    type_pk = {column.name for column in TABLES[4].primary_key}
    assert type_pk == {"relation_type", "valid_from", "knowledge_time", "version"}
