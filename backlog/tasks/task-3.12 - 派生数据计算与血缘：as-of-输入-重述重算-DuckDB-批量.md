---
id: TASK-3.12
title: 派生数据计算与血缘：as-of 输入 / 重述重算 / DuckDB 批量
status: To Do
assignee: []
created_date: '2026-09-13 08:50'
updated_date: '2026-09-13 12:26'
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
平台派生数据管线：从 as-of 正确的输入计算派生指标/复权/面板聚合；记录血缘（输入数据集版本、公式版本、computed_at、knowledge_date）；源数据重述触发重算与版本追加（不回写历史）；DuckDB 批量计算；派生写入走内部写角色（derived schema 最小授权）；提交后刷新读模型与 Redis 代际失效。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 派生任务按 as-of 输入计算，结果带血缘字段（输入版本/公式版本/computed_at/knowledge_date）
- [ ] #2 源数据重述触发重算并追加版本，不回写历史
- [ ] #3 DuckDB 批量计算接入；派生写角色按 schema 最小授权
- [ ] #4 提交后读模型刷新与 Redis 代际失效联动；测试覆盖
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
复权因子推导（事件→累计因子）属派生管线；需与 Tushare adj_factor / Fuyao 预计算复权价对账（doc-2 §6.16）。

算法登记方案（2026-09-13，doc-11 §4）：派生指标代码实现 + @register(id, version)，字典登记 output/algorithm_id/implementation/owner/inputs/description；算法升级=新 algorithm_id（历史永久保留）；派生结果记录 algorithm_id 以审计回溯；CI 校验 id 唯一/实现可导入/docstring 含 Formula+PIT/inputs 存在。
<!-- SECTION:NOTES:END -->
