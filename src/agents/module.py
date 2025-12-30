"""
Agents module implementation moved under `src.agents`.
This file contains the IModule-compatible wrapper that loads agent
configurations and instantiates agent handlers from `src.agents.registry`.
"""
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.core.interfaces import IModule
from src.core.events import Event, EventType
from src.agents.registry import create_agent
from src.agents.base import AgentResponse


class AgentsModule(IModule):
    """Agents module - provides available agents to the system.

    This is the same implementation previously located at
    `src/modules/agents_module.py`, moved here so that all agent
    implementations live under `src.agents`.
    """

    def __init__(self, config_path: str = "config/agents_config.yaml"):
        self._name = "agents"
        self._running = False
        self._agents: List[Dict[str, Any]] = []
        self._config_path = config_path
        self._agent_handlers: Dict[str, Any] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_running(self) -> bool:
        return self._running

    def initialize(self) -> bool:
        """Initialize by loading agents from YAML config."""
        try:
            config_file = Path(self._config_path)
            if not config_file.exists():
                print(f"❌ Agent配置文件不存在: {self._config_path}")
                return False

            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            self._agents = config.get('agents', [])
            print(f"✅ Agents模块初始化: 加载了 {len(self._agents)} 个Agent")

            for agent in self._agents:
                status = "✓" if agent.get('enabled', True) else "✗"
                print(f"   {status} {agent['name']}: {agent['description']}")
                if agent.get('enabled', True):
                    handler = create_agent(
                        name=agent.get('name'),
                        description=agent.get('description', ''),
                        capabilities=agent.get('capabilities', [])
                    )
                    self._agent_handlers[handler.name] = handler

            return True

        except Exception as e:
            print(f"❌ Agents模块初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def start(self) -> bool:
        """Start the module."""
        self._running = True
        print("✅ Agents模块启动成功")
        return True

    def stop(self):
        """Stop the module."""
        self._running = False
        print("🛑 Agents模块已停止")

    def cleanup(self):
        """Cleanup resources."""
        self._agents.clear()
        self._agent_handlers.clear()

    def handle_event(self, event: Event):
        """Handle events - AgentsModule does not process events by default."""
        pass

    # ==================== Agents data access API ====================

    def get_available_agents(self) -> List[Dict[str, Any]]:
        return [agent for agent in self._agents if agent.get('enabled', True)]

    def get_all_agents(self) -> List[Dict[str, Any]]:
        return self._agents.copy()

    def get_agent_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        for agent in self._agents:
            if agent.get('name') == name:
                return agent.copy()
        return None

    def execute_agent(self, agent_name: str, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        handler = self._agent_handlers.get(agent_name)
        if not handler:
            message = f"Agent {agent_name} 未启用或不存在，已忽略请求。"
            return AgentResponse(agent=agent_name, success=False, message=message, data={})
        return handler.handle(query=query, context=context or {})

    def get_statistics(self) -> Dict[str, Any]:
        enabled_count = sum(1 for a in self._agents if a.get('enabled', True))
        return {
            'total_agents': len(self._agents),
            'enabled_agents': enabled_count,
            'disabled_agents': len(self._agents) - enabled_count,
            'agent_count': enabled_count
        }
