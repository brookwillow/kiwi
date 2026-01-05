# ToolAgentBase 多轮交互设计说明

## 核心设计理念

**ToolAgentBase 不是单纯的单轮交互Agent**。它能够根据 LLM 的判断，灵活地支持单轮和多轮交互模式，无需为多轮场景单独创建抽象。

## 设计原理

### 传统问题

之前的设计将 Agent 分为：
- `SimpleAgentBase` - 单轮交互
- `ToolAgentBase` - 单轮 + 工具调用
- `SessionAgentBase` - 多轮交互 + 显式会话管理

这种分类过于刚性，忽略了一个重要事实：**工具调用型 Agent 在实际使用中经常需要多轮交互**。

### 新设计

`ToolAgentBase` 支持两种自适应模式：

#### 1. 单轮模式（信息充足）

```
用户："导航到北京故宫"
  ↓
LLM 判断：信息充足，有目的地
  ↓
调用工具：search_location(query="北京故宫")
  ↓
返回：AgentStatus.SUCCESS
```

#### 2. 多轮模式（信息不足）

```
用户："我想导航"
  ↓
LLM 判断：缺少目的地，无法调用工具
  ↓
返回询问：AgentStatus.WAITING_INPUT
  ↓
用户："去故宫"
  ↓
LLM 调用工具：search_location(query="故宫")
  ↓
返回：AgentStatus.COMPLETED
```

## 实现机制

### 1. 智能检测

当 LLM 没有调用工具，而是返回文本回复时，系统会自动检测该回复是否在询问用户：

```python
def _is_asking_for_input(self, response_text: str) -> bool:
    """
    判断依据：
    1. 包含问号（？或?）
    2. 包含询问词（请问、什么、哪里等）
    """
    # 包含问号
    if "？" in response_text or "?" in response_text:
        return True
    
    # 包含常见询问词
    asking_keywords = [
        "请问", "请告诉", "请说", "请提供",
        "什么", "哪里", "哪个", "多少", ...
    ]
    
    for keyword in asking_keywords:
        if keyword in response_text:
            return True
    
    return False
```

### 2. 自动会话管理

当检测到询问行为时，自动创建轻量级会话：

```python
if is_asking:
    session_id = self._generate_session_id()
    
    return AgentResponse(
        agent=self.name,
        status=AgentStatus.WAITING_INPUT,
        query=query,
        message=response_content,
        prompt=response_content,
        session_id=session_id,
        data={"conversation_history": messages}
    )
```

### 3. LLM 提示词指导

系统提示词明确告诉 LLM 如何处理信息不足的情况：

```python
重要提示：
1. 仔细理解用户意图，选择最合适的工具
2. 如果用户提供的信息不足以调用工具（如缺少必需参数），
   不要调用工具，而是礼貌地询问缺失的信息
3. 如果需要多个步骤，可以依次调用多个工具
...

注意：当信息不足时，直接回复询问用户，系统会自动处理多轮交互。
```

## 使用示例

### 单轮场景

```python
class MusicAgent(ToolAgentBase):
    def __init__(self):
        super().__init__(
            name="music_agent",
            description="音乐播放助手",
            capabilities=["音乐", "播放"],
            tool_categories=[ToolCategory.ENTERTAINMENT],
            api_key=os.getenv("DASHSCOPE_API_KEY")
        )

# 用户："播放周杰伦的晴天"
# → LLM 直接调用 play_music(song="晴天", artist="周杰伦")
# → 返回 SUCCESS
```

### 多轮场景

```python
# 同一个 MusicAgent，不需要任何改动

# 轮次1:
# 用户："播放音乐"
# → LLM: "好的，请问想听什么歌？"
# → 返回 WAITING_INPUT

# 轮次2:
# 用户："周杰伦的晴天"
# → LLM 调用 play_music(song="晴天", artist="周杰伦")
# → 返回 COMPLETED
```

## 设计优势

### 1. 统一性
- 不需要为单轮/多轮创建不同的 Agent 类
- 一个 Agent 自动适应不同的交互模式

### 2. 智能性
- LLM 根据用户输入智能判断是否需要更多信息
- 无需硬编码状态机或流程控制

### 3. 简洁性
- Agent 实现者无需关心多轮逻辑
- 基类自动处理会话管理和状态切换

### 4. 灵活性
- 同一个查询可能是单轮或多轮，取决于信息完整度
- 支持中间插入新的询问（如工具参数需要确认）

## 与 SessionAgentBase 的区别

| 特性 | ToolAgentBase | SessionAgentBase |
|-----|--------------|------------------|
| **目标场景** | 工具调用 | 复杂业务流程 |
| **多轮方式** | LLM自动判断 | 显式状态管理 |
| **会话管理** | 轻量级（自动） | 重量级（手动） |
| **状态持久化** | 临时 | 长期 |
| **适用场景** | 导航、音乐、控制 | 酒店预订、表单填写 |
| **实现复杂度** | 低 | 高 |

### 选择指南

- **ToolAgentBase**: 需要调用外部工具，可能需要澄清参数
  - 例：导航、音乐、天气、车控
  
- **SessionAgentBase**: 需要复杂的多步骤流程和显式状态管理
  - 例：酒店预订（需要收集城市、日期、房型等）、行程规划

## 实际案例

### 案例1：导航Agent

```python
# 场景A：信息完整（单轮）
用户："导航到北京故宫"
LLM：调用 search_location("北京故宫")
结果：成功

# 场景B：信息不足（多轮）
用户："我想去个地方"
LLM："好的，请问您想去哪里？"
用户："去故宫"
LLM：调用 search_location("故宫")
结果：成功
```

### 案例2：音乐Agent

```python
# 场景A：明确指定（单轮）
用户："播放周杰伦的晴天"
LLM：调用 play_music(song="晴天", artist="周杰伦")
结果：成功

# 场景B：逐步补充（多轮）
用户："播放音乐"
LLM："好的，请问想听什么歌？"
用户："周杰伦的"
LLM："好的，想听周杰伦的哪首歌？"
用户："晴天"
LLM：调用 play_music(song="晴天", artist="周杰伦")
结果：成功
```

### 案例3：车控Agent

```python
# 场景A：明确指令（单轮）
用户："打开主驾驶车窗"
LLM：调用 control_window(window="driver", action="open")
结果：成功

# 场景B：需要确认（多轮）
用户："打开车窗"
LLM："好的，请问是哪个车窗？"
用户："主驾驶"
LLM：调用 control_window(window="driver", action="open")
结果：成功
```

## 总结

`ToolAgentBase` 的多轮能力是通过 **LLM 智能判断 + 自动会话管理** 实现的，而不是通过硬编码的状态机。这使得它：

1. **更智能** - LLM 根据上下文自主决定是否需要更多信息
2. **更简洁** - Agent 实现者无需编写多轮逻辑
3. **更灵活** - 同一个 Agent 自适应单轮/多轮场景

**核心观点**：无需为多轮场景单独创建 Agent 抽象，`ToolAgentBase` 本身就能根据 LLM 判断灵活切换交互模式。
