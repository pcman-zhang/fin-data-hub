---
id: TASK-3.17
title: README 定位重构：平台层 + Docker 部署为主，接入层（fin_data_hub）分述
status: Done
assignee: []
created_date: '2026-09-14 11:11'
updated_date: '2026-09-14 11:21'
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
- [x] #1 README 定位为 fin-data-platform 客户端（只读访问已部署服务）与 Docker 部署；服务端/客户端现状与规划分述
- [x] #2 安装章节：客户端仅 `pip install fin-data-platform`（无任何数据源 extras）；接入层使用预留包名 fin-data-hub（注明当前未单独发布），不出现 `fin-data-platform[源]` 写法
- [x] #3 「系统架构」「仓库结构」「当前状态」反映现状：接入层可用；平台层存储/迁移/Entity Graph 已落地，服务与部署进行中
- [x] #4 包名、模块名、安装命令与 pyproject 及实际实现一致，无矛盾描述
- [x] #5 仅改动文档（README），不触碰代码；pytest/ruff/mypy 保持通过
- [x] #6 新增「系统架构」章节：FinDataHub→数据库的数据流、数据库存储与组织（schema/PIT/分区/读模型）、平台使用方式（客户端/开发用法，现状与规划分述）
- [x] #7 删除向前兼容/过渡期表述（开发阶段、无外部使用者），文档只描述当前系统与既有设计
- [x] #8 「当前状态」明确 Docker 现状：仅 dev TimescaleDB 数据库容器，没有任何 Backend 程序在运行
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 任务补充验收：新增「系统架构」章节（Hub→DB 数据流 / DB 存储组织 / Platform 使用）；删除向前兼容与过渡期表述（开发阶段、无外部使用者）；现状诚实标注（Docker 仅 dev 数据库；后端服务未运行）。
2. README 重构：平台层定位与安装在前（不含源 extras）、接入层 fin_data_hub 分述在后；快速开始=部署（现状：dev 数据库 + 迁移）与平台层用法示例。
3. 自检：与 pyproject/实际实现一致；pytest/ruff/mypy 通过。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
实现与验证：README 重构为「平台层 + Docker 部署」定位（安装区分平台层/接入层 extras）；新增「系统架构」三节（Hub→DB 数据流 / 数据库存储与组织 / Platform 使用，现状与规划分述）与「仓库结构」；「当前状态」表按能力标注落地/建设中，明确 Docker 仅 dev TimescaleDB、无 Backend 程序；全文 grep 无兼容/过渡表述。验证：仅 README + 任务文件改动，pytest 328 passed / ruff / mypy 全绿。

修正记录：安装章节初稿误将数据源 extras 写入 fin-data-platform；按定位改为「客户端只读访问服务」（仅 pip install fin-data-platform），接入层改用预留包名 fin-data-hub（注明未单独发布，不提供 fin-data-platform[源] 写法）。验证：README 无 fin-data-platform[extras] 模式，pytest 328 passed / ruff / mypy 全绿；代码零改动。
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @freeman
created: 2026-09-14 11:11
---
实现边界说明：当前 pyproject.toml 中 fin-data-platform 发行包仍声明源 extras（tushare/akshare/ifind/wind/fuyao/baostock，过渡态，供接入层开发使用）。本任务只改 README 口径；若要求移除/迁移这些 extras，属包边界调整，应与 TASK-3.11（SDK 发布与版本兼容）统筹，或另建任务。
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
README 定位重构完成：fin-data-platform = 只读访问已部署服务的客户端（安装无数据源 extras），fin-data-hub = 接入层独立包（预留包名，未单独发布）；新增系统架构三节（Hub→数据库数据流、数据库 schema/PIT/分区/读模型组织、平台使用方式）与仓库结构；当前状态诚实标注（Docker 仅 dev TimescaleDB、无 Backend 程序）；去除向前兼容/过渡表述。验证：328 单测 + ruff/mypy 通过，代码零改动。
<!-- SECTION:FINAL_SUMMARY:END -->
