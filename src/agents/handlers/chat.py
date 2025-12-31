"""Chat agent implementation."""
from __future__ import annotations

from typing import Dict, Any, Optional
import os
import re
from ollama import chat

from src.agents.base import AgentResponse


class ChatAgent:
    name = "chat_agent"

    def __init__(
        self,
        description: str,
        capabilities: list[str],
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.description = description
        self.capabilities = capabilities
        self._ollama_model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
        self._ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")

    def handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """Generate a chat reply using LLM if available, otherwise fallback rules."""
        # Build structured chat messages per Ollama's Python client expectations
        system_prompt = (
            "你是一个闲聊助手，根据用户的说的话，跟他进行聊天。要求：不要超过100个字，"
            "禁止展示思考过程。"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query or ""},
        ]

        try:
            response = chat(
                model=self._ollama_model,
                messages=messages,
                think=False
            )
            content = response.message.content if hasattr(response, "message") else ""

            # Remove <think> tags and their content
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
            content = content.strip()

            print("Processed Model response:", content)  # Debugging: Print the cleaned model response
            return AgentResponse(
                agent=self.name,
                success=True,
                message=content,
                data={"intent": "chat", "model": f"ollama:{self._ollama_model}"},
            )
        except Exception as e:
            print("Ollama request failed with exception:", e)  # Debugging: Log the exception
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
                agent=self.name, success=True, message=message, data=data
            )
