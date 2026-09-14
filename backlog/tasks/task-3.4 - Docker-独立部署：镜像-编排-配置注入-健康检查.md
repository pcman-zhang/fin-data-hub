---
id: TASK-3.4
title: Docker 独立部署：镜像 / 编排 / 配置注入 / 健康检查
status: To Do
assignee: []
created_date: '2026-09-13 06:00'
updated_date: '2026-09-14 12:25'
labels: []
milestone: m-0
dependencies:
  - TASK-3.1
  - TASK-3.3
  - TASK-3.18
parent_task_id: TASK-3
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
容器化与独立部署：应用镜像（含采集/调度/服务/WebUI）、PostgreSQL + TimescaleDB 与 Redis 编排、配置与凭证注入（环境变量/secret，不落镜像）、健康检查、资源限制、初始化与迁移自动执行。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 docker compose up 一键起服务并完成初始化迁移
- [ ] #2 凭证不进入镜像与仓库；配置可复现注入
- [ ] #3 健康检查/日志/资源限制就绪
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
部署形态（2026-09-13）：单机 Docker（compose），暂不需要 K8s。

迁移器打包要求（来自 TASK-3.3.1 评审）：pip install 不打包 alembic.ini/migrations；镜像需显式 COPY 两路径，或经 FDP_ALEMBIC_INI/FDP_ALEMBIC_SCRIPT_LOCATION 指定。自动迁移入口：fin_data_platform.storage.migrations.upgrade()。

依赖更新（2026-09-14）：按 doc-20 增加前置 TASK-3.18（FinDataRuntime 骨架）；部署 Runtime（runtime/runtime-scheduler/runtime-worker 入口）与消费入口，单镜像多 service。
<!-- SECTION:NOTES:END -->
