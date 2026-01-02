# Agent系统快速参考

## 启动系统

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置API密钥
export DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxx"

# 3. 运行系统
python main.py
```

## 创建新Agent

### 1. 定义Agent类

```python
# src/agents/handlers/my_agent.py
from src.agents.handlers.base_tool_agent import BaseToolAgent
from src.execution.tool_registry import ToolCategory

class MyAgent(BaseToolAgent):
    name = "my_agent"
    
    def __init__(self, description: str, capabilities: list[str], api_key: Optional[str] = None):
        super().__init__(
            name=self.name,
            description=description,
            capabilities=capabilities,
            tool_categories=[
                ToolCategory.YOUR_CATEGORY,  # 选择合适的工具类别
            ],
            api_key=api_key
        )
```

### 2. 注册Agent

在`src/agents/registry.py`中添加：

```python
from src.agents.handlers.my_agent import MyAgent

def get_agent_class(name: str):
    registry: Dict[str, Type[BaseAgent]] = {
        # ... 现有agents
        "my_agent": MyAgent,  # 添加新agent
    }
    return registry.get(name)
```

### 3. 配置Agent

在`config/agents_config.yaml`中添加：

```yaml
agents:
  # ... 现有agents
  - name: "my_agent"
    description: "我的自定义Agent"
    enabled: true
    capabilities:
      - "功能1"
      - "功能2"
```

## 工具类别选择

根据Agent功能选择合适的工具类别：

| 工具类别 | 说明 | 示例工具 |
|---------|------|---------|
| VEHICLE_CONTROL | 车辆基础控制 | 启动/停止引擎 |
| CLIMATE | 空调控制 | 设置温度、风速 |
| ENTERTAINMENT | 娱乐系统 | 音乐播放、收音机 |
| NAVIGATION | 导航 | 路线规划、地点搜索 |
| INFORMATION | 信息查询 | 天气、新闻 |
| WINDOW | 车窗控制 | 开关车窗 |
| SEAT | 座椅控制 | 调节座椅位置 |
| LIGHTING | 灯光控制 | 开关车灯 |
| DOOR | 车门控制 | 锁定/解锁 |

## 调试技巧

### 查看工具调用日志

系统会自动打印工具调用信息：

```
🔧 调用工具: set_temperature
   参数: {'temperature': 25}
```

### 处理错误

检查常见问题：

1. **未配置API密钥**
   ```
   ⚠️  未设置DASHSCOPE_API_KEY环境变量
   ```
   解决：`export DASHSCOPE_API_KEY="your-key"`

2. **LLM调用失败**
   ```
   ❌ weather_agent 处理失败: API调用超时
   ```
   解决：检查网络连接或API配额

3. **工具未找到**
   ```
   ❌ 工具 xxx 未找到
   ```
   解决：检查ToolRegistry中是否注册了该工具

## API说明

### BaseToolAgent.handle()

```python
def handle(self, query: str, context: AgentContext = None) -> AgentResponse:
    """
    处理用户查询
    
    Args:
        query: 用户查询文本
        context: Agent上下文（包含对话历史、长期记忆、系统状态）
    
    Returns:
        AgentResponse: 包含执行结果的响应对象
    """
```

### AgentResponse

```python
@dataclass
class AgentResponse:
    agent: str           # Agent名称
    success: bool        # 是否成功
    query: str          # 原始查询
    message: str        # 返回给用户的消息
    data: Dict[str, Any] # 额外数据（工具结果等）
```

### AgentContext

```python
@dataclass
class AgentContext:
    short_term_memories: List[ShortTermMemory]  # 最近对话
    long_term_memory: Optional[LongTermMemory]  # 长期记忆
    system_states: List[SystemState]            # 系统状态
```

## 常见用例

### 单工具调用

```python
用户: "把温度调到23度"
→ LLM选择: set_temperature(temperature=23)
→ 执行工具
→ 返回: "已将温度设置为23度"
```

### 多工具调用

```python
用户: "把空调开到25度，打开天窗"
→ LLM选择: 
  1. set_temperature(temperature=25)
  2. control_window(window="sunroof", action="open")
→ 并行执行工具
→ 返回: "已将空调温度设为25度，并打开天窗"
```

### 工具链调用

```python
用户: "播放周杰伦的歌"
→ LLM规划:
  1. search_music(query="周杰伦") → 返回歌曲列表
  2. play_music(song_id=搜索结果[0].id)
→ 顺序执行
→ 返回: "正在播放周杰伦的《稻香》"
```

## 环境变量

```bash
# 必需
export DASHSCOPE_API_KEY="sk-xxxxx"        # 阿里云DashScope API密钥

# 可选
export OLLAMA_MODEL="qwen3:8b"            # chat_agent使用的模型
export OLLAMA_URL="http://localhost:11434" # Ollama服务地址
```

## 获取API密钥

1. 访问：https://dashscope.aliyun.com/
2. 注册/登录阿里云账号
3. 创建API密钥
4. 复制密钥到环境变量

## 文件结构

```
src/agents/
├── __init__.py
├── base.py                          # AgentResponse, BaseAgent协议
├── registry.py                      # Agent注册表
├── agent_manager.py                 # AgentsModule（IModule实现）
└── handlers/
    ├── base_tool_agent.py          # 基础工具Agent类
    ├── weather.py                  # 天气Agent
    ├── music.py                    # 音乐Agent
    ├── navigation.py               # 导航Agent
    ├── vehicle.py                  # 车辆控制Agent
    └── chat.py                     # 闲聊Agent（不使用工具）
```

## 性能优化

### 减少LLM调用延迟

```python
# 使用更简洁的系统提示词
def _build_system_prompt(self, context):
    # 只包含必要信息
    return f"你是{self.description}。处理用户请求时选择合适的工具。"
```

### 缓存常见查询

```python
# 在Agent类中添加缓存
from functools import lru_cache

@lru_cache(maxsize=100)
def _cached_tool_call(self, tool_name: str, args_hash: str):
    # 缓存工具执行结果
    pass
```

## 故障排查

### 问题：Agent响应慢

**可能原因：**
1. LLM API延迟高
2. 工具执行时间长
3. 网络问题

**解决：**
```bash
# 检查API响应时间
curl -X POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -d '{"model":"qwen-plus","messages":[{"role":"user","content":"test"}]}'
```

### 问题：工具未被调用

**可能原因：**
1. 工具类别未匹配
2. 系统提示词不清晰
3. LLM理解偏差

**解决：**
- 检查Agent的tool_categories配置
- 优化系统提示词
- 查看LLM调用日志

### 问题：API密钥无效

**错误信息：**
```
❌ 未配置API密钥，无法使用智能工具调用
```

**解决：**
```bash
# 检查环境变量
echo $DASHSCOPE_API_KEY

# 重新设置
export DASHSCOPE_API_KEY="sk-xxxxx"

# 验证密钥
python -c "import os; print(os.getenv('DASHSCOPE_API_KEY'))"
```

## 更多资源

- [完整重构文档](./AGENT_REFACTORING.md)
- [工具注册中心文档](./EXECUTION_MODULE.md)
- [Orchestrator集成](./ORCHESTRATOR_INTEGRATION.md)
- [阿里云DashScope文档](https://help.aliyun.com/zh/dashscope/)
