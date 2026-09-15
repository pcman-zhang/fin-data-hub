---
id: TASK-3.3.3
title: 只读角色与按域授权
status: Done
assignee:
  - '@freeman'
created_date: '2026-09-14 06:33'
updated_date: '2026-09-15 14:19'
labels: []
dependencies: []
parent_task_id: TASK-3.3
ordinal: 54000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
创建只读角色（读模型/域 schema SELECT），读写 DSN 分离验证；mart 只读、canonical 按域授权；文档记录授权矩阵。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 只读角色与授权脚本（mart/域 SELECT；禁内部原始表）
- [x] #2 读写 DSN 分离验证（reader 无法写入）；集成测试
- [x] #3 文档同步；全量测试/ruff/mypy 通过
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 角色模型：权限角色（NOLOGIN）分层——mart/ref 只读角色 + 按域 canonical 只读角色；登录用户由调用方创建并继承
2. grants 模块：幂等授权脚本（USAGE/SELECT、future tables default privileges；raw/meta/revision 不授权）
3. DSN 分离：StorageConfig.from_env 支持 DATABASE_READ_*（缺省回退写端）；create_read_engine 验证
4. 执行入口：程序化 apply_readonly_roles() + compose 一次性服务（migrate 之后）
5. 集成测试：reader 可读 mart/授权域；写入被拒；raw/meta 不可见
6. 文档：授权矩阵（角色/对象/权限）+ 配置手册与存储策略同步
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
复审修复（5 项）：① 读写 DSN 成对校验改真值判断（compose 空串路径）+ 用例；② 角色名白名单校验 + DO 块字面量转义；③ readable_schemas 去重（缺省路径不再重复授权 ref）；④ runtime/拆分角色 depends_on grant-readonly 成功后再启动（实测）；⑤ 集成测试补 DEFAULT PRIVILEGES 断言与 TimescaleDB 内部 schema 权限传播校验。待验证项已实测：fdp_ro 对 _timescaledb_internal 有 USAGE 与 8 个 chunk 授权（扩展自动传播，压缩块可读）。验证：404 单测 + 全量集成 + ruff/mypy/链接检查全绿。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
只读角色与读写 DSN 分离落地（个人平台：只读/可写两分）：① storage/grants.py——幂等授权（fdp_ro：mart + ref + 各数据域 USAGE/SELECT、mart 函数 EXECUTE、DEFAULT PRIVILEGES；raw/meta 不授权）+ CLI 入口；② StorageConfig 支持 DATABASE_READ_*（缺省沿用写端，半配置报错）；③ compose 一次性 grant-readonly 服务（迁移后执行）+ 读端变量透传；④ 集成测试：reader 可读 mart/ref/域、写入被 DB 拒绝（permission denied）、meta 不可见；⑤ 文档：授权矩阵与目标架构（按域角色演进方向）、架构/组件/doc-13 同步。验证：379 单测 + 13 集成 + ruff/mypy/链接检查全绿；容器 grant-readonly 退出 0，fdp_ro NOLOGIN 授权 18 条、raw/meta 零授权。
<!-- SECTION:FINAL_SUMMARY:END -->
