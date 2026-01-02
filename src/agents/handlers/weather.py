"""Weather agent implementation."""
from __future__ import annotations

from typing import Dict, Any, Optional

from src.agents.base import AgentResponse
from src.core.events import AgentContext
from src.execution.tool_registry import ToolCategory
from .base_tool_agent import BaseToolAgent


class WeatherAgent(BaseToolAgent):
    name = "weather_agent"

    def __init__(self, description: str, capabilities: list[str], api_key: Optional[str] = None):
        super().__init__(
            name=self.name,
            description=description,
            capabilities=capabilities,
            tool_categories=[ToolCategory.INFORMATION],  # 天气相关工具
            api_key=api_key
        )
