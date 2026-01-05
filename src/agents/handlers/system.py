from src.agents.base_classes import SimpleAgentBase
from src.core.events import AgentResponse, AgentStatus
from typing import Optional

class SystemAgent(SimpleAgentBase):
    name = "system_agent"

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

    def handle(self, query: str, context=None):
        """处理系统异常的查询"""
        decision = context.data.get("decision", "未知系统异常") if context and context.data else "未知系统异常"
        reasoning = decision.get("reasoning", "无详细信息") if isinstance(decision, dict) else "无详细信息"
        # 获取desioon
        response_message = f"{reasoning}"

        return AgentResponse(
            agent=self.name,
            query=query,
            message=response_message,
            status=AgentStatus.COMPLETED,
        )
    
