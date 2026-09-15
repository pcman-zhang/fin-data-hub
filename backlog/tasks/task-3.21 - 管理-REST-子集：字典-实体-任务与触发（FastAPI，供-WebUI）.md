---
id: TASK-3.21
title: 管理 REST 子集：字典 / 实体 / 任务与触发（FastAPI，供 WebUI）
status: Done
assignee: []
created_date: '2026-09-15 14:41'
updated_date: '2026-09-15 14:49'
labels: []
milestone: m-0
dependencies:
  - TASK-3.1
  - TASK-3.6
  - TASK-3.3.3
parent_task_id: TASK-3
ordinal: 60000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
WebUI 的 API 支撑（doc-14：REST 单一数据面，WebUI 不直连 DB）。面向**平台治理**的管理子集；对外完整能力（API Key / 导出 / Arrow / ETag / SLO）仍归 TASK-3.7。

设计（已确认）：
- FastAPI + uvicorn；OpenAPI 自动生成；本机默认 127.0.0.1
- 读路径使用只读角色连接（read DSN）；控制路径使用写 DSN，但仅向 meta 提交任务意图（不绕过 Runtime 控制面）
- 端点（v1）：
  - `GET /v1/datasets`、`GET /v1/datasets/{dataset}`（字段/口径/PIT/主键/SLA/质量/血缘/存储/源映射）
  - `GET /v1/entities`（检索/筛选/分页）、`GET /v1/entities/{entity_id}`（当前态 + 属性时间轴 + 代码履历 + 关系 + 外部标识）
  - `GET /v1/jobs`（筛选/分页）、`GET /v1/jobs/{run_id}`、`GET /v1/watermarks`
  - `POST /v1/jobs/sync`（代码清单 + 窗口 → 写 meta 队列；高风险操作，WebUI 侧二次确认）
  - `GET /healthz`（数据库 + 字典 + schema 版本）
- 静态资源：托管 web/dist（SPA 回退），供同镜像 service 使用
- 依赖：新 extra `api`（fastapi/uvicorn）；dev 依赖同步

验收：
1. 端点可用且契约稳定（OpenAPI 文档生成）
2. 读走只读 DSN、写只走 meta 意图（不直连 ingestion）；越权/非法参数显式报错
3. 单测（TestClient + 内存/字典）+ 真库集成；随 compose service 一键可用
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 FastAPI 应用与全部 v1 端点落地；OpenAPI 可访问；本机默认绑定
- [x] #2 读路径走只读 DSN；POST /v1/jobs/sync 仅提交 meta 意图（校验 job 已注册）；非法参数显式报错
- [x] #3 单测（TestClient）+ 真库集成（实体检索/任务列表/触发意图）+ compose service 可启动；pytest/ruff/mypy 全绿
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
管理 REST 子集落地（FastAPI）：① 端点——数据集字典（列表/详情）、实体注册表（检索/详情/词表）、任务运行与水位、同步触发（只写 meta 意图，校验 job 已注册/窗口/幂等键）、/healthz、OpenAPI（/api/docs）；② 连接口径——数据读取走只读 DSN，控制面走写连接且仅提交意图；③ 读取层——registry/reader.py（SCD2 当前态/时间轴/履历/双向关系/外部标识，跨方言）与 MetaRepository.list_watermarks；④ 部署——compose service 长驻（默认仅本机 8000）+ SPA 静态托管（web/dist，供 TASK-3.8）；⑤ 依赖 extra api。验证：412 单测（API 8 项）+ 16 集成（真库端到端）+ ruff/mypy/链接检查全绿；容器 service healthy，/healthz ok、数据集 7 项、触发校验正常。
<!-- SECTION:FINAL_SUMMARY:END -->
