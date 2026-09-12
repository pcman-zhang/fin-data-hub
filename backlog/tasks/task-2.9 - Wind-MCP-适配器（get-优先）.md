---
id: TASK-2.9
title: Wind MCP 适配器（get 优先）
status: To Do
assignee: []
created_date: '2026-09-12 12:01'
labels: []
dependencies:
  - TASK-2.4
  - TASK-2.5
parent_task_id: TASK-2
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Wind 7 服务适配高频端点；get 类工具优先，精确代码批量；EDB get_economic_data 批量；债券长区间分块；解析 {date, indicatorInfo} 结构。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 fixture 测试覆盖 K线/快照/EDB/债券
- [ ] #2 批量分块逻辑有单测（超过 50 代码、超过 90 天区间自动分批）
- [ ] #3 不调用 query 类工具
<!-- AC:END -->
