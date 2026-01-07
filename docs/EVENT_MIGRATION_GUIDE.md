# 事件系统迁移指南

## 概述

本次重构使用强类型 Payload 替代灵活的 `data: Any` 字段，提供清晰的模块间协议。

## 核心变化

### 1. Event 基类不再包含 session_id

```python
# ❌ 旧代码
event.session_id  # 所有事件都有这个字段

# ✅ 新代码  
if isinstance(event, SessionAwareEvent):
    event.session_id  # 只有会话感知事件才有
```

### 2. 使用 Payload 类型

```python
# ❌ 旧代码
event = AgentRequestEvent(
    source="orchestrator",
    query="播放音乐",
    context={},
    data={'agent_name': 'music_agent', ...}
)

# ✅ 新代码
from src.core.events import AgentRequestPayload

payload = AgentRequestPayload(
    agent_name='music_agent',
    query="播放音乐",
    context={},
    decision={...}
)

event = AgentRequestEvent(
    source="orchestrator",
    payload=payload,
    session_id="sess_123",
    session_action='new'
)
```

## 事件迁移对照表

### AudioFrameEvent

```python
# ❌ 旧
event = AudioFrameEvent(
    source="audio",
    frame_data=data,
    sample_rate=16000
)

# ✅ 新
from src.core.events import AudioFramePayload

event = AudioFrameEvent(
    source="audio",
    payload=AudioFramePayload(
        frame_data=data,
        sample_rate=16000,
        channels=1
    )
)

# 访问数据
frame_data = event.payload.frame_data
sample_rate = event.payload.sample_rate
```

### WakewordEvent

```python
# ❌ 旧
event = WakewordEvent(
    source="wakeword",
    keyword="小智",
    confidence=0.95
)

# ✅ 新
from src.core.events import WakewordPayload

event = WakewordEvent(
    source="wakeword",
    payload=WakewordPayload(
        keyword="小智",
        confidence=0.95
    )
)

# 访问数据
keyword = event.payload.keyword
```

### VADEvent

```python
# ❌ 旧
event = VADEvent(
    event_type=EventType.VAD_SPEECH_START,
    source="vad",
    audio_data=audio,
    duration_ms=1500
)

# ✅ 新
from src.core.events import VADPayload

event = VADEvent(
    event_type=EventType.VAD_SPEECH_START,
    source="vad",
    payload=VADPayload(
        audio_data=audio,
        duration_ms=1500,
        is_speech=True
    )
)

# 访问数据
audio = event.payload.audio_data
duration = event.payload.duration_ms
```

### ASREvent

```python
# ❌ 旧
event = ASREvent(
    event_type=EventType.ASR_RECOGNITION_SUCCESS,
    source="asr",
    text="你好",
    confidence=0.95,
    latency_ms=150
)

# ✅ 新
from src.core.events import ASRPayload

event = ASREvent(
    event_type=EventType.ASR_RECOGNITION_SUCCESS,
    source="asr",
    payload=ASRPayload(
        text="你好",
        confidence=0.95,
        is_partial=False,
        latency_ms=150
    )
)

# 访问数据
text = event.payload.text
confidence = event.payload.confidence
```

### StateChangeEvent

```python
# ❌ 旧
event = StateChangeEvent(
    source="state_machine",
    from_state="idle",
    to_state="listening",
    reason="唤醒词检测"
)

# ✅ 新
from src.core.events import StateChangePayload

event = StateChangeEvent(
    source="state_machine",
    payload=StateChangePayload(
        from_state="idle",
        to_state="listening",
        reason="唤醒词检测"
    )
)
```

### AgentRequestEvent

```python
# ❌ 旧
event = AgentRequestEvent(
    source="orchestrator",
    query="播放音乐",
    context={},
    session_id="sess_123",
    session_action='new',
    data={
        'agent_name': 'music_agent',
        'query': '播放音乐',
        'decision': {...}
    }
)

# ✅ 新
from src.core.events import AgentRequestPayload

event = AgentRequestEvent(
    source="orchestrator",
    payload=AgentRequestPayload(
        agent_name='music_agent',
        query="播放音乐",
        context={},
        decision={...}
    ),
    session_id="sess_123",
    session_action='new'
)

# 访问数据
agent_name = event.payload.agent_name
query = event.payload.query
decision = event.payload.decision
```

## 向后兼容性

为了保持向后兼容，所有事件的 `data` 字段仍然存在，会自动填充 `payload.to_dict()` 的结果。

```python
# 旧代码仍然可以工作
text = event.data['text']  # ✅ 兼容

# 但建议迁移到新方式
text = event.payload.text  # ✅ 推荐，有类型检查
```

## SessionAwareEvent 的使用

只有需要会话管理的事件才继承 `SessionAwareEvent`：

```python
# 检查是否为会话感知事件
if isinstance(event, SessionAwareEvent):
    session_id = event.session_id
    session_action = event.session_action
    
    # 获取会话信息
    session_info = event.get_session_info()
    if session_info:
        print(f"Session: {session_info.session_id}")
        print(f"Action: {session_info.session_action}")
```

## 类型提示的好处

```python
def handle_agent_request(event: AgentRequestEvent):
    """处理 Agent 请求"""
    # IDE 会提供自动补全
    agent_name = event.payload.agent_name  # ✅ 类型安全
    query = event.payload.query            # ✅ 类型安全
    
    # 类型检查会捕获错误
    # event.payload.wrong_field  # ❌ IDE 会报错
```

## 迁移检查清单

### 第一阶段：更新事件创建代码

- [ ] audio_adapter.py - AudioFrameEvent
- [ ] wakeword_adapter.py - WakewordEvent
- [ ] vad_adapter.py - VADEvent
- [ ] asr_adapter.py - ASREvent
- [ ] controller.py - StateChangeEvent
- [ ] orchestrator_adapter.py - AgentRequestEvent

### 第二阶段：更新事件处理代码

- [ ] 将 `event.data['field']` 改为 `event.payload.field`
- [ ] 添加类型提示 `event: SpecificEvent`
- [ ] 移除对 `event.session_id` 的直接访问（非 SessionAwareEvent）

### 第三阶段：移除向后兼容代码

- [ ] 移除 `data` 字段的自动填充
- [ ] 完全迁移到 Payload 模式

## 常见问题

### Q: 为什么还保留 data 字段？

A: 为了向后兼容。在迁移完成后，可以逐步移除。

### Q: 如何判断事件是否需要会话管理？

A: 使用 `isinstance(event, SessionAwareEvent)` 判断。

### Q: Payload 的 to_dict() 方法有什么用？

A: 用于序列化、日志记录和向后兼容。

### Q: 为什么不直接使用 Pydantic？

A: 避免引入新的依赖。如果需要更强的验证，可以考虑后续迁移到 Pydantic。
