"""
核心类型定义

集中定义系统中使用的各种数据类型
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, Dict, List


# ============================================================================
# 记忆相关类型
# ============================================================================

@dataclass
class ShortTermMemory:
    """短期记忆（对话历史）"""
    query: str                          # 用户查询
    response: str                       # 系统响应
    timestamp: float                    # 时间戳
    agent: str = ""                     # 处理该记忆的Agent名称
    tools_used: List[str] = field(default_factory=list)  # 使用的工具列表
    description: str = ""               # 文本化描述
    success: bool = True                # 记忆是否成功
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LongTermMemory:
    """长期记忆（用户画像和总结）"""
    summary: str                       # 对话摘要
    user_profile: Dict[str, Any]       # 用户画像
    preferences: Dict[str, Any]        # 用户偏好
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 系统相关类型
# ============================================================================

class QueryType(Enum):
    """查询类型"""
    USER_QUERY = "user_query"          # 用户语音查询
    SYSTEM_EVENT = "system_event"      # 系统事件


@dataclass
class SystemState:
    """系统状态"""
    state_type: str                    # 状态类型（vehicle/music/navigation等）
    state_data: Dict[str, Any]         # 状态数据
    timestamp: float                   # 时间戳


# ============================================================================
# Agent 相关类型
# ============================================================================

@dataclass
class AgentInfo:
    """Agent信息"""
    name: str                          # Agent名称
    description: str                   # Agent描述
    capabilities: List[str]            # Agent能力列表
    priority: int                       # 优先级
    enabled: bool = True               # 是否启用
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContext:
    """Agent上下文"""
    recent_memories: List[ShortTermMemory]  # 最近的短期记忆（按时间顺序）
    related_memories: List[ShortTermMemory]  # 相关的短期记忆（按语义相似度）
    long_term_memory: Optional[LongTermMemory]  # 长期记忆
    system_states: List[SystemState]   # 系统状态
    data: Optional[Any]
    
    @property
    def short_term_memories(self) -> List[ShortTermMemory]:
        """向后兼容：返回所有短期记忆（最近+相关，去重）"""
        seen = set()
        merged = []
        for mem in self.recent_memories:
            if mem.timestamp not in seen:
                merged.append(mem)
                seen.add(mem.timestamp)
        for mem in self.related_memories:
            if mem.timestamp not in seen:
                merged.append(mem)
                seen.add(mem.timestamp)
        return merged


@dataclass
class IAgent(Protocol):
    """
    Agent协议接口
    所有Agent都应该遵循这个协议
    """
    name: str
    description: str
    capabilities: list[str]
    
    def can_handle(self, query: str) -> bool:
        """判断是否能处理该查询"""
        ...


# ============================================================================
# Orchestrator 相关类型
# ============================================================================

@dataclass
class OrchestratorInput:
    """Orchestrator输入"""
    query_type: QueryType              # 查询类型
    query_content: str                 # 查询内容
    timestamp: float                   # 时间戳
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorContext:
    """Orchestrator上下文"""
    input_query: OrchestratorInput     # 输入查询
    short_term_memories: List[ShortTermMemory]  # 短期记忆
    long_term_memory: Optional[LongTermMemory]  # 长期记忆
    system_states: List[SystemState]   # 系统状态
    available_agents: List[AgentInfo]  # 可用的Agents
    
    
@dataclass
class OrchestratorDecision:
    """Orchestrator决策结果"""
    selected_agent: str                # 选中的Agent名称
    confidence: float                  # 置信度
    reasoning: str                     # 决策理由
    parameters: Dict[str, Any] = field(default_factory=dict)  # 传递给Agent的参数
    metadata: Dict[str, Any] = field(default_factory=dict)
