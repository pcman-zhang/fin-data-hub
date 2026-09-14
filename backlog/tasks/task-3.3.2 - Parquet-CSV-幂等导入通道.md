---
id: TASK-3.3.2
title: Parquet/CSV 幂等导入通道
status: To Do
assignee: []
created_date: '2026-09-14 06:33'
labels: []
dependencies: []
parent_task_id: TASK-3.3
ordinal: 53000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
用户提供历史数据文件（Parquet/CSV）→ staging → 校验（PIT 字段/physical key）→ 幂等合并入库；大文件分块与错误报告。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Parquet/CSV 导入（staging + 幂等合并，重复导入 0 新增）
- [ ] #2 PIT 字段与物理键校验；错误行报告；测试覆盖
- [ ] #3 文档同步；全量测试/ruff/mypy 通过
<!-- AC:END -->
