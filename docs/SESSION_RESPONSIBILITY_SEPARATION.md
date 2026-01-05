# Session 管理职责分离设计

## 核心理念

**Agent 不应该关心 session_id，session 的创建和管理应该由上层（agent_adapter）负责**。

## 设计原则

### 1. 关注点分离（Separation of Concerns）

- **Agent 层**：专注于业务逻辑
  - 处理用户查询
  - 调用工具
  - 返回响应

- **Adapter 层**：负责基础设施
  - 创建和管理 session
  - 维护 session 栈
  - 处理 session 生命周期

### 2. 单一职责原则（Single Responsibility Principle）

- Agent：只做业务逻辑判断
- Adapter：只做协调和管理

## 架构对比

### 旧设计（❌ 职责混乱）

```
┌─────────────────────────────────────────────┐
│            SessionAgentBase                  │
│                                             │
│  1. 创建 session                            │
│  2. 管理 session_id                         │
│  3. 处理业务逻辑                            │
│  4. 返回 AgentResponse                      │
│                                             │
│  问题：Agent 需要关心 session 管理          │
└─────────────────────────────────────────────┘
```

### 新设计（✅ 职责清晰）

```
┌─────────────────────────────────────────────┐
│           agent_adapter                      │
│                                             │
│  1. 创建 session（根据优先级）              │
│  2. 分发给 Agent                            │
│  3. 接收 AgentResponse                      │
│  4. 设置 session_id（如果 WAITING_INPUT）   │
│  5. 维护 session 栈                         │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│              Agent                          │
│                                             │
│  1. 处理业务逻辑                            │
│  2. 返回 AgentResponse（不带 session_id）   │
│                                             │
│  优势：Agent 不关心 session                 │
└─────────────────────────────────────────────┘
```

## 实现细节

### agent_adapter 的职责

```python
class AgentModuleAdapter:
    def _handle_agent_dispatch(self, event: Event):
        """处理 Agent 分发请求"""
        
        # 1. 获取 Agent 优先级
        agent_config = self._agent_manager.get_agent_by_name(agent_name)
        priority = agent_config.get('priority', 2)
        
        # 2. 创建 session（Adapter 负责）
        session = self._session_manager.create_session(
            agent_name=agent_name,
            priority=priority
        )
        
        if session is None:
            # Session 创建失败，直接返回错误
            return error_response
        
        # 3. 调用 Agent（Agent 不需要知道 session_id）
        response = self._agent_manager.execute_agent(
            agent_name=agent_name,
            query=query,
            context=data
        )
        
        # 4. Adapter 负责设置 session_id
        if response.status == AgentStatus.WAITING_INPUT:
            response.session_id = session.session_id
            self._session_manager.wait_for_input(session.session_id, response.prompt)
        elif response.status == AgentStatus.COMPLETED:
            self._session_manager.complete_session(session.session_id)
        elif response.status == AgentStatus.ERROR:
            self._session_manager.complete_session(session.session_id)
```

### Agent 的简化接口

```python
class SessionAgentBase(SimpleAgentBase):
    """
    会话型 Agent 基类
    注意：Agent 不需要关心 session_id
    """
    
    @abstractmethod
    async def _process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        处理查询（子类实现）
        
        返回：
        - AgentStatus.WAITING_INPUT：需要更多信息
        - AgentStatus.COMPLETED：完成
        - AgentStatus.ERROR：错误
        
        注意：不需要设置 session_id，由 adapter 负责
        """
        pass
```

## 使用示例

### 简化后的 Agent 实现

```python
class HotelBookingAgent(SessionAgentBase):
    """酒店预订 Agent"""
    
    async def _process(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        """Agent 只关心业务逻辑"""
        
        # 检查是否有城市信息
        if not self._has_city(query, context):
            # 需要更多信息，返回 WAITING_INPUT
            # 不需要关心 session_id
            return AgentResponse(
                agent=self.name,
                query=query,
                message="请问您想预订哪个城市的酒店？",
                status=AgentStatus.WAITING_INPUT,
                prompt="请说出城市名称",
                data={"waiting_for": "city"}
            )
        
        # 检查是否有日期信息
        if not self._has_date(query, context):
            return AgentResponse(
                agent=self.name,
                query=query,
                message="请问入住日期是？",
                status=AgentStatus.WAITING_INPUT,
                prompt="请说出日期",
                data={"waiting_for": "date"}
            )
        
        # 信息齐全，执行预订
        result = self._book_hotel(query, context)
        
        # 完成，返回结果
        # 不需要关心 session_id
        return AgentResponse(
            agent=self.name,
            query=query,
            message=f"已为您预订{result['hotel']}",
            status=AgentStatus.COMPLETED,
            data=result
        )
```

### adapter 的处理流程

```
用户："我想订酒店"
    ↓
agent_adapter:
    1. create_session(agent="hotel_booking", priority=2)
       → session_id: "abc123"
    2. execute_agent()
    ↓
HotelBookingAgent:
    - 判断：缺少城市信息
    - 返回：AgentResponse(status=WAITING_INPUT, message="请问您想预订哪个城市的酒店？")
    ↓
agent_adapter:
    3. 检测到 WAITING_INPUT
    4. 设置 response.session_id = "abc123"
    5. wait_for_input("abc123", "请问您想预订哪个城市的酒店？")
    ↓
用户："北京"
    ↓
agent_adapter:
    1. 恢复 session "abc123"
    2. execute_agent(context={"session_id": "abc123", "city": "北京"})
    ↓
HotelBookingAgent:
    - 判断：有城市，缺少日期
    - 返回：AgentResponse(status=WAITING_INPUT, message="请问入住日期是？")
    ↓
agent_adapter:
    3. 保持 session "abc123"
    4. wait_for_input("abc123", "请问入住日期是？")
    ↓
...（继续多轮对话）
    ↓
HotelBookingAgent:
    - 判断：信息齐全
    - 执行预订
    - 返回：AgentResponse(status=COMPLETED, message="已为您预订...")
    ↓
agent_adapter:
    3. 检测到 COMPLETED
    4. complete_session("abc123")
    5. 发送 TTS 播报
```

## 设计优势

### 1. 更清晰的职责划分

| 层级 | 职责 | 不关心 |
|------|------|--------|
| **Agent** | 业务逻辑判断 | session_id, 优先级, session 栈 |
| **Adapter** | Session 管理, 协调 | 业务逻辑细节 |

### 2. Agent 实现更简单

**旧代码**（复杂）：
```python
async def _new_process(self, query, msg_id, session: AgentSession):
    # 需要管理 session
    if not self._has_city(query):
        return self.ask_user(session.session_id, "请问城市？")
    ...
    return self.complete_session(session.session_id, "已预订")
```

**新代码**（简洁）：
```python
async def _process(self, query, context):
    # 只关心业务逻辑
    if not self._has_city(query):
        return AgentResponse(..., status=WAITING_INPUT)
    ...
    return AgentResponse(..., status=COMPLETED)
```

### 3. 更容易测试

```python
# Agent 测试：只测试业务逻辑
async def test_hotel_booking_agent():
    agent = HotelBookingAgent()
    
    # 测试：缺少城市信息
    response = await agent._process("我想订酒店")
    assert response.status == AgentStatus.WAITING_INPUT
    assert "城市" in response.message
    
    # 测试：提供完整信息
    response = await agent._process(
        "北京，明天", 
        context={"city": "北京", "date": "明天"}
    )
    assert response.status == AgentStatus.COMPLETED
```

### 4. 统一的 session 管理策略

所有 Agent 的 session 管理都在 adapter 层统一处理：
- 优先级检查
- Session 创建
- Session 栈维护
- Session 生命周期管理

### 5. 更好的扩展性

**添加新功能**只需修改 adapter 层：
- 添加 session 超时机制：在 adapter 处理
- 添加 session 持久化：在 adapter 处理
- 添加 session 恢复机制：在 adapter 处理

**Agent 层无需改动**。

## 迁移指南

### 旧的 SessionAgentBase

```python
class OldAgent(SessionAgentBase):
    async def _new_process(self, query, msg_id, session: AgentSession):
        if need_more_info:
            return self.ask_user(session.session_id, "请问...")
        return self.complete_session(session.session_id, "完成")
    
    async def _resume_process(self, query, msg_id, session_id, context):
        ...
```

### 新的 SessionAgentBase

```python
class NewAgent(SessionAgentBase):
    async def _process(self, query, context=None):
        if need_more_info:
            return AgentResponse(
                agent=self.name,
                query=query,
                message="请问...",
                status=AgentStatus.WAITING_INPUT
            )
        return AgentResponse(
            agent=self.name,
            query=query,
            message="完成",
            status=AgentStatus.COMPLETED
        )
```

## 总结

通过将 session 管理职责从 Agent 层移到 adapter 层：

✅ **Agent 更简单** - 只关心业务逻辑
✅ **职责更清晰** - 每层做自己该做的事
✅ **更易测试** - Agent 测试不需要 mock session
✅ **更易维护** - Session 管理集中在一处
✅ **更易扩展** - 添加 session 功能无需改 Agent

这是一个更符合软件工程原则的设计！
