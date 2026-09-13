---
id: TASK-2.27
title: 申万行业分类：三级树 + 成分（industry_classify/industry_member）
status: Done
assignee: []
created_date: '2026-09-13 11:30'
updated_date: '2026-09-13 11:38'
labels: []
dependencies:
  - TASK-2.18
parent_task_id: TASK-2
ordinal: 43000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Tushare index_classify(src=SW2021, L1/L2/L3) + index_member_all。① get_reference(kind="industry_classify")：行业树全量（index_code/industry_name/level/parent_code/industry_code/src）；② kind="industry_member"：股票→L1/L2/L3 成分（含 in_date/out_date/is_new），支持组成完整申万三级数据。spec + 测试 + doc-6 增补。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 industry_classify 返回 L1/L2/L3 全量且 parent 关系可组装成树；测试校验
- [x] #2 industry_member 返回股票到三级行业的映射（含 in/out 日期）；测试校验
- [x] #3 doc-6 契约增补；全量测试与 ruff/mypy 通过
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. schema：REFERENCE_COLUMNS + industry_classify/industry_member；2. Tushare fetch_reference：index_classify（SW2021 L1/L2/L3 三次查询合并）+ index_member_all（全量成分，含 in/out/is_new；确认分页/上限）；3. 测试（adapter+facade）；4. doc-6/README 更新；5. 全量测试/ruff/mypy + 实时冒烟；6. 任务收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
PIT 语义（2026-09-13）：industry_member 采用区间型（in_date/out_date），as-of 成分 = in_date <= as_of AND (out_date IS NULL OR out_date > as_of)；含 is_new 标记，需保留完整历史而非仅最新。

实现与验证（2026-09-13）：
- industry_classify：index_classify SW2021 L1/L2/L3 三次查询合并 → 511 条（31/134/346）；parent_code 引用上级 industry_code（实测 L2/L3 parents 全部命中）。
- industry_member：index_member_all 按 is_new=Y/N 分别 offset 分页（页 3000）→ 全量 7908 行（Y 5902 + N 2006），out_date 非空 2006 条（历史保留，PIT 区间型）。
- 测试：三级树/parent 组装、Y/N 查询、out_date 与日期类型；全量 254 tests passed；ruff/mypy clean。
- 文档：doc-6 reference kinds/schema 增补（含 parent_code 口径），README 能力表更新。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
申万三级行业分类落地：industry_classify（L1/L2/L3 全量，parent 按 industry_code 组树）与 industry_member（含历史剔除记录，区间型 PIT）；实时验证 511 + 7908 行，254 tests/ruff/mypy 全绿。
<!-- SECTION:FINAL_SUMMARY:END -->
