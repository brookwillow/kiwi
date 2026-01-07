"""Phone agent implementation."""
from __future__ import annotations

from typing import Dict, Any, Optional

from src.agents.base_classes import AgentResponse, ToolAgentBase
from src.core.types import AgentContext
from src.execution.tool_registry import ToolCategory

class PhoneAgent(ToolAgentBase):
    name = "phone_agent"

    def __init__(self, description: str, capabilities: list[str],
                 priority: int = 2, api_key: Optional[str] = None):
        super().__init__(
            name=self.name,
            description=description,
            capabilities=capabilities,
            tool_categories=[
                ToolCategory.COMMUNICATION,  # 通信系统工具
                ToolCategory.INFORMATION      # 添加信息查询类别，支持状态查询
            ],
            priority=priority,
            api_key=api_key
        )
