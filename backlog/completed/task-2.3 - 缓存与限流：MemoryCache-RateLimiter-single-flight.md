---
id: TASK-2.3
title: 缓存与限流：MemoryCache + RateLimiter + single-flight
status: Done
assignee: []
created_date: '2026-09-12 12:01'
updated_date: '2026-09-12 12:06'
labels: []
dependencies:
  - TASK-2.1
parent_task_id: TASK-2
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
MemoryCache：TTL + LRU + 字节预算（max_bytes/条数 max_entries/单条 max_entry_bytes），force 覆盖，single-flight 防击穿，线程安全；RateLimiter：令牌桶、endpoint 级覆盖、超时、退避重试。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 TTL 过期、force、覆盖写、LRU 淘汰、字节预算淘汰均有单测（注入时钟）
- [x] #2 single-flight：并发同 key 仅触发一次底层调用
- [x] #3 RateLimiter 线程安全、endpoint 覆盖、超时抛 RateLimitTimeout、限流响应退避重试
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. cache.py：MemoryCache（OrderedDict LRU + monotonic TTL + 字节预算/条数/单条上限 + force + single-flight + 线程安全 + stats/time_fn 注入）；2. ratelimit.py：RateLimiter 令牌桶、EndpointRateLimiter 覆盖、retry_call 指数退避+jitter；3. tests/test_cache.py 与 tests/test_ratelimit.py；4. pytest/ruff/mypy 验证；5. 收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
验证：tests/test_cache.py + tests/test_ratelimit.py；全库 53 passed；ruff/mypy 全过。实现：MemoryCache（TTL/LRU/字节预算/单条上限/force/single-flight/stats/time_fn 注入/CoW 零拷贝）、RateLimiter 令牌桶、RateLimiterSet endpoint 覆盖、retry_call 指数退避+抖动。修复了 LRU popitem 解包顺序 bug。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成缓存与限流：cache.py（含 single-flight 与字节预算）与 ratelimit.py（令牌桶 + endpoint 覆盖 + 退避重试）。验证：53 项单测通过，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
