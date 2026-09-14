"""平台写入端（ingestion）：FinDataHub → Canonical 的同步引擎与任务注册。"""

from fin_data_platform.ingestion.daily_bar import DATASET as DAILY_BAR_DATASET
from fin_data_platform.ingestion.daily_bar import SyncResult, sync_daily_bar
from fin_data_platform.ingestion.tasks import register_daily_bar_task

__all__ = [
    "DAILY_BAR_DATASET",
    "SyncResult",
    "register_daily_bar_task",
    "sync_daily_bar",
]
