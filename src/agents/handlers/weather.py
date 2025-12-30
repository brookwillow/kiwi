"""Weather agent implementation."""
from __future__ import annotations

from typing import Dict, Any, Optional

from src.agents.base import AgentResponse


class WeatherAgent:
    name = "weather_agent"

    def __init__(self, description: str, capabilities: list[str]):
        self.description = description
        self.capabilities = capabilities

    def handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        location = "当前所在地"
        if "北京" in query:
            location = "北京"
        elif "上海" in query:
            location = "上海"
        message = f"{location}现在气温22℃，微风，稍晚可能有阵雨，记得带伞。"
        return AgentResponse(agent=self.name, success=True, message=message, data={"location": location})
