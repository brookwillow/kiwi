"""
DashScope Provider - 阿里云通义千问

支持通过OpenAI兼容API访问阿里云模型
"""
from typing import List, Dict, Any, Optional, Iterator
from openai import OpenAI, APIError, AuthenticationError, RateLimitError
import time

from ..base_provider import BaseProvider
from ..types import (
    LLMRequest, LLMResponse, StreamChunk, EmbeddingResponse,
    TokenUsage, LLMMessage
)
from ..utils.errors import (
    LLMProviderError, LLMAPIError, LLMAuthenticationError,
    LLMRateLimitError, LLMTimeoutError, LLMNetworkError
)


class DashScopeProvider(BaseProvider):
    """阿里云DashScope Provider"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化DashScope Provider
        
        Args:
            config: Provider配置，包含：
                - api_key: API密钥
                - base_url: API基础URL
                - default_model: 默认模型名
                - timeout: 超时时间
                - max_retries: 最大重试次数
        """
        super().__init__(config, "dashscope")
        
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.timeout = config.get("timeout", 30)
        self.max_retries = config.get("max_retries", 3)
        
        # 初始化OpenAI客户端
        if self.api_key:
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=self.timeout,
                    max_retries=self.max_retries
                )
                self._initialized = True
            except Exception as e:
                self.logger.error(f"初始化DashScope客户端失败: {e}")
                self._initialized = False
        else:
            self.logger.warning("未提供DashScope API密钥")
            self._initialized = False
    
    def chat_completion(self, request: LLMRequest) -> LLMResponse:
        """同步聊天完成"""
        if not self.is_available():
            raise LLMProviderError(
                provider=self.provider_name,
                message="Provider不可用，请检查API密钥配置"
            )
        
        self._log_request(request)
        
        try:
            # 准备请求参数
            params = request.to_openai_format()
            if not params.get("model"):
                raise LLMProviderError(
                    provider=self.provider_name,
                    message="必须指定模型名称"
                )
            
            # 详细日志：打印发送给API的消息序列（用于调试）
            self.logger.info(f"📤 发送到DashScope API的消息序列 (共{len(params['messages'])}条):")
            for i, msg in enumerate(params['messages']):
                role = msg.get('role', 'unknown')
                has_tool_calls = 'tool_calls' in msg
                has_tool_call_id = 'tool_call_id' in msg
                content_preview = msg.get('content', '')[:50] if msg.get('content') else '(空)'
                
                log_line = f"  [{i+1}] role={role}"
                if has_tool_calls:
                    log_line += f" [有tool_calls: {len(msg['tool_calls'])}个]"
                if has_tool_call_id:
                    log_line += f" [tool_call_id={msg['tool_call_id']}]"
                if not has_tool_calls and not has_tool_call_id:
                    log_line += f" - {content_preview}"
                
                self.logger.info(log_line)
            
            # 调用API
            start_time = time.time()
            response = self.client.chat.completions.create(**params)
            elapsed_time = time.time() - start_time
            
            # 解析响应
            choice = response.choices[0]
            message = choice.message
            content = message.content or ""
            
            # 如果用户明确要求关闭思考模式，则过滤 <think> 标签
            # 通义千问等模型可能会在输出中包含 <think></think> 标签
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
                    self.logger.warning(f"过滤<think>标签后内容为空，原始响应: {message.content[:100] if message.content else ''}")
            
            result = LLMResponse(
                content=content,
                model=response.model,
                provider=self.provider_name,
                finish_reason=choice.finish_reason,
                usage=TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens
                ),
                tool_calls=message.tool_calls if hasattr(message, 'tool_calls') else None,
                raw_response=response
            )
            
            self._log_response(result)
            self.logger.info(f"DashScope请求成功，耗时: {elapsed_time:.2f}s")
            
            return result
            
        except AuthenticationError as e:
            raise LLMAuthenticationError(
                provider=self.provider_name,
                message="API密钥无效或已过期",
                original_error=e
            )
        except RateLimitError as e:
            raise LLMRateLimitError(
                provider=self.provider_name,
                message="请求频率超限，请稍后重试",
                original_error=e
            )
        except APIError as e:
            # 增强错误日志：打印导致错误的消息序列
            self.logger.error(f"❌ DashScope API错误: {str(e)}")
            self.logger.error(f"请求的消息序列:")
            for i, msg in enumerate(params.get('messages', [])):
                role = msg.get('role', 'unknown')
                has_tool_calls = 'tool_calls' in msg
                has_tool_call_id = 'tool_call_id' in msg
                content = msg.get('content', '')[:100] if msg.get('content') else '(空)'
                
                log_msg = f"  [{i+1}] {role}"
                if has_tool_calls:
                    tool_calls_info = []
                    for tc in msg.get('tool_calls', []):
                        tc_id = tc.get('id', 'no-id')
                        tc_func = tc.get('function', {}).get('name', 'unknown')
                        tool_calls_info.append(f"{tc_func}(id={tc_id})")
                    log_msg += f" + tool_calls=[{', '.join(tool_calls_info)}]"
                elif has_tool_call_id:
                    log_msg += f" + tool_call_id={msg['tool_call_id']}"
                else:
                    log_msg += f": {content}"
                
                self.logger.error(log_msg)
            
            raise LLMAPIError(
                provider=self.provider_name,
                status_code=getattr(e, 'status_code', 500),
                message=str(e),
                original_error=e
            )
        except Exception as e:
            raise self._handle_error(e, "DashScope聊天完成失败")
    
    def stream_completion(self, request: LLMRequest) -> Iterator[StreamChunk]:
        """流式聊天完成"""
        if not self.is_available():
            raise LLMProviderError(
                provider=self.provider_name,
                message="Provider不可用，请检查API密钥配置"
            )
        
        self._log_request(request)
        
        try:
            # 准备请求参数
            params = request.to_openai_format()
            params["stream"] = True
            if not params.get("model"):
                raise LLMProviderError(
                    provider=self.provider_name,
                    message="必须指定模型名称"
                )
            
            # 调用流式API
            stream = self.client.chat.completions.create(**params)
            
            for chunk in stream:
                if chunk.choices:
                    choice = chunk.choices[0]
                    delta = choice.delta
                    
                    yield StreamChunk(
                        content=delta.content or "",
                        finish_reason=choice.finish_reason,
                        tool_calls=delta.tool_calls if hasattr(delta, 'tool_calls') else None
                    )
                    
        except Exception as e:
            raise self._handle_error(e, "DashScope流式完成失败")
    
    def embedding(self, texts: List[str], model: Optional[str] = None) -> EmbeddingResponse:
        """
        文本向量化
        
        注意：DashScope的embedding需要使用专门的endpoint
        这里提供基本实现，实际使用时可能需要调整
        """
        if not self.is_available():
            raise LLMProviderError(
                provider=self.provider_name,
                message="Provider不可用"
            )
        
        # DashScope embedding实现
        # 注意：这里需要根据实际的DashScope embedding API进行调整
        raise NotImplementedError("DashScope embedding功能待实现，请使用Ollama进行向量化")
    
    def is_available(self) -> bool:
        """检查Provider是否可用"""
        return self._initialized and self.client is not None
