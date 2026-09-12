---
id: TASK-2.14
title: 限流接入调用链
status: Done
assignee: []
created_date: '2026-09-12 13:06'
updated_date: '2026-09-12 13:11'
labels: []
dependencies:
  - TASK-2.3
parent_task_id: TASK-2
ordinal: 16000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
把已实现的 RateLimiter/RateLimiterSet 接入适配器真实调用边界：BaseAdapter 支持注入限流器，四个适配器在每次源端调用前 acquire；HubConfig 增加按源限流配置（默认：Tushare 2 QPS、AkShare 1 QPS、Wind 1 QPS、iFinD 2 QPS），超时抛 RateLimitTimeout。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 BaseAdapter.bind_rate_limits/_acquire 生效；四个适配器调用边界均先 acquire 再调用
- [x] #2 HubConfig.rate_limits 可按源覆盖；未覆盖时使用默认表（iFinD 默认 2 QPS）
- [x] #3 限流超时抛 RateLimitTimeout（有测试）；直接使用适配器时也应用默认限流
- [x] #4 README 与 doc-1 记录默认值与覆盖方式
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. ratelimit.py：DEFAULT_RATE_LIMITS（tushare 2/akshare 1/wind 1/ifind 2）+ default_rate_limiter_set + RateLimiterSet 支持默认 timeout；2. config.py：HubConfig.rate_limits 按源覆盖；3. base.py：bind_rate_limits/_acquire；4. 四个适配器：__init__ 应用默认限流 + 调用边界 _acquire；5. facade：按源构建/绑定 limiter；6. tests/test_rate_limit_wiring.py；7. README/doc-1 更新；8. pytest/ruff/mypy 验证并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
验证：tests/test_rate_limit_wiring.py 9 项；全库 159 passed（4 deselected）；ruff/mypy 全过。实现：DEFAULT_RATE_LIMITS（tushare 2/akshare 1/wind 1/ifind 2 QPS）+ default_rate_limiter_set；RateLimiterSet 默认 timeout；BaseAdapter.bind_rate_limits/_acquire；四适配器 __init__ 安装默认限流并在调用边界 acquire；facade 按源构建并绑定（HubConfig.rate_limits 覆盖）；README/doc-1 记录默认值与覆盖方式。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成限流接入：四适配器在真实调用前 acquire，默认 iFinD 2 QPS（Tushare 2 / AkShare 1 / Wind 1），可按源覆盖，超时抛 RateLimitTimeout；直接使用适配器也生效。验证：全库 159 项单测通过，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
