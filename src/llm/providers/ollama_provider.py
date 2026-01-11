"""
Ollama Provider - 本地Ollama模型

支持聊天完成和文本向量化
"""
from typing import List, Dict, Any, Optional, Iterator
import ollama
import time

from ..base_provider import BaseProvider
from ..types import (
    LLMRequest, LLMResponse, StreamChunk, EmbeddingResponse,
    TokenUsage, LLMMessage
)
from ..utils.errors import LLMProviderError, LLMNetworkError, LLMTimeoutError


class OllamaProvider(BaseProvider):
    """Ollama本地Provider"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Ollama Provider
        
        Args:
            config: Provider配置，包含：
                - base_url: Ollama服务URL
                - default_model: 默认聊天模型
                - embedding_model: 默认embedding模型
                - timeout: 超时时间
        """
        super().__init__(config, "ollama")
        
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.timeout = config.get("timeout", 60)
        
        # 配置Ollama客户端
        try:
            # 检查Ollama服务是否可用
            ollama.list()
            self._initialized = True
            self.logger.info(f"Ollama Provider初始化成功: {self.base_url}")
        except Exception as e:
            self.logger.warning(f"Ollama服务不可用: {e}")
            self._initialized = False
    
    def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """同步聊天完成"""
        if not self.is_available():
            raise LLMProviderError(
                provider=self.provider_name,
                message="Ollama服务不可用，请检查服务是否启动"
            )
        
        self._log_request(request)
        
        try:
            # 准备消息格式
            messages = [msg.to_dict() for msg in request.messages]
            model = request.model
            
            if not model:
                raise LLMProviderError(
                    provider=self.provider_name,
                    message="必须指定模型名称"
                )
            
            # 构建请求参数
            options = {
                "temperature": request.temperature,
                "top_p": request.top_p,
            }
            if request.max_tokens:
                options["num_predict"] = request.max_tokens
            
            # 处理思考模式：映射到 Ollama 的 think 参数
            enable_thinking = getattr(request, 'enable_thinking', True)
            
            # 准备调用参数
            call_params = {
                "model": model,
                "messages": messages,
                "options": options,
                "stream": False
            }
            
            # 根据 enable_thinking 设置 think 参数
            # True: 不设置（使用模型默认行为）
            # False: 明确设置 think=False 尝试禁用思考模式
            if enable_thinking is False:
                call_params["think"] = False
            
            # 调用Ollama，如果模型不支持 think 参数则降级
            start_time = time.time()
            try:
                response = ollama.chat(**call_params)
            except ollama.ResponseError as e:
                if "does not support thinking" in str(e) and "think" in call_params:
                    # 模型不支持 think 参数，移除后重试
                    self.logger.warning(f"模型 {model} 不支持 think 参数，使用默认行为")
                    call_params.pop("think", None)
                    response = ollama.chat(**call_params)
                else:
                    raise
            elapsed_time = time.time() - start_time
            
            # 解析响应
            message = response.get("message", {})
            content = message.get("content", "")
            
            # 如果用户明确要求关闭思考模式，则过滤 <think> 标签
            # 某些模型（如 qwen3:8b）会在输出中包含 <think></think> 标签
            # 即使使用 think=False，模型仍可能输出这些标签
            enable_thinking = getattr(request, 'enable_thinking', True)
            if enable_thinking is False:
                import re
                # 移除 <think>...</think> 标签及其内容
                content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
                # 如果有未闭合的 <think> 标签（内容被截断），也移除
                content = re.sub(r"<think>.*$", "", content, flags=re.DOTALL)
                content = content.strip()
                
                # 如果过滤后内容为空，记录警告
                if not content:
                    self.logger.warning(f"过滤<think>标签后内容为空，原始响应: {message.get('content', '')[:100]}")
            
            # 估算token使用（Ollama不直接返回token数）
            prompt_tokens = response.get("prompt_eval_count", 0)
            completion_tokens = response.get("eval_count", 0)
            
            result = LLMResponse(
                content=content,
                model=model,
                provider=self.provider_name,
                finish_reason="stop",
                usage=TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens
                ),
                raw_response=response
            )
            
            self._log_response(result)
            self.logger.info(f"Ollama请求成功，耗时: {elapsed_time:.2f}s")
            
            return result
            
        except ollama.ResponseError as e:
            raise LLMProviderError(
                provider=self.provider_name,
                message=f"Ollama响应错误: {str(e)}",
                original_error=e
            )
        except Exception as e:
            if "timeout" in str(e).lower():
                raise LLMTimeoutError(
                    provider=self.provider_name,
                    message=f"请求超时（{self.timeout}s）",
                    original_error=e
                )
            raise self._handle_error(e, "Ollama聊天完成失败")
    
    def stream_completion(self, request: LLMRequest) -> Iterator[StreamChunk]:
        """流式聊天完成"""
        if not self.is_available():
            raise LLMProviderError(
                provider=self.provider_name,
                message="Ollama服务不可用"
            )
        
        self._log_request(request)
        
        try:
            # 准备消息格式
            messages = [msg.to_dict() for msg in request.messages]
            model = request.model
            
            if not model:
                raise LLMProviderError(
                    provider=self.provider_name,
                    message="必须指定模型名称"
                )
            
            # 构建请求参数
            options = {
                "temperature": request.temperature,
                "top_p": request.top_p,
            }
            if request.max_tokens:
                options["num_predict"] = request.max_tokens
            
            # 处理思考模式
            enable_thinking = getattr(request, 'enable_thinking', True)
            
            # 准备调用参数
            call_params = {
                "model": model,
                "messages": messages,
                "options": options,
                "stream": True
            }
            
            # 根据 enable_thinking 设置 think 参数
            if enable_thinking is False:
                call_params["think"] = False
            
            # 调用流式API，如果模型不支持则降级
            try:
                stream = ollama.chat(**call_params)
            except ollama.ResponseError as e:
                if "does not support thinking" in str(e) and "think" in call_params:
                    self.logger.warning(f"模型 {model} 不支持 think 参数，使用默认行为")
                    call_params.pop("think", None)
                    stream = ollama.chat(**call_params)
                else:
                    raise
            
            for chunk in stream:
                message = chunk.get("message", {})
                content = message.get("content", "")
                done = chunk.get("done", False)
                
                yield StreamChunk(
                    content=content,
                    finish_reason="stop" if done else None
                )
                
        except Exception as e:
            raise self._handle_error(e, "Ollama流式完成失败")
    
    def embedding(self, texts: List[str], model: Optional[str] = None) -> EmbeddingResponse:
        """文本向量化"""
        if not self.is_available():
            raise LLMProviderError(
                provider=self.provider_name,
                message="Ollama服务不可用"
            )
        
        if not model:
            raise LLMProviderError(
                provider=self.provider_name,
                message="必须指定embedding模型名称"
            )
        
        try:
            embeddings = []
            total_tokens = 0
            
            for text in texts:
                response = ollama.embeddings(
                    model=model,
                    prompt=text
                )
                embeddings.append(response.get("embedding", []))
                # Ollama不返回token数，估算
                total_tokens += len(text.split())
            
            return EmbeddingResponse(
                embeddings=embeddings,
                model=model,
                provider=self.provider_name,
                usage=TokenUsage(
                    prompt_tokens=total_tokens,
                    completion_tokens=0,
                    total_tokens=total_tokens
                )
            )
            
        except Exception as e:
            raise self._handle_error(e, "Ollama向量化失败")
    
    def is_available(self) -> bool:
        """检查Ollama服务是否可用"""
        if not self._initialized:
            # 尝试重新初始化
            try:
                ollama.list()
                self._initialized = True
            except:
                return False
        return self._initialized
