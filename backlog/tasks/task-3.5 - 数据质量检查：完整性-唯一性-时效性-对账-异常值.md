---
id: TASK-3.5
title: 数据质量检查：完整性 / 唯一性 / 时效性 / 对账 / 异常值
status: To Do
assignee: []
created_date: '2026-09-13 06:00'
labels: []
milestone: m-0
dependencies:
  - TASK-3.3
parent_task_id: TASK-3
ordinal: 24000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
质量检查框架：完整性（缺失窗口/断点）、唯一性（重复键）、时效性（更新延迟）、跨源对账（复用 v0 对账框架）、异常值与跳变检测；每日质量报告与阈值告警。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 质量检查覆盖首批数据域并产出每日报告
- [ ] #2 关键指标跨源对账通过率 100%（阈值内）
- [ ] #3 异常检出可追溯到来源与时间窗口
<!-- AC:END -->
