---
id: TASK-1
title: 编写 README（基于 doc-1 架构设计）
status: Done
assignee: []
created_date: '2026-09-12 11:03'
updated_date: '2026-09-12 11:43'
labels: []
dependencies: []
documentation:
  - backlog/docs/architecture/doc-1 - 多源金融数据聚合库-v0-架构设计.md
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
基于已定型的架构设计 doc-1，为 fin-data-hub 编写中文 README：项目定位（Python 库、无存储层、内存缓存）、安装 extras、快速开始示例、统一代码模型、数据源能力矩阵、配置与凭证、缓存/force、限流与并发、开发环境。必须标注当前为设计阶段（尚未实现代码），不得把规划功能写成已实现。
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 README 包含项目定位、安装方式（按源 extras）与快速开始示例（配置注入 + DataHub 调用）
- [x] #2 README 说明统一代码模型（symbol.VENUE）与 source 参数语义
- [x] #3 README 覆盖缓存（TTL/force）、限流、并发安全与凭证配置说明
- [x] #4 README 含数据源能力/接入方式矩阵（Tushare/Wind/iFinD/AkShare）
- [x] #5 README 明确标注设计阶段状态并引用 doc-1，无虚构已实现功能
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. 以 doc-1 为唯一事实来源梳理 README 结构；2. 撰写各节内容（定位/安装/快速开始/代码模型/数据源矩阵/配置/缓存/限流/开发）；3. 核对与 doc-1 一致性及“未实现”标注；4. 自检 AC 并收尾。
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
验证：脚本对 README.md 逐项核验 5 条 AC 关键内容，全部 PASS（extras 安装、统一代码模型、缓存/force/限流/并发/凭证、四源矩阵、设计阶段+doc-1 标注）；README 共 118 行、约 3.1k 字符。API 示例按 doc-1 §3.1 设计草案编写，已标注可能调整。
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
完成仓库 README.md：项目定位与设计阶段声明、按源 extras 安装、快速开始（配置注入 + DataHub）、统一代码模型 symbol.VENUE、Tushare/Wind/iFinD/AkShare 接入矩阵、配置与凭证、TTL 缓存与 force、限流与并发、开发流程，并引用 doc-1。验证方式：内容核验脚本 5 条验收标准全部 PASS。
<!-- SECTION:FINAL_SUMMARY:END -->
