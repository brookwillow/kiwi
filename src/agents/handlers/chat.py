"""Chat agent implementation."""
from __future__ import annotations

from typing import Dict, Any, Optional
import os
import re

from src.agents.base_classes import AgentResponse, SimpleAgentBase
from src.core.events import AgentResponse, AgentStatus
from src.core.types import AgentContext
from src.llm import get_llm_manager, LLMError


class ChatAgent(SimpleAgentBase):
    name = "chat_agent"

    def __init__(
        self,
        description: str,
        capabilities: list[str],
        priority: int = 2,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        super().__init__(name=self.name, description=description, 
                        capabilities=capabilities, priority=priority)
        # 使用统一的LLM Manager
        self.llm_manager = get_llm_manager()

    def handle(self, query: str, context: AgentContext  = None) -> AgentResponse:
        """Generate a chat reply using LLM if available, otherwise fallback rules."""
        # Build structured chat messages per Ollama's Python client expectations

        # 之前三轮对话内容
        last_three_conversations = ""
        if context and context.recent_memories:
            for memory in context.recent_memories[-3:]:
                last_three_conversations += "[query]" + memory.query + "[response]" + memory.response + "\n"

        # last_conversation = "[query]"+ context.short_term_memories[0].query + "[response]" + context.short_term_memories[0].response if context and context.short_term_memories else ""

        system_prompt = (
            "你是一个闲聊助手，根据用户的说的话，跟他进行聊天。要求："\
            "1. 不要超过100个字"\
            "2. 禁止展示思考过程" \
            "3. 如果根据query无法回答，可参考之前的对话内容" \
            "4. 禁止回复系统错误信息（如'当前会话不允许被打断'、'有更重要的任务'等），这些是系统错误，不是给用户的回复" \
            "5. 用户的每个请求都应该积极响应，不要拒绝" \
            "之前三轮的对话内容："\
            f"{last_three_conversations}"\
            "之前相关的对话内容："\
            f"{context.related_memories}"\
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query or ""},
        ]

        print("chat prompt:", messages)  
        ollama_failed = False
        try:
            # 使用统一的LLM Manager调用
            response = self.llm_manager.chat(
                messages=messages,
                model="qwen3-8b",  # 闲聊使用本地qwen3-8b
                temperature=0.7,
                max_tokens=500,  # 增加token限制，确保即使有<think>标签也能输出完整内容
                enable_thinking=False  # 闲聊场景关闭思考模式，Provider层会自动过滤<think>标签
            )
            content = response.content
            
            # Provider层已经根据enable_thinking参数过滤了<think>标签
            # 这里可以直接使用content

            print("Processed Model response:", content)
            return AgentResponse(
                agent=self.name,
                status=AgentStatus.COMPLETED,
                query=query,
                message=content,
                data={
                    "intent": "chat", 
                    "model": response.model,
                    "provider": response.provider
                },
            )
        except LLMError as e:
            print(f"LLM request failed: {e}")
            ollama_failed = True

        # Only if Ollama failed (no valid content) do we run local fallback rules
        if ollama_failed:
            # Simple fallback rules if no LLM available or call failed
            q = (query or "").lower()
            if "笑话" in q or "幽默" in q:
                message = "当然可以：程序员的浪漫是git commit -m 'I love you'。"
            elif "天气" in q:
                message = "出门前看下实时天气，注意保暖。"
            elif "谢谢" in q or "感谢" in q:
                message = "不客气，很高兴帮到你。"
            elif len(q.strip()) == 0:
                message = "有什么我可以帮忙的吗？"
            else:
                # generic short reply
                message = "我在的，请说吧。"

            data = {"intent": "chat"}
            return AgentResponse(
                agent=self.name, status=AgentStatus.COMPLETED, query=query, message=message, data=data
            )
