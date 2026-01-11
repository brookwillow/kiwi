"""
Agent基类统一定义
提供清晰的Agent抽象层次结构
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from src.core.session_manager import get_session_manager, AgentSession
from src.core.events import AgentResponse, AgentStatus
from src.core.types import AgentContext
from src.execution.tool_registry import ToolCategory
from src.execution.manager import get_execution_manager
from src.llm import get_llm_manager, LLMError
import asyncio
import json
from typing import List
import os



# ============================================================================
# 抽象基类 - 简单Agent（同步，单轮对话）
# ============================================================================

class SimpleAgentBase(ABC):
    """
    简单Agent抽象基类
    适用于：不需要多轮对话的简单任务
    返回：AgentResponse
    """
    
    def __init__(self, name: str, description: str, capabilities: list[str],
                 priority: int = 2):
        self.name = name
        self.description = description
        self.capabilities = capabilities
        self.priority = priority  # 优先级（1/2/3）
        self.interruptible = (priority < 3)  # 优先级3不可打断，1和2可打断
    
    @abstractmethod
    def handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """
        处理查询（子类实现）
        
        Args:
            query: 用户查询
            context: 上下文信息
            
        Returns:
            AgentResponse对象
        """
        pass
    
    def can_handle(self, query: str) -> bool:
        """默认实现：通过capabilities判断"""
        return any(cap.lower() in query.lower() for cap in self.capabilities)


# ============================================================================
# 抽象基类 - 会话Agent（异步，支持多轮对话）
# ============================================================================

class SessionAgentBase(SimpleAgentBase):
    """
    会话型Agent抽象基类
    适用于：需要多轮对话、收集信息的复杂任务
    返回：AgentResponse（带会话管理字段）
    
    注意：Agent 不需要关心 session_id，session 的创建和管理由 agent_adapter 负责
    """
    
    def __init__(self, name: str, description: str, capabilities: list[str],
                 priority: int = 2):
        super().__init__(name, description, capabilities, priority)

    def handle(self, query, context = None):
        """Agent 不再关心 session，只关注业务逻辑"""
        return asyncio.run(self._process(query, context))
    
    @abstractmethod
    async def _process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        处理查询（子类实现）
        
        Args:
            query: 用户查询
            context: 上下文数据
            
        Returns:
            AgentResponse对象
            - 如果需要更多信息，返回 status=WAITING_INPUT
            - 如果完成，返回 status=COMPLETED
            - 如果出错，返回 status=ERROR
        """
        pass
    
    def can_handle(self, query: str) -> bool:
        """默认实现：通过capabilities判断"""
        return any(cap.lower() in query.lower() for cap in self.capabilities)


# ============================================================================
# 辅助基类 - 工具调用Agent
# ============================================================================

class ToolAgentBase(SimpleAgentBase):
    """
    工具调用Agent抽象基类
    继承自SimpleAgentBase，专门用于集成LLM和工具执行
    
    适用于：需要调用外部工具/API的Agent
    
    多轮交互支持：
    - 当LLM认为信息不足、无法调用工具或无法确定工具参数时
    - 可以返回 AgentStatus.WAITING_INPUT 来请求用户补充信息
    - 通过这种方式可以自然地构建多轮对话场景
    - 无需单独的多轮Agent抽象，ToolAgentBase本身就支持灵活的交互模式
    """

    def __init__(
        self,
        name: str,
        description: str,
        capabilities: list[str],
        tool_categories: List[ToolCategory],
        priority: int = 2,
        api_key: Optional[str] = None,
        base_url: str = None  # 保留兼容性，实际不再使用
    ):
        # 调用父类初始化
        super().__init__(name, description, capabilities, priority)
        
        self.tool_categories = tool_categories
        
        # 使用统一的LLM Manager
        self.llm_manager = get_llm_manager()
        # 工具调用Agent默认使用qwen-plus（支持function calling）
        self.model = "qwen-plus"
        
        # 初始化执行管理器（统一对外接口，必须用单例）
        self.execution_manager = get_execution_manager()
        
        # 获取当前agent可用的工具
        self.available_tools = self._get_available_tools()

    @property
    def llm_client(self):
        """兼容旧代码的属性（实际使用llm_manager）"""
        return self.llm_manager
    

    
    def _get_available_tools(self) -> List[Dict]:
        """获取当前agent可用的工具列表（OpenAI格式）"""
        tools = []
        for category in self.tool_categories:
            category_tools = self.execution_manager.list_tools(category)
            print(f"📦 {self.name} - 类别 {category.value}: 找到 {len(category_tools)} 个工具")
            
            for tool in category_tools:
                try:
                    # 获取MCP schema
                    mcp_schema = tool.to_mcp_schema()
                    
                    # 转换为OpenAI tools格式
                    openai_tool = {
                        "type": "function",
                        "function": {
                            "name": mcp_schema.get("name"),
                            "description": mcp_schema.get("description"),
                            "parameters": mcp_schema.get("inputSchema", {})
                        }
                    }
                    
                    # 验证格式
                    if openai_tool["function"]["name"]:
                        tools.append(openai_tool)
                    else:
                        print(f"⚠️  工具 {tool.name} 缺少名称，已跳过")
                        
                except Exception as e:
                    print(f"⚠️  处理工具 {tool.name} 失败: {e}")
                    import traceback
                    traceback.print_exc()
        
        print(f"✅ 为 {self.name} 加载了 {len(tools)} 个有效工具")
        return tools
    
    def handle(self, query: str, context: AgentContext = None) -> AgentResponse:
        """
        处理用户查询（同步接口，内部使用asyncio.run）
        1. 使用LLM理解查询意图
        2. 选择合适的工具
        3. 执行工具
        4. 生成回复
        """
        # 使用asyncio.run来运行异步逻辑
        try:
            return asyncio.run(self._async_handle(query, context))
        except RuntimeError as e:
            # 如果已经在事件循环中，使用当前循环
            if "cannot be called from a running event loop" in str(e):
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(self._async_handle(query, context))
            raise
    
    async def _async_handle(self, query: str, context: AgentContext = None) -> AgentResponse:
        """
        处理用户查询的异步实现
        """
        if not self.llm_manager:
            return AgentResponse(
                agent=self.name,
                status=AgentStatus.ERROR,
                query=query,
                message="LLM Manager未初始化"
            )
        
        try:
            # 构建系统提示词
            system_prompt = self._build_system_prompt(context)
            
            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]

            print(f"可用工具: {[tool['function']['name'] for tool in self.available_tools]}")
            
            # 使用统一的LLM Manager调用（支持function calling）
            response = self.llm_manager.chat(
                messages=messages,
                model=self.model,
                tools=self.available_tools if self.available_tools else None,
                tool_choice="auto" if self.available_tools else None
            )
            
            # 注意：LLMResponse格式不同，需要适配
            # 检查是否有工具调用
            has_tool_calls = response.has_tool_calls

            print(f"选择的工具调用: {response.tool_calls}" if has_tool_calls else "没有选择工具调用")
            
            # 处理工具调用
            if has_tool_calls:
                return await self._handle_tool_calls_from_response(query, response, messages, context)
            else:
                # 没有工具调用，LLM直接回复
                response_content = response.content
                
                # 检查响应内容是否为空
                if not response_content or not response_content.strip():
                    print(f"⚠️ [{self.name}] LLM返回空响应，可能是模型不支持当前任务")
                    return AgentResponse(
                        agent=self.name,
                        status=AgentStatus.ERROR,
                        query=query,
                        message="抱歉，当前模型无法处理这个请求，请稍后再试",
                        data={"error": "empty_response", "model": self.model}
                    )
                
                # 尝试解析JSON响应
                parsed_response = self._parse_json_response(response_content)
                
                if parsed_response is None:
                    # JSON解析失败，但如果有文本内容，则直接返回
                    print(f"⚠️ [{self.name}] LLM未返回JSON格式，但有文本内容，将直接使用")
                    print(f"   原始响应: {response_content[:200]}")
                    
                    # 智能判断：如果内容像是在询问问题，标记为需要输入
                    content_lower = response_content.lower()
                    is_question = any(marker in content_lower for marker in 
                        ['?', '？', '请问', '什么', '哪里', '怎么', '如何', '是否', '确认'])
                    
                    return AgentResponse(
                        agent=self.name,
                        status=AgentStatus.WAITING_INPUT if is_question else AgentStatus.COMPLETED,
                        query=query,
                        message=response_content.strip(),
                        data={"format": "plain_text", "is_fallback": True}
                    )
                
                # 根据need_input判断状态
                if parsed_response.get("need_input", True):
                    # LLM明确表示需要用户输入
                    print(f"🔄 [{self.name}] LLM表示需要更多信息")
                    
                    return AgentResponse(
                        agent=self.name,
                        status=AgentStatus.WAITING_INPUT,
                        query=query,
                        message=parsed_response["message"]
                    )
                else:
                    # 任务完成或可以直接回答
                    print(f"✅ [{self.name}] LLM表示任务完成")
                    return AgentResponse(
                        agent=self.name,
                        status=AgentStatus.COMPLETED,
                        query=query,
                        message=parsed_response["message"]
                    )
        
        except Exception as e:
            print(f"❌ {self.name} 处理失败: {e}")
            import traceback
            traceback.print_exc()
            
            return AgentResponse(
                agent=self.name,
                status=AgentStatus.ERROR,
                query=query,
                message=f"处理失败: {str(e)}",
                data={"error": str(e)}
            )
    
    async def _handle_tool_calls_from_response(
        self,
        query: str,
        response: Any,  # LLMResponse
        messages: List[Dict],
        context: AgentContext = None
    ) -> AgentResponse:
        """
        处理新LLMResponse格式的工具调用
        
        将LLMResponse适配到原有的_handle_tool_calls方法
        """
        # 从LLMResponse提取tool_calls并转换格式
        # 构造一个兼容的message对象用于_handle_tool_calls
        class MessageAdapter:
            def __init__(self, tool_calls):
                self.tool_calls = tool_calls
        
        message = MessageAdapter(response.tool_calls)
        return await self._handle_tool_calls(query, message, messages, context)
    
    async def _handle_tool_calls(
        self,
        query: str,
        message: Any,
        messages: List[Dict],
        context: AgentContext = None
    ) -> AgentResponse:
        """处理工具调用"""
        tool_results = []
        tools_used = []
        


        messages.clear()
        messages.append({
            "role": "user",
            "content": query
        })

        # 首先添加 assistant 的 tool_calls 消息（必须在所有 tool 消息之前）
        messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": [tool_call.model_dump() for tool_call in message.tool_calls]
        })
        
        # 执行所有工具调用
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tools_used.append(tool_name)
            
            try:
                # 解析参数
                arguments = json.loads(tool_call.function.arguments)
                
                print(f"🔧 调用工具: {tool_name}")
                print(f"   参数: {arguments}")
                
                # 通过ExecutionManager执行工具
                result = await self.execution_manager.execute_tool(tool_name, **arguments)
                tool_results.append(result)
                
                # 添加工具执行结果
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })
            
            except Exception as e:
                error_msg = f"工具执行失败: {str(e)}"
                print(f"❌ {error_msg}")
                error_result = {"success": False, "message": error_msg}
                tool_results.append(error_result)
                
                # 添加错误结果
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(error_result, ensure_ascii=False)
                })
        
        # 让LLM根据工具结果生成最终回复
        try:
            # 添加提示，让LLM结合记忆和上下文生成回复
            # 注意：不能在tool消息后添加system消息，这会导致API错误
            # 将上下文提醒作为user消息添加，而不是system消息
            context_reminder = self._build_context_reminder(context)
            if context_reminder:
                messages.append({
                    "role": "user",
                    "content": f"请根据工具执行结果，结合以下上下文信息，生成自然友好的回复：\n\n{context_reminder}"
                })
            else:
                # 如果没有上下文提醒，添加一个简单的user消息让LLM总结结果
                messages.append({
                    "role": "user",
                    "content": "请根据工具执行结果，用自然友好的语言总结并回复用户。"
                })
            
            # 使用LLM Manager生成最终回复
            final_response = self.llm_manager.chat(
                messages=messages,
                model=self.model,
                enable_thinking=False  # 最终回复不需要思考过程，用户只需要看到结果
            )

            print(f"生成的最终回复: {final_response.content}")
            
            final_message = final_response.content
            
            return AgentResponse(
                agent=self.name,
                status=AgentStatus.COMPLETED,
                query=query,
                message=final_message or "已完成操作",
                data={
                    "tools_used": tools_used,
                    "tool_results": tool_results
                }
            )
        
        except Exception as e:
            print(f"❌ 生成最终回复失败: {e}")
            # 降级方案：直接返回工具执行结果
            success_count = sum(1 for r in tool_results if r.get("success", False))
            message = f"已执行 {len(tools_used)} 个操作，{success_count} 个成功"
            
            return AgentResponse(
                agent=self.name,
                status=AgentStatus.ERROR,
                query=query,
                message=message,
                data={
                    "tools_used": tools_used,
                    "tool_results": tool_results
                }
            )
    
    def _build_system_prompt(self, context: AgentContext = None) -> str:
        """构建系统提示词"""
        prompt = f"""你是{self.description}。

你的能力：
{chr(10).join(f"- {cap}" for cap in self.capabilities)}

# 工作流程
1. 如果有可用工具，优先使用function calling调用工具
2. 如果信息不足，先询问用户，获取完整信息后再调用工具
3. 如果没有合适的工具，直接用自然语言回复用户

# 重要规则
- 信息充足时：直接调用工具，不要询问
- 信息不足时：询问缺失的必需参数
- 需要确认时：询问用户是否确认
- 无法完成时：礼貌说明原因

# 回复格式（仅在无法调用工具时使用）
如果不使用工具，请用JSON格式回复：

{{"need_input": true, "message": "你的问题"}}  # 需要更多信息时
{{"need_input": false, "message": "你的回答"}}  # 可以直接回答时

示例：
- {{"need_input": true, "message": "请问你要去哪里？"}}
- {{"need_input": false, "message": "好的，我明白了"}}

注意：优先使用工具调用。如果无工具可用或信息不足，才返回JSON文本。
"""
        
        # 添加上下文信息
        if context and context.short_term_memories:
            recent_conversations = "\n".join([
                f"用户: {m.query}\n助手: {m.response}"
                for m in context.short_term_memories[-3:]
            ])
            prompt += f"\n\n【重要】最近的对话记忆（请在选择工具和生成回复时参考）：\n{recent_conversations}"
            prompt += "\n\n请结合上述对话记忆来理解用户意图，选择合适的工具参数。"
        
        return prompt
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        解析LLM的JSON响应
        
        Args:
            response_text: LLM的响应文本
            
        Returns:
            解析后的字典，包含 need_input 和 message 字段
            如果解析失败返回 None
        """
        if not response_text:
            return None
        
        # 去除可能的Markdown代码块标记
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        try:
            # 尝试直接解析JSON
            data = json.loads(text)
            
            # 验证必需字段
            if isinstance(data, dict) and "message" in data:
                # need_input 默认为 false
                if "need_input" not in data:
                    data["need_input"] = False
                return data
            else:
                print(f"⚠️ JSON格式正确但缺少必需字段: {data}")
                return None
                
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON解析失败: {e}")
            # 尝试提取JSON（可能被包裹在文本中）
            import re
            json_match = re.search(r'\{[^{}]*"message"[^{}]*\}', text)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    if isinstance(data, dict) and "message" in data:
                        if "need_input" not in data:
                            data["need_input"] = False
                        return data
                except json.JSONDecodeError:
                    pass
        
        return None
    
    def _build_context_reminder(self, context: AgentContext = None) -> str:
        """构建上下文提醒，用于工具调用后的最终回复"""
        if not context or not context.short_term_memories:
            return ""
        
        recent_conversations = "\n".join([
            f"用户: {m.query}\n助手: {m.response}"
            for m in context.short_term_memories[-3:]
        ])
        
        return f"""请根据工具执行结果生成回复。注意：
1. 结合之前的对话记忆理解用户的真实需求
2. 用自然、友好的语言总结操作结果
3. 如果工具执行结果与用户期望有关联，请明确指出

对话记忆：
{recent_conversations}

用户的画像：
{context.long_term_memory.user_profile if context.long_term_memory else "无"}

用户的习惯和偏好：
{context.long_term_memory.preferences if context.long_term_memory else "无"}
"""
