---
id: TASK-2.11
title: 请求合并与 capability 元数据
status: Done
assignee: []
created_date: '2026-09-12 12:02'
updated_date: '2026-09-12 12:50'
labels: []
dependencies:
  - TASK-2.4
parent_task_id: TASK-2
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
capability 元数据（每源/端点：最大代码数、多指标支持、历史支持、成本提示）；facade 批量分块与合并；结果去重排序。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 capability 表驱动；超限自动分块并合并
- [x] #2 iFinD EDB 一指标一次、Wind 单次代码数上限有单测
- [x] #3 合并结果无重复、顺序稳定
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. capabilities.py：EndpointCapability（max_codes_per_call/max_indicators_per_call/supports_multi_symbol/supports_history/cost_class）+ 按 (source, capability/endpoint) 的表 + get_capability/split_codes；2. facade：get_bars/get_snapshot/get_fund_nav 在 load 内按 capability 分块调用并合并（去重 + 排序 + 单次 finalize），空 codes 明确报错；3. tests/test_capabilities.py：分块边界（AkShare=1、Wind snapshot=50、iFinD EDB 指标=1）、facade 分块调用次数、去重排序；4. pytest/ruff/mypy 验证并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
验证：tests/test_capabilities.py 6 项；全库 144 passed；ruff/mypy 全过。实现：capabilities.py（EndpointCapability + (source,capability) 表 + get_capability/split_codes，cost_class 仅通用分级不含价格）；facade 三个 API 在缓存 load 内按 capability 分块、_merge_frames 去重排序、最终一次 finalize；空 codes 明确 ValueError。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成请求合并与 capability 元数据：表驱动的分块策略（AkShare=1、iFinD=50、Wind snapshot=50、Wind bars=1、Tushare 批量），门面自动分块/合并/去重/稳定排序。验证：全库 144 项单测通过，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
