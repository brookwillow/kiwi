# Agent系统重构文档

## 概述

本次重构将原来硬编码响应的Agent系统改造成基于LLM的智能工具调用系统。通过使用qwen-plus模型的function calling能力，Agent能够根据用户意图自动选择和执行合适的工具，实现真正的智能化响应。

## 架构变更

### 重构前
```
User Query -> Agent -> Hardcoded Response
```

所有Agent（除chat_agent外）的响应都是硬编码的，例如：
```python
# 旧的weather_agent
def handle(self, query, context):
    return AgentResponse(
        agent=self.name,
        success=True,
        message="今天天气不错，温度适宜。"  # 硬编码
    )
```

### 重构后
```
User Query -> BaseToolAgent -> LLM (qwen-plus) -> Tool Selection -> Tool Execution -> LLM Response
```

新的智能流程：
1. BaseToolAgent接收用户查询
2. 调用qwen-plus模型理解意图并选择工具
3. 执行选中的工具（通过ToolRegistry）
4. LLM根据工具执行结果生成自然语言响应

## 核心组件

### 1. BaseToolAgent (`src/agents/handlers/base_tool_agent.py`)

新增的基础类，所有需要工具调用的Agent都继承自它。

**核心功能：**
- 初始化qwen-plus客户端（通过OpenAI兼容接口）
- 管理可用工具列表（基于ToolCategory）
- 实现智能handle()流程：
  - 构建系统提示词（包含Agent能力和上下文）
  - 调用LLM进行function calling
  - 执行工具并收集结果
  - 生成最终用户友好的响应

**关键方法：**
```python
def handle(self, query: str, context: AgentContext) -> AgentResponse:
    """同步接口，内部使用asyncio.run处理异步逻辑"""
    
async def _async_handle(self, query: str, context: AgentContext) -> AgentResponse:
    """异步实现：LLM调用 -> 工具执行 -> 响应生成"""
    
async def _handle_tool_calls(self, query: str, message, messages) -> AgentResponse:
    """处理LLM返回的工具调用列表"""
    
def _build_system_prompt(self, context: AgentContext) -> str:
    """构建包含Agent能力和对话历史的系统提示词"""
```

**配置参数：**
- `api_key`: DASHSCOPE_API_KEY（从环境变量读取）
- `base_url`: https://dashscope.aliyuncs.com/compatible-mode/v1
- `model`: qwen-plus
- `tool_categories`: 该Agent可使用的工具类别列表

**架构设计：**
- 使用`ExecutionManager`作为统一执行接口（而不是直接使用ToolRegistry）
- `ExecutionManager`封装了工具注册、工具执行、车辆状态管理等功能
- 遵循单一职责和依赖注入原则

### 2. 重构的Agent处理器

所有原有的Agent（除chat_agent外）都已重构：

#### WeatherAgent (`src/agents/handlers/weather.py`)
```python
class WeatherAgent(BaseToolAgent):
    def __init__(self, description: str, capabilities: list[str], api_key: Optional[str] = None):
        super().__init__(
            name="weather_agent",
            description=description,
            capabilities=capabilities,
            tool_categories=[ToolCategory.INFORMATION],  # 天气相关工具
            api_key=api_key
        )
```

#### MusicAgent (`src/agents/handlers/music.py`)
```python
class MusicAgent(BaseToolAgent):
    def __init__(self, description: str, capabilities: list[str], api_key: Optional[str] = None):
        super().__init__(
            name="music_agent",
            description=description,
            capabilities=capabilities,
            tool_categories=[ToolCategory.ENTERTAINMENT],  # 娱乐/音乐工具
            api_key=api_key
        )
```

#### NavigationAgent (`src/agents/handlers/navigation.py`)
```python
class NavigationAgent(BaseToolAgent):
    def __init__(self, description: str, capabilities: list[str], api_key: Optional[str] = None):
        super().__init__(
            name="navigation_agent",
            description=description,
            capabilities=capabilities,
            tool_categories=[ToolCategory.NAVIGATION],  # 导航工具
            api_key=api_key
        )
```

#### VehicleControlAgent (`src/agents/handlers/vehicle.py`)
```python
class VehicleControlAgent(BaseToolAgent):
    def __init__(self, description: str, capabilities: list[str], api_key: Optional[str] = None):
        super().__init__(
            name="vehicle_control_agent",
            description=description,
            capabilities=capabilities,
            tool_categories=[
                ToolCategory.VEHICLE_CONTROL,
                ToolCategory.CLIMATE,
                ToolCategory.WINDOW,
                ToolCategory.SEAT
            ],
            api_key=api_key
        )
```

### 3. Agent注册和初始化

#### 更新的registry.py
```python
def create_agent(name: str, description: str, capabilities: list[str], api_key: str = None) -> BaseAgent:
    cls = get_agent_class(name)
    if cls:
        return cls(description=description, capabilities=capabilities, api_key=api_key)
    return GenericAgent(name=name, description=description, capabilities=capabilities)
```

**变更点：**
- 新增`api_key`参数
- 所有Agent实例化时都会接收api_key

#### 更新的agent_manager.py
```python
def initialize(self) -> bool:
    # 从环境变量获取API密钥
    import os
    api_key = os.getenv('DASHSCOPE_API_KEY')
    if not api_key:
        print("⚠️  未设置DASHSCOPE_API_KEY环境变量，智能工具调用功能将不可用")
    
    # 创建Agent时传递api_key
    for agent in self._agents:
        if agent.get('enabled', True):
            handler = create_agent(
                name=agent.get('name'),
                description=agent.get('description', ''),
                capabilities=agent.get('capabilities', []),
                api_key=api_key  # 传递API密钥
            )
            self._agent_handlers[handler.name] = handler
```

**变更点：**
- 在初始化时读取`DASHSCOPE_API_KEY`环境变量
- 如果未设置，打印警告信息
- 将api_key传递给所有Agent

## 工具系统集成

### ExecutionManager（统一执行接口）
BaseToolAgent通过`ExecutionManager`访问所有执行模块功能：

```python
# 初始化执行管理器
self.execution_manager = ExecutionManager()

# 获取可用工具
self.available_tools = self._get_available_tools()

def _get_available_tools(self) -> List[Dict]:
    tools = []
    for category in self.tool_categories:
        category_tools = self.execution_manager.list_tools(category)
        tools.extend([tool.to_mcp_schema() for tool in category_tools])
    return tools

# 执行工具
result = await self.execution_manager.execute_tool(tool_name, **arguments)
```

**ExecutionManager优势：**
- 统一的对外接口，隐藏内部实现细节
- 封装了ToolRegistry、VehicleStateManager、MCPServer
- 便于测试和Mock
- 符合依赖倒置原则

### ToolRegistry
ToolRegistry是ExecutionManager内部使用的工具注册中心，外部代码不应直接访问。

### 工具类别（ToolCategory）
```python
class ToolCategory(Enum):
    VEHICLE_CONTROL = "vehicle_control"     # 车辆控制
    CLIMATE = "climate"                     # 空调控制
    ENTERTAINMENT = "entertainment"         # 娱乐系统
    NAVIGATION = "navigation"               # 导航
    INFORMATION = "information"             # 信息查询
    WINDOW = "window"                       # 车窗控制
    SEAT = "seat"                          # 座椅控制
    LIGHTING = "lighting"                   # 灯光控制
    DOOR = "door"                          # 车门控制
```

### 工具执行流程
```python
# 1. LLM返回工具调用
tool_calls = message.tool_calls  # [{"function": {"name": "set_temperature", "arguments": "{\"temperature\": 24}"}}]

# 2. 通过ExecutionManager执行工具
for tool_call in tool_calls:
    tool_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)
    
    # 使用ExecutionManager统一接口执行工具
    result = await self.execution_manager.execute_tool(tool_name, **arguments)
    
    # 3. 将结果添加到消息历史
    messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)})

# 4. LLM根据工具结果生成最终响应
final_response = self.client.chat.completions.create(model=self.model, messages=messages)
```

## 同步/异步处理

由于原有系统是同步的，但工具执行需要异步（`tool.execute()`是async），我们采用了混合方案：

```python
def handle(self, query: str, context: AgentContext) -> AgentResponse:
    """同步接口供外部调用"""
    try:
        return asyncio.run(self._async_handle(query, context))
    except RuntimeError as e:
        # 处理已存在事件循环的情况
        if "cannot be called from a running event loop" in str(e):
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self._async_handle(query, context))
        raise

async def _async_handle(self, query: str, context: AgentContext) -> AgentResponse:
    """内部异步实现"""
    # ... LLM调用和工具执行
```

## 配置要求

### 环境变量
```bash
export DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxx"
```

获取API密钥：https://dashscope.aliyun.com/

### 依赖包
已更新`requirements.txt`：
```
openai>=1.0.0  # For qwen function calling via DashScope API
```

安装：
```bash
pip install -r requirements.txt
```

## 使用示例

### 示例1：天气查询
```
用户: "今天天气怎么样？"

流程:
1. WeatherAgent接收查询
2. qwen-plus理解意图 -> 选择get_weather工具
3. 执行get_weather(location="当前位置", time="今天")
4. 工具返回: {"temperature": 24, "condition": "晴朗"}
5. LLM生成响应: "今天天气晴朗，温度24度，适合出行。"
```

### 示例2：车辆控制
```
用户: "把空调温度调到25度，打开前排左侧车窗"

流程:
1. VehicleControlAgent接收查询
2. qwen-plus理解意图 -> 选择set_temperature和control_window工具
3. 并行执行:
   - set_temperature(temperature=25, zone="driver")
   - control_window(window="front_left", action="open", percentage=100)
4. 工具返回执行结果
5. LLM生成响应: "好的，已将空调温度调到25度，并打开前排左侧车窗。"
```

### 示例3：音乐播放
```
用户: "播放周杰伦的稻香"

流程:
1. MusicAgent接收查询
2. qwen-plus理解意图 -> 选择search_music和play_music工具
3. 顺序执行:
   - search_music(query="周杰伦 稻香") -> 返回歌曲ID
   - play_music(song_id="xxx")
4. LLM生成响应: "正在为您播放周杰伦的《稻香》。"
```

## 系统提示词示例

BaseToolAgent为每个查询构建的系统提示词：

```
你是天气查询Agent，负责查询天气信息。

你的能力：
- 查询当前天气
- 查询未来天气
- 天气预警
- 空气质量查询

你可以使用以下工具来完成任务。请根据用户的需求选择合适的工具。

重要提示：
1. 仔细理解用户意图，选择最合适的工具
2. 如果需要多个步骤，可以依次调用多个工具
3. 执行工具后，用自然语言总结结果给用户
4. 保持回复简洁友好，不超过100字
5. 如果无法完成请求，礼貌地说明原因

最近的对话：
用户: 现在几点了
助手: 现在是下午3点30分。
用户: 今天天气怎么样？
```

## 回退机制

如果API密钥未配置或LLM调用失败：

```python
if not self.client:
    return AgentResponse(
        agent=self.name,
        success=False,
        query=query,
        message="未配置API密钥，无法使用智能工具调用",
        data={}
    )
```

## 监控和调试

系统会打印详细的执行日志：

```
🔧 调用工具: set_temperature
   参数: {'temperature': 25, 'zone': 'driver'}
✅ 工具执行成功: {'success': True, 'message': '已将温度设置为25度'}
```

失败时：
```
❌ weather_agent 处理失败: API调用超时
```

## 性能考虑

1. **LLM调用延迟**: qwen-plus通常在1-3秒内返回
2. **工具执行**: 大部分工具执行时间<100ms
3. **总响应时间**: 通常2-5秒（包含LLM推理和工具执行）

优化建议：
- 使用流式输出（未实现）
- 缓存常见查询结果
- 并行执行独立工具调用

## 测试

运行系统测试：
```bash
python main.py
```

设置环境变量：
```bash
export DASHSCOPE_API_KEY="your-key-here"
python main.py
```

## 未来改进

1. **流式响应**: 支持LLM流式输出，提升用户体验
2. **工具链优化**: 智能规划多步骤工具调用顺序
3. **上下文增强**: 更好地利用对话历史和长期记忆
4. **错误恢复**: 工具失败时的自动重试和降级策略
5. **性能监控**: 添加详细的性能指标和追踪

## 总结

本次重构实现了从硬编码响应到智能工具调用的完整转变，使Agent系统具备了真正的理解和执行能力。通过qwen-plus的function calling能力和ToolRegistry的工具管理，系统能够灵活应对各种用户需求，并提供更自然、更准确的响应。
