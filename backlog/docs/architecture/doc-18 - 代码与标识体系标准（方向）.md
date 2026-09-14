---
id: doc-18
title: 代码与标识体系标准（方向）
type: specification
created_date: '2026-09-13 14:44'
updated_date: '2026-09-14 01:00'
---
# 代码与标识体系标准（方向）

> 状态：方向已定（宏观/序列**暂不接入**，按需逐项接入并登记数据字典） | 关联：doc-10 §3、doc-11（字典）、doc-6（代码契约）、doc-17（数据库）
> 目的：统一"我们有哪些数据、以什么 code 获取"的基础标准；数据字典承担**数据目录 + 契约**双重角色。

## 1. canonical 代码（WindCode 风格）

| 数据类 | canonical | 例子 | 说明 |
|---|---|---|---|
| 证券 | WindCode（现状） | `600519.SH`、`510300.SH`、`000300.SH` | 已实现 |
| 市场报价序列（方向） | `symbol.IB` | `DR007.IB`、`SHIBORON.IB` | 银行间市场 |
| 外汇序列（方向） | `symbol.FX` | `USDCNY.FX` | 外汇市场 |
| 统计序列 EDB（方向） | `EDB码.EDB` | `M0000612.EDB` | 虚拟命名空间后缀（非交易所），保持 `symbol.VENUE` 语法 |

**枚举扩展（待实施，宏观接入时落地）**：`Venue.IB / .FX / .EDB`；`SecType.SERIES`。

## 2. 归一化原则

1. 一切源代码在 **FinDataHub 归一为 canonical**；入库与对外接口只使用 canonical；
2. 证券类映射 = **机械规则**（CodeMapper，无状态）；
3. 序列类映射 = **定义性映射**（人工维护"某源指标码 → canonical"），登记在字典/映射文件；
4. 平台侧不存"每源别名表"（证券），序列映射随接入逐项登记。

## 3. 注册表范围（与 doc-10 §3.3 一致）

- **entity 注册表（Entity Graph）**：身份（entity_id/code/name/分类面）+ 关系（entity_relation，单向存储 + inverse 字典驱动双向查询）+ 外部标识（ISIN/FIGI 等）+ 社会实体状态（issuer 专用）；
- **交易状态不在注册表**：上市/停牌/ST/退市由交易状态数据集承载（`listing_lifecycle` + suspension/st 事件），**PIT Universe 由数据集推导**；
- 不承担"每源别名"（证券由 Hub mapper 解决；序列映射是定义数据，登记字典）；宏观/序列注册表在接入时随条目建立。

## 4. 宏观/序列接入策略（本期不接）

```
需要某指标 → ① 定义 canonical code → ② Hub 映射（源码→canonical）
          → ③ 数据字典条目（dataset + fields + mappings + SLA）
          → ④ 数据集/表（doc-17 自动包含）→ ⑤ 接口（get_edb_series）
```

## 5. 数据字典的双重角色

| 角色 | 回答 | 落地 |
|---|---|---|
| **数据目录** | 我们有哪些数据、以什么 code 获取 | 自动生成目录（doc-19，随字典更新） |
| **契约** | 字段/单位/PIT/SLA/质量/血缘/映射 | doc-11 规范 + CI 校验 |
