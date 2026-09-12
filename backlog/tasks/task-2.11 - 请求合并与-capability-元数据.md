---
id: TASK-2.11
title: 请求合并与 capability 元数据
status: To Do
assignee: []
created_date: '2026-09-12 12:02'
labels: []
dependencies:
  - TASK-2.4
parent_task_id: TASK-2
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
capability 元数据（每源/端点：最大代码数、多指标支持、历史支持、成本提示）；facade 批量分块与合并；结果去重排序。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 capability 表驱动；超限自动分块并合并
- [ ] #2 iFinD EDB 一指标一次、Wind 单次代码数上限有单测
- [ ] #3 合并结果无重复、顺序稳定
<!-- AC:END -->
