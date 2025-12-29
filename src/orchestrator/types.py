"""
Orchestrator 类型定义
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum


class QueryType(Enum):
    """查询类型"""
    USER_QUERY = "user_query"          # 用户语音查询
    SYSTEM_EVENT = "system_event"      # 系统事件


@dataclass
class ShortTermMemory:
    """短期记忆（对话历史）"""
    role: str                          # user/assistant/system
    content: str                       # 内容
    timestamp: float                   # 时间戳
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LongTermMemory:
    """长期记忆（用户画像和总结）"""
    summary: str                       # 对话摘要
    user_profile: Dict[str, Any]       # 用户画像
    preferences: Dict[str, Any]        # 用户偏好
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemState:
    """系统状态"""
    state_type: str                    # 状态类型（vehicle/music/navigation等）
    state_data: Dict[str, Any]         # 状态数据
    timestamp: float                   # 时间戳


@dataclass
class AgentInfo:
    """Agent信息"""
    name: str                          # Agent名称
    description: str                   # Agent描述
    capabilities: List[str]            # Agent能力列表
    enabled: bool = True               # 是否启用
    metadata: Dict[str, Any] = field(default_factory=dict)


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
