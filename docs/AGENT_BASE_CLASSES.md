# Agent基类架构说明

> **相关文档**:
> - [ToolAgentBase 多轮交互设计说明](TOOLAGENT_MULTIROUND_DESIGN.md) - 详细说明如何通过 WAITING_INPUT 实现多轮交互
> - [快速参考指南](AGENT_QUICK_REFERENCE.md) - 快速选择合适的基类

## 当前问题

之前agents模块中存在3个不同的基类，使用方式不统一：

1. **BaseAgent (Protocol)** - 旧的协议定义，使用Protocol
2. **SessionAwareAgent (ABC)** - 支持会话管理的抽象基类
3. **BaseToolAgent** - 工具调用的具体基类

导致的问题：
- ❌ 命名混乱（BaseAgent是接口，BaseToolAgent是具体类）
- ❌ 返回类型不一致（AgentResponse vs Dict）
- ❌ 同步/异步混用
- ❌ 继承关系不清晰

## 新的统一架构

新创建的 `src/agents/base_classes.py` 提供了清晰的继承层次：

```
IAgent (Protocol) - 顶层协议接口
    │
    ├── SimpleAgentBase (ABC) - 简单Agent抽象基类
    │       │
    │       └── ToolAgentBase (ABC) - 工具调用Agent基类
    │
    └── SessionAgentBase (ABC) - 会话型Agent抽象基类
```

### 1. IAgent (Protocol)

顶层协议接口，定义所有Agent的基本契约：

```python
class IAgent(Protocol):
    name: str
    description: str
    capabilities: list[str]
    
    def can_handle(self, query: str) -> bool:
        ...
```

**用途**: 类型检查和接口定义

---

### 2. SimpleAgentBase (ABC)

简单Agent抽象基类，适用于不需要多轮对话的任务：

```python
class SimpleAgentBase(ABC):
    @abstractmethod
    def handle(self, query: str, context: Optional[Dict] = None) -> AgentResponse:
        pass
```

**特点**:
- ✅ 同步接口
- ✅ 单轮对话
- ✅ 返回 `AgentResponse`
- ✅ 适合简单快速的任务

**适用场景**:
- 天气查询
- 简单控制（开窗、关灯）
- 播放音乐
- 闲聊对话

**使用示例**:
```python
from src.agents.base_classes import SimpleAgentBase, AgentResponse

class WeatherAgent(SimpleAgentBase):
    def __init__(self):
        super().__init__(
            name="weather_agent",
            description="天气查询助手",
            capabilities=["天气", "温度", "降雨"]
        )
    
    def handle(self, query: str, context=None) -> AgentResponse:
        # 调用天气API
        weather_info = self.get_weather(query)
        
        return AgentResponse(
            agent=self.name,
            success=True,
            query=query,
            message=f"今天天气{weather_info['condition']}，温度{weather_info['temp']}度",
            data=weather_info
        )
```

---

### 3. SessionAgentBase (ABC)

会话型Agent抽象基类，支持多轮对话和状态管理：

```python
class SessionAgentBase(ABC):
    async def process(self, query, msg_id, session_id=None, context=None) -> SessionResponse:
        ...
    
    @abstractmethod
    async def _new_process(self, query, msg_id, session: AgentSession) -> SessionResponse:
        pass
    
    @abstractmethod
    async def _resume_process(self, query, msg_id, session_id, context) -> SessionResponse:
        pass
```

**特点**:
- ✅ 异步接口
- ✅ 支持多轮对话
- ✅ 返回 `SessionResponse`
- ✅ 自动管理会话状态
- ✅ 可以暂停和恢复

**适用场景**:
- 酒店预订（需要收集多个信息）
- 行程规划（多步骤确认）
- 复杂表单填写
- 工作流编排

**使用示例**:
```python
from src.agents.base_classes import SessionAgentBase, SessionResponse

class HotelBookingAgent(SessionAgentBase):
    def __init__(self):
        super().__init__(
            name="hotel_booking_agent",
            description="酒店预订助手",
            capabilities=["酒店", "预订", "住宿"]
        )
    
    async def _new_process(self, query, msg_id, session):
        """新会话：开始收集信息"""
        session.context['step'] = 'collect_city'
        
        return self.ask_user(
            session.session_id,
            "请问您想在哪个城市预订酒店？",
            "location"
        )
    
    async def _resume_process(self, query, msg_id, session_id, context):
        """恢复会话：继续收集信息"""
        step = context.get('step')
        session = self.session_manager.get_session(session_id)
        
        if step == 'collect_city':
            # 保存城市，询问日期
            session.context['city'] = query
            session.context['step'] = 'collect_date'
            
            return self.ask_user(
                session_id,
                f"好的，{query}。请问什么时候入住？",
                "date"
            )
        
        elif step == 'collect_date':
            # 保存日期，执行预订
            session.context['date'] = query
            result = await self.book_hotel(session.context)
            
            return self.complete_session(
                session_id,
                result,
                f"已为您预订{session.context['city']}的酒店"
            )
```

---

### 4. ToolAgentBase (ABC)

工具调用Agent基类，继承自SimpleAgentBase：

```python
class ToolAgentBase(SimpleAgentBase):
    @abstractmethod
    def get_available_tools(self) -> list[Dict]:
        pass
    
    @abstractmethod
    def execute_tool(self, tool_name: str, tool_args: Dict) -> Any:
        pass
```

**特点**:
- ✅ 集成LLM客户端
- ✅ 支持工具调用
- ✅ 继承SimpleAgentBase的简单接口
- ✅ **支持灵活的多轮交互**（通过返回 WAITING_INPUT）

**交互模式**:
1. **单轮模式**：信息充足时，直接调用工具并返回结果
2. **多轮模式**：当LLM判断信息不足、无法确定工具参数时，返回 `AgentStatus.WAITING_INPUT` 请求用户补充

**适用场景**:
- 导航（调用地图API）- 可单轮可多轮
- 音乐控制（调用播放器工具）- 可单轮可多轮
- 车辆控制（调用车载系统工具）- 可单轮可多轮

**设计优势**：
无需为多轮场景单独创建抽象，ToolAgentBase 本身就能根据LLM判断灵活切换单轮/多轮模式

**单轮交互示例**:
```python
# 用户："导航到北京故宫"（信息充足）
# LLM 直接调用工具：search_location(query="北京故宫")
# 返回：AgentResponse(status=SUCCESS, message="已为您规划前往故宫的路线")
```

**多轮交互示例**:
```python
# 用户："我想导航"（信息不足）
# LLM 判断缺少目的地，不调用工具，而是返回：
AgentResponse(
    agent="navigation_agent",
    status=AgentStatus.WAITING_INPUT,
    query="我想导航",
    message="好的，请问您要去哪里？",
    prompt="请说出目的地",
    session_id="auto_generated_session_id"
)

# 用户继续："去故宫"
# LLM 调用工具：search_location(query="故宫")
# 返回：AgentResponse(status=COMPLETED, message="已为您规划前往故宫的路线")
```

**实现示例**:
```python
from src.agents.base_classes import ToolAgentBase, AgentResponse

class NavigationAgent(ToolAgentBase):
    def __init__(self):
        super().__init__(
            name="navigation_agent",
            description="导航助手",
            capabilities=["导航", "路线", "地图"],
            tool_categories=[ToolCategory.NAVIGATION],
            api_key=os.getenv("DASHSCOPE_API_KEY")
        )
    
    # 无需重写 handle() 方法，基类已实现智能的单轮/多轮切换
    # LLM 会自动判断是否需要更多信息
```

---

## 响应数据类

### AgentResponse (SimpleAgentBase使用)

```python
@dataclass
class AgentResponse:
    agent: str
    success: bool
    query: str
    message: str
    data: Dict[str, Any]
```

### SessionResponse (SessionAgentBase使用)

```python
@dataclass
class SessionResponse:
    status: str  # waiting_input, completed, error
    agent: str
    session_id: Optional[str]
    response: str
    prompt: Optional[str]  # 如果waiting_input
    expected_input_type: Optional[str]
    result: Optional[Any]  # 如果completed
    error: Optional[str]  # 如果error
    need_tts: bool
```

---

## 迁移指南

### 从旧的BaseAgent (Protocol) 迁移

**旧代码**:
```python
from src.agents.base import BaseAgent, AgentResponse

class MyAgent:
    name = "my_agent"
    description = "..."
    capabilities = [...]
    
    def handle(self, query, context) -> AgentResponse:
        ...
```

**新代码**:
```python
from src.agents.base_classes import SimpleAgentBase, AgentResponse

class MyAgent(SimpleAgentBase):
    def __init__(self):
        super().__init__(
            name="my_agent",
            description="...",
            capabilities=[...]
        )
    
    def handle(self, query, context=None) -> AgentResponse:
        ...
```

### 从旧的SessionAwareAgent迁移

**旧代码**:
```python
from src.agents.session_aware_base import SessionAwareAgent

class MyAgent(SessionAwareAgent):
    def __init__(self):
        super().__init__("my_agent", "type", "...")
    
    async def _new_process(self, query, msg_id, session) -> Dict:
        return {
            'status': 'waiting_input',
            'prompt': '...',
            ...
        }
```

**新代码**:
```python
from src.agents.base_classes import SessionAgentBase, SessionResponse

class MyAgent(SessionAgentBase):
    def __init__(self):
        super().__init__(
            name="my_agent",
            description="...",
            capabilities=[...]
        )
    
    async def _new_process(self, query, msg_id, session) -> SessionResponse:
        return self.ask_user(
            session.session_id,
            '...',
            'text'
        )
```

### 从BaseToolAgent迁移

**旧代码**:
```python
from src.agents.handlers.base_tool_agent import BaseToolAgent

class MyAgent(BaseToolAgent):
    def __init__(self):
        super().__init__(
            name="my_agent",
            description="...",
            capabilities=[...],
            tool_categories=[ToolCategory.NAVIGATION]
        )
```

**新代码**:
```python
from src.agents.base_classes import ToolAgentBase, AgentResponse

class MyAgent(ToolAgentBase):
    def __init__(self):
        super().__init__(
            name="my_agent",
            description="...",
            capabilities=[...],
            api_key=os.getenv("DASHSCOPE_API_KEY")
        )
    
    def get_available_tools(self):
        # 实现工具列表
        ...
    
    def execute_tool(self, tool_name, tool_args):
        # 实现工具执行
        ...
    
    def handle(self, query, context=None) -> AgentResponse:
        # 实现处理逻辑
        ...
```

---

## 选择哪个基类？

### 决策树：

```
需要复杂的多轮会话管理？（如：预订酒店需要收集多个信息、复杂的状态管理）
├─ 是 → SessionAgentBase
│   └─ 适用于需要显式会话状态管理的复杂流程
│
└─ 否 → 根据功能需求选择
    ├─ 需要调用工具/API？
    │   └─ 是 → ToolAgentBase
    │       ├─ 支持单轮交互（有足够信息直接执行）
    │       └─ 支持多轮交互（信息不足时返回WAITING_INPUT请求补充）
    │
    └─ 否 → SimpleAgentBase
        └─ 简单查询、直接响应
```

---

## 向后兼容

为了不破坏现有代码，在 `base_classes.py` 中提供了类型别名：

```python
BaseAgent = IAgent  # Protocol
SessionAwareAgent = SessionAgentBase
SimpleAgent = SimpleAgentBase
```

现有代码可以继续使用旧名称，但建议逐步迁移到新的命名。

---

## 文件组织

```
src/agents/
├── __init__.py
├── base.py                    # 【废弃】旧的Protocol定义
├── base_classes.py            # 【推荐】新的统一基类
├── session_aware_base.py      # 【废弃】旧的会话基类
├── agent_manager.py           # Agent管理器
├── registry.py                # Agent注册表
├── handlers/                  # 具体Agent实现
│   ├── base_tool_agent.py    # 【可废弃】旧的工具Agent基类
│   ├── chat.py
│   ├── weather.py
│   ├── music.py
│   └── ...
└── domains/                   # 领域Agent
    └── workflow.py
```

---

## 下一步

1. ✅ 创建统一的base_classes.py
2. ⏳ 更新__init__.py导出新的基类
3. ⏳ 逐步迁移现有Agent到新基类
4. ⏳ 标记旧文件为废弃
5. ⏳ 更新文档和示例
