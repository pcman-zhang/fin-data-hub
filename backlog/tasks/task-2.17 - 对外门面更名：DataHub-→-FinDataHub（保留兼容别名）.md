---
id: TASK-2.17
title: 对外门面更名：DataHub → FinDataHub（保留兼容别名）
status: To Do
assignee: []
created_date: '2026-09-13 08:24'
labels: []
dependencies:
  - TASK-2.4
parent_task_id: TASK-2
ordinal: 31000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
按系统分层定稿（doc-2 §6.10），v0 多源接入平面的对外接口命名为 FinDataHub：将公开类 DataHub 更名为 FinDataHub，保留 DataHub 兼容别名并标注弃用；同步 README、doc-1 与测试；行为不变。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 FinDataHub 为公开类名并从包根导出；DataHub 别名可用且标注弃用
- [ ] #2 README/doc-1 同步命名与分层说明
- [ ] #3 全量测试通过，行为不变
<!-- AC:END -->
