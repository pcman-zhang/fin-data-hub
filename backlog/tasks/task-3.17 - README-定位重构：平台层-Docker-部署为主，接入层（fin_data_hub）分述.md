---
id: TASK-3.17
title: README 叙事重构：数据基础设施（四大件 / 三平面 / 消费层）
status: Done
assignee: []
created_date: '2026-09-14 11:11'
updated_date: '2026-09-14 11:33'
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
- [x] #1 叙事定位为数据基础设施：架构图以 Dictionary / Entity Registry / Storage → Derived Engine → Read Model → 消费层为主线，SDK / REST 明确为消费适配器
- [x] #2 Derived Engine 作为一级能力呈现（算法登记 / as-of 输入 / 重述台账 / 建设状态）
- [x] #3 引入 Control Plane / Data Plane / Consumption Plane 结构（meta.* / raw-canonical-mart / 消费适配器）
- [x] #4 「无 Backend」中性表述：SDK 直连 Read Model（SDK direct mode）为合法消费路径，不把 REST 作为系统终点
- [x] #5 安装章节：客户端仅 `pip install fin-data-platform`（无任何数据源 extras）；接入层使用预留包名 fin-data-hub（注明当前未单独发布）
- [x] #6 「系统架构」「仓库结构」「当前状态」反映现状：字典 / 注册表 / 存储 / 迁移已落地；派生 / Control Plane / 消费层建设中
- [x] #7 包名、模块名、安装命令与 pyproject 及实际实现一致，无矛盾描述
- [x] #8 仅改动文档（README），不触碰代码；pytest/ruff/mypy 保持通过
- [x] #9 删除向前兼容/过渡期表述（开发阶段、无外部使用者）
- [x] #10 「当前状态」明确部署现状：仅 dev TimescaleDB 数据库容器，平台不依赖常驻 Backend
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

叙事重构（按评审意见）：① 定位改为数据基础设施（Financial Data Infrastructure），顶部流程图 = Sources → FinDataHub → Dictionary/Registry/Storage → Derived Engine → Read Model → 消费层；② 引入 Control/Data/Consumption 三平面；③ 平台四大件（Dictionary / Entity Registry / PIT Storage / Derived Engine）成节，Derived Engine 一级呈现；④ 消费方式重写：SDK direct mode 为合法路径、REST 降为薄封装，部署现状改为中性表述（仅 dev 数据库、不依赖常驻 Backend）；⑤ 状态表按平台能力重排。验证：grep 无服务层/三层结构/平台包源 extras，pytest 328 passed / ruff / mypy 全绿，代码零改动。
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
README 完成数据基础设施叙事重构：顶部架构图为 Sources → FinDataHub → Dictionary/Entity Registry/Storage → Derived Engine → Read Model → 消费层（SDK/REST/Export/MCP）；平台四大件成节、Derived Engine 一级呈现；引入 Control/Data/Consumption 三平面；消费方式明确 SDK direct mode 与 REST 薄封装定位，部署现状中性表述（仅 dev 数据库、不依赖常驻 Backend）；安装为客户端 pip install fin-data-platform（无数据源 extras），接入层预留 fin-data-hub 包名。验证：328 单测 + ruff/mypy 通过，代码零改动。
<!-- SECTION:FINAL_SUMMARY:END -->
