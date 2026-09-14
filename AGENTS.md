# AGENTS.md — fin-data-platform

## 项目性质（最重要）
- 这是一个 **Python 库**，不是可执行程序/服务：提供可被其他程序 `import` 的模块，不要引入 CLI、常驻进程或调度器作为主入口。
- 目标：聚合多源金融数据（Tushare / Wind / 同花顺 iFinD / AkShare 等公开源），对外提供统一查询接口。**不含持久化存储层**（不落库/不写文件）；缓存仅在库内内存维护（TTL + 可选 `force` 刷新）。
- **阶段边界**：「无存储层」约束适用于 v0 库；后一阶段（里程碑 `m-0` / TASK-3）演进为带 PostgreSQL 的「金融数据基座 v1」（规划见 `doc-2`），届时相关约束按新阶段更新。
- 任务与文档统一用 Backlog.md CLI 管理（见文末 Backlog 工作流；`backlog/` 下的文件不要手改）。项目已初始化，task 前缀 `task`，状态为 To Do / In Progress / Done。
- 架构基线见 Backlog 文档 `doc-1`（`backlog doc view doc-1`）：统一 WindCode、显式 `source` 参数、配置注入、每源限流、并发安全、TTL 缓存 + `force`。

## 当前状态
- 仓库是骨架：仅一行 README，无代码、无 `pyproject.toml`、无测试/lint 配置。不要假设存在构建或测试命令；首次加入实现时再建立打包配置。
- 本机 Python 3.13（miniconda，用 `python3`/`python3 -m pip`）：已装 `tushare`、`akshare`、`pandas`、`numpy`；未装 `uv`/`poetry`。
- WindPy / iFinDPy 均未安装。

## 数据源接入方式
- Tushare / AkShare：Python 包（`tushare`、`akshare`）；Tushare 需 token，AkShare 无鉴权。
- iFinD / Wind：**库内通道是厂商远端 MCP（HTTP JSON-RPC）**，不使用厂商 SDK（终端授权成本高）。iFinD 服务 `hexin-ifind-ds-{stock,fund,edb,news,bond,global-stock,index,futures}-mcp`；Wind 服务 `https://mcp.wind.com.cn/vserver_*/mcp/`（`Bearer` 鉴权）。协议细节见 doc-1 §3.3。
- 凭证一律由调用方注入（配置对象/环境变量）；库不隐式读取用户目录或任何外部配置。
- 付费源按调用计费（iFinD 按次、Wind 按积分，`query` 类接口显著更贵）：**调用次数即成本，优先合并调用与缓存**。

## 开源纪律（重要）
- 本仓库为开源项目：`README.md`、`AGENTS.md`、代码、注释与文档中不得出现本项目之外的信息——外部项目/仓库名、外部文档编号、个人目录或机器路径、账号/额度/价格信息、凭证位置等。
- 设计结论可以保留，但必须去掉来源引用与内部上下文，只写本仓库自洽的内容。

## 聚合层约定
- 各源代码格式不统一（Tushare `600000.SH`、iFinD/东财六位代码、Wind 代码），聚合层必须先定义统一标的主键再 join/merge。
- 各源字段口径、复权方式、币种不同，不要直接横向拼接原始字段；跨源合并前先对齐口径。
- 凭证不得写入仓库或代码；一律由调用方注入（见 doc-1 §4）。

## Git 工作流（硬约束）
- **严格禁止在 `main` 上直接修改**：任何改动（代码、文档、Backlog 文件）必须在新分支进行，经 PR 合并回 `main`；
- 开工前先确认当前分支；若位于 `main`，必须先创建分支（`feat/*` / `fix/*` / `docs/*` / `chore/*`）再操作；
- **`commit` 与 `push` 均需用户明确批准后执行**，不得自行提交或推送；
- 合并后同步：`git fetch --prune` → 更新本地 `main` → 删除已合并的本地分支。

## 交互要求
- 使用中文交互
- 使用准确、明晰的、专业的语言

<!-- BACKLOG.MD GUIDELINES START -->
<!-- backlog.md-instructions-version: 1.50.1 -->
<CRITICAL_INSTRUCTION>

## Backlog.md Workflow

This project uses Backlog.md for task and project management.

**For every user request in this project, run `backlog instructions overview` before answering or taking action.**

Use the overview to decide whether to search, read, create, or update Backlog tasks.

Before task lifecycle actions, read the matching detailed guide:
- `backlog instructions task-creation` before creating or splitting tasks
- `backlog instructions task-execution` before planning, changing status or assignee, adding a plan or implementation notes, or implementing task work
- `backlog instructions task-finalization` before checking acceptance criteria, writing final summaries, or moving tasks to terminal statuses

Use `backlog <command> --help` before running unfamiliar commands. Help shows options, fields, and examples.

Do not edit Backlog task, draft, document, decision, or milestone markdown files directly. Use the `backlog` CLI so metadata, relationships, and history stay consistent.

</CRITICAL_INSTRUCTION>
<!-- BACKLOG.MD GUIDELINES END -->
