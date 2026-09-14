"""FinDataPlatform（v1）SDK 与平台核心。

分层（doc-10 §2）：``fin_data_hub``（接入层）→ ``fin_data_platform``（数据层/服务层核心）
→ ``services/*``（REST/WebUI，后续任务）。
"""

from fin_data_platform._version import __version__

__all__ = ["__version__"]
