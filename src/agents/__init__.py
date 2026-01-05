"""Agents package exports."""

from .registry import create_agent
from .agent_manager import AgentsModule

# 统一基类导出
from .base_classes import (
    # 响应数据类和枚举
    AgentResponse,
    AgentStatus,
    
    # 抽象基类
    SimpleAgentBase,
    SessionAgentBase,
    ToolAgentBase,
)

from src.core.events import IAgent

__all__ = [
    # 响应类型
    "AgentResponse",
    "AgentStatus",
    
    # 协议和基类
    "IAgent",
    "BaseAgent",
    "SimpleAgentBase",
    "SessionAgentBase", 
    "ToolAgentBase",
    
    # 别名（向后兼容）
    "SimpleAgent",
    "SessionAwareAgent",
    
    # 工具函数
    "create_agent",
    "AgentsModule",
]
