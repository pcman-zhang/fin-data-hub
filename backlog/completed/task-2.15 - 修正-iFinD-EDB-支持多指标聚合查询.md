---
id: TASK-2.15
title: 修正 iFinD EDB 支持多指标聚合查询
status: Done
assignee: []
created_date: '2026-09-12 13:14'
updated_date: '2026-09-12 13:18'
labels: []
dependencies:
  - TASK-2.8
parent_task_id: TASK-2
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
实测 iFinD get_edb_data 支持一次查询多个指标（此前按“一次一指标”实现并做了接口层限制）。修正：capabilities 取消单指标上限；IfindAdapter.fetch_edb_series 支持多指标单次聚合调用；解析多指标响应为长表；同步测试与文档。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 capabilities (ifind, edb) 不再限制 max_indicators=1；fetch_edb_series 接受多指标且只发一次调用
- [x] #2 解析多指标响应为 indicator/obs_date/value 长表（兼容实测结构）；单指标路径不回归
- [x] #3 README 与 doc-1 同步修正为支持多指标聚合
- [x] #4 更新测试并全绿（含多指标与单指标）
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 实测 get_edb_data 多指标聚合（示例：请查询DR007/R007数据）确认响应结构；2. capabilities 取消 (ifind, edb) 单指标上限；3. fetch_edb_series 支持多指标单次聚合调用 + 多指标解析（兼容实测结构，单指标不回归）；4. 更新测试/README/doc-1；5. pytest/ruff/mypy 验证并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
实测证据：get_edb_data 输入“请查询DR007/R007数据”返回宽表（answer markdown 列：日期|DR007（单位：%）|R007（单位：%）；datas[0].data.columns 同名列，rows 为 [日期, DR007, R007]），一次调用返回多指标。实现：capabilities (ifind,edb).max_indicators=None；fetch_edb_series 支持多指标、join 为一次 query；_edb_frame 宽表/窄表熔炼为 indicator/obs_date/value 长表（指标名去单位），datas 缺失时回退解析 answer markdown。测试更新为多指标聚合 + answer 回退 + 空指标校验；全库 161 passed，ruff/mypy 干净。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
修正 iFinD EDB 多指标聚合：取消单指标限制，一次 query 返回多指标宽表并解析为长表（含 answer markdown 回退）；README/doc-1 同步。验证：全库 161 项单测通过，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
