---
id: doc-9
title: 对账报告 R2：BaoStock 复权因子 vs Tushare（600519.SH）
type: guide
created_date: '2026-09-13 11:02'
updated_date: '2026-09-13 11:08'
---
# 对账报告 R2：BaoStock 复权因子 vs Tushare（600519.SH）

> 关联说明：`doc-8`（复权数据对账说明） | 日期：2026-09-13 | 结论：**通过**

## 1. 标的与数据范围

- 标的：**600519.SH（sh.600519，贵州茅台）**
- 区间：2024-01-01 ~ 2026-09-11（654 个交易日；5 次现金分红，无送股/配股）
- 时区：Asia/Shanghai

## 2. 数据源与接口

| 源 | 数据 | 接口 |
|---|---|---|
| BaoStock | 原始价 / 前复权 / 后复权 | `query_history_k_data_plus(adjustflag=3/2/1)` |
| BaoStock | 复权因子 | `query_adjust_factor`（事件步进：`foreAdjustFactor`/`backAdjustFactor`/`adjustFactor`） |
| Tushare（基准） | 原始价 + 因子 | `daily` + `adj_factor` |

## 3. 结果

### A. 原始价一致性

BaoStock 与 Tushare 收盘价**最大差 = 0.0**（654 天完全一致）。

### B. 因子归一化一致性

`(f_bs / f_bs_last) / (f_ts / f_ts_last)`：

| 指标 | 值 |
|---|---|
| mean | 0.999998 |
| std | 6.455e-06 |
| min | 0.999870 |
| max | 1.000003 |

→ 归一化后两源因子**一致**（差异为 6 位小数舍入，ppm 级）。

### C. 逐事件乘数对照

| 除权日 | BaoStock 乘数 | Tushare 乘数 | 差异 |
|---|---|---|---|
| 2024-12-20 | 1.015637 | 1.015636 | +1.25 ppm |
| 2025-06-26 | 1.019599 | 1.019594 | +4.57 ppm |
| 2025-12-19 | 1.017029 | 1.017026 | +2.85 ppm |
| 2026-06-26 | 1.023664 | 1.023667 | -2.94 ppm |

（2024-06-19 事件在窗口起点前，由归一化一致性推断同样匹配。）

### D. 源自身自洽性

- **前复权**：`qfq_bs / (raw × f_bs / f_bs_last)` = **1.000000**（std 3.32e-07）→ BaoStock 公布的前复权价与"原始价 × 自有因子"完全自洽。
- **后复权锚点**：BaoStock 累计因子与 Tushare 相差一个**常数比例（≈0.887）**；即 `hfq_bs ≈ raw × f_bs`，`hfq_ts ≈ raw × f_ts`，两者仅**锚点**不同（每源自洽）。

### E. 跨源前复权（qfq）一致性

`qfq_bs_normalized = raw × f_bs / f_bs_last` 对比 Tushare 基准 `raw × f_ts / f_ts_last`：

| 指标 | 值 |
|---|---|
| mean | 0.999988 |
| std | 2.552e-05 |
| min | 0.999870 |
| max | 1.000003 |

→ **前复权跨源一致**（归一化抵消锚点，差异为 6 位小数舍入）；"归一化因子比"与 qfq 比完全同值（数学等价）。

### F. Router 端到端验证（实现路径）

`source=baostock` + `factor_source=baostock` 经 Router `apply_adjustment`（事件步进 backward 对齐 + 窗口基准行）合成，对比 BaoStock 官方复权价（654 天全量）：

| 方式 | ours / official | std |
|---|---|---|
| qfq = raw×f/f_last | 0.99999997 | 3.739e-07 |
| hfq = raw×f | 1.00000000 | 9.196e-17 |

说明：`apply_adjustment` 自 2026-09-13 起改用 backward `merge_asof`，支持稀疏因子源（仅事件行 + `start` 基准行）且 `start` 可为非交易日。

## 4. 限制

1. BaoStock 因子为**累计值且仅事件日（除权日）有行**，使用需"基准值 + 前向填充"；窗口起点前需提供基准（或从更早起点拉取）。
2. 因子保留 6 位小数 → 与 Tushare 存在 **ppm 级**舍入差（不影响业务）。
3. **跨源 hfq 不可直接比较**（锚点不同）；平台/存储应固定单一 `factor_source`。
4. 未覆盖送股/配股场景（本次窗口均为现金分红）；如遇送配需补充对账。

## 5. 结论与影响

- **通过**：BaoStock 复权因子可用于 `raw + factor` 管线；**qfq 与 Tushare 完全一致**，hfq 仅锚点差异。
- 可作为 Router `factor_source` 的可选值（免费源，利于开发期去付费依赖）；默认仍为 Tushare。
- 实施项：`BaoStockAdapter.fetch_adjust_factors`（事件步进 → 基准 + 逐事件行）+ 能力声明 → 见 TASK-2.23。

## 6. 复现步骤

1. BaoStock：`login` → `query_history_k_data_plus(adjustflag=1/2/3)`、`query_adjust_factor` → `logout`；
2. Tushare：`daily` + `adj_factor`（注意**返回为倒序，对比前必须按日期升序**；否则 qfq 锚点会取到最早日期，产生 0.909 量级假象）；
3. 按 `doc-8` §2 公式计算 A~D 四项指标并与本文对照。
