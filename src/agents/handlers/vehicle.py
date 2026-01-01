"""Vehicle control agent."""
from __future__ import annotations

from typing import Dict, Any, Optional

from src.agents.base import AgentResponse
from src.core.events import AgentContext


class VehicleControlAgent:
    name = "vehicle_control_agent"

    def __init__(self, description: str, capabilities: list[str]):
        self.description = description
        self.capabilities = capabilities

    def handle(self, query: str, context: AgentContext  = None) -> AgentResponse:
        q = query.lower()
        if "窗" in q or "window" in q:
            message = "车窗已调整，注意外面的风哦。"
        elif "空调" in q or "ac" in q:
            message = "空调温度已设为23℃，让你保持舒适。"
        elif "座椅" in q:
            message = "座椅位置已微调，坐姿更放松。"
        else:
            message = "车辆控制中心已待命，可以帮你调节空调、座椅或车窗。"
        return AgentResponse(agent=self.name, success=True, query=query, message=message, data={"action": "vehicle_control"})
