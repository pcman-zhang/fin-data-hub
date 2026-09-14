---
id: TASK-3.3.1
title: Alembic 版本化迁移与回滚
status: Done
assignee: []
created_date: '2026-09-14 06:33'
updated_date: '2026-09-14 10:47'
labels: []
dependencies: []
parent_task_id: TASK-3.3
ordinal: 52000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
为存储层引入 Alembic：迁移脚手架 + 基线迁移（由数据字典生成）+ upgrade/downgrade 幂等可重复执行；集成测试（真实 PG）验证版本升级与回滚。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Alembic 脚手架与基线迁移落地（从字典生成，含 hypertable/压缩语句）
- [x] #2 upgrade/downgrade 可重复执行（幂等）；真实 PG 集成验证
- [x] #3 文档同步；全量测试/ruff/mypy 通过
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 依赖与脚手架：pyproject 增加 alembic/psycopg[binary]；根目录 alembic.ini + migrations/env.py（target_metadata=build_metadata()，DSN 走 DATABASE_*/FDP_DATABASE_HOST 或 -x db_url）。
2. 基线生成：storage/migrations.py 提供 baseline_statements()/render_baseline_script()（由 schema_sql + timescale_statements 生成冻结 DDL）；schema_sql 增加 if_not_exists 参数；生成 migrations/versions/0001_baseline.py。
3. 执行入口：upgrade()/downgrade() 程序化 API（供 TASK-3.4 自动迁移）；downgrade 用 DROP TABLE IF EXISTS。
4. 漂移 CI：tests/test_platform_migrations.py 校验基线脚本与当前字典生成的 DDL 一致（同 meta-schema 漂移检查模式）。
5. dev compose：docker-compose.dev.yml（timescaledb pg17 + healthcheck + 卷）+ .env.example + .gitignore 加 .env + README 章节。
6. 集成测试：tests/test_integration_migrations.py（真实 PG：upgrade → 校验表/hypertable → 重复 upgrade no-op → downgrade base → 重复 downgrade → 再 upgrade）。
7. 验证与收口：全量 pytest/ruff/mypy；Docker 就绪后跑 -m integration；文档同步。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
实现与验证：① 基线 migrations/versions/0001_baseline.py 由 dictionary→metadata 生成（schema/表/hypertable/压缩 + mart.entity_latest_v1 视图与 entity_asof 函数），tests/test_platform_migrations.py 做漂移校验与回滚完备性检查；② 真实 PG17+TimescaleDB 集成（docker-compose.dev.yml）验证 upgrade→重复 upgrade→downgrade base→重复 downgrade→再 upgrade 全链路幂等，并补充读模型函数真实建函数冒烟；③ README 增加「本地数据库与迁移」章节，.env.example + .gitignore(.env) 保证凭证不入库。验证：327 单测 + 5 集成通过，ruff/mypy 全绿。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
引入 Alembic 版本化迁移：由数据字典生成基线（含 hypertable/压缩与 mart 读模型），upgrade/downgrade 程序化入口幂等可重复；真实 PG17+TimescaleDB 集成验证升级与回滚；docker-compose.dev.yml 提供本地开发数据库，凭证经 .env 注入不入库。验证：327 单测 + 5 集成 + ruff/mypy 全绿。
<!-- SECTION:FINAL_SUMMARY:END -->
