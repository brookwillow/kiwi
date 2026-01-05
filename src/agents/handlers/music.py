"""Music agent implementation."""
from __future__ import annotations

from typing import Dict, Any, Optional

from src.agents.base_classes import AgentResponse, ToolAgentBase
from src.core.events import AgentContext
from src.execution.tool_registry import ToolCategory


class MusicAgent(ToolAgentBase):
    name = "music_agent"

    def __init__(self, description: str, capabilities: list[str], 
                 priority: int = 2, api_key: Optional[str] = None):
        super().__init__(
            name=self.name,
            description=description,
            capabilities=capabilities,
            tool_categories=[
                ToolCategory.ENTERTAINMENT,
                ToolCategory.INFORMATION  # 添加信息查询类别，支持音乐和娱乐系统状态查询
            ],
            priority=priority,
            api_key=api_key
        )
