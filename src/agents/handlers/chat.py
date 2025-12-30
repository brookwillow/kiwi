"""Chat agent implementation."""
from __future__ import annotations

from typing import Dict, Any, Optional

from src.agents.base import AgentResponse


class ChatAgent:
    name = "chat_agent"

    def __init__(self, description: str, capabilities: list[str]):
        self.description = description
        self.capabilities = capabilities

    def handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        message = "今天的状态不错！我可以陪你聊天、讲笑话或回答常识问题。"
        if "笑话" in query:
            message = "当然！程序员的浪漫是什么？git commit -m 'I love you'。"
        elif "天气" in query:
            message = "天气有点变幻莫测，出门前记得看看实时预报。"
        elif "谢谢" in query:
            message = "不客气，能帮到你很开心！"
        return AgentResponse(agent=self.name, success=True, message=message, data={"intent": "chat"})
