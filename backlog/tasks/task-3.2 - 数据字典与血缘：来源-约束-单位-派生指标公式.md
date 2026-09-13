---
id: TASK-3.2
title: 数据字典与血缘：来源 / 约束 / 单位 / 派生指标公式
status: To Do
assignee: []
created_date: '2026-09-13 05:59'
updated_date: '2026-09-13 08:41'
labels: []
milestone: m-0
dependencies:
  - TASK-3.1
parent_task_id: TASK-3
ordinal: 21000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
按设计规范落地可执行数据字典：每个数据项记录来源、更新频率、覆盖范围、约束与注意事项、单位、时区；派生指标记录公式与依赖；提供字典校验与查询接口。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 首批数据域字典条目完整，字段可机读校验
- [ ] #2 派生指标公式可追溯依赖数据项
- [ ] #3 字典与代码/表结构一致性检查通过
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
数据字典需登记每项的 PIT 类别与时间字段（event_date/knowledge_date/ingest_ts/version/is_latest）及复权/重述口径（doc-2 §6.9）。

数据字典需与 hub 归一化层映射 spec 校验一致（source × endpoint 覆盖度），并登记指数子平面与 Wind 标准 venue（doc-2 §6.12）。
<!-- SECTION:NOTES:END -->
