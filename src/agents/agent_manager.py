"""
Agents Manager - 负责Agent的加载、配置和执行

这是一个纯业务逻辑类，不继承IModule接口
事件处理由agent_adapter负责
"""
import yaml
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.agents.registry import create_agent
from src.agents.base import AgentResponse
from src.core.events import AgentContext, SystemState


class AgentsModule:
    """
    Agents Manager - 管理所有Agent的加载和执行
    
    职责：
    - 加载Agent配置
    - 实例化Agent handlers
    - 召回记忆和构建上下文
    - 执行Agent并返回响应
    
    注意：不处理事件，所有事件由agent_adapter处理
    """

    def __init__(self, controller, config_path: str = "config/agents_config.yaml"):
        self.controller = controller
        self._agents: List[Dict[str, Any]] = []
        self._config_path = config_path
        self._agent_handlers: Dict[str, Any] = {}

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

            # Get API key from environment
            import os
            api_key = os.getenv('DASHSCOPE_API_KEY')
            if not api_key:
                print("⚠️  未设置DASHSCOPE_API_KEY环境变量，智能工具调用功能将不可用")

            for agent in self._agents:
                status = "✓" if agent.get('enabled', True) else "✗"
                print(f"   {status} {agent['name']}: {agent['description']}")
                if agent.get('enabled', True):
                    handler = create_agent(
                        name=agent.get('name'),
                        description=agent.get('description', ''),
                        capabilities=agent.get('capabilities', []),
                        api_key=api_key
                    )
                    self._agent_handlers[handler.name] = handler
            
            # 为planner_agent设置可用的agents信息
            planner = self._agent_handlers.get('planner_agent')
            if planner:
                agents_info = {}
                for agent_name, handler in self._agent_handlers.items():
                    if agent_name != 'planner_agent':
                        agent_config = self.get_agent_by_name(agent_name)
                        if agent_config:
                            agents_info[agent_name] = {
                                'description': agent_config.get('description', ''),
                                'capabilities': agent_config.get('capabilities', [])
                            }
                planner.set_available_agents(agents_info)
                print(f"✅ PlannerAgent已配置，可协调{len(agents_info)}个agents")

            return True

        except Exception as e:
            print(f"❌ Agents模块初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False

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
    
    def _get_recent_memories(self, max_count: int = 5):
        """
        从 memory模块获取最近的短期记忆（按时间顺序）
        
        Args:
            max_count: 最大返回数量
            
        Returns:
            短期记忆列表
        """
        memory_module = self.controller.get_module('memory')
        if memory_module and hasattr(memory_module, 'get_short_term_memories'):
            return memory_module.get_short_term_memories(max_count)
        return []
    
    def _get_related_memories(self, query: str, max_count: int = 3):
        """
        从 memory模块基于语义相似度获取相关记忆
        
        Args:
            query: 查询内容（用于语义相似度检索）
            max_count: 最大返回数量
            
        Returns:
            短期记忆列表
        """
        memory_module = self.controller.get_module('memory')
        if memory_module and hasattr(memory_module, 'get_related_short_term_memory'):
            return memory_module.get_related_short_term_memory(query, max_count)
        return []
    
    def _get_long_term_memory(self,query: str = ""):
        """
        从memory模块获取长期记忆
        
        Returns:
            长期记忆（如果存在）
        """
        memory_module = self.controller.get_module('memory')
        if memory_module and hasattr(memory_module, 'get_related_long_term_memory'):
            return memory_module.get_related_long_term_memory(query)
        return None
    
    def _get_system_states(self, query: str):
        """
        从perception模块获取系统状态
        
        Args:
            query: 查询内容
            
        Returns:
            系统状态列表
        """
        # 通过controller获取perception模块
        perception_module = self.controller.get_module('perception')
        if perception_module and hasattr(perception_module, 'get_all_states'):
            states = perception_module.get_all_states()
            return [
                SystemState(
                    state_type=state.get('type', 'unknown'),
                    state_data=state.get('data', {}),
                    timestamp=state.get('timestamp', time.time())
                )
                for state in states
            ]
        return []
    
    def get_agent_context(self, query:str, agent_name: str) -> AgentContext:
        """
        为agent构建上下文，统一召回记忆
        
        Args:
            query: 用户查询
            agent_name: Agent名称
            
        Returns:
            AgentContext对象，包含所有相关记忆和上下文
        """
        agent = self.get_agent_by_name(agent_name)
        if not agent:
            return AgentContext(
                recent_memories=[],
                related_memories=[],
                long_term_memory=None,
                system_states=[]
            )
        
        agent_info = {
            'name': agent.get('name', ''),
            'description': agent.get('description', ''),
            'capabilities': agent.get('capabilities', []),
        }

        print(f"\n📚 [记忆召回] 为 {agent_name} 准备上下文...")
        
        # 1. 获取最近的短期记忆（按时间顺序）
        recent_memories = self._get_recent_memories(max_count=5)
        print(f"   ✅ 最近记忆: {len(recent_memories)} 条")
        
        # 2. 基于语义相似度获取相关短期记忆
        related_memories = self._get_related_memories(query, max_count=3)
        print(f"   ✅ 相关记忆: {len(related_memories)} 条")
        
        # 3. 从 memory模块召回长期记忆（用户画像）
        long_term_memory = self._get_long_term_memory(query)
        if long_term_memory:
            print(f"   ✅ 长期记忆: 已加载")
            if long_term_memory.user_profile:
                print(f"      - 用户画像: {len(long_term_memory.user_profile)} 个字段")
            if long_term_memory.preferences:
                print(f"      - 用户偏好: {len(long_term_memory.preferences)} 个字段")
        else:
            print(f"   ⚠️  长期记忆: 未找到")
            
        # 4. 从 perception模块召回系统状态
        system_states = self._get_system_states(query)
        print(f"   ✅ 系统状态: {len(system_states)} 条\n")
        
        context = AgentContext(
            recent_memories=recent_memories,
            related_memories=related_memories,
            long_term_memory=long_term_memory,
            system_states=system_states
        )
        
        # 5. 发送记忆召回事件到GUI（已禁用，显示效果不好）
        # self._send_memory_recall_event(agent_name, context)

        return context
    
    def _send_memory_recall_event(self, agent_name: str, context: AgentContext):
        """发送记忆召回事件到GUI用于显示
        
        Args:
            agent_name: Agent名称
            context: Agent上下文
        """
        try:
            from src.core.events import Event, EventType
            event = Event.create(
                event_type=EventType.GUI_UPDATE_TEXT,
                source='agent_manager',
                data={
                    'event_type': 'memory_recall',
                    'agent_name': agent_name,
                    'recent_memories': [
                        {
                            'query': m.query,
                            'response': m.response,
                            'timestamp': m.timestamp,
                            'agent': m.agent
                        } for m in context.recent_memories
                    ],
                    'related_memories': [
                        {
                            'query': m.query,
                            'response': m.response,
                            'timestamp': m.timestamp,
                            'agent': m.agent
                        } for m in context.related_memories
                    ],
                    'long_term_memory': {
                        'summary': context.long_term_memory.summary if context.long_term_memory else '',
                        'profile': context.long_term_memory.user_profile if context.long_term_memory else {},
                        'preferences': context.long_term_memory.preferences if context.long_term_memory else {}
                    }
                }
            )
            self.controller.publish_event(event)
        except Exception as e:
            print(f"⚠️ 发送记忆召回事件失败: {e}")

    def execute_agent(self, agent_name: str, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        handler = self._agent_handlers.get(agent_name)
        if not handler:
            message = f"Agent {agent_name} 未启用或不存在，已忽略请求。"
            return AgentResponse(agent=agent_name, success=False, query=query, message=message, data={})
        
        # 获取agent context
        agent_context = self.get_agent_context(query=query, agent_name=agent_name)
        
        # 为planner_agent传递agent_manager引用（通过扩展context）
        if agent_name == "planner_agent":
            # 将AgentContext转换为dict并添加agent_manager
            context_dict = {
                "short_term_memories": agent_context.short_term_memories,
                "long_term_memory": agent_context.long_term_memory,
                "system_states": agent_context.system_states,
                "agent_manager": self
            }
            return handler.handle(query=query, context=context_dict)
        
        return handler.handle(query=query, context=agent_context)

    def get_statistics(self) -> Dict[str, Any]:
        enabled_count = sum(1 for a in self._agents if a.get('enabled', True))
        return {
            'total_agents': len(self._agents),
            'enabled_agents': enabled_count,
            'disabled_agents': len(self._agents) - enabled_count,
            'agent_count': enabled_count
        }
