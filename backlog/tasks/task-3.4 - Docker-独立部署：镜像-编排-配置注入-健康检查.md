---
id: TASK-3.4
title: Docker 独立部署：镜像 / 编排 / 配置注入 / 健康检查
status: Done
assignee:
  - '@freeman'
created_date: '2026-09-13 06:00'
updated_date: '2026-09-14 15:44'
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
- [x] #1 docker compose up 一键起服务并完成初始化迁移
- [x] #2 凭证不进入镜像与仓库；配置可复现注入
- [x] #3 健康检查/日志/资源限制就绪
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 镜像：单镜像多入口（python:3.13-slim；安装 platform + 数据源 extras；COPY alembic.ini + migrations/；非 root 用户；健康检查入口）
2. 健康检查：runtime 入口新增 --check（就绪检查退出码 0/1），供 Docker HEALTHCHECK 使用；补单测
3. 编排：新增 docker-compose.yml（全栈：TimescaleDB + 一次性 migrate + runtime），dev 文件保留
   - migrate 用 one-shot 服务，runtime depends_on service_completed_successfully
   - 默认单进程 role=all；拆分角色（scheduler/worker）以 profile 提供
   - Redis 服务同期纳入（基础设施先就绪，待 TASK-3.9 接入）
   - 凭证经环境变量注入（.env 不入库、不进镜像）；日志上限、资源限制、健康检查
4. .dockerignore（.git/.venv/backlog/tests/.env 等不入镜像）
5. 文档：配置手册新增「容器化部署」章节（一键起、迁移、配置、健康检查、资源限制）；README 交付形态更新
6. 验证：本地 docker build + compose up 实测（db → migrate → runtime 就绪）；pytest/ruff/mypy；凭证不入镜像核查
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
部署形态（2026-09-13）：单机 Docker（compose），暂不需要 K8s。

迁移器打包要求（来自 TASK-3.3.1 评审）：pip install 不打包 alembic.ini/migrations；镜像需显式 COPY 两路径，或经 FDP_ALEMBIC_INI/FDP_ALEMBIC_SCRIPT_LOCATION 指定。自动迁移入口：fin_data_platform.storage.migrations.upgrade()。

依赖更新（2026-09-14）：按 doc-20 增加前置 TASK-3.18（FinDataRuntime 骨架）；部署 Runtime（runtime/runtime-scheduler/runtime-worker 入口）与消费入口，单镜像多 service。

容器化实测（2026-09-14）：docker compose up 端到端通过——全新卷迁移 0001→0002、migrate 完成后 runtime 启动、健康检查 healthy、--check 容器内退出 0、资源限制生效（mem 1g / cpu 1.5 / 非 root fdp）、镜像无凭证环境变量。发现：迁移日志有 TimescaleDB 建议性 WARNING（压缩键未覆盖物理键、enum VARCHAR），已拆分为 TASK-3.20 后续治理。项目命名：全栈 fin-data-platform（5432），dev 改名 fin-data-platform-dev 并端口退避 15432，两者并存验证通过。

验证汇总：① 单测 371（+5：入口 --check 退出码、Docker 工件回归 4 项）；② ruff/mypy 全绿；③ docker compose config 校验通过（stack/dev 两份）；④ 重建镜像后全栈仍 healthy；⑤ 新增 DATABASE_CONNECT_TIMEOUT（默认 5s）修复网络不可达时 readiness 无限挂起。

复审修复（8 项 + nits）：① 引擎工厂仅对 PostgreSQL 注入 connect_timeout（修复 SQLite DSN 回归，补 2 项测试）；② 拆分角色文档改为「先 stop runtime 再按名启动 scheduler/worker」并实测通过；③ .env.example 行内注释改独立行（兼容 export 用法）；④ 配置手册子节编号修正 5.x；⑤ 资源限制措辞修正并给 migrate 加限制；⑥ migrations/env.py 复用引擎工厂（迁移亦继承连接超时）；⑦ dev 卷更名说明；⑧ 新增 POSTGRES_BIND/DEV_POSTGRES_BIND（默认不变）；nits：.dockerignore 补 egg-info/build、redis 命令断言精确化。验证：373 单测 + ruff/mypy 全绿；全栈/拆分/单机三种形态实测 healthy。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Docker 交付落地：单镜像多入口（Dockerfile，非 root + 内置健康检查）；Compose 全栈编排（TimescaleDB + Redis + 一次性迁移 + Runtime，拆分角色经 profile）；一键启动自动迁移（001→002 实测）、健康检查 healthy、资源限制生效、镜像无凭证；dev 编排独立项目并端口退避（5432/15432 并存）。配套修复：readiness 连接超时（DATABASE_CONNECT_TIMEOUT）与迁移继承超时。验证：373 单测 + ruff/mypy；全栈/拆分/单机三形态实测。遗留：TimescaleDB DDL 告警治理 → TASK-3.20。
<!-- SECTION:FINAL_SUMMARY:END -->
