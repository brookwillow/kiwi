"""
LLM模块类型定义

定义统一的消息、请求、响应格式
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Iterator
from enum import Enum


class LLMProvider(str, Enum):
    """支持的LLM提供商"""
    DASHSCOPE = "dashscope"
    OLLAMA = "ollama"
    OPENAI = "openai"


class MessageRole(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class LLMMessage:
    """统一的消息格式"""
    role: str  # system/user/assistant/tool
    content: str
    name: Optional[str] = None  # 用于tool消息
    tool_calls: Optional[List[Dict[str, Any]]] = None  # function calling响应
    tool_call_id: Optional[str] = None  # 用于tool响应消息，关联到assistant的tool_calls
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "role": self.role,
            "content": self.content
        }
        if self.name:
            result["name"] = self.name
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMMessage':
        """从字典创建消息"""
        return cls(
            role=data["role"],
            content=data["content"],
            name=data.get("name"),
            tool_calls=data.get("tool_calls"),
            tool_call_id=data.get("tool_call_id")
        )


@dataclass
class LLMRequest:
    """统一的LLM请求格式"""
    messages: List[LLMMessage]
    model: Optional[str] = None  # 可选，覆盖默认模型
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None  # function calling工具定义
    tool_choice: Optional[str] = None  # auto/none 或具体工具名
    stop: Optional[List[str]] = None
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    enable_thinking: bool = True  # 是否开启思考模式（某些模型支持）
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI格式的请求参数"""
        params = {
            "messages": [msg.to_dict() for msg in self.messages],
            "temperature": self.temperature,
            "top_p": self.top_p,
            "stream": self.stream,
        }
        
        if self.model:
            params["model"] = self.model
        if self.max_tokens:
            params["max_tokens"] = self.max_tokens
        if self.tools:
            params["tools"] = self.tools
        if self.tool_choice:
            params["tool_choice"] = self.tool_choice
        if self.stop:
            params["stop"] = self.stop
        if self.presence_penalty != 0:
            params["presence_penalty"] = self.presence_penalty
        if self.frequency_penalty != 0:
            params["frequency_penalty"] = self.frequency_penalty
            
        return params


@dataclass
class TokenUsage:
    """Token使用统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> 'TokenUsage':
        """从字典创建"""
        if not data:
            return cls()
        return cls(
            prompt_tokens=data.get("prompt_tokens", 0),
            completion_tokens=data.get("completion_tokens", 0),
            total_tokens=data.get("total_tokens", 0)
        )


@dataclass
class LLMResponse:
    """统一的LLM响应格式"""
    content: str
    model: str
    provider: str
    finish_reason: str
    usage: TokenUsage
    tool_calls: Optional[List[Dict[str, Any]]] = None  # function calling结果
    raw_response: Optional[Any] = None  # 原始响应（调试用）
    
    @property
    def has_tool_calls(self) -> bool:
        """是否包含工具调用"""
        return self.tool_calls is not None and len(self.tool_calls) > 0


@dataclass
class StreamChunk:
    """流式响应的数据块"""
    content: str
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


@dataclass
class EmbeddingResponse:
    """向量化响应"""
    embeddings: List[List[float]]
    model: str
    provider: str
    usage: TokenUsage
    
    @property
    def dimension(self) -> int:
        """向量维度"""
        return len(self.embeddings[0]) if self.embeddings else 0
