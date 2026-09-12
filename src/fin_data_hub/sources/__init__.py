"""数据源适配器。"""

from fin_data_hub.sources.base import BaseAdapter
from fin_data_hub.sources.registry import SourceRegistry

__all__ = ["BaseAdapter", "SourceRegistry"]
