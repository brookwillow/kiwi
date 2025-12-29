"""
Orchestrator - 编排者模块
负责接收用户查询，召回上下文，决策选择Agent
通过SystemController获取其他模块的数据
"""
import time
from typing import Optional, Dict, Any, TYPE_CHECKING

from .types import (
    QueryType, OrchestratorInput, OrchestratorContext, 
    OrchestratorDecision, ShortTermMemory, SystemState, AgentInfo
)
from .llm_decision import LLMDecisionMaker, MockLLMDecisionMaker

if TYPE_CHECKING:
    from ..core.controller import SystemController


class Orchestrator:
    """编排者"""
    
    def __init__(self, 
                 controller: 'SystemController',
                 llm_api_key: Optional[str] = None,
                 use_mock_llm: bool = False):
        """
        初始化Orchestrator
        
        Args:
            controller: 系统控制器
            llm_api_key: LLM API密钥
            use_mock_llm: 是否使用模拟LLM
        """
        self.controller = controller
        
        # 初始化LLM决策器
        if use_mock_llm or not llm_api_key:
            print("⚠️  使用模拟LLM决策器")
            self.decision_maker = MockLLMDecisionMaker()
        else:
            print("✅ 使用阿里百炼LLM决策器")
            self.decision_maker = LLMDecisionMaker(api_key=llm_api_key)
        
        self._statistics = {
            "total_queries": 0,
            "successful_decisions": 0,
            "failed_decisions": 0
        }
    
    def process_query(self, query_content: str, 
                     query_type: QueryType = QueryType.USER_QUERY,
                     metadata: Optional[Dict[str, Any]] = None) -> OrchestratorDecision:
        """
        处理查询
        
        Args:
            query_content: 查询内容
            query_type: 查询类型
            metadata: 元数据
            
        Returns:
            决策结果
        """
        try:
            self._statistics["total_queries"] += 1
            
            # 1. 构建输入
            orchestrator_input = OrchestratorInput(
                query_type=query_type,
                query_content=query_content,
                timestamp=time.time(),
                metadata=metadata or {}
            )
            
            # 2. 从memory模块召回短期记忆（对话历史）
            short_term_memories = self._get_short_term_memories(query_content)
            
            # 3. 从memory模块召回长期记忆（用户画像）
            long_term_memory = self._get_long_term_memory()
            
            # 4. 从perception模块召回系统状态
            system_states = self._get_system_states(query_content)
            
            # 5. 从agents模块获取可用Agents
            available_agents = self._get_available_agents()
            
            # 6. 构建上下文
            context = OrchestratorContext(
                input_query=orchestrator_input,
                short_term_memories=short_term_memories,
                long_term_memory=long_term_memory,
                system_states=system_states,
                available_agents=available_agents
            )
            
            # 7. LLM决策
            decision = self.decision_maker.make_decision(context)
            
            # 8. 通知memory模块记录查询
            self._record_query(query_content, query_type)
            
            # 9. 更新统计
            if decision.confidence > 0.5:
                self._statistics["successful_decisions"] += 1
            else:
                self._statistics["failed_decisions"] += 1
            
            # 10. 输出决策信息
            print(f"\n{'='*60}")
            print(f"📊 Orchestrator 决策结果")
            print(f"{'='*60}")
            print(f"用户查询: {query_content}")
            print(f"选中Agent: {decision.selected_agent}")
            print(f"置信度: {decision.confidence:.2f}")
            print(f"决策理由: {decision.reasoning}")
            if decision.parameters:
                print(f"参数: {decision.parameters}")
            print(f"{'='*60}\n")
            
            return decision
            
        except Exception as e:
            print(f"❌ Orchestrator处理失败: {e}")
            self._statistics["failed_decisions"] += 1
            # 返回默认决策
            return OrchestratorDecision(
                selected_agent="chat_agent",
                confidence=0.1,
                reasoning=f"处理异常，降级到默认Agent: {str(e)}",
                parameters={},
                metadata={"error": str(e)}
            )
    
    def _get_short_term_memories(self, query: str, max_count: int = 5):
        """
        从memory模块获取短期记忆
        
        Args:
            query: 查询内容
            max_count: 最大返回数量
            
        Returns:
            短期记忆列表
        """
        # 通过controller获取memory模块
        memory_module = self.controller.get_module('memory')
        if memory_module and hasattr(memory_module, 'get_recent_conversations'):
            conversations = memory_module.get_recent_conversations(max_count)
            return [
                ShortTermMemory(
                    role=conv.get('role', 'user'),
                    content=conv.get('content', ''),
                    timestamp=conv.get('timestamp', time.time()),
                    metadata=conv.get('metadata', {})
                )
                for conv in conversations
            ]
        return []
    
    def _get_long_term_memory(self):
        """
        从memory模块获取长期记忆
        
        Returns:
            长期记忆（如果存在）
        """
        # 通过controller获取memory模块
        memory_module = self.controller.get_module('memory')
        if memory_module and hasattr(memory_module, 'get_user_profile'):
            profile = memory_module.get_user_profile()
            if profile:
                from .types import LongTermMemory
                return LongTermMemory(
                    summary=profile.get('summary', ''),
                    user_profile=profile.get('profile', {}),
                    preferences=profile.get('preferences', {}),
                    metadata=profile.get('metadata', {})
                )
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
    
    def _get_available_agents(self):
        """
        从agents模块获取可用Agents
        
        Returns:
            可用的Agent列表
        """
        # 通过controller获取agents模块
        agents_module = self.controller.get_module('agents')
        if agents_module and hasattr(agents_module, 'get_available_agents'):
            agents = agents_module.get_available_agents()
            return [
                AgentInfo(
                    name=agent.get('name', ''),
                    description=agent.get('description', ''),
                    capabilities=agent.get('capabilities', []),
                    enabled=agent.get('enabled', True),
                    metadata=agent.get('metadata', {})
                )
                for agent in agents
            ]
        return []
    
    def _record_query(self, query_content: str, query_type: QueryType):
        """
        记录查询到memory模块
        
        Args:
            query_content: 查询内容
            query_type: 查询类型
        """
        memory_module = self.controller.get_module('memory')
        if memory_module and hasattr(memory_module, 'add_conversation'):
            memory_module.add_conversation(
                role='user',
                content=query_content,
                metadata={'query_type': query_type.value, 'timestamp': time.time()}
            )
    
    def record_agent_response(self, agent_name: str, response: str):
        """
        记录Agent响应到memory模块
        
        Args:
            agent_name: Agent名称
            response: 响应内容
        """
        memory_module = self.controller.get_module('memory')
        if memory_module and hasattr(memory_module, 'add_conversation'):
            memory_module.add_conversation(
                role='assistant',
                content=response,
                metadata={'agent': agent_name, 'timestamp': time.time()}
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息
        """
        stats = {**self._statistics}
        
        # 从各个模块获取统计信息
        memory_module = self.controller.get_module('memory')
        if memory_module and hasattr(memory_module, 'get_statistics'):
            stats['memory'] = memory_module.get_statistics()
        
        perception_module = self.controller.get_module('perception')
        if perception_module and hasattr(perception_module, 'get_statistics'):
            stats['perception'] = perception_module.get_statistics()
        
        agents_module = self.controller.get_module('agents')
        if agents_module and hasattr(agents_module, 'get_statistics'):
            stats['agents'] = agents_module.get_statistics()
        
        return stats
    
    def reset(self):
        """重置Orchestrator"""
        self._statistics = {
            "total_queries": 0,
            "successful_decisions": 0,
            "failed_decisions": 0
        }

