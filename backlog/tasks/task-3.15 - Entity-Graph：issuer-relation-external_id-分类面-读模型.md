---
id: TASK-3.15
title: Entity Graph：issuer / relation / external_id / 分类面 / 读模型
status: Done
assignee: []
created_date: '2026-09-14 06:33'
updated_date: '2026-09-14 08:20'
labels: []
dependencies: []
parent_task_id: TASK-3
ordinal: 51000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
按 doc-10 §3.3 冻结稿修订落地：① 分类面收敛（entity_type/entity_class/market，删 sec_type）；② issuer 模型（listing --issued_by--> issuer；财务/股东/公司事件改挂 issuer_id）；③ ref.entity_relation + ref.relation_type_dict（单向存储、inverse 元数据驱动双向查询）；④ ref.entity_external_id（isin/figi/cusip/sedol/lei/uscc，不含 ticker）；⑤ 注册表移除交易状态（status/list/delist），universe 改由交易状态数据集推导；⑥ cn_equity.listing_lifecycle 数据集；⑦ 读模型 mart.entity_latest_v1 + entity_asof；⑧ 字典/文档/测试同步。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 分类面（entity_type/entity_class/market）与 social_status 落地，sec_type 移除；交易状态字段移出注册表
- [x] #2 entity_relation + relation_type_dict（inverse 双向查询无硬编码）+ entity_external_id 落地（含 CI 校验）
- [x] #3 issuer 模型与财务改挂 issuer_id（字典/数据集同步）；listing_lifecycle 数据集落地
- [x] #4 读模型 entity_latest/entity_asof；文档（doc-10 §3.3、doc-17/19）同步；全量测试/ruff/mypy 通过
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
按 doc-10 §3.3 冻结稿分三片实施（每片含字典同步与测试）：
1. 分类面与 issuer：EntityType/EntityClass/Market/SocialStatus 枚举；EntityRecord 重构（去 status/sec_type/list_date/delist_date，加 entity_class/market/social_status）；register/refresh/build_from_hub 改造；universe 迁至由生命周期行推导（registry/universe.py）。
2. relation/external_id：relation_types.yaml 词表（唯一 + inverse 对称校验）；entity_relation/entity_external_id/relation_type_dict schema 与仓储；inverse 字典驱动双向查询（零硬编码）；external id 注册/按值解析；字典条目 ref.entity_relation/ref.entity_external_id/ref.relation_type_dict。
3. 读模型与财务改挂：balance_sheet 键 entity_id→issuer_id；storage/read_models.py 生成 mart.entity_latest_v1 视图 + mart.entity_asof(ts) 函数（PG）+ SDK as-of 查询构造器；cn_equity.listing_lifecycle 字典条目；catalog/report 实体识别含 issuer_id。
4. 文档与收口：doc-10 §3.3 状态更新；重生成 doc-17/doc-19；全量 pytest/ruff/mypy；TASK-3.15 验收收口。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
验证证据：pytest 321 passed（8 deselected 集成）；ruff 全通过；mypy 56 文件无问题。分类面/词表/外部标识/universe 推导见 tests/test_platform_registry.py（22 用例）；读模型语义与 PG DDL 契约见 tests/test_platform_read_models.py；字典 CI（含 relation 词表对称、issuer_id 键）见 test_platform_dictionary.py / test_platform_storage.py。文档：doc-10 §3.3 状态更新，doc-17/19 由 dictionary.catalog_markdown / storage.report.database_markdown 重生成。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Entity Graph 落地：分类面（entity_type/entity_class/market）与 social_status 替代 sec_type；交易状态移出注册表，PIT Universe 改由 cn_equity.listing_lifecycle 数据集推导；issuer 模型（issued_by/issues 词表驱动双向查询，零硬编码）；entity_external_id（不含 ticker）注册与解析；读模型 mart.entity_latest_v1 视图 + mart.entity_asof(ts) 表函数与查询构造器；财务数据集改挂 issuer_id。验证：321 测试 + ruff/mypy 全绿，doc-10/17/19 同步。
<!-- SECTION:FINAL_SUMMARY:END -->
