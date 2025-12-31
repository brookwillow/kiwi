"""
LLM决策器 - 基于阿里百炼平台
负责调用大模型进行Agent选择决策
"""
import json
from typing import Dict, Any, Optional
from openai import OpenAI

from .types import OrchestratorContext, OrchestratorDecision


class LLMDecisionMaker:
    """LLM决策器"""
    
    def __init__(self, api_key: str, base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"):
        """
        初始化LLM决策器
        
        Args:
            api_key: API密钥
            base_url: API基础URL
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = "qwen-plus"  # 使用通义千问Plus模型
    
    def build_prompt(self, context: OrchestratorContext) -> str:
        """
        构建决策提示词
        
        Args:
            context: Orchestrator上下文
            
        Returns:
            决策提示词
        """
        # 构建可用Agents信息
        agents_info = []
        for agent in context.available_agents:
            agent_desc = {
                "name": agent.name,
                "description": agent.description,
                "capabilities": agent.capabilities
            }
            agents_info.append(agent_desc)
        
        # 构建短期记忆（对话历史）
        conversation_history = []
        for memory in context.short_term_memories:
            conversation_history.append({
                "role": memory.role,
                "content": memory.content
            })
        
        # 构建长期记忆
        long_term_info = ""
        if context.long_term_memory:
            long_term_info = f"""
用户画像和偏好：
- 摘要：{context.long_term_memory.summary}
- 用户信息：{json.dumps(context.long_term_memory.user_profile, ensure_ascii=False, indent=2)}
- 偏好设置：{json.dumps(context.long_term_memory.preferences, ensure_ascii=False, indent=2)}
"""
        
        # 构建系统状态
        system_states_info = []
        for state in context.system_states:
            system_states_info.append({
                "type": state.state_type,
                "data": state.state_data
            })
        
        # 构建完整提示词
        prompt = f"""你是一个智能车载助手的决策中心，需要根据用户的查询和当前上下文信息，选择最合适的Agent来处理用户请求。

**用户当前查询：**
{context.input_query.query_content}

**对话历史：**
{json.dumps(conversation_history, ensure_ascii=False, indent=2)}

** 用户画像和偏好：**
{long_term_info}

**当前系统状态：**
{json.dumps(system_states_info, ensure_ascii=False, indent=2)}

**可用的Agents：**
{json.dumps(agents_info, ensure_ascii=False, indent=2)}

**决策要求：**
1. 仔细分析用户查询的意图
2. 考虑对话历史和用户偏好
3. 参考当前系统状态
4. 从可用的Agents中选择最合适的一个
5. 如果用户查询不明确或无法由任何Agent处理，选择"chat_agent"进行闲聊对话

**输出格式（必须是有效的JSON）：**
{{
    "selected_agent": "agent名称",
    "confidence": 0.95,
    "reasoning": "选择这个agent的详细理由",
    "parameters": {{
        "key1": "value1",
        "key2": "value2"
    }}
}}

请直接返回JSON格式的决策结果，不要包含任何其他文字说明。
"""
        return prompt
    
    def make_decision(self, context: OrchestratorContext) -> OrchestratorDecision:
        """
        进行决策
        
        Args:
            context: Orchestrator上下文
            
        Returns:
            决策结果
        """
        try:
            # 构建提示词
            prompt = self.build_prompt(context)
            
            # 调用大模型
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的智能决策系统，负责分析用户意图并选择合适的Agent处理请求。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # 降低温度，使输出更确定
                response_format={"type": "json_object"}  # 强制JSON输出
            )
            
            # 解析响应
            response_text = completion.choices[0].message.content
            decision_data = json.loads(response_text)
            
            # 构建决策结果
            decision = OrchestratorDecision(
                selected_agent=decision_data.get("selected_agent", "chat_agent"),
                confidence=float(decision_data.get("confidence", 0.5)),
                reasoning=decision_data.get("reasoning", ""),
                parameters=decision_data.get("parameters", {}),
                metadata={
                    "model": self.model,
                    "tokens_used": completion.usage.total_tokens if completion.usage else 0
                }
            )
            
            return decision
            
        except Exception as e:
            print(f"❌ LLM决策失败: {e}")
            # 返回默认决策
            return OrchestratorDecision(
                selected_agent="chat_agent",
                confidence=0.1,
                reasoning=f"决策失败，降级到默认Agent: {str(e)}",
                parameters={},
                metadata={"error": str(e)}
            )


class MockLLMDecisionMaker:
    """模拟LLM决策器（用于测试）"""
    
    def __init__(self):
        """初始化模拟决策器"""
        self.decision_rules = {
            "音乐": "music_agent",
            "歌": "music_agent",
            "播放": "music_agent",
            "导航": "navigation_agent",
            "路线": "navigation_agent",
            "去": "navigation_agent",
            "天气": "weather_agent",
            "温度": "weather_agent",
            "车窗": "vehicle_control_agent",
            "空调": "vehicle_control_agent",
            "座椅": "vehicle_control_agent",
            "车门": "vehicle_control_agent"
        }
    
    def make_decision(self, context: OrchestratorContext) -> OrchestratorDecision:
        """
        进行模拟决策
        
        Args:
            context: Orchestrator上下文
            
        Returns:
            决策结果
        """
        query = context.input_query.query_content.lower()
        
        # 简单的关键词匹配
        selected_agent = "chat_agent"
        confidence = 0.5
        reasoning = "基于关键词匹配的默认决策"
        
        for keyword, agent_name in self.decision_rules.items():
            if keyword in query:
                selected_agent = agent_name
                confidence = 0.9
                reasoning = f"检测到关键词'{keyword}'，选择{agent_name}"
                break
        
        return OrchestratorDecision(
            selected_agent=selected_agent,
            confidence=confidence,
            reasoning=reasoning,
            parameters={},
            metadata={"mode": "mock"}
        )
