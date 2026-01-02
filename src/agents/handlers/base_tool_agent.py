"""
基础工具Agent - 使用qwen模型智能选择和调用工具
"""
from typing import Dict, Any, Optional, List
import json
import os
import asyncio
from openai import OpenAI

from src.agents.base import AgentResponse
from src.core.events import AgentContext
from src.execution.tool_registry import ToolCategory
from src.execution.manager import get_execution_manager


class BaseToolAgent:
    """
    基础工具Agent
    使用qwen模型的function calling能力智能选择和执行工具
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        capabilities: list[str],
        tool_categories: List[ToolCategory],
        api_key: Optional[str] = None,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ):
        self.name = name
        self.description = description
        self.capabilities = capabilities
        self.tool_categories = tool_categories
        
        # 初始化LLM客户端
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.client = OpenAI(api_key=self.api_key, base_url=base_url) if self.api_key else None
        self.model = "qwen-plus"
        
        # 初始化执行管理器（统一对外接口，必须用单例）
        self.execution_manager = get_execution_manager()
        
        # 获取当前agent可用的工具
        self.available_tools = self._get_available_tools()
    
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
        import time
        start_time = time.time()
        print(f"🔍 [BaseToolAgent] {self.name}.handle() 开始: query='{query}', time={start_time}")
        
        # 使用asyncio.run来运行异步逻辑
        try:
            result = asyncio.run(self._async_handle(query, context))
            end_time = time.time()
            print(f"🔍 [BaseToolAgent] {self.name}.handle() 完成: time={end_time}, 耗时={(end_time-start_time)*1000:.0f}ms")
            return result
        except RuntimeError as e:
            # 如果已经在事件循环中，使用当前循环
            if "cannot be called from a running event loop" in str(e):
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(self._async_handle(query, context))
                end_time = time.time()
                print(f"🔍 [BaseToolAgent] {self.name}.handle() 完成(使用已有loop): time={end_time}, 耗时={(end_time-start_time)*1000:.0f}ms")
                return result
            raise
    
    async def _async_handle(self, query: str, context: AgentContext = None) -> AgentResponse:
        """
        处理用户查询的异步实现
        """
        print(f"🔍 [BaseToolAgent] {self.name}._async_handle() 开始")
        
        if not self.client:
            return AgentResponse(
                agent=self.name,
                success=False,
                query=query,
                message="未配置API密钥，无法使用智能工具调用",
                data={}
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
            
            # 调用LLM（支持function calling）
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.available_tools if self.available_tools else None,
                tool_choice="auto" if self.available_tools else None
            )
            
            message = response.choices[0].message

            print(f"选择的工具调用: {message.tool_calls}" if message.tool_calls else "没有选择工具调用")
            
            # 处理工具调用
            if message.tool_calls:
                return await self._handle_tool_calls(query, message, messages, context)
            else:
                # 没有工具调用，直接返回回复
                return AgentResponse(
                    agent=self.name,
                    success=True,
                    query=query,
                    message=message.content or "好的",
                    data={"no_tool_call": True}
                )
        
        except Exception as e:
            print(f"❌ {self.name} 处理失败: {e}")
            import traceback
            traceback.print_exc()
            
            return AgentResponse(
                agent=self.name,
                success=False,
                query=query,
                message=f"处理失败: {str(e)}",
                data={"error": str(e)}
            )
    
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
        
        # 首先添加 assistant 的 tool_calls 消息（必须在所有 tool 消息之前）
        messages.append({
            "role": "assistant",
            "content": None,
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
            context_reminder = self._build_context_reminder(context)
            if context_reminder:
                messages.append({
                    "role": "system",
                    "content": context_reminder
                })
            
            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            
            final_message = final_response.choices[0].message.content
            
            return AgentResponse(
                agent=self.name,
                success=all(r.get("success", False) for r in tool_results),
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
                success=success_count > 0,
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

你可以使用以下工具来完成任务。请根据用户的需求选择合适的工具。

重要提示：
1. 仔细理解用户意图，选择最合适的工具
2. 如果需要多个步骤，可以依次调用多个工具
3. 执行工具后，用自然语言总结结果给用户
4. 保持回复简洁友好，不超过100字
5. 如果无法完成请求，礼貌地说明原因
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
{recent_conversations}"""
