"""Vehicle control agent."""
from __future__ import annotations

from typing import Dict, Any, Optional

from src.agents.base_classes import AgentResponse, ToolAgentBase
from src.core.types import AgentContext
from src.execution.tool_registry import ToolCategory


class VehicleControlAgent(ToolAgentBase):
    name = "vehicle_control_agent"

    def __init__(self, description: str, capabilities: list[str],
                 priority: int = 2, api_key: Optional[str] = None):
        super().__init__(
            name=self.name,
            description=description,
            capabilities=capabilities,
            tool_categories=[
                ToolCategory.VEHICLE_CONTROL,
                ToolCategory.CLIMATE,
                ToolCategory.WINDOW,
                ToolCategory.SEAT,
                ToolCategory.LIGHTING,
                ToolCategory.DOOR,
                ToolCategory.INFORMATION  # 添加信息查询类别，支持状态查询
            ],  # 车辆控制相关的所有工具
            priority=priority,
            api_key=api_key
        )
