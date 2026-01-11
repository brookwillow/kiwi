"""
LLM Manager - 统一的LLM管理器

提供单例模式的LLM访问接口，支持多Provider路由和降级
"""
import logging
from typing import Dict, List, Optional, Iterator, Any
from threading import Lock

from .config import ConfigManager, LLMConfig
from .base_provider import BaseProvider
from .providers import DashScopeProvider, OllamaProvider
from .types import (
    LLMRequest, LLMResponse, StreamChunk, EmbeddingResponse,
    LLMMessage, LLMProvider
)
from .utils.errors import (
    LLMError, LLMAllProviderFailedError, LLMProviderUnavailableError
)


class LLMManager:
    """
    LLM统一管理器（单例模式）
    
    负责:
    1. 管理多个LLM Provider
    2. 根据场景路由到合适的Provider
    3. 支持Provider失败时的降级策略
    4. 提供统一的聊天、流式、向量化接口
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls, config_path: Optional[str] = None):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化LLM Manager
        
        Args:
            config_path: 配置文件路径，仅第一次初始化时生效
        """
        if self._initialized:
            return
        
        # 加载配置
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.get_config()
        
        # 初始化日志
        self.logger = logging.getLogger("llm.manager")
        self.logger.setLevel(getattr(logging, self.config.logging_level))
        
        # 初始化Providers
        self._providers: Dict[str, BaseProvider] = {}
        self._initialize_providers()
        
        self._initialized = True
        self.logger.info("LLM Manager初始化完成")
    
    def _initialize_providers(self):
        """初始化所有配置的Provider"""
        provider_classes = {
            "dashscope": DashScopeProvider,
            "ollama": OllamaProvider,
        }
        
        for provider_name, provider_config in self.config.providers.items():
            if provider_name not in provider_classes:
                self.logger.warning(f"未知的Provider类型: {provider_name}")
                continue
            
            try:
                provider_class = provider_classes[provider_name]
                provider = provider_class(provider_config.config)
                self._providers[provider_name] = provider
                
                status = "✅ 可用" if provider.is_available() else "❌ 不可用"
                self.logger.info(f"Provider {provider_name}: {status}")
            except Exception as e:
                self.logger.error(f"初始化Provider {provider_name} 失败: {e}")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        enable_thinking: bool = True,
        **kwargs
    ) -> LLMResponse:
        """
        统一的聊天接口
        
        Args:
            messages: 消息列表，格式: [{"role": "user", "content": "..."}]
            model: 模型名称 (qwen-plus/qwen3-8b/qwen-turbo等)
            temperature: 温度参数
            max_tokens: 最大生成token数
            stream: 是否流式
            enable_thinking: 是否开启思考模式，默认True。chat_agent等闲聊场景应设为False
            **kwargs: 其他参数
            
        Returns:
            LLMResponse: 统一的响应格式
            
        Raises:
            LLMAllProviderFailedError: 所有尝试都失败时
        """
        # 转换为LLMMessage格式
        llm_messages = [
            LLMMessage(
                role=msg["role"],
                content=msg.get("content", ""),
                name=msg.get("name"),
                tool_calls=msg.get("tool_calls"),
                tool_call_id=msg.get("tool_call_id")
            )
            for msg in messages
        ]
        
        # 构建请求
        request = LLMRequest(
            messages=llm_messages,
            model=None,  # 不直接传model，由Provider决定
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            enable_thinking=enable_thinking,
            **kwargs
        )
        
        # 确定使用的模型
        target_model = model
        
        # 执行请求（带降级）
        return self._execute_with_fallback(target_model, request)
    
    def stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        enable_thinking: bool = True,
        **kwargs
    ) -> Iterator[StreamChunk]:
        """
        流式聊天接口
        
        Args:
            messages: 消息列表
            model: 模型名称 (qwen-plus/qwen3-8b/qwen-turbo等)
            temperature: 温度参数
            max_tokens: 最大生成token数
            enable_thinking: 是否开启思考模式，默认True
            **kwargs: 其他参数
            
        Yields:
            StreamChunk: 流式响应块
        """
        # 转换为LLMMessage格式
        llm_messages = [
            LLMMessage(
                role=msg["role"],
                content=msg.get("content", ""),
                name=msg.get("name"),
                tool_calls=msg.get("tool_calls"),
                tool_call_id=msg.get("tool_call_id")
            )
            for msg in messages
        ]
        
        # 构建请求
        request = LLMRequest(
            messages=llm_messages,
            model=None,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            enable_thinking=enable_thinking,
            **kwargs
        )
        
        # 确定使用的模型
        target_model = model
        model_config = self.config_manager.get_model_config(target_model)
        
        if not model_config:
            raise LLMError(f"未找到模型配置: {target_model}")
        
        # 获取对应的Provider
        provider = self._get_provider(model_config.provider)
        
        if not provider or not provider.is_available():
            raise LLMProviderUnavailableError(
                provider=model_config.provider,
                message="Provider不可用"
            )
        
        # 设置实际的模型名
        request.model = model_config.model_name
        
        # 执行流式请求
        yield from provider.stream_completion(request)
    
    def embedding(
        self,
        texts: List[str],
        model: str = "bge-m3"
    ) -> EmbeddingResponse:
        """
        文本向量化接口
        
        Args:
            texts: 文本列表
            model: 模型名称，默认为 bge-m3
            
        Returns:
            EmbeddingResponse: 向量化响应
        """
        # 确定使用的模型
        target_model = model
        model_config = self.config_manager.get_model_config(target_model)
        
        if not model_config:
            raise LLMError(f"未找到模型配置: {target_model}")
        
        # 获取对应的Provider
        provider = self._get_provider(model_config.provider)
        
        if not provider or not provider.is_available():
            raise LLMProviderUnavailableError(
                provider=model_config.provider,
                message="Embedding Provider不可用"
            )
        
        return provider.embedding(texts, model_config.model_name)
    
    def _execute_with_fallback(
        self,
        model_name: str,
        request: LLMRequest
    ) -> LLMResponse:
        """执行请求，支持模型级别的降级"""
        # 构建尝试的模型列表（包含降级模型）
        models_to_try = [model_name]
        
        if self.config.fallback_enabled:
            # 添加降级模型
            fallback_model = self.config_manager.get_model_fallback(model_name)
            if fallback_model and fallback_model not in models_to_try:
                models_to_try.append(fallback_model)
        
        # 记录失败信息
        errors = {}
        
        for target_model in models_to_try:
            # 获取模型配置
            model_config = self.config_manager.get_model_config(target_model)
            
            if not model_config:
                errors[target_model] = LLMError(f"未找到模型配置: {target_model}")
                continue
            
            # 获取对应的Provider
            provider = self._get_provider(model_config.provider)
            
            if not provider:
                errors[target_model] = LLMError(f"Provider {model_config.provider} 未初始化")
                continue
            
            if not provider.is_available():
                errors[target_model] = LLMError(f"Provider {model_config.provider} 不可用")
                continue
            
            try:
                self.logger.info(
                    f"使用模型 '{target_model}' "
                    f"(Provider: {model_config.provider}, 实际模型: {model_config.model_name})"
                )
                
                # 设置实际的模型名
                request.model = model_config.model_name
                response = provider.chat_completion(request)
                
                # 成功
                if target_model != model_name:
                    self.logger.warning(
                        f"原始模型 '{model_name}' 失败，已降级到 '{target_model}'"
                    )
                
                return response
                
            except Exception as e:
                self.logger.error(f"模型 {target_model} 调用失败: {e}")
                errors[target_model] = e
                continue
        
        # 所有模型都失败
        raise LLMAllProviderFailedError(errors)
    
    def _get_provider(self, provider_name: str) -> Optional[BaseProvider]:
        """获取Provider实例"""
        return self._providers.get(provider_name)
    
    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有Provider的状态
        
        Returns:
            Dict: Provider状态信息
        """
        status = {}
        for name, provider in self._providers.items():
            is_available = provider.is_available()
            # 获取该Provider下的所有模型
            provider_models = [
                model_config.name 
                for model_config in self.config.models.values() 
                if model_config.provider == name
            ]
            status[name] = {
                "available": is_available,
                "models": provider_models,
                "status": "✅ 可用" if is_available else "❌ 不可用"
            }
        return status
    
    def switch_scenario_model(self, scenario: str, model_name: str):
        """
        动态切换场景使用的模型
        
        Args:
            scenario: 场景名称
            model_name: 模型名称
        """
        if model_name not in self.config.models:
            raise LLMError(f"未知的模型: {model_name}")
        
        self.config.scenarios[scenario] = model_name
        self.logger.info(f"场景 '{scenario}' 已切换到模型: {model_name}")
    
    def reload_config(self):
        """重新加载配置"""
        self.logger.info("重新加载配置...")
        self.config_manager.reload()
        self.config = self.config_manager.get_config()
        
        # 重新初始化Providers
        self._providers.clear()
        self._initialize_providers()
        
        self.logger.info("配置重新加载完成")


# 全局单例访问函数
_manager_instance = None

def get_llm_manager(config_path: Optional[str] = None) -> LLMManager:
    """
    获取LLM Manager单例
    
    Args:
        config_path: 配置文件路径，仅第一次调用时生效
        
    Returns:
        LLMManager: 单例实例
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = LLMManager(config_path)
    return _manager_instance
