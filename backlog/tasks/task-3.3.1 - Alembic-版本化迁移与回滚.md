---
id: TASK-3.3.1
title: Alembic 版本化迁移与回滚
status: To Do
assignee: []
created_date: '2026-09-14 06:33'
labels: []
dependencies: []
parent_task_id: TASK-3.3
ordinal: 52000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
为存储层引入 Alembic：迁移脚手架 + 基线迁移（由数据字典生成）+ upgrade/downgrade 幂等可重复执行；集成测试（真实 PG）验证版本升级与回滚。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Alembic 脚手架与基线迁移落地（从字典生成，含 hypertable/压缩语句）
- [ ] #2 upgrade/downgrade 可重复执行（幂等）；真实 PG 集成验证
- [ ] #3 文档同步；全量测试/ruff/mypy 通过
<!-- AC:END -->
