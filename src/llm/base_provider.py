"""
LLM Provider抽象基类

定义所有Provider必须实现的接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Iterator
import logging

from .types import LLMRequest, LLMResponse, StreamChunk, EmbeddingResponse
from .utils.errors import LLMProviderError


class BaseProvider(ABC):
    """LLM Provider抽象基类"""
    
    def __init__(self, config: Dict[str, Any], provider_name: str):
        """
        初始化Provider
        
        Args:
            config: Provider配置
            provider_name: Provider名称
        """
        self.config = config
        self.provider_name = provider_name
        self.logger = logging.getLogger(f"llm.{provider_name}")
        self._initialized = False
    
    @abstractmethod
    def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """
        同步聊天完成
        
        Args:
            request: 统一的LLM请求
            
        Returns:
            统一的LLM响应
            
        Raises:
            LLMProviderError: Provider相关错误
        """
        pass
    
    @abstractmethod
    def stream_completion(self, request: LLMRequest) -> Iterator[StreamChunk]:
        """
        流式聊天完成
        
        Args:
            request: 统一的LLM请求
            
        Yields:
            StreamChunk: 流式响应块
            
        Raises:
            LLMProviderError: Provider相关错误
        """
        pass
    
    @abstractmethod
    def embedding(self, texts: List[str], model: Optional[str] = None) -> EmbeddingResponse:
        """
        文本向量化
        
        Args:
            texts: 文本列表
            model: 可选的embedding模型名称
            
        Returns:
            EmbeddingResponse: 向量化响应
            
        Raises:
            LLMProviderError: Provider相关错误
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        检查Provider是否可用
        
        Returns:
            bool: 是否可用
        """
        pass
    
    def _log_request(self, request: LLMRequest):
        """记录请求日志"""
        self.logger.debug(
            f"Request: model={request.model}, "
            f"messages={len(request.messages)}, "
            f"temperature={request.temperature}"
        )
    
    def _log_response(self, response: LLMResponse):
        """记录响应日志"""
        self.logger.debug(
            f"Response: model={response.model}, "
            f"usage={response.usage.total_tokens} tokens, "
            f"finish_reason={response.finish_reason}"
        )
    
    def _handle_error(self, error: Exception, context: str = "") -> LLMProviderError:
        """
        统一错误处理
        
        Args:
            error: 原始异常
            context: 错误上下文
            
        Returns:
            LLMProviderError: 封装后的错误
        """
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self.logger.error(f"Provider error: {error_msg}")
        
        return LLMProviderError(
            provider=self.provider_name,
            message=error_msg,
            original_error=error
        )
