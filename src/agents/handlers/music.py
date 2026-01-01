"""Music agent implementation."""
from __future__ import annotations

from typing import Dict, Any, Optional

from src.agents.base import BaseAgent, AgentResponse
from src.core.events import AgentContext


class MusicAgent:
    name = "music_agent"

    def __init__(self, description: str, capabilities: list[str]):
        self.description = description
        self.capabilities = capabilities

    def handle(self, query: str, context: AgentContext  = None) -> AgentResponse:
        query_lower = query.lower()
        if "暂停" in query_lower or "pause" in query_lower:
            message = "好的，音乐已暂停。"
        elif "继续" in query_lower or "播放" in query_lower or "play" in query_lower:
            message = "马上为你播放喜欢的歌曲。"
        elif "音量" in query_lower or "大声" in query_lower:
            message = "正在调节音量，确保舒适的聆听体验。"
        else:
            message = "我可以帮你播放、暂停、调节音量或切换歌曲，有什么想听的吗？"
        return AgentResponse(agent=self.name, success=True, query= query, message=message, data={"intent": "music_control"})
