---
id: TASK-2.10
title: 成本与配额计量、预算告警
status: Done
assignee: []
created_date: '2026-09-12 12:02'
updated_date: '2026-09-12 12:49'
labels: []
dependencies:
  - TASK-2.4
parent_task_id: TASK-2
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
每源调用计数器（按次/按积分）；调用记录（source/endpoint/codes/latency/est_cost）；预算阈值可配置并告警；hub.stats() 暴露。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 调用计数在 FakeAdapter 与真实适配器路径均生效；stats() 返回 calls/cost 等
- [x] #2 预算阈值触发告警（日志/回调策略）有测试
- [x] #3 计数器线程安全
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. usage.py：BudgetConfig（calls/cost 预算、cost_table、warn_ratio、on_alert）+ UsageLedger（线程安全、按日计数、告警去重、summary、records 环形缓冲）+ UsageRecord/BudgetAlert；2. config.py 增加 budget；3. BaseAdapter.bind_usage/_record；4. 四个适配器在真实调用边界记录（tushare._query/akshare._call/ifind._call_service/wind._call_data）；5. facade 绑定 + hub.stats()；6. tests/test_usage.py；7. pytest/ruff/mypy 验证并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
验证：tests/test_usage.py 10 项；全库 138 passed；ruff/mypy 全过。实现：usage.py（UsageRecord/BudgetAlert/BudgetConfig/UsageLedger，线程安全、按日聚合、阈值告警去重、records 环形缓冲、cost_table 支持 endpoint/source 两级）；BaseAdapter.bind_usage/_record；四适配器在真实调用边界记录（tushare._query/akshare._call/ifind._call_service/wind._call_data）；facade 绑定 + hub.stats()。跨进程：不落盘，通过 BudgetConfig.on_record 回调汇总（异常不影响主流程，有测试）。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成成本/配额计量：进程内线程安全台账（按日 calls/cost、预算告警、records 环形缓冲）、适配器调用边界自动记录、hub.stats() 暴露、on_record 跨进程汇总钩子。验证：全库 138 项单测通过，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
