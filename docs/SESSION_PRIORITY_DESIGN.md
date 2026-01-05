# 基于优先级的会话管理设计

## 核心设计理念

**会话的优先级和是否可打断应该在 Agent 配置中定义，而不是在创建会话时手动传入**。这样可以：

1. **集中管理** - 所有 Agent 的优先级在配置文件中一目了然
2. **一致性** - 避免同一个 Agent 在不同地方创建会话时传入不同的参数
3. **可维护性** - 修改优先级策略无需改代码，只需修改配置
4. **自动化** - 系统根据优先级自动决定是否打断当前会话

## 配置方案

### Agent 配置文件 (`config/agents_config.yaml`)

每个 Agent 都有两个新属性：

```yaml
agents:
  - name: "phone_agent"
    description: "电话通信Agent"
    priority: 90  # 优先级(0-100)，数字越大优先级越高
    interruptible: false  # 是否可被更高优先级任务打断
    enabled: true
    capabilities: [...]

  - name: "navigation_agent"
    priority: 80  # 导航是核心功能，高优先级
    interruptible: false  # 导航中不可被打断
    ...

  - name: "music_agent"
    priority: 20  # 娱乐功能，中等偏低优先级
    interruptible: true  # 可随时被打断
    ...

  - name: "chat_agent"
    priority: 10  # 闲聊功能，最低优先级
    interruptible: true  # 可随时被打断
    ...
```

### 优先级分级建议

| 优先级范围 | 类型 | 示例 | 说明 |
|----------|------|------|------|
| 90-100 | 紧急/安全 | 电话通信 | 最高优先级，通常不可打断 |
| 70-89 | 核心功能 | 导航、紧急控制 | 高优先级，通常不可打断 |
| 50-69 | 重要功能 | 车辆控制、任务规划 | 中高优先级，可选择性打断 |
| 30-49 | 一般功能 | 天气查询、信息查询 | 中等优先级，可被打断 |
| 10-29 | 娱乐功能 | 音乐播放 | 中低优先级，容易被打断 |
| 0-9 | 背景任务 | 闲聊对话 | 最低优先级，随时可被打断 |

## 实现机制

### 1. 配置传递

```python
# AgentManager 加载配置时提取优先级
class AgentsModule:
    def initialize(self):
        for agent in self._agents:
            handler = create_agent(
                name=agent.get('name'),
                description=agent.get('description', ''),
                capabilities=agent.get('capabilities', []),
                priority=agent.get('priority', 50),      # 从配置读取
                interruptible=agent.get('interruptible', True),  # 从配置读取
                api_key=api_key
            )
```

### 2. Agent 基类存储

```python
class SimpleAgentBase(ABC):
    def __init__(self, name: str, description: str, capabilities: list[str],
                 priority: int = 50, interruptible: bool = True):
        self.name = name
        self.description = description
        self.capabilities = capabilities
        self.priority = priority        # 存储在实例中
        self.interruptible = interruptible  # 存储在实例中
```

### 3. 会话创建时使用

```python
class SessionAgentBase(ABC):
    async def process(self, query: str, msg_id: str, ...):
        # 创建会话时从 Agent 属性读取，无需手动传入
        session = self.session_manager.create_session(
            agent_name=self.name,
            priority=self.priority,           # 从实例属性读取
            interruptible=self.interruptible  # 从实例属性读取
        )
```

### 4. 自动打断控制

```python
class SessionManager:
    def create_session(self, agent_name: str, user_id: str = "default", 
                      priority: int = 0, interruptible: bool = True):
        """
        创建新会话，根据优先级自动决定是否打断当前会话
        """
        current_session = self.get_active_session(user_id)
        
        if current_session:
            # 有活跃会话，检查优先级
            if priority > current_session.priority:
                # 新会话优先级更高
                if current_session.interruptible:
                    # 当前会话可被打断，暂停它
                    print(f"⏸️  暂停会话 [{current_session.agent_name}] "
                          f"以启动更高优先级会话 [{agent_name}]")
                    current_session.update(state="paused")
                else:
                    # 当前会话不可打断，拒绝创建新会话
                    print(f"🚫 会话 [{current_session.agent_name}] 不可被打断")
                    return None
            else:
                # 新会话优先级不够高，拒绝创建
                print(f"🚫 当前会话优先级更高，拒绝创建新会话")
                return None
        
        # 创建新会话...
```

## 使用场景

### 场景1：电话打断音乐

```
用户正在听音乐 (priority=20, interruptible=true)
  ↓
收到来电，phone_agent 创建会话 (priority=90)
  ↓
SessionManager 检测到: 90 > 20 且 music 可被打断
  ↓
自动暂停音乐会话，创建电话会话
  ↓
通话结束后，可恢复音乐会话
```

### 场景2：导航中拒绝闲聊

```
用户正在导航 (priority=80, interruptible=false)
  ↓
用户说："给我讲个笑话"，chat_agent 尝试创建会话 (priority=10)
  ↓
SessionManager 检测到: 10 < 80
  ↓
拒绝创建闲聊会话，返回 None
  ↓
Orchestrator 得到 None，告知用户"导航中，暂时无法闲聊"
```

### 场景3：紧急车控打断规划

```
用户正在使用规划功能 (priority=60, interruptible=true)
  ↓
用户说："快关上车窗，下雨了"，vehicle_agent 创建会话 (priority=50)
  ↓
SessionManager 检测到: 50 < 60
  ↓
拒绝创建会话（优先级不够）
```

**注意**：如果这是紧急情况，应该将紧急车控的优先级设置得更高，或者创建专门的紧急控制 Agent。

### 场景4：同优先级任务

```
用户正在播放音乐 (priority=20)
  ↓
用户说："查一下天气"，weather_agent 尝试创建会话 (priority=30)
  ↓
SessionManager 检测到: 30 > 20
  ↓
暂停音乐，查询天气
  ↓
天气查询完成后，可恢复音乐
```

## 配置示例

实际系统中的配置：

```yaml
agents:
  # 最高优先级：紧急/安全相关
  - name: "phone_agent"
    priority: 90
    interruptible: false  # 通话中不可被打断
    
  # 高优先级：核心功能
  - name: "navigation_agent"
    priority: 80
    interruptible: false  # 导航中不可被打断
    
  # 中高优先级：重要功能
  - name: "planner_agent"
    priority: 60
    interruptible: true  # 可被打断后恢复
    
  - name: "vehicle_control_agent"
    priority: 50
    interruptible: true  # 一般控制可被打断
    
  # 中等优先级：一般功能
  - name: "weather_agent"
    priority: 30
    interruptible: true
    
  # 中低优先级：娱乐功能
  - name: "music_agent"
    priority: 20
    interruptible: true  # 音乐随时可被打断
    
  # 最低优先级：背景任务
  - name: "chat_agent"
    priority: 10
    interruptible: true  # 闲聊随时可被打断
```

## 优势总结

1. **配置驱动** - 优先级策略集中管理，易于调整
2. **自动化决策** - SessionManager 根据优先级自动处理打断逻辑
3. **一致性** - 同一 Agent 的优先级始终一致
4. **可维护性** - 无需在代码中硬编码优先级逻辑
5. **灵活性** - 可根据实际使用情况调整配置

## 与原设计的对比

### 原设计（❌）

```python
# Agent 需要在创建会话时手动传入
session = self.session_manager.create_session(
    agent_name=self.name,
    interruptible=True  # 每次都要手动指定
)

# 问题：
# 1. 同一 Agent 可能在不同地方传入不同值
# 2. 优先级逻辑不明确
# 3. 修改策略需要改多处代码
```

### 新设计（✅）

```python
# 配置文件中定义
priority: 50
interruptible: true

# Agent 初始化时存储
def __init__(self, ..., priority: int = 50, interruptible: bool = True):
    self.priority = priority
    self.interruptible = interruptible

# 创建会话时自动使用
session = self.session_manager.create_session(
    agent_name=self.name,
    priority=self.priority,      # 自动从实例属性读取
    interruptible=self.interruptible
)

# 优势：
# 1. 配置集中管理
# 2. 值始终一致
# 3. 修改策略只需改配置
```

## 未来扩展

### 1. 动态优先级

可以根据上下文动态调整优先级：

```python
def get_dynamic_priority(self) -> int:
    """根据当前状态动态计算优先级"""
    base_priority = self.priority
    
    # 如果是紧急情况，提升优先级
    if self.is_emergency_situation():
        return base_priority + 20
    
    return base_priority
```

### 2. 用户偏好

可以让用户自定义优先级：

```yaml
user_preferences:
  user_id_123:
    agent_priority_overrides:
      music_agent: 50  # 用户特别喜欢音乐，提升优先级
      chat_agent: 5    # 不喜欢闲聊，降低优先级
```

### 3. 时间段优先级

可以根据时间段调整优先级：

```python
def get_time_based_priority(self) -> int:
    """根据时间段调整优先级"""
    current_hour = datetime.now().hour
    
    # 夜间降低娱乐功能优先级
    if 22 <= current_hour or current_hour < 7:
        if self.name == "music_agent":
            return self.priority - 10
    
    return self.priority
```

## 总结

通过将优先级和可打断性配置化，系统实现了：
- ✅ 集中的优先级策略管理
- ✅ 自动的会话打断控制
- ✅ 一致的 Agent 行为
- ✅ 灵活的配置调整能力

这种设计使得会话管理更加清晰、可维护和可扩展。
