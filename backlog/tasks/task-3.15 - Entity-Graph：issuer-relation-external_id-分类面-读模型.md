---
id: TASK-3.15
title: Entity Graph：issuer / relation / external_id / 分类面 / 读模型
status: In Progress
assignee: []
created_date: '2026-09-14 06:33'
updated_date: '2026-09-14 06:35'
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
- [ ] #1 分类面（entity_type/entity_class/market）与 social_status 落地，sec_type 移除；交易状态字段移出注册表
- [ ] #2 entity_relation + relation_type_dict（inverse 双向查询无硬编码）+ entity_external_id 落地（含 CI 校验）
- [ ] #3 issuer 模型与财务改挂 issuer_id（字典/数据集同步）；listing_lifecycle 数据集落地
- [ ] #4 读模型 entity_latest/entity_asof；文档（doc-10 §3.3、doc-17/19）同步；全量测试/ruff/mypy 通过
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 模型/枚举：entity_type/class/market、social_status、EntityRelation/RelationTypeDict/ExternalId；2. 服务：relation 双向查询（inverse 字典驱动）、external id 管理、issuer 关联；移除交易状态（universe 由数据集推导）；3. schema：ref.entity 调整 + relation/external_id/relation_type_dict 表；4. 字典条目：ref.entity 更新、relation/external_id/relation_type_dict、cn_equity.listing_lifecycle；5. 财务数据集改挂 issuer_id；6. 读模型 mart.entity_latest_v1/entity_asof；7. 测试 + doc-17/19 重生成；8. 全量 pytest/ruff/mypy。
<!-- SECTION:PLAN:END -->
