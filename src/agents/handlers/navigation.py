"""Navigation agent implementation."""
from __future__ import annotations

from typing import Dict, Any, Optional

from src.agents.base import AgentResponse
from src.core.events import AgentContext


class NavigationAgent:
    name = "navigation_agent"

    def __init__(self, description: str, capabilities: list[str]):
        self.description = description
        self.capabilities = capabilities

    def handle(self, query: str, context: AgentContext  = None) -> AgentResponse:
        message = "已为你规划一条避开拥堵的路线，预计30分钟到达。"
        if "最快" in query or "快速" in query:
            message = "已切换至最快路线，预计25分钟到达。"
        elif "风景" in query or "景色" in query:
            message = "选择了一条沿途风景优美的路线，放松一下吧。"
        return AgentResponse(
            agent=self.name,
            success=True,
            query=query,
            message=message,
            data={"eta_minutes": 25 if "最快" in query else 30}
        )
