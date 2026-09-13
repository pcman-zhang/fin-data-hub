---
id: TASK-2.28
title: 财务数据：get_financials（资产负债表/财务指标，核心列）
status: To Do
assignee: []
created_date: '2026-09-13 11:30'
labels: []
dependencies:
  - TASK-2.18
parent_task_id: TASK-2
ordinal: 44000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
新增 get_financials(codes, *, kind="balance_sheet"|"financial_indicator", start, end)：Tushare balancesheet/fina_indicator。公共 PIT 键 ann_date/end_date/report_type；canonical 采用核心 curated 列（资产负债/权益/营运/盈利能力/成长/杠杆，约 20~30 列），跨源可对齐。spec + 测试 + doc-6 增补。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 方法签名与核心列定稿并写入 doc-6；balance_sheet 与 financial_indicator 两 kind 可用
- [ ] #2 公共键（ann_date/end_date/report_type）与核心列映射有 spec 与测试；单位/类型正确
- [ ] #3 全量测试与 ruff/mypy 通过
<!-- AC:END -->
