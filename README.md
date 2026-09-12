# fin-data-hub

多源金融数据聚合库（Python）。用统一接口获取 Tushare / Wind / 同花顺 iFinD / AkShare 的行情、净值、指数与参考数据，并在库内统一标的代码、字段口径、并发安全与内存缓存。**本库不含持久化存储层**（不落库、不写文件）。

## 特性

- **统一代码模型**：以 WindCode 风格 `symbol.VENUE` 作为标的主键（如 `600000.SH`、`000001.SZ`、`510300.SH`、`000001.OF`），各源代码差异由映射层收敛。
- **统一接口 + 显式来源**：取数接口通过 `source` 参数明确数据来源，内部按 source 调度到对应适配器。
- **配置注入**：Tushare token、Wind / iFinD 凭证由调用方通过配置对象传入；库不读取环境变量、全局配置或用户目录。
- **能力驱动的请求合并**：按各源/端点上限自动分块（如单标的源逐代码、Wind 快照 ≤50、iFinD EDB 多指标聚合）并合并去重。
- **每源限流**：令牌桶（QPS）在适配器调用边界生效，可按源覆盖；等待超时抛出 `RateLimitTimeout`。
- **线程安全**：共享状态加锁、缓存 single-flight，避免并发重复请求消耗配额。
- **内存缓存**：TTL + LRU + 字节预算，`force=True` 跳过缓存强制刷新。
- **调用计量**：按源统计调用次数与估算成本、预算告警，`hub.stats()` 查看；跨进程汇总通过 `on_record` 回调。

## 安装

```bash
pip install "fin-data-hub[tushare]"   # Tushare
pip install "fin-data-hub[akshare]"   # AkShare
pip install "fin-data-hub[ifind]"     # 同花顺 iFinD（含 httpx）
pip install "fin-data-hub[wind]"      # Wind（含 httpx）
```

按需安装对应数据源的 extras；不使用某源时无需安装其依赖。核心依赖仅 `pandas`。iFinD / Wind 通过厂商远端 MCP（HTTP JSON-RPC）接入，**不需要安装 WindPy / iFinDPy**。

版本：`fin_data_hub.__version__`（单一来源 `src/fin_data_hub/_version.py`，`pyproject.toml` 动态读取）。

## 快速开始

```python
from fin_data_hub import DataHub, HubConfig, Source
from fin_data_hub.config import TushareConfig, WindConfig, IfindConfig

config = HubConfig(
    tushare=TushareConfig(token="..."),
    wind=WindConfig(api_key="..."),
    ifind=IfindConfig(authorization="..."),
    # akshare 无需凭证
)

# 按配置自动装配可用数据源（缺凭证/依赖的源会被跳过）
hub = DataHub.from_config(config)

# 日线行情：显式指定数据源
bars = hub.get_bars(
    ["600000.SH", "510300.SH"],
    start="2026-09-01",
    end="2026-09-11",
    source=Source.TUSHARE,
)

# 强制刷新（跳过缓存）
bars = hub.get_bars(
    ["600519.SH"], "2026-09-09", "2026-09-11",
    source=Source.WIND, force=True,
)

# 场外基金净值（iFinD 支持多基金合并为一次调用）
nav = hub.get_fund_nav(["000001.OF"], source=Source.IFIND)

# 交易日历与参考数据
calendar = hub.get_trade_calendar(start="2026-09-01", end="2026-09-11", source=Source.AKSHARE)
stocks = hub.get_reference("stock_list", source=Source.TUSHARE)

# 缓存与调用统计（内存）
stats = hub.stats()
```

也可以手动装配：

```python
from fin_data_hub.sources import SourceRegistry
from fin_data_hub.sources.tushare import TushareAdapter

registry = SourceRegistry([TushareAdapter(config.tushare)])
hub = DataHub(config, registry=registry)
```

## 统一代码模型

格式为 `symbol.VENUE`：

| 示例 | 含义 |
|---|---|
| `600000.SH` / `000001.SZ` / `920002.BJ` | A 股（沪 / 深 / 北） |
| `510300.SH` / `159915.SZ` | 场内 ETF / LOF |
| `000001.OF` | 场外基金 |
| `000300.SH` / `399006.SZ` | 指数 |

- 代码统一 6 位补零、VENUE 大写；`000001.SZ`（平安银行）与 `000001.OF`（华夏成长）必须靠后缀区分，不接受裸代码。
- Tushare、Wind、iFinD 直接接受该格式；AkShare 由映射层转换为 6 位或接口专有格式。

## 各源支持范围（v0）

| 能力 | Tushare | AkShare | Wind | iFinD |
|---|---|---|---|---|
| `get_bars` | ✅ 日线，支持 qfq/hfq | ✅ 股票 / ETF / LOF / 指数 | ⚠️ 仅日线、单代码逐次调用 | ⚠️ 仅指数 |
| `get_snapshot` | — | — | ✅ 单次 ≤50 代码 | — |
| `get_fund_nav` | ✅ | ✅ 场外基金 | — | ✅ 多基金合并 |
| `get_reference` | ✅ 股票 / 基金 / 指数列表 | — | — | — |
| `get_trade_calendar` | ✅ | ✅ | — | — |
| EDB 宏观指标 | — | — | ✅ 精确代码批量 | ✅ 多指标聚合 |
| 债券行情 | — | — | ✅ 长区间 ≤90 天分块 | — |

限制说明：

- Wind 日线不传 `period`（后端不接受 `period=1d`）；K 线为单代码接口，多代码由库逐次调用。
- iFinD 的 K 线目前仅支持指数（`index_data`）；场外基金净值走 `get_fund_market_performance`（NL 聚合）。
- iFinD 的 NL 工具普遍支持多标的/多指标聚合（已抽验 stock/fund/edb），库内合并为一次调用，不做逐标的拆分；单次 50 代码为请求体积的安全上限。
- AkShare 无参考数据接口；各接口为单标的形式，批量请求由库自动拆分。

## 配置与凭证

- 凭证一律显式注入：`HubConfig(tushare=..., wind=..., ifind=...)`；缺失凭证且调用该源时抛出 `MissingCredentialError`。
- 凭证不写入日志，配置对象的 `repr` 已脱敏。
- 如需自定义各源限制与预算，通过 `HubConfig` 的 `cache` / `budget` 子配置：

```python
from fin_data_hub import BudgetConfig, CacheConfig, HubConfig

config = HubConfig(
    cache=CacheConfig(max_bytes=256 * 1024 * 1024, ttl=6 * 3600),
    budget=BudgetConfig(
        calls_per_day={"wind": 50},
        cost_table={"wind.get_economic_data": 10.0},
        on_record=lambda record: my_sink(record),  # 跨进程汇总入口
    ),
)
```

## 限流

- 每源独立令牌桶（QPS），在适配器真实调用前获取令牌；等待超时抛出 `RateLimitTimeout`。
- 默认值（保守起步）：Tushare 2 QPS、AkShare 1 QPS、Wind 1 QPS、**iFinD 2 QPS**。
- 按源覆盖：

```python
from fin_data_hub import HubConfig
from fin_data_hub.ratelimit import RateLimitConfig

config = HubConfig(
    rate_limits={"ifind": RateLimitConfig(rate=2.0, burst=2.0, timeout=30.0)}
)
```

- 限流为进程内限制；多进程部署会叠加实际请求量。

## 缓存与刷新

- 进程内 TTL + LRU 缓存，付费源默认 6h；`force=True` 跳过缓存并覆盖写入。
- 内存约束：`max_bytes`（字节预算，主约束）+ `max_entries`（条数兜底）+ `max_entry_bytes`（单条过大跳过缓存）。
- 结果 `df.attrs` 携带 `source / cached / fetched_at` 等元信息。
- 缓存仅存于内存，进程退出即失效；本库不负责任何持久化。

## 调用计量

- `hub.stats()` 返回缓存与用量统计（按日调用次数、估算成本、告警）。
- 计量仅统计当前进程；跨进程汇总由调用方在 `BudgetConfig.on_record` 中写入自有存储或指标系统。

## 开发

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev,tushare,akshare,ifind,wind]"

.venv/bin/python -m pytest              # 离线单测（默认跳过 integration）
.venv/bin/python -m pytest -m integration   # 端到端测试，需真实凭证
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy
```

集成测试读取的环境变量（仅测试使用，库本身不读取环境变量）：

- `FIN_DATA_HUB_TUSHARE_TOKEN`
- `FIN_DATA_HUB_WIND_API_KEY`
- `FIN_DATA_HUB_IFIND_TOKEN`

架构设计见仓库 Backlog 文档 `doc-1`（`backlog doc view doc-1`）。

## 许可证

本项目采用 [MIT License](LICENSE)。

Copyright (c) 2026 Freeman Zhang
