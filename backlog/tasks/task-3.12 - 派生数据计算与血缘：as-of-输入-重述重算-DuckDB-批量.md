---
id: TASK-3.12
title: 派生数据计算与血缘：as-of 输入 / 重述重算 / DuckDB 批量
status: To Do
assignee: []
created_date: '2026-09-13 08:50'
updated_date: '2026-09-14 04:40'
labels: []
milestone: m-0
dependencies:
  - TASK-3.2
  - TASK-3.3
parent_task_id: TASK-3
ordinal: 33000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
按 doc-10 §3.5 / doc-11 §4 落地 DerivedEngine：算法注册（@register + meta.algorithm_registry 生成，CI 与字典一致）+ 定义解析（字典 derived，含 materialize/refresh）+ 计划器/执行器（读模型内联字段级 / DuckDB 批量 / 按需计算）；as_of 输入 + algorithm_id（默认 active，可 pin 复现）；物化策略 none|latest（latest 单份投影、可重建、升级全量重算+代次切换）；升级事件（effective_from/reason）；不落多版本派生数据。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 DerivedEngine 骨架：@register 注册表 + meta.algorithm_registry 生成 + 字典 derived（materialize/refresh）解析与 CI 一致
- [ ] #2 as_of 输入 + algorithm_id（默认 active / 可 pin）执行；响应元数据（algorithm_id / inputs as_of / data_generation）
- [ ] #3 物化策略 none|latest：latest 投影单份可重建、升级重算+代次切换；不落多版本派生数据；测试覆盖
- [ ] #4 升级事件记录与查询；文档同步（doc-10/11/13）；全量测试/ruff/mypy 通过
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
复权因子推导（事件→累计因子）属派生管线；需与 Tushare adj_factor / Fuyao 预计算复权价对账（doc-2 §6.16）。

算法登记方案（2026-09-13，doc-11 §4）：派生指标代码实现 + @register(id, version)，字典登记 output/algorithm_id/implementation/owner/inputs/description；算法升级=新 algorithm_id（历史永久保留）；派生结果记录 algorithm_id 以审计回溯；CI 校验 id 唯一/实现可导入/docstring 含 Formula+PIT/inputs 存在。

设计定稿（2026-09-13）：存输入与算法，不存多版本派生结果；algorithm_id 升级=新 id、旧实现永久保留（复现靠 pin+重算）；三种服务形态（读模型内联/按需计算/最新投影）；物化=可重建缓存（Cache Never Owns Data 延伸）；meta.algorithm_registry + algorithm_events。
<!-- SECTION:NOTES:END -->
