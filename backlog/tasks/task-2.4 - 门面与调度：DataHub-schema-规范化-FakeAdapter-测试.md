---
id: TASK-2.4
title: 门面与调度：DataHub + schema 规范化 + FakeAdapter 测试
status: Done
assignee: []
created_date: '2026-09-12 12:01'
updated_date: '2026-09-12 12:07'
labels: []
dependencies:
  - TASK-2.2
  - TASK-2.3
parent_task_id: TASK-2
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
DataHub 门面（get_bars/get_snapshot/get_fund_nav/get_reference/get_trade_calendar）；显式 source；SourceRegistry/BaseAdapter；能力检查；调用链 normalize→cache→limit→fetch→schema；统一 df.attrs。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 FakeAdapter 端到端跑通五个方法；source 参数生效
- [x] #2 缓存命中 attrs.cached=True；force 绕过缓存
- [x] #3 不支持能力抛 UnsupportedCapability（列出可用 source）
- [x] #4 schema 列名与类型统一，有单测
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. schemas.py（各端点规范列 + finalize）；2. sources/base.py 与 registry.py（capability 机制）；3. config.py（HubConfig/子配置，密钥字段 repr=False）；4. facade.py（五方法 + 缓存键 + source 校验 + attrs）；5. cache.contains() 辅助；6. tests/test_facade.py 用 FakeAdapter 覆盖 AC；7. pytest/ruff/mypy 验证并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
验证：tests/test_facade.py 11 项；全库 64 passed；ruff/mypy 全过。实现：schemas.py（各端点规范列 + finalize_frame + 日期强制 datetime64[ns]）、sources/base.py（capability 常量）、sources/registry.py（按能力校验并列出可用 source）、config.py（密钥 repr=False）、facade.py（五方法 + 缓存键含全部参数 + attrs.cached）、cache.contains()。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成门面与调度：DataHub 五方法（bars/snapshot/fund_nav/reference/trade_calendar），显式 source + default_source，SourceRegistry capability 校验，统一 schema 与 df.attrs，缓存命中/force 语义。验证：64 项单测通过，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
