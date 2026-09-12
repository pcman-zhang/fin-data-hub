---
id: TASK-2.12
title: 集成测试与使用文档
status: To Do
assignee: []
created_date: '2026-09-12 12:02'
labels: []
dependencies:
  - TASK-2.6
  - TASK-2.7
  - TASK-2.8
  - TASK-2.9
parent_task_id: TASK-2
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
标记 integration 的端到端测试（凭证可用时运行）；使用文档与 README 更新为可用状态；各源支持范围与限制说明。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 pytest -m "not integration" 离线全绿；integration 默认跳过
- [ ] #2 文档示例与实际 API 一致，标注各源支持范围与限制
- [ ] #3 测试断言无持久化写盘
<!-- AC:END -->
