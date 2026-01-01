"""Agent base classes and response types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol


@dataclass
class AgentResponse:
    """Standard response returned by concrete agents."""

    agent: str
    success: bool
    query: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(Protocol):
    """Protocol for all agents."""

    name: str
    description: str
    capabilities: list[str]

    def handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Generate a response for the incoming query."""
        ...
