"""
Orchestrator - 编排者模块
负责接收用户查询，召回上下文，决策选择Agent
通过SystemController获取其他模块的数据
支持会话管理和多轮对话
"""
import time
from typing import Optional, Dict, Any, TYPE_CHECKING, Tuple
from src.core.events import OrchestratorContext, OrchestratorInput, OrchestratorDecision, QueryType, SystemState, AgentInfo
from .llm_decision import LLMDecisionMaker, MockLLMDecisionMaker
from src.core.events import ShortTermMemory, LongTermMemory
from src.core.session_manager import get_session_manager

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
        
        # 获取会话管理器
        self.session_manager = get_session_manager()
        
        self._statistics = {
            "total_queries": 0,
            "successful_decisions": 0,
            "failed_decisions": 0
        }
    
    def process_query(self, query_content: str, 
                     query_type: QueryType = QueryType.USER_QUERY,
                     metadata: Optional[Dict[str, Any]] = None) -> OrchestratorDecision:
        """
        处理查询（支持会话恢复）
        
        Args:
            query_content: 查询内容
            query_type: 查询类型
            metadata: 元数据
            
        Returns:
            决策结果
        """
        try:
            self._statistics["total_queries"] += 1
            
            # 1. 检查是否有活跃会话在等待输入
            # 注意：如果没有活跃会话或会话不在waiting_input状态，会直接跳到步骤2继续处理
            active_session = self.session_manager.get_active_session()
            if active_session:
                print(f"[SessionManager] {active_session.session_id}, {active_session.state}")
            if active_session and active_session.state == "waiting_input":
                # 判断用户输入是回答问题还是新的意图
                intent_type = self._classify_user_intent(
                    query_content,
                    active_session.pending_prompt or "",
                    active_session.expected_input_type or "text"
                )
                
                if intent_type == "answer":
                    # 用户在回答问题，恢复原会话
                    print(f"🔄 用户回答问题，恢复会话 {active_session.session_id} ({active_session.agent_name})")
                    self.session_manager.resume_session(active_session.session_id, query_content)
                    
                    return OrchestratorDecision(
                        selected_agent=active_session.agent_name,
                        confidence=1.0,
                        reasoning="恢复之前的会话",
                        parameters={
                            # 标准化的会话信息
                            'session_id': active_session.session_id,
                            'session_action': 'resume',  # 会话动作
                            # 恢复会话特有的信息
                            'user_input': query_content,  # 用户的回答
                            'context': active_session.context,  # 会话上下文
                            'previous_prompt': active_session.pending_prompt  # 之前的提问
                        },
                        metadata={
                            'session_id': active_session.session_id,
                            'session_action': 'resume'
                        }
                    )
            
            # 2. 构建输入
            orchestrator_input = OrchestratorInput(
                query_type=query_type,
                query_content=query_content,
                timestamp=time.time(),
                metadata=metadata or {}
            )
            
            # 3. 从memory模块召回短期记忆（对话历史）
            short_term_memories = self._get_short_term_memories(query_content)
            
            # 4. 从memory模块召回长期记忆（用户画像）
            long_term_memory = self._get_long_term_memory()
            
            # 5. 从perception模块召回系统状态
            system_states = self._get_system_states(query_content)
            
            # 6. 从agents模块获取可用Agents
            available_agents = self._get_available_agents()
            
            # 7. 构建上下文
            context = OrchestratorContext(
                input_query=orchestrator_input,
                short_term_memories=short_term_memories,
                long_term_memory=long_term_memory,
                system_states=system_states,
                available_agents=available_agents
            )
            
            # 8. LLM决策
            decision = self.decision_maker.make_decision(context)
            
            # 9. 在orchestrator中创建新会话
            # 获取选中 Agent 的优先级
            selected_agent_priority = 2  # 默认优先级
            for agent_info in available_agents:
                if agent_info.name == decision.selected_agent:
                    selected_agent_priority = agent_info.priority
                    break
            
            # 创建新会话并获取session_id
            session = self.session_manager.create_session(
                agent_name=decision.selected_agent,
                priority=selected_agent_priority
            )

            if not session:
                # 不允许打断，提醒用户
                return OrchestratorDecision(
                    selected_agent="system_agent",
                    confidence=1.0,
                    reasoning="当前会话不允许被打断",
                    parameters={
                        'response': f"当前正在执行{active_session.agent_name}，请先完成当前操作。"
                    },
                    metadata={'session_id': active_session.session_id}
                )

            elif session :
                # 将标准化的会话信息传递给agent
                decision.parameters.update({
                    # 标准化的会话信息
                    'session_id': session.session_id,
                    'session_action': 'new',  # 会话动作
                    # 新会话特有的信息
                    'priority': selected_agent_priority
                })
                
                decision.metadata.update({
                    'session_id': session.session_id,
                    'session_action': 'new',
                    'priority': selected_agent_priority
                })
            
                print(f"🆕 创建新会话: {session.session_id} (Agent: {decision.selected_agent}, Priority: {selected_agent_priority})")
            
            # 10. 更新统计
            if decision.confidence > 0.5:
                self._statistics["successful_decisions"] += 1
            else:
                self._statistics["failed_decisions"] += 1
            
            # 11. 输出决策信息
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
            import traceback
            traceback.print_exc()
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
        从 memory模块获取短期记忆（优先使用语义检索）
        
        Args:
            query: 查询内容（用于语义相似度检索）
            max_count: 最大返回数量
            
        Returns:
            短期记忆列表
        """
        memory_module = self.controller.get_module('memory')
        if memory_module:
            # 优先尝试语义检索
            if hasattr(memory_module, 'get_related_memories'):
                return memory_module.get_related_memories(query, max_count)
            # 降级为时间顺序检索
            elif hasattr(memory_module, 'get_short_term_memories'):
                return memory_module.get_short_term_memories(max_count)
        return []
    
    def _classify_user_intent(self, query: str, previous_prompt: str, 
                             expected_type: str) -> str:
        """
        使用LLM判断用户意图类型
        
        Args:
            query: 用户输入
            previous_prompt: 之前的问题
            expected_type: 期望的回答类型
            
        Returns:
            "answer": 用户在回答之前的问题
            "new_intent": 用户提出了新的请求
        """
        try:
            # 如果没有使用真实LLM，使用简单规则判断
            if isinstance(self.decision_maker, MockLLMDecisionMaker):
                return self._simple_intent_classification(query, expected_type)
            
            # 使用LLM判断
            system_prompt = """你是一个意图分类专家。
用户刚才被问了一个问题，现在给出了回复。
请判断用户的回复是：
1. "answer" - 回答之前的问题
2. "new_intent" - 提出了新的、不相关的请求

只返回 answer 或 new_intent，不要其他内容。"""

            user_prompt = f"""之前的问题：{previous_prompt}
期望的回答类型：{expected_type}

用户的回复：{query}

请判断用户的意图类型："""

            response = self.decision_maker.client.chat.completions.create(
                model=self.decision_maker.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            result = response.choices[0].message.content.strip().lower()
            
            if "new_intent" in result or "new" in result:
                return "new_intent"
            else:
                return "answer"
                
        except Exception as e:
            print(f"⚠️  意图分类失败: {e}")
            # 默认认为是回答
            return "answer"
    
    def _simple_intent_classification(self, query: str, expected_type: str) -> str:
        """
        简单的意图分类（基于规则）
        
        Args:
            query: 用户输入
            expected_type: 期望的回答类型
            
        Returns:
            意图类型
        """
        # 常见的新意图关键词
        new_intent_keywords = [
            "打开", "关闭", "播放", "停止", "导航", "去", "到",
            "设置", "调节", "查询", "帮我", "我要", "请"
        ]
        
        # 如果包含明显的新意图关键词
        for keyword in new_intent_keywords:
            if keyword in query:
                return "new_intent"
        
        # 如果是简短回答，通常是回答问题
        if len(query) < 10:
            return "answer"
        
        # 默认认为是回答
        return "answer"
    
    def _get_long_term_memory(self):
        """
        从memory模块获取长期记忆
        
        Returns:
            长期记忆（如果存在）
        """
        memory_module = self.controller.get_module('memory')
        if memory_module and hasattr(memory_module, 'get_related_long_term_memory'):
            return memory_module.get_related_long_term_memory()
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
        agents_module = self.controller.get_module('agent_adapter')
        if agents_module and hasattr(agents_module, 'get_available_agents'):
            agents = agents_module.get_available_agents()
            return [
                AgentInfo(
                    name=agent.get('name', ''),
                    description=agent.get('description', ''),
                    capabilities=agent.get('capabilities', []),
                    priority=agent.get('priority', 1),
                    enabled=agent.get('enabled', True),
                    metadata=agent.get('metadata', {})
                )
                for agent in agents
            ]
        return []
    
    
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

