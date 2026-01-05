# Agent系统架构说明

## ⚠️ 重要更新

**本文档描述的是旧的Agent架构。新的统一基类架构请参考：**
- [Agent基类架构 (AGENT_BASE_CLASSES.md)](AGENT_BASE_CLASSES.md) - 新的统一基类体系
- [Agent快速参考 (AGENT_QUICK_REFERENCE.md)](AGENT_QUICK_REFERENCE.md) - 快速选择指南

---

## 整体架构（旧版本）

```
┌─────────────────────────────────────────────────────────────┐
│                       AgentsModule                          │
│  (IModule接口实现 - src/agents/agent_manager.py)            │
└─────────────────┬───────────────────────────────────────────┘
                  │ 初始化并管理所有Agent
                  │
        ┌─────────┴─────────────────────┐
        │                               │
        ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│   ChatAgent      │          │  BaseToolAgent   │
│  (闲聊对话)       │          │  (工具调用基类)   │
└──────────────────┘          └────────┬─────────┘
                                       │ 继承
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
            ┌───────▼───────┐  ┌──────▼──────┐  ┌───────▼────────┐
            │ WeatherAgent  │  │ MusicAgent  │  │ VehicleAgent  │
            │ NavigationAgent│  │   ...       │  │   ...         │
            └───────┬───────┘  └──────┬──────┘  └───────┬────────┘
                    │                  │                  │
                    └──────────────────┼──────────────────┘
                                       │ 使用
                                       ▼
                           ┌────────────────────┐
                           │ ExecutionManager   │
                           │  (统一执行接口)     │
                           └─────────┬──────────┘
                                     │ 封装
                    ┌────────────────┼────────────────┐
                    │                │                │
            ┌───────▼────────┐ ┌────▼────────┐ ┌────▼────────┐
            │ ToolRegistry   │ │ VehicleState│ │ MCPServer   │
            │  (工具注册)     │ │  (车辆状态)  │ │ (MCP协议)   │
            └────────────────┘ └─────────────┘ └─────────────┘
```

## 关键原则

### 1. 统一接口原则

❌ **错误做法**：Agent直接访问ToolRegistry
```python
class BaseToolAgent:
    def __init__(self):
        self.tool_registry = ToolRegistry()  # 直接依赖
        tool = self.tool_registry.get_tool("xxx")
```

✅ **正确做法**：Agent通过ExecutionManager访问
```python
class BaseToolAgent:
    def __init__(self):
        self.execution_manager = ExecutionManager()  # 统一接口
        result = await self.execution_manager.execute_tool("xxx")
```

**优势：**
- 解耦：Agent不需要知道工具系统的内部实现
- 灵活：可以轻松替换底层实现（如Mock测试）
- 可维护：修改工具系统不影响Agent代码
- 安全：统一的权限控制和错误处理

### 2. 职责分离

```
AgentsModule        → 管理Agent生命周期、配置加载、Agent路由
BaseToolAgent       → LLM调用、工具选择、响应生成
ExecutionManager    → 工具执行、状态管理、统一接口
ToolRegistry        → 工具注册、查询（内部使用）
```

### 3. 依赖注入

```python
# AgentsModule创建Agent时注入API密钥
handler = create_agent(
    name=agent.get('name'),
    description=agent.get('description', ''),
    capabilities=agent.get('capabilities', []),
    api_key=api_key  # 注入依赖
)

# BaseToolAgent内部创建ExecutionManager
class BaseToolAgent:
    def __init__(self, ..., api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.execution_manager = ExecutionManager()  # 内部依赖
```

## 数据流

### 用户查询处理流程

```
用户输入 "把温度调到25度"
    │
    ├─> Orchestrator（决策）
    │       └─> 选择 vehicle_control_agent
    │
    ├─> AgentsModule.execute_agent()
    │       └─> VehicleControlAgent.handle()
    │
    ├─> BaseToolAgent._async_handle()
    │       ├─> 构建系统提示词（包含能力、上下文）
    │       ├─> 调用qwen-plus LLM
    │       └─> LLM返回：tool_calls=[{"name": "set_temperature", "args": {"temperature": 25}}]
    │
    ├─> BaseToolAgent._handle_tool_calls()
    │       └─> execution_manager.execute_tool("set_temperature", temperature=25)
    │
    ├─> ExecutionManager.execute_tool()
    │       ├─> tool = registry.get_tool("set_temperature")
    │       ├─> result = await tool.execute(temperature=25)
    │       └─> 更新 VehicleState.temperature = 25
    │
    ├─> BaseToolAgent（收到工具结果）
    │       ├─> 将结果添加到消息历史
    │       ├─> 再次调用qwen-plus LLM生成响应
    │       └─> LLM返回："好的，已将温度设置为25度"
    │
    └─> AgentResponse返回给用户
            └─> TTS播报："好的，已将温度设置为25度"
```

## API层次结构

### Level 1: 外部系统接口
```python
# Orchestrator Adapter调用
agents_module.execute_agent(agent_name="vehicle_control_agent", query="...")
```

### Level 2: Agent接口
```python
# VehicleControlAgent（继承BaseToolAgent）
agent.handle(query="把温度调到25度", context=AgentContext(...))
```

### Level 3: 执行管理器接口
```python
# ExecutionManager（统一接口）
execution_manager.execute_tool("set_temperature", temperature=25)
execution_manager.list_tools(ToolCategory.CLIMATE)
execution_manager.get_state_value("temperature")
```

### Level 4: 内部实现（不对外暴露）
```python
# ToolRegistry（内部）
registry.get_tool("set_temperature")
tool.execute(**kwargs)

# VehicleStateManager（内部）
vehicle_state.set_value("temperature", 25)
```

## 配置流程

### 1. 环境变量配置
```bash
export DASHSCOPE_API_KEY="sk-xxxxx"  # qwen API密钥
export OLLAMA_MODEL="qwen3:8b"       # chat_agent使用的模型
export OLLAMA_URL="http://localhost:11434"
```

### 2. YAML配置文件
```yaml
# config/agents_config.yaml
agents:
  - name: "vehicle_control_agent"
    description: "车辆控制Agent"
    enabled: true
    capabilities:
      - "开关车窗"
      - "控制空调"
      - "调节座椅"
```

### 3. 代码配置
```python
# src/agents/handlers/vehicle.py
class VehicleControlAgent(BaseToolAgent):
    def __init__(self, description, capabilities, api_key):
        super().__init__(
            name="vehicle_control_agent",
            tool_categories=[
                ToolCategory.VEHICLE_CONTROL,
                ToolCategory.CLIMATE,
                ToolCategory.WINDOW,
                ToolCategory.SEAT
            ],
            api_key=api_key
        )
```

## 错误处理层次

### Level 1: API密钥检查
```python
if not self.client:
    return AgentResponse(
        success=False,
        message="未配置API密钥，无法使用智能工具调用"
    )
```

### Level 2: LLM调用异常
```python
try:
    response = self.client.chat.completions.create(...)
except Exception as e:
    return AgentResponse(success=False, message=f"LLM调用失败: {e}")
```

### Level 3: 工具执行异常
```python
result = await self.execution_manager.execute_tool(tool_name, **arguments)
if not result.get("success"):
    # 记录失败并继续处理其他工具
    tool_results.append({"success": False, "message": result.get("message")})
```

### Level 4: 降级响应
```python
# 如果所有工具都失败，返回降级响应
if not any(r.get("success") for r in tool_results):
    return AgentResponse(
        success=False,
        message="抱歉，操作执行失败，请稍后重试"
    )
```

## 扩展指南

### 添加新的工具类别

1. 在`ToolCategory`枚举中添加新类别
2. 在`tool_handlers.py`中注册对应的工具
3. 在Agent初始化时指定使用该类别

### 添加新的Agent

1. 创建新的Agent类继承`BaseToolAgent`
2. 在`registry.py`中注册
3. 在`agents_config.yaml`中配置
4. 指定该Agent使用的`tool_categories`

### 添加新的工具

1. 在`tool_handlers.py`中定义工具函数
2. 注册到`ToolRegistry`时指定类别和MCP schema
3. 工具会自动对拥有该类别的Agent可见

## 测试策略

### 单元测试

```python
# 测试ExecutionManager接口
async def test_execution_manager():
    manager = ExecutionManager()
    result = await manager.execute_tool("set_temperature", temperature=25)
    assert result["success"] == True
    assert manager.get_state_value("temperature") == 25
```

### Mock测试

```python
# Mock ExecutionManager用于测试Agent
class MockExecutionManager:
    async def execute_tool(self, tool_name, **kwargs):
        return {"success": True, "message": "Mock result"}

# 在BaseToolAgent中注入
agent.execution_manager = MockExecutionManager()
```

### 集成测试

```python
# 测试完整流程
async def test_agent_workflow():
    agent = VehicleControlAgent(...)
    response = agent.handle("把温度调到25度", context=...)
    assert response.success == True
    assert "25度" in response.message
```

## 性能优化

### 1. 工具并行执行
当工具调用相互独立时，可以并行执行：
```python
tasks = [execution_manager.execute_tool(name, **args) for name, args in tool_calls]
results = await asyncio.gather(*tasks)
```

### 2. 结果缓存
对于频繁查询的工具结果可以缓存：
```python
from functools import lru_cache

@lru_cache(maxsize=100)
async def cached_execute_tool(tool_name, args_hash):
    return await execution_manager.execute_tool(tool_name, ...)
```

### 3. LLM响应流式输出（未来）
```python
stream = self.client.chat.completions.create(
    model=self.model,
    messages=messages,
    stream=True
)
for chunk in stream:
    # 实时返回部分响应
    yield chunk.choices[0].delta.content
```

## 安全考虑

### 1. API密钥保护
- 从环境变量读取，不写入代码
- 不记录到日志文件
- 使用加密存储（生产环境）

### 2. 工具执行权限
- ExecutionManager统一控制工具访问
- 可以添加权限检查逻辑
- 记录所有工具调用审计日志

### 3. 输入验证
- ExecutionManager验证工具参数
- LLM输出解析异常处理
- 用户输入过滤和清理

## 总结

通过**ExecutionManager统一接口**的架构设计：
- ✅ Agent代码简洁，只关注LLM交互逻辑
- ✅ 工具系统可独立演进，不影响Agent
- ✅ 易于测试、Mock和扩展
- ✅ 清晰的职责划分和数据流
- ✅ 符合SOLID设计原则

**核心要点**：
> Agent应该通过`ExecutionManager`统一接口访问工具系统，而不是直接依赖`ToolRegistry`。这是良好架构设计的关键。
