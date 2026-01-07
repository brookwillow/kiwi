"""Agent registry for mapping configuration to concrete classes."""
from __future__ import annotations

from typing import Dict, Type

from src.core.types import IAgent
from src.agents.handlers.music import MusicAgent
from src.agents.handlers.navigation import NavigationAgent
from src.agents.handlers.vehicle import VehicleControlAgent
from src.agents.handlers.weather import WeatherAgent
from src.agents.handlers.chat import ChatAgent
from src.agents.handlers.phone import PhoneAgent
from src.agents.handlers.planner import PlannerAgent
from src.agents.handlers.system import SystemAgent


class GenericAgent:
    """Fallback agent that simply echoes the query."""

    def __init__(self, name: str, description: str, capabilities: list[str],
                 priority: int = 2):
        self.name = name
        self.description = description
        self.capabilities = capabilities
        self.priority = priority
        self.interruptible = (priority < 3)

    def handle(self, query: str, context=None):
        from src.agents.base_classes import AgentResponse
        from src.core.events import AgentStatus

        message = f"{self.description} 已收到: {query}"
        return AgentResponse(agent=self.name, status=AgentStatus.COMPLETED, query=query, message=message)


def get_agent_class(name: str):
    registry: Dict[str, Type[IAgent]] = {
        "music_agent": MusicAgent,
        "navigation_agent": NavigationAgent,
        "vehicle_control_agent": VehicleControlAgent,
        "weather_agent": WeatherAgent,
        "chat_agent": ChatAgent,
        "phone_agent": PhoneAgent,
        "planner_agent": PlannerAgent,
        "system_agent": SystemAgent,
    }
    return registry.get(name)

def create_agent(name: str, description: str, capabilities: list[str], 
                priority: int = 2, api_key: str = None) -> IAgent:
    cls = get_agent_class(name)
    if cls:
        return cls(description=description, capabilities=capabilities, 
                  priority=priority, api_key=api_key)
    return GenericAgent(name=name, description=description, capabilities=capabilities,
                       priority=priority)
