# Agent快速参考指南

> **深入阅读**:
> - [ToolAgentBase 多轮交互设计](TOOLAGENT_MULTIROUND_DESIGN.md) - 如何使用 WAITING_INPUT 实现灵活的多轮交互
> - [完整架构文档](AGENT_BASE_CLASSES.md) - 详细的类说明和迁移指南

## 🎯 我应该使用哪个基类？

### 快速决策树

```
我的Agent需要：
│
├─ 复杂的多步骤流程 + 显式会话状态管理？
│   └─ 是 → 使用 SessionAgentBase
│       示例：酒店预订（需要收集多个信息）、复杂行程规划
│
└─ 否 → 根据功能选择
    │
    ├─ 需要调用外部工具/API？
    │   └─ 是 → 使用 ToolAgentBase
    │       示例：导航、音乐控制、车辆控制
    │       注：支持单轮和多轮（通过WAITING_INPUT）
    │
    └─ 否 → 使用 SimpleAgentBase
        示例：天气查询、简单问答、状态查询
```

## 📚 三种基类对比

| 特性 | SimpleAgentBase | ToolAgentBase | SessionAgentBase |
|------|----------------|---------------|------------------|
| **继承关系** | 独立 | 继承SimpleAgentBase | 独立 |
| **接口方式** | 同步 | 同步 | 异步 |
| **对话轮数** | 单轮 | 灵活（单轮/多轮） | 多轮 |
| **返回类型** | AgentResponse | AgentResponse | SessionResponse |
| **状态管理** | ❌ | 通过status实现 | ✅显式管理 |
| **会话恢复** | ❌ | ❌ | ✅ |
| **LLM集成** | 自行处理 | ✅内置 | 自行处理 |
| **工具调用** | 自行处理 | ✅内置 | 自行处理 |
| **多轮支持** | ❌ | ✅WAITING_INPUT | ✅显式管理 |
| **复杂度** | 低 | 中 | 高 |

## 🚀 快速开始

### 1. SimpleAgentBase - 最简单

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
        city = self.extract_city(query)
        weather = self.get_weather(city)
        
        return AgentResponse(
            agent=self.name,
            success=True,
            query=query,
            message=f"{city}今天{weather['condition']}，{weather['temp']}度",
            data=weather
        )
```

### 2. ToolAgentBase - 集成工具

**单轮交互示例**（有足够信息，直接执行）：
```python
from src.agents.base_classes import ToolAgentBase, AgentResponse

class MusicAgent(ToolAgentBase):
    def __init__(self):
        super().__init__(
            name="music_agent",
            description="音乐播放助手",
            capabilities=["音乐", "播放"],
            api_key=os.getenv("DASHSCOPE_API_KEY")
        )
    
    def get_available_tools(self):
        return [{
            "type": "function",
            "function": {
                "name": "play_music",
                "description": "播放音乐",
                "parameters": {...}
            }
        }]
    
    def execute_tool(self, tool_name, tool_args):
        if tool_name == "play_music":
            return self.music_service.play(tool_args['song'])
```

**多轮交互示例**（信息不足时，请求用户补充）：
```python
# LLM 会自动判断是否需要更多信息
# 如果用户说："播放音乐"（没有指定歌曲名）
# LLM 可以选择不调用工具，而是返回：
AgentResponse(
    agent="music_agent",
    status=AgentStatus.WAITING_INPUT,
    query="播放音乐",
    message="好的，请问想听什么歌？",
    prompt="请说出歌曲名称",
    session_id="generated_session_id"
)

# 用户回复："周杰伦的晴天"
# 然后 LLM 调用工具 play_music(song="晴天", artist="周杰伦")
```

### 3. SessionAgentBase - 多轮对话

```python
from src.agents.base_classes import SessionAgentBase, SessionResponse

class HotelAgent(SessionAgentBase):
    def __init__(self):
        super().__init__(
            name="hotel_agent",
            description="酒店预订",
            capabilities=["酒店", "预订"]
        )
    
    async def _new_process(self, query, msg_id, session):
        """开始收集信息"""
        return self.ask_user(
            session.session_id,
            "请问哪个城市？",
            "location"
        )
    
    async def _resume_process(self, query, msg_id, session_id, context):
        """继续收集信息"""
        result = await self.book_hotel(query)
        return self.complete_session(session_id, result, "预订成功！")
```

## 📦 导入方式

```python
# 推荐：直接使用基类名
from src.agents.base_classes import (
    SimpleAgentBase,
    SessionAgentBase,
    ToolAgentBase,
    AgentResponse,
    SessionResponse
)

# 或从包级别导入
from src.agents import SimpleAgentBase, SessionAgentBase

# 向后兼容别名
from src.agents import SimpleAgent, SessionAwareAgent
```

## 📖 更多资源

- [完整架构文档](AGENT_BASE_CLASSES.md) - 详细的类说明和迁移指南
- [会话管理集成](SESSION_MANAGEMENT_INTEGRATION.md) - 多轮对话实现细节
