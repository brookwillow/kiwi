# 事件系统 Payload 重构总结

## 改造概览

本次重构实现了强类型的 Payload 系统，解决了以下架构问题：

1. **session_id 不应该是 Event 的基础属性** - 只有部分事件需要会话管理
2. **data: Optional[Any] 缺少类型约束** - 模块间协议不清晰，容易出错
3. **缺少编译时类型检查** - IDE 无法提供自动补全和类型检查

## 核心改进

### 1. Payload 数据类

为每种事件定义了强类型的 Payload 类：

```python
@dataclass
class AudioFramePayload:
    frame_data: bytes
    sample_rate: int
    channels: int = 1

@dataclass
class WakewordPayload:
    keyword: str
    confidence: float

@dataclass
class VADPayload:
    audio_data: Optional[bytes]
    duration_ms: float
    is_speech: bool

@dataclass
class ASRPayload:
    text: str
    confidence: float
    is_partial: bool
    latency_ms: Optional[float] = None

@dataclass
class StateChangePayload:
    from_state: str
    to_state: str
    reason: Optional[str] = None

@dataclass
class AgentRequestPayload:
    agent_name: str
    query: str
    context: Dict[str, Any]
    decision: Dict[str, Any]

@dataclass
class SessionInfo:
    session_id: str
    session_action: str
```

### 2. 事件层次结构

```
Event (基类)
├─ session_id ❌ 移除
├─ payload ✅ 新增（强类型）
└─ data ✅ 保留（向后兼容）

SessionAwareEvent (子类)
├─ 继承自 Event
├─ session_id ✅ 只在这里有
└─ session_action ✅ 会话操作
```

### 3. 事件类型更新

所有事件类更新为接受 `payload` 参数：

- **AudioFrameEvent**: 使用 `AudioFramePayload`
- **WakewordEvent**: 使用 `WakewordPayload`
- **VADEvent**: 使用 `VADPayload`
- **ASREvent**: 使用 `ASRPayload`
- **StateChangeEvent**: 使用 `StateChangePayload`
- **AgentRequestEvent**: 使用 `AgentRequestPayload`，继承 `SessionAwareEvent`

## 代码迁移

### 修改的文件

#### 核心文件
1. **src/core/events.py**
   - 添加 8 个 Payload 类
   - 重构 Event 基类（移除 session_id）
   - 创建 SessionAwareEvent 子类
   - 更新所有 6 个事件类

2. **src/core/controller.py**
   - AudioFrameEvent 创建（使用 AudioFramePayload）
   - StateChangeEvent 创建（使用 StateChangePayload）

#### 适配器文件
3. **src/adapters/orchestrator_adapter.py**
   - 导入 AgentRequestPayload
   - AgentRequestEvent 创建（使用 Payload）
   - ASR 事件处理（访问 payload.text/confidence）

4. **src/adapters/agent_adapter.py**
   - AgentRequestEvent 处理（访问 payload.agent_name/query/decision）

5. **src/adapters/asr_adapter.py**
   - 导入 ASRPayload
   - VAD 事件处理（访问 payload.audio_data）
   - ASR 成功/失败事件创建（使用 ASRPayload）

6. **src/adapters/wakeword_adapter.py**
   - 导入 WakewordPayload
   - WakewordEvent 创建（使用 WakewordPayload）

7. **src/adapters/vad_adapter.py**
   - 导入 VADPayload
   - VAD_SPEECH_START 事件创建（使用 VADPayload）
   - VAD_SPEECH_END 事件创建（使用 VADPayload）

8. **src/adapters/gui_adapter.py**
   - Wakeword 事件处理（访问 payload.keyword/confidence）
   - ASR 事件处理（访问 payload.text/confidence/latency_ms）

### 迁移对比

#### 创建事件

**旧方式:**
```python
event = ASREvent(
    EventType.ASR_RECOGNITION_SUCCESS,
    source="asr",
    text="你好",
    confidence=0.95,
    latency_ms=150
)
```

**新方式:**
```python
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
```

#### 访问数据

**旧方式:**
```python
text = event.data.get('text', '')  # 无类型检查，需要默认值
confidence = event.data.get('confidence', 0.0)
```

**新方式:**
```python
text = event.payload.text  # 有类型检查，IDE自动补全
confidence = event.payload.confidence
```

#### 会话管理

**旧方式:**
```python
# 所有事件都有 session_id，即使不需要
if event.session_id:
    ...
```

**新方式:**
```python
# 只有 SessionAwareEvent 才有 session_id
if isinstance(event, SessionAwareEvent):
    session_id = event.session_id
    session_action = event.session_action
```

## 向后兼容性

为了保持向后兼容，我们保留了 `data` 字段：

```python
class Event:
    def __init__(self, ...):
        self.payload = payload
        # 向后兼容：自动填充 data
        if payload is not None:
            self.data = payload.to_dict()
        else:
            self.data = data or {}
```

这意味着：
- **旧代码** (`event.data.get('field')`) 仍然可以工作
- **新代码** (`event.payload.field`) 更安全、更清晰
- **逐步迁移** 可以在不破坏现有代码的情况下进行

## 优势总结

### 1. 类型安全

```python
def handle_asr(event: ASREvent):
    text = event.payload.text  # ✅ IDE知道这是 str
    conf = event.payload.confidence  # ✅ IDE知道这是 float
    wrong = event.payload.wrong_field  # ❌ IDE会报错
```

### 2. 清晰的协议

每个 Payload 类就是模块间的协议：
- `AudioFramePayload`: 音频模块 → VAD/唤醒词
- `VADPayload`: VAD → ASR
- `ASRPayload`: ASR → Orchestrator
- `AgentRequestPayload`: Orchestrator → Agent

### 3. 自动补全

IDE 可以提供完整的自动补全和文档：
```python
event.payload.  # IDE 自动列出所有可用字段
```

### 4. 架构清晰

- Event 基类：通用事件属性
- SessionAwareEvent：需要会话管理的事件
- 职责分离，符合接口隔离原则（ISP）

### 5. 便于维护

添加新字段时：
```python
@dataclass
class ASRPayload:
    text: str
    confidence: float
    is_partial: bool
    latency_ms: Optional[float] = None
    language: str = "zh-CN"  # ✅ 新字段，所有使用处都会看到
```

## 测试验证

所有修改的文件都通过了类型检查：

```bash
✅ src/core/events.py - No errors
✅ src/core/controller.py - No errors
✅ src/adapters/orchestrator_adapter.py - No errors
✅ src/adapters/agent_adapter.py - No errors
✅ src/adapters/asr_adapter.py - No errors
✅ src/adapters/wakeword_adapter.py - No errors
✅ src/adapters/vad_adapter.py - No errors
✅ src/adapters/gui_adapter.py - No errors
```

## 下一步计划

### 短期（可选）

1. **移除向后兼容代码**：在所有模块迁移完成后，可以移除 `data` 字段
2. **添加 Pydantic 验证**：如果需要更强的运行时验证，可以将 dataclass 迁移到 Pydantic
3. **完整测试**：编写单元测试验证所有事件的创建和处理

### 长期

1. **事件版本控制**：为 Payload 添加版本号，支持协议演进
2. **序列化优化**：统一事件序列化/反序列化机制
3. **事件追踪**：增强事件追踪和调试能力

## 文档

相关文档已创建：

1. **docs/EVENT_MIGRATION_GUIDE.md** - 详细迁移指南
2. **docs/EVENT_SYSTEM_REFACTORING.md** - 设计文档（之前创建）
3. **docs/EVENT_PAYLOAD_SUMMARY.md** - 本文档

## 总结

本次重构成功实现了强类型的事件系统：

✅ 移除了 Event 基类中不必要的 session_id  
✅ 为每种事件定义了清晰的 Payload 类型  
✅ 创建了 SessionAwareEvent 子类处理会话  
✅ 保持了向后兼容性  
✅ 提供了更好的类型检查和 IDE 支持  
✅ 使模块间协议更加清晰  

系统架构更加清晰，代码更易维护，类型更安全。
