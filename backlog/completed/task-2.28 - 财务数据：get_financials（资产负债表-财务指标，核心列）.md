---
id: TASK-2.28
title: 财务数据：get_financials（资产负债表/财务指标，核心列）
status: Done
assignee: []
created_date: '2026-09-13 11:30'
updated_date: '2026-09-13 11:46'
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
- [x] #1 方法签名与核心列定稿并写入 doc-6；balance_sheet 与 financial_indicator 两 kind 可用
- [x] #2 公共键（ann_date/end_date/report_type）与核心列映射有 spec 与测试；单位/类型正确
- [x] #3 全量测试与 ruff/mypy 通过
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. probe balancesheet/fina_indicator 字段与多代码支持；2. 定义核心 curated 列（~20 列/类）+ 公共 PIT 键 ann_date/end_date/report_type；3. specs/tushare.toml 映射 + Capability.FINANCIALS + schemas 列；4. adapter fetch_financials + facade get_financials；5. 测试 + doc-6/README；6. 全量测试/冒烟/收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
实现与验证（2026-09-13）：
- 核心列：balance_sheet 22 列（资产/负债/权益）+ financial_indicator 21 列（每股/盈利/成长/杠杆）；公共 PIT 键 ann_date/end_date/report_type（indicator 的 report_type 为 optional）。
- start/end 按公告日（ann_date）过滤；balancesheet 不支持逗号多代码 → 逐代码，fina_indicator 批量（实测）。
- 实时冒烟：600519.SH + 000001.SZ（2025 年报期）→ balance_sheet 8 行（4 期×2 标的）、indicator 8 行；数值正确（茅台 2025 总资产 3047 亿、ROE 34.46%）。
- 全量 261 tests passed；ruff/mypy clean；doc-6/README 契约同步。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
新增 get_financials（balance_sheet/financial_indicator 核心 curated 列 + PIT 公共键），处理 balancesheet 单代码限制；测试+实时冒烟通过，261 tests/ruff/mypy 全绿，契约文档同步。
<!-- SECTION:FINAL_SUMMARY:END -->
