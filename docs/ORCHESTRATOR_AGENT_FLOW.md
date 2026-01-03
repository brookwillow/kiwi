# Orchestrator与Agent执行流程

## 架构原则：职责分离

系统现在遵循**适配器模式**和**单一职责原则**，将决策、调度和执行逻辑分离到不同的模块：

### 模块职责划分

1. **orchestrator_adapter**: 只负责Agent选择决策
2. **agent_adapter**: 负责监听事件并调度Agent执行
3. **agent_manager**: 纯业务逻辑，负责Agent执行、记忆召回、上下文构建

## 完整流程

```
用户语音/文本输入
    ↓
ASR识别成功 (ASR_RECOGNITION_SUCCESS事件)
    ↓
┌─────────────────────────────────────┐
│  orchestrator_adapter               │
│  - 接收ASR识别结果                   │
│  - 调用Orchestrator.process_query() │
│  - 基于LLM/规则做出决策               │
│  - 选择合适的Agent                   │
│  - 发布GUI更新显示决策结果            │
│  - 发送AGENT_DISPATCH_REQUEST事件    │
└─────────────────────────────────────┘
    ↓ (AGENT_DISPATCH_REQUEST事件)
┌─────────────────────────────────────┐
│  agent_adapter                      │
│  - 监听AGENT_DISPATCH_REQUEST       │
│  - 调用agent_manager.execute_agent()│
│  - 记录执行追踪                      │
│  - 发布Agent响应到GUI                │
│  - 发送TTS播报请求                   │
└─────────────────────────────────────┘
    ↓ (调用)
┌─────────────────────────────────────┐
│  agent_manager                      │
│  - 召回相关记忆和上下文               │
│  - 构建AgentContext                 │
│  - 执行具体的Agent handler           │
│  - 返回AgentResponse                │
└─────────────────────────────────────┘
    ↓ (TTS_SPEAK_REQUEST事件)
┌─────────────────────────────────────┐
│  tts_adapter                        │
│  - 执行语音播报                      │
│  - 完成消息追踪                      │
└─────────────────────────────────────┘
```

## 架构优势

### 1. 适配器模式
- **agent_adapter**: 适配器层，处理事件通信
- **agent_manager**: 业务逻辑层，不关心事件系统
- 符合"开闭原则"，易于扩展和测试

### 2. 职责清晰
- **orchestrator_adapter**: 专注于决策逻辑（选择哪个Agent）
- **agent_adapter**: 专注于事件调度和结果发布
- **agent_manager**: 专注于Agent执行和记忆召回

## 事件定义

### AGENT_DISPATCH_REQUEST
Agent分发请求事件，由orchestrator发送给agent_manager

**数据结构**:
```python
{
    'agent_name': str,      # Agent名称
    'query': str,           # 用户查询
    'decision': {           # 决策详情
        'selected_agent': str,
        'confidence': float,
        'reasoning': str,
        'parameters': dict
    }
}
```

## 代码示例

### orchestrator_adapter发送分发请求

```python
def _publish_agent_dispatch_request(self, agent_name: str, query: str, decision, msg_id: Optional[str] = None):
    """发布Agent分发请求事件"""
    dispatch_event = Event.create(
        event_type=EventType.AGENT_DISPATCH_REQUEST,
        source=self._name,
        msg_id=msg_id,
        data={
            'agent_name': agent_name,
            'query': query,
            'decision': {
                'selected_agent': decision.selected_agent,
                'confidence': decision.confidence,
                'reasoning': decision.reasoning,
                'parameters': decision.parameters
            }
        }
    )
    self._controller.publish_event(dispatch_event)
```

### agent_manager处理分发请求

```python
# agent_adapter监听事件并调用agent_manager
def handle_event(self, event: Event):
    """处理事件 - 监听Agent分发请求"""
    if event.type == EventType.AGENT_DISPATCH_REQUEST:
        threading.Thread(
            target=self._handle_agent_dispatch,
            args=(event,),
            daemon=True
        ).start()

def _handle_agent_dispatch(self, event: Event):
    """处理Agent分发请求"""
    agent_name = event.data.get('agent_name')
    query = event.data.get('query')
    msg_id = event.msg_id
    
    # 调用agent_manager执行
    response = self._agent_manager.execute_agent(
        agent_name=agent_name,
        query=query,
        context=event.data
    )
    
    # 发布响应
    self._publish_agent_response(response, msg_id)
    
    # 请求TTS播报
    if response.success and response.message:
       适配器模式
- **agent_adapter**: 适配器层，处理事件通信
- **agent_manager**: 业务逻辑层，不关心事件系统
- 符合"开闭原则"，易于扩展和测试

### 2. 职责清晰
- **orchestrator_adapter**: 专注于决策逻辑（选择哪个Agent）
- **agent_adapter**: 专注于事件调度和结果发布
- **agent_manager**: 专注于Agent执行和记忆召回

### 3ef execute_agent(self, agent_name: str, query: str, context: dict) -> AgentResponse:
        """执行Agent（不涉及事件处理）"""
        # 召回记忆
        agent_context = self.get_agent_context(query, agent_name)
        
        # 执行handler
        handler = self._agent_handlers.get(agent_name)
        return handler.handle(query=query, context=agent_context)
```

## 优3. 解耦合
- adapter层与业务层分离，通过方法调用通信
- agent_manager可以独立测试，无需mock事件系统
- 便于单元测试和集成测试

### 4. 可扩展性
- 可以轻松替换agent_manager实现
- 可以在adapter层添加中间件（如权限检查、限流等）
- 可以监听AGENT_DISPATCH_REQUEST做日志、监控
- 便于实现Agent执行的重试、缓存等机制

### 5
### 3. 可扩展性
- 可以轻松添加中间层（如权限检查、限流等）
- 可以监听AGENT_DISPATCH_REQUEST做日志、监控
- 便于实现Agent执行的重试、缓存等机制

### 4. 消息追踪
- 每个阶段都有清晰的trace记录
- 便于调试和性能分析
- 支持完整的对话流程追踪

## 消息追踪点

系统在以下关键点记录trace：

1. **orchestrator_input**: Orchestrator收到ASR结果
2. **orchestrator_decision**: 决策完成，选择Agent
3. **agent_dispatch_request**: 发送Agent分发请求
4. **agent_execution_start**: Agent开始执行
5. **agent_response**: Agent执行完成
6. **tts_request**: 请求TTS播报

查询追踪：
```bash
python tools/query_message_trace.py --msg-id <msg_id>
```

## 相关文档

- [Orchestrator文档](ORCHESTRATOR.md)
- [Agent架构](AGENT_ARCHITECTURE.md)
- [消息追踪系统](MESSAGE_TRACKING.md)
- [事件系统](../src/core/events.py)
