"""库内异常体系。

约定：
- 所有异常继承 ``FinDataHubError``；
- 参数/代码错误尽量同时继承内置 ``ValueError``，限流等待超时继承 ``TimeoutError``，
  便于调用方按内置类型兜底。
"""

from __future__ import annotations


class FinDataHubError(Exception):
    """本库所有异常的基类。"""


class UnknownSecurityError(FinDataHubError, ValueError):
    """无法解析或识别的标的代码 / venue / 证券类型。"""


class MissingCredentialError(FinDataHubError):
    """调用需要凭证的数据源时未提供凭证。"""


class UnsupportedCapability(FinDataHubError):
    """指定数据源不支持所请求的能力。"""


class RateLimitTimeout(FinDataHubError, TimeoutError):
    """等待限流令牌超时。"""


class RateLimitError(FinDataHubError):
    """数据源返回限流 / 配额错误。"""


class SourceError(FinDataHubError):
    """数据源调用失败的基类。"""


class NetworkError(SourceError):
    """网络 / 传输层错误。"""


class ResponseParseError(SourceError):
    """数据源响应无法解析为预期结构。"""
