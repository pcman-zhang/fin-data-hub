---
id: TASK-3.3.3
title: 只读角色与按域授权
status: To Do
assignee: []
created_date: '2026-09-14 06:33'
labels: []
dependencies: []
parent_task_id: TASK-3.3
ordinal: 54000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
创建只读角色（读模型/域 schema SELECT），读写 DSN 分离验证；mart 只读、canonical 按域授权；文档记录授权矩阵。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 只读角色与授权脚本（mart/域 SELECT；禁内部原始表）
- [ ] #2 读写 DSN 分离验证（reader 无法写入）；集成测试
- [ ] #3 文档同步；全量测试/ruff/mypy 通过
<!-- AC:END -->
