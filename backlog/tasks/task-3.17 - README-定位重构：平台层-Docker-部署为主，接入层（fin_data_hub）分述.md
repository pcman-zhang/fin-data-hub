---
id: TASK-3.17
title: README 定位重构：平台层 + Docker 部署为主，接入层（fin_data_hub）分述
status: To Do
assignee: []
created_date: '2026-09-14 11:11'
updated_date: '2026-09-14 11:11'
labels: []
dependencies: []
parent_task_id: TASK-3
ordinal: 55000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
背景：项目已转向 FinDataPlatform（平台层，doc-10 三层结构）与 Docker 独立部署；README 仍以 v0 聚合库（fin_data_hub）为主线，且安装示例给出 `fin-data-platform[tushare/akshare/...]` 等数据源 extras，与当前定位不符。

目标：
1. 平台层是发行与使用主体：`fin-data-platform` 包用于访问 Docker 部署的服务（SDK/REST 客户端，见 doc-12；落地任务 TASK-3.7/3.11），不直接对接数据源，**不需要数据源相关 extras**；
2. 数据源适配（Tushare/Wind/同花顺 iFinD/AkShare/Fuyao/BaoStock）与限流/内存缓存属接入层 `fin_data_hub`，单独成章说明（其 extras 与用法不得与平台层混排）；
3. 快速开始改为「Docker Compose 部署服务（TASK-3.4）→ 客户端接入示例」；
4. 修正与现状矛盾的表述：旧的「v0 已完成」主线叙事、源 extras 安装示例、项目结构/当前状态章节。

参考：doc-10 §1/§2（层间依赖与写入边界）、doc-2（v1 规划）、doc-17/19（自动生成文档不手改）。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 README 定位为 fin-data-platform（平台层）与 Docker 部署，快速开始为「部署服务 + 客户端接入」
- [ ] #2 安装章节不再为平台包提供数据源 extras；源适配器与相关 extras 归入 fin_data_hub（接入层）章节单独说明
- [ ] #3 「项目结构」与「当前状态」反映现状：接入层 v0 可用；平台层存储/迁移/Entity Graph 已落地，服务与部署进行中
- [ ] #4 包名、模块名、安装命令与 pyproject 及实际实现一致，无矛盾描述
- [ ] #5 仅改动文档（README），不触碰代码；pytest/ruff/mypy 保持通过
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @freeman
created: 2026-09-14 11:11
---
实现边界说明：当前 pyproject.toml 中 fin-data-platform 发行包仍声明源 extras（tushare/akshare/ifind/wind/fuyao/baostock，过渡态，供接入层开发使用）。本任务只改 README 口径；若要求移除/迁移这些 extras，属包边界调整，应与 TASK-3.11（SDK 发布与版本兼容）统筹，或另建任务。
---
<!-- COMMENTS:END -->
