---
id: doc-5
title: FinDataHub Router Policy（复权路由策略）
type: specification
created_date: '2026-09-13 10:01'
updated_date: '2026-09-13 11:08'
---
# FinDataHub Router Policy（统一输出与跨源路由策略）

> 状态：已定（2026-09-13） | 关联：doc-4（Fuyao 复权对账调查）、doc-2 §6.16、TASK-2.21

## 1. 目标

FinDataHub 对外输出**统一 schema**；但单源数据常不完整（缺字段、缺复权能力、单源失败、覆盖范围不同）。Router 是**顶层编排层**：在不改变 `source` 语义（`source` = 主数据源）的前提下，组合多个 adapter，产出**完整、可溯源、可审计**的结果。

## 2. 职责

1. **主源执行**：`source` 指定的 adapter 作为主源；
2. **完整性检测**：对照 canonical schema 检查缺列/全空列/缺复权能力；
3. **补充执行**（仅在需要时触发）：
   - **字段补全**：主源缺失字段从 fallback 源按 `(code, date)` coalesce（first-non-null，不覆盖主源已有值）；
   - **复权合成**：`trusted_native_adjust` 之外的源，用 `raw（主源） + factor（factor_source）` 合成；
   - **失败回退**：主源失败且配置 `fallbacks` 时按顺序尝试；
4. **溯源标注**与缓存。

## 3. 路由规则（优先级）

1. 请求 `source` 始终是主源，不因补全而改变；
2. **仅补缺**：不覆盖主源已有值；字段级合并；不静默近似；
3. **复权**：可信源走原生复权；否则 `raw + factor` 合成（`hfq = raw × f`、`qfq = raw × f / f_latest`；按 code 分组、backward `merge_asof` **事件步进**对齐，支持稀疏因子源（事件行 + 窗口基准行）与非交易日 `start`）；
   - 因子覆盖（实测，doc-8 §3.1）：股票 → Tushare `adj_factor` / BaoStock；ETF/LOF → Tushare `fund_adj`；场外基金/指数无因子（显式报错，不静默回退）；
   - `factor_source` 默认 `TUSHARE`；可选 `BAOSTOCK`（仅股票，R2=doc-9 通过）且需按资产类型可用性校验；
4. **回退**：主源失败 → 依序尝试 `fallbacks`；实际执行源写入溯源；
5. **按需触发**：只有缺数据/缺字段时才调用补充源（成本最小化）；
6. **无法补齐**：明确报错（`SourceError` / `UnsupportedCapability`）。

## 4. 配置

```python
@dataclass(frozen=True, slots=True)
class RoutingConfig:
    factor_source: Source | None = Source.TUSHARE
    trusted_native_adjust: frozenset[Source] = frozenset(
        {Source.TUSHARE, Source.AKSHARE}  # 开发期排除付费源 Wind/iFinD
    )
    fallbacks: tuple[Source, ...] = ()   # 主源失败时的回退链
    field_fill: bool = True              # 允许字段级补全
```

- 默认 trusted：Tushare / Wind / AkShare（原生复权经抽查验证）；**Fuyao 不在 trusted**（doc-4）。
- `factor_source` 可替换为 Wind / iFinD（待其因子能力实现并对账通过）。

## 5. 溯源与缓存

- 结果 `df.attrs`：`source`（实际主数据源）、`requested_source`（请求源）、`factor_source`（复权合成时）、`filled_from`（列→补充源）、`adjust`、`cached`。
- 缓存键包含请求源 + adjust + 关键参数；**组合结果整体缓存**（不重复调用补充源）。

## 6. 原因（为什么这样设计）

- **单源覆盖差异**：Fuyao 无复权、reference 无 industry；iFinD K 线仅指数；Wind K 线单代码；AkShare 单标的——统一输出必然需要跨源补全。
- **复权必须可审计**：厂商预计算复权是黑盒（doc-4 实测异常），raw + factor 可复现、可对账。
- **成本最小化**：付费源按调用计费，补充只在缺失时触发。
- **可替换性**：因子源与回退链均可配置，不绑定单一厂商。

## 7. 一期范围与扩展

- **一期（TASK-2.21）**：`get_bars` 的复权合成 + 字段补全 + 主源失败回退；
- **扩展**：`snapshot` / `fund_nav` / `reference` 的字段补全；跨源对账择优；DataPanel 跨源合并。
