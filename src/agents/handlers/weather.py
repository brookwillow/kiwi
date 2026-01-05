"""Weather agent implementation."""
from __future__ import annotations

from typing import Dict, Any, Optional

from src.agents.base_classes import AgentResponse, ToolAgentBase
from src.core.events import AgentContext
from src.execution.tool_registry import ToolCategory


class WeatherAgent(ToolAgentBase):
    name = "weather_agent"

    def __init__(self, description: str, capabilities: list[str],
                 priority: int = 2, api_key: Optional[str] = None):
        super().__init__(
            name=self.name,
            description=description,
            capabilities=capabilities,
            tool_categories=[ToolCategory.INFORMATION],  # 天气相关工具
            priority=priority,
            api_key=api_key
        )
