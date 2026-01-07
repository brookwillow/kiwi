# 事件系统重构方案

## 问题分析

### 问题1: session_id 污染事件基类

**当前设计**：
```python
@dataclass
class Event:
    type: EventType
    source: str
    timestamp: float
    data: Optional[Any] = None
    metadata: Optional[dict] = None
    msg_id: Optional[str] = None
    session_id: Optional[str] = None  # ❌ 大部分事件不需要
```

**问题**：
- 音频、唤醒词、VAD、ASR 等事件都不需要 session_id
- 只有 Agent 相关的事件才需要会话管理
- 违反了接口隔离原则（Interface Segregation Principle）

### 问题2: data 字段缺乏类型约束

**当前设计**：
```python
data: Optional[Any] = None  # ❌ 太灵活，没有约束
```

**问题**：
- 无法通过类型检查发现错误
- 模块间协议隐含在代码中
- 容易出现字段拼写错误、类型错误

## 重构方案

### 方案1: 移除 session_id，使用事件特化

**设计原则**：
- 只在需要的事件类中添加 session_id
- 保持 Event 基类的简洁性

**重构后的代码**：

```python
@dataclass
class Event:
    """事件基类 - 只包含所有事件共有的字段"""
    type: EventType
    source: str
    timestamp: float
    data: Optional[Any] = None
    metadata: Optional[dict] = None
    msg_id: Optional[str] = None  # 用于追踪整个对话流程
    
    @classmethod
    def create(cls, event_type: EventType, source: str, data: Any = None, 
               msg_id: Optional[str] = None, **metadata):
        """创建事件"""
        return cls(
            type=event_type,
            source=source,
            timestamp=time.time(),
            data=data,
            metadata=metadata or {},
            msg_id=msg_id
        )


@dataclass
class SessionAwareEvent(Event):
    """需要会话管理的事件基类"""
    session_id: Optional[str] = None
    session_action: Optional[str] = None  # 'new', 'resume', 'complete'
    
    def __init__(self, type: EventType, source: str, data: Any = None,
                 msg_id: Optional[str] = None, session_id: Optional[str] = None,
                 session_action: Optional[str] = None, **metadata):
        super().__init__(type, source, time.time(), data, metadata, msg_id)
        self.session_id = session_id
        self.session_action = session_action


@dataclass
class AgentRequestEvent(SessionAwareEvent):
    """Agent请求事件 - 继承 SessionAwareEvent"""
    def __init__(self, source: str, query: str, agent_name: str,
                 msg_id: Optional[str] = None, session_id: Optional[str] = None,
                 session_action: str = 'new', **kwargs):
        data = {
            'agent_name': agent_name,
            'query': query,
            **kwargs
        }
        super().__init__(
            type=EventType.AGENT_DISPATCH_REQUEST,
            source=source,
            data=data,
            msg_id=msg_id,
            session_id=session_id,
            session_action=session_action
        )
```

### 方案2: 使用强类型 Payload 替代 data

**设计原则**：
- 为每种事件定义明确的 Payload 类
- 使用 dataclass 提供类型检查
- 协议清晰可见

**Payload 定义**：

```python
from typing import Protocol, TypeVar, Generic

# === Payload 协议 ===

class EventPayload(Protocol):
    """事件载荷协议"""
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        ...


# === 具体 Payload 类型 ===

@dataclass
class AudioFramePayload:
    """音频帧载荷"""
    frame_data: bytes
    sample_rate: int
    channels: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'frame_size': len(self.frame_data)
        }


@dataclass
class WakewordPayload:
    """唤醒词载荷"""
    keyword: str
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'keyword': self.keyword,
            'confidence': self.confidence
        }


@dataclass
class ASRPayload:
    """ASR识别载荷"""
    text: str
    confidence: float
    is_partial: bool = False
    latency_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'text': self.text,
            'confidence': self.confidence,
            'is_partial': self.is_partial
        }
        if self.latency_ms is not None:
            result['latency_ms'] = self.latency_ms
        return result


@dataclass
class AgentRequestPayload:
    """Agent请求载荷"""
    agent_name: str
    query: str
    context: Dict[str, Any] = field(default_factory=dict)
    decision: Optional[Dict[str, Any]] = None  # Orchestrator决策信息
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'agent_name': self.agent_name,
            'query': self.query,
            'context': self.context,
            'decision': self.decision
        }


@dataclass
class AgentResponsePayload:
    """Agent响应载荷"""
    agent: str
    query: str
    message: str
    status: str  # 'completed', 'waiting_input', 'error'
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'agent': self.agent,
            'query': self.query,
            'message': self.message,
            'status': self.status,
            'data': self.data
        }
```

**使用泛型的事件类**：

```python
P = TypeVar('P', bound=EventPayload)

@dataclass
class TypedEvent(Event, Generic[P]):
    """带类型的事件"""
    payload: P
    
    def __init__(self, event_type: EventType, source: str, payload: P,
                 msg_id: Optional[str] = None):
        super().__init__(
            type=event_type,
            source=source,
            timestamp=time.time(),
            data=payload.to_dict(),
            msg_id=msg_id
        )
        self.payload = payload


# 使用示例
audio_event = TypedEvent(
    event_type=EventType.AUDIO_FRAME_READY,
    source="audio_recorder",
    payload=AudioFramePayload(
        frame_data=b'...',
        sample_rate=16000,
        channels=1
    )
)

asr_event = TypedEvent(
    event_type=EventType.ASR_RECOGNITION_SUCCESS,
    source="asr_engine",
    payload=ASRPayload(
        text="你好",
        confidence=0.95,
        latency_ms=150.5
    )
)
```

### 方案3: 使用 Pydantic 进行验证（推荐）

**优势**：
- 自动类型验证
- JSON 序列化/反序列化
- 清晰的错误提示
- 文档自动生成

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from enum import Enum


# === Payload Models ===

class AudioFramePayload(BaseModel):
    """音频帧载荷"""
    frame_data: bytes
    sample_rate: int = Field(gt=0, description="采样率（Hz）")
    channels: int = Field(default=1, ge=1, le=2, description="声道数")
    
    class Config:
        arbitrary_types_allowed = True


class WakewordPayload(BaseModel):
    """唤醒词载荷"""
    keyword: str = Field(min_length=1, description="唤醒词")
    confidence: float = Field(ge=0.0, le=1.0, description="置信度")


class ASRPayload(BaseModel):
    """ASR识别载荷"""
    text: str = Field(description="识别文本")
    confidence: float = Field(ge=0.0, le=1.0, description="置信度")
    is_partial: bool = Field(default=False, description="是否为部分结果")
    latency_ms: Optional[float] = Field(default=None, ge=0, description="延迟（毫秒）")


class AgentRequestPayload(BaseModel):
    """Agent请求载荷"""
    agent_name: str = Field(min_length=1, description="Agent名称")
    query: str = Field(min_length=1, description="用户查询")
    context: Dict[str, Any] = Field(default_factory=dict, description="上下文")
    decision: Optional[Dict[str, Any]] = Field(default=None, description="决策信息")
    
    @validator('agent_name')
    def validate_agent_name(cls, v):
        """验证Agent名称格式"""
        if not v.endswith('_agent'):
            raise ValueError("Agent名称必须以'_agent'结尾")
        return v


class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str = Field(min_length=1, description="会话ID")
    session_action: str = Field(
        default='new',
        regex='^(new|resume|complete)$',
        description="会话动作"
    )
    priority: Optional[int] = Field(default=2, ge=1, le=3, description="优先级")


# === 事件定义 ===

class Event(BaseModel):
    """事件基类"""
    type: str = Field(description="事件类型")
    source: str = Field(description="事件源")
    timestamp: float = Field(description="时间戳")
    msg_id: Optional[str] = Field(default=None, description="消息ID")
    
    class Config:
        use_enum_values = True


class AgentRequestEvent(Event):
    """Agent请求事件"""
    type: str = Field(default="agent_dispatch_request", const=True)
    payload: AgentRequestPayload
    session: Optional[SessionInfo] = None


# 使用示例
try:
    event = AgentRequestEvent(
        source="orchestrator",
        timestamp=time.time(),
        payload=AgentRequestPayload(
            agent_name="music_agent",
            query="播放音乐",
            context={"user_id": "123"}
        ),
        session=SessionInfo(
            session_id="sess_123",
            session_action="new",
            priority=2
        )
    )
    
    # 自动验证通过
    print(event.json(indent=2))
    
except ValueError as e:
    # 验证失败会抛出清晰的错误
    print(f"验证失败: {e}")
```

## 推荐的重构步骤

### 阶段1: 最小改动（立即可做）

1. **移除 Event 基类的 session_id**
2. **创建 SessionAwareEvent 子类**
3. **让 AgentRequestEvent 继承 SessionAwareEvent**

```python
# 改动文件: src/core/events.py

# 1. Event 基类去掉 session_id
@dataclass
class Event:
    type: EventType
    source: str
    timestamp: float
    data: Optional[Any] = None
    metadata: Optional[dict] = None
    msg_id: Optional[str] = None
    # session_id: Optional[str] = None  # ❌ 删除

# 2. 新增 SessionAwareEvent
@dataclass
class SessionAwareEvent(Event):
    """需要会话管理的事件"""
    session_id: Optional[str] = None
    session_action: Optional[str] = None

# 3. AgentRequestEvent 继承 SessionAwareEvent
@dataclass
class AgentRequestEvent(SessionAwareEvent):
    # ... 保持原有逻辑
```

**影响**：
- 需要更新使用 `event.session_id` 的地方，改为判断是否为 SessionAwareEvent
- 向下兼容性好，改动小

### 阶段2: 引入 Payload（逐步迁移）

1. **定义常用的 Payload 类**（如 AgentRequestPayload, ASRPayload）
2. **逐步迁移现有事件使用 Payload**
3. **保持 data 字段向后兼容**

### 阶段3: 完整类型化（长期目标）

1. **使用 Pydantic 替换 dataclass**
2. **所有事件使用强类型 Payload**
3. **移除 data 的 Any 类型**

## 协议约定文档

无论采用哪种方案，都应该维护一个协议文档：

### 文档模板：`EVENT_PROTOCOLS.md`

```markdown
# 事件协议规范

## Agent 相关事件

### AGENT_DISPATCH_REQUEST

**发送者**: orchestrator_adapter
**接收者**: agent_adapter

**Payload 结构**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| agent_name | str | ✅ | Agent名称，必须以'_agent'结尾 |
| query | str | ✅ | 用户查询内容 |
| context | dict | ❌ | 上下文信息 |
| decision | dict | ❌ | Orchestrator决策详情 |

**Session 信息**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| session_id | str | ✅ | 会话ID |
| session_action | str | ✅ | 'new' \| 'resume' \| 'complete' |
| priority | int | ❌ | 优先级 1-3 |

**示例**:
```json
{
  "type": "agent_dispatch_request",
  "source": "orchestrator",
  "timestamp": 1704528000.123,
  "payload": {
    "agent_name": "music_agent",
    "query": "播放音乐",
    "context": {},
    "decision": {
      "confidence": 0.95,
      "reasoning": "用户请求播放音乐"
    }
  },
  "session": {
    "session_id": "sess_abc123",
    "session_action": "new",
    "priority": 2
  }
}
```

### AGENT_RESPONSE

**发送者**: agent_adapter
**接收者**: orchestrator_adapter, gui_adapter

**Payload 结构**:
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| agent | str | ✅ | Agent名称 |
| query | str | ✅ | 原始查询 |
| message | str | ✅ | 响应消息（用于TTS） |
| status | str | ✅ | 'completed' \| 'waiting_input' \| 'error' |
| data | dict | ❌ | 附加数据 |

**示例**:
```json
{
  "type": "agent_response",
  "source": "agent_adapter",
  "timestamp": 1704528001.456,
  "payload": {
    "agent": "music_agent",
    "query": "播放音乐",
    "message": "已经为你播放音乐了",
    "status": "completed",
    "data": {
      "song_name": "默认歌单"
    }
  }
}
```
```

## 总结

### 建议的实施方案

**短期（立即）**：
1. ✅ 移除 Event 基类的 session_id
2. ✅ 创建 SessionAwareEvent
3. ✅ 创建 EVENT_PROTOCOLS.md 文档

**中期（1-2周）**：
1. 定义核心 Payload 类（Agent、ASR、Audio）
2. 逐步迁移到 Payload 模式
3. 添加类型提示和验证

**长期（1-2月）**：
1. 引入 Pydantic
2. 完整的类型化系统
3. 自动生成 API 文档

### 优势对比

| 方案 | 类型安全 | 易用性 | 迁移成本 | 推荐度 |
|------|---------|--------|---------|--------|
| 当前方案 | ❌ 低 | ✅ 高 | - | ⭐⭐ |
| 移除session_id | ⭐ | ✅ 高 | 🟢 低 | ⭐⭐⭐⭐ |
| Payload类 | ⭐⭐⭐ | ⭐⭐ | 🟡 中 | ⭐⭐⭐⭐ |
| Pydantic | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 🔴 高 | ⭐⭐⭐⭐⭐ |

最推荐的路径是：**先移除session_id + 编写协议文档**，然后逐步引入 Pydantic。
