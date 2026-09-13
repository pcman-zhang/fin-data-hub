---
id: TASK-2.5
title: MCP 传输层：HTTP JSON-RPC 客户端 + 解析基础设施
status: Done
assignee: []
created_date: '2026-09-12 12:01'
updated_date: '2026-09-12 12:27'
labels: []
dependencies:
  - TASK-2.1
parent_task_id: TASK-2
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
mcp/client.py：Streamable HTTP JSON-RPC（initialize/notifications/initialized/tools/call）；会话按服务缓存并设 TTL；JSON 与 SSE 双解析；超时重试；content 解包；错误映射。fixture 测试不联网。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 MockTransport 下跑通 initialize/会话/调用全流程；JSON 与 SSE 响应均可解析
- [x] #2 会话按服务缓存并 TTL 过期重建
- [x] #3 HTTP/JSON-RPC/业务错误映射为库异常；重试有测试
- [x] #4 不引入官方 mcp SDK
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. mcp/client.py：McpServerConfig（url/token/auth_scheme/timeout/session_ttl/protocol_version）+ McpHttpClient（initialize→initialized→tools/call、会话缓存 TTL、JSON/SSE 双解析、httpx 注入、重试、content 解包、错误映射）；2. mcp/__init__.py 导出；3. pyproject dev 增加 httpx；4. tests/test_mcp_client.py 用 httpx.MockTransport 覆盖全流程/SSE/TTL/错误/重试/鉴权头；5. pytest/ruff/mypy 验证并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
验证：tests/test_mcp_client.py 14 项；全库 78 passed；ruff/mypy 全过。实现：McpServerConfig（token repr=False）、McpHttpClient（会话 TTL 缓存、JSON/SSE 解析、Bearer/裸 token、httpx 注入、NetworkError 重试、JSON-RPC/HTTP/isError/解析错误映射）、unwrap_content（structuredContent 优先）、list_tools。依赖仅 httpx。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成 MCP 传输层：mcp/client.py（initialize→initialized→tools/call、会话缓存 TTL、JSON/SSE、错误映射、重试）与 unwrap_content；MockTransport 测试 14 项，全库 78 passed，ruff/mypy 干净。
<!-- SECTION:FINAL_SUMMARY:END -->
