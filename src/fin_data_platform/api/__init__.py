"""管理 API（doc-14：REST 单一数据面，WebUI 不直连 DB）。

- 数据集字典浏览（`/v1/datasets*`）
- 实体注册表浏览（`/v1/entities*`）
- 任务与水位、同步触发（`/v1/jobs*`、`/v1/watermarks`）
- 健康检查（`/healthz`）与 SPA 静态托管（供同镜像 service 使用）

对外完整能力（API Key / 导出 / Arrow / ETag / SLO）归 TASK-3.7，另行演进。
"""

from fin_data_platform.api.app import create_app
from fin_data_platform.api.deps import ApiContext, build_context

__all__ = ["ApiContext", "build_context", "create_app"]
