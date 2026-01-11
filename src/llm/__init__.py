"""
LLM统一管理模块

提供统一的大模型访问接口，支持多Provider动态切换
"""
from .manager import LLMManager, get_llm_manager
from .types import (
    LLMProvider, MessageRole,
    LLMMessage, LLMRequest, LLMResponse,
    StreamChunk, EmbeddingResponse, TokenUsage
)
from .utils.errors import (
    LLMError, LLMProviderError, LLMConfigError,
    LLMAPIError, LLMAuthenticationError, LLMRateLimitError,
    LLMTimeoutError, LLMNetworkError, LLMProviderUnavailableError,
    LLMAllProviderFailedError
)

__version__ = "1.0.0"

__all__ = [
    # 核心类
    'LLMManager',
    'get_llm_manager',
    
    # 类型
    'LLMProvider',
    'MessageRole',
    'LLMMessage',
    'LLMRequest',
    'LLMResponse',
    'StreamChunk',
    'EmbeddingResponse',
    'TokenUsage',
    
    # 异常
    'LLMError',
    'LLMProviderError',
    'LLMConfigError',
    'LLMAPIError',
    'LLMAuthenticationError',
    'LLMRateLimitError',
    'LLMTimeoutError',
    'LLMNetworkError',
    'LLMProviderUnavailableError',
    'LLMAllProviderFailedError',
]
