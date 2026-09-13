---
id: TASK-3.7
title: FinDataPlatform REST（SDK 薄封装）与权限审计
status: To Do
assignee: []
created_date: '2026-09-13 06:01'
updated_date: '2026-09-13 08:24'
labels: []
milestone: m-0
dependencies:
  - TASK-3.1
  - TASK-3.3
parent_task_id: TASK-3
ordinal: 26000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
在 SDK 之上实现 REST 薄封装（版本化 + OpenAPI）：直接调用 FinDataPlatform SDK 查询（含 PIT/as-of 参数），不重复实现语义；游标分页与字段裁剪、压缩（gzip/zstd）、可选 Arrow 列式响应、ETag/If-None-Match、批量端点与异步导出触发；**API Key 鉴权与作用域（read/export/admin；不提供数据写入）**、按 key 限流与成本归因、调用审计；接口文档与数据字典联动；SLO：小批量在线查询 P95 ≤ 200–500ms。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 服务形态按设计落地并通过联调；压缩/分页/字段裁剪/Arrow 响应可用
- [ ] #2 权限模型与调用审计可用
- [ ] #3 接口文档与数据字典联动；SLO 有基准测试
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
分层（2026-09-13）：REST 仅封装 FinDataPlatform SDK；WebUI 依赖本层（TASK-3.8 已加依赖）。
<!-- SECTION:NOTES:END -->
