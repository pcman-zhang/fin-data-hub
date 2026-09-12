# fin-data-hub

多源金融数据聚合库（Python）。用统一接口获取 Tushare / Wind / 同花顺 iFinD / AkShare 的行情、净值、指数与基础资料数据，并在库内统一标的代码、限流与内存缓存。

> **状态：设计阶段。** 当前仓库仅包含架构设计（Backlog 文档 `doc-1`）与项目文档，尚未有实现代码；README 中的 API 为设计草案，可能调整。

## 特性

- **统一代码模型**：以 WindCode 风格 `symbol.VENUE` 作为标的主键（如 `600000.SH`、`000001.SZ`、`510300.SH`、`000001.OF`），各源代码差异由映射层收敛。
- **统一接口 + 显式来源**：取数接口通过 `source` 参数明确数据来源，内部按 source 调度到对应适配器。
- **配置注入**：Tushare token、Wind / iFinD 凭证由调用方通过配置对象或环境变量传入；库不读取全局配置、不落盘。
- **每源限流**：按数据源（及接口）配置 QPS / 并发，遇服务端限流指数退避重试。
- **线程安全**：共享状态加锁、缓存 single-flight，避免并发重复请求消耗配额。
- **内存缓存**：TTL + LRU，`force=True` 跳过缓存强制刷新；本库不含持久化存储层。

## 安装

```bash
pip install "fin-data-hub[tushare]"   # Tushare
pip install "fin-data-hub[akshare]"   # AkShare
pip install "fin-data-hub[ifind]"     # 同花顺 iFinD（含 httpx）
pip install "fin-data-hub[wind]"      # Wind（含 httpx）
```

按需安装对应数据源的 extras；不使用某源时无需安装其依赖。核心依赖仅 `pandas`。

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
hub = DataHub(config)

# 日线行情：显式指定数据源
bars = hub.get_bars(
    ["600000.SH", "510300.SH"],
    start="20260101",
    end="20260901",
    source=Source.TUSHARE,
)

# 强制刷新（跳过缓存）
bars = hub.get_bars(
    ["600519.SH"], "20260101", "20260901",
    source=Source.WIND, force=True,
)

# 场外基金净值
nav = hub.get_fund_nav(["000001.OF"], source=Source.IFIND)
```

> 以上 API 为设计草案（见 `doc-1` §3.1），以未来实现为准。

## 统一代码模型

格式为 `symbol.VENUE`：

| 示例 | 含义 |
|---|---|
| `600000.SH` / `000001.SZ` / `920002.BJ` | A 股（沪 / 深 / 北） |
| `510300.SH` / `159915.SZ` | 场内 ETF / LOF |
| `000001.OF` | 场外基金 |
| `000300.SH` / `399006.SZ` | 指数 |

- 代码统一 6 位补零、VENUE 大写；`000001.SZ`（平安银行）与 `000001.OF`（华夏成长）必须靠后缀区分，不接受裸代码。
- 兼容性（已实测）：Tushare、Wind、iFinD 直接接受该格式；AkShare 各接口需 6 位或专有格式，由映射层转换。

## 数据源

| 数据源 | 接入方式 | 凭证 | 备注 |
|---|---|---|---|
| Tushare | `tushare` 包 | Token | 接口限额随积分档变化 |
| Wind | 远端 MCP（HTTP JSON-RPC） | API Key（配置注入） | 无需 WindPy |
| 同花顺 iFinD | 远端 MCP（HTTP JSON-RPC） | Authorization token | 无需 iFinDPy；响应需按工具解析 |
| AkShare | `akshare` 包 | 无需 | 公开源，默认低 QPS 保守运行 |

iFinD / Wind 不要求安装厂商 SDK：库内置 MCP 客户端（基于 `httpx`），使用方只需安装对应 extras 并配置凭证。详见 `doc-1` §3.3。

## 配置与凭证

- 通过构造参数或配置对象注入：`HubConfig(tushare=..., wind=..., ifind=...)`。
- 支持环境变量回退（如 `FIN_DATA_HUB_TUSHARE_TOKEN`）与本地配置文件（不入库）。
- 缺失对应凭证且调用该 source 时抛出明确异常；凭证不写入日志。
- 库运行时**不读取**任何外部全局配置或用户目录。

## 缓存与刷新

- 进程内 TTL + LRU 缓存，按数据类型分级 TTL（参考数据、日线、快照、净值）。
- 内存约束：`max_bytes`（字节预算，主约束）+ `max_entries`（条数兜底）+ `max_entry_bytes`（单条过大跳过缓存），超限按 LRU 淘汰。
- `force=True` 跳过缓存并刷新；结果 `df.attrs` 携带 `source / cached / fetched_at` 等元信息。
- 缓存仅存于内存，进程退出即失效；本库不负责任何持久化。

## 限流与并发

- 每源独立限流（令牌桶），支持按接口覆盖（Tushare 不同接口限额不同）。
- 批量查询受每源 `max_concurrency` 与 QPS 双重约束；缓存 single-flight 防止并发击穿。
- 限流为进程内限制，多进程部署会叠加实际请求量。
- 遇服务端限流自动退避重试；AkShare 默认最保守。

## 开发

规划中的开发流程（脚手架建立后生效）：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev,tushare,akshare,ifind,wind]"
.venv/bin/python -m pytest
```

- 架构设计：Backlog 文档 `doc-1`（`backlog doc view doc-1`）
- 任务与文档统一由 Backlog.md CLI 管理（详见 `AGENTS.md`）
