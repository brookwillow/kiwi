# PlannerAgent - 规划协调Agent

## 概述

PlannerAgent是一个元代理(Meta-Agent)，专门用于处理复杂的、跨域的任务。它不直接调用系统工具，而是将其他专业agents作为可执行的"工具"，通过智能规划和协调来完成复杂任务。

## 核心能力

1. **任务分解**：将复杂需求分解为多个可执行的子任务
2. **Agent协调**：选择合适的专业agent执行每个子任务
3. **执行管理**：按照依赖关系顺序执行任务
4. **动态调整**：根据执行结果动态调整后续计划
5. **结果汇总**：将多个子任务的结果汇总为统一的回复

## 工作流程

### 1. 任务规划阶段

PlannerAgent接收用户的复杂请求后，使用LLM分析需求并生成任务执行计划：

```json
[
    {
        "task_id": 1,
        "description": "导航到目的地",
        "agent": "navigation_agent",
        "depends_on": []
    },
    {
        "task_id": 2,
        "description": "播放适合长途驾驶的音乐",
        "agent": "music_agent",
        "depends_on": []
    },
    {
        "task_id": 3,
        "description": "将空调设置为舒适温度",
        "agent": "vehicle_control_agent",
        "depends_on": []
    }
]
```

### 2. 执行阶段

按照任务计划依次执行：

- 检查任务依赖关系
- 调用对应的专业agent处理子任务
- 记录执行结果

### 3. 动态调整

如果某个任务执行失败，评估影响：

- 如果后续任务依赖该任务，则终止执行
- 如果后续任务独立，则继续执行

### 4. 结果汇总

使用LLM将所有子任务的执行结果汇总为自然、友好的统一回复。

## 适用场景

PlannerAgent适合处理以下类型的复杂任务：

### 1. 跨域组合任务

需要多个领域协作完成的任务：

- ❌ 单领域：「播放音乐」→ music_agent
- ✅ 跨域：「准备长途驾驶：导航到目的地，播放轻音乐，调整座椅到舒适模式」→ planner_agent

### 2. 多步骤依赖任务

有明确步骤顺序和依赖关系的任务：

```
用户：「帮我安排一下，先导航到加油站，加完油再去公司」

Plan:
1. 导航到附近加油站 (navigation_agent)
2. 等待加油完成 (等待用户确认)
3. 导航到公司 (navigation_agent, depends_on: [1, 2])
```

### 3. 场景化任务

预设场景，需要一系列配置：

```
用户：「进入驾驶模式」

Plan:
1. 启动发动机 (vehicle_control_agent)
2. 调整座椅到记忆位置1 (vehicle_control_agent)
3. 打开空调自动模式 (vehicle_control_agent)
4. 连接蓝牙播放音乐 (music_agent)
```

## 配置

### agents_config.yaml

```yaml
- name: "planner_agent"
  description: "任务规划协调Agent，负责处理复杂的跨域任务"
  enabled: true
  capabilities:
    - "任务分解"
    - "多Agent协调"
    - "执行计划管理"
    - "跨域任务处理"
```

### Orchestrator集成

在orchestrator的决策提示词中添加：

```
5. 如果查询涉及多个领域（如：导航+音乐+空调），或需要多步骤协调完成，选择"planner_agent"进行任务规划和协调执行
```

## 使用示例

### 示例1：准备出行

```
用户：帮我准备一下，要去机场，路上播放轻音乐，空调设置到舒适温度

PlannerAgent执行计划：
✓ 任务1: 导航到机场 (navigation_agent)
✓ 任务2: 播放轻音乐 (music_agent)  
✓ 任务3: 将空调设置为22度 (vehicle_control_agent)

最终回复：好的，已经为您准备好了：导航已设置到机场，正在播放轻音乐，空调已调至22度。
```

### 示例2：回家场景

```
用户：我要回家了，帮我设置一下

PlannerAgent执行计划：
✓ 任务1: 导航回家 (navigation_agent)
✓ 任务2: 播放收藏的音乐 (music_agent)
✓ 任务3: 打开座椅加热 (vehicle_control_agent)
✓ 任务4: 开启勿扰模式 (phone_agent)

最终回复：已为您设置好回家模式：导航已启动，播放您喜欢的音乐，座椅加热已开启，勿扰模式已启用。
```

## 技术实现

### 核心组件

1. **PlannerAgent** (`src/agents/handlers/planner.py`)
   - 主处理逻辑
   - 任务规划、执行、调整、汇总

2. **AgentManager** 扩展
   - `set_available_agents()`: 设置可用agents信息
   - `execute_agent()`: 为planner_agent传递agent_manager引用

3. **LLM决策器** 更新
   - 识别需要planner_agent的复杂任务

### 关键接口

```python
class PlannerAgent:
    def handle(self, query: str, context: Dict[str, Any]) -> AgentResponse:
        """
        处理复杂任务
        
        Args:
            query: 用户查询
            context: 包含agent_manager引用的上下文
            
        Returns:
            AgentResponse with plan and execution_history
        """
```

### 数据流

```
用户查询 
  → Orchestrator (LLM决策) 
  → PlannerAgent.handle()
    → _generate_plan() [LLM规划]
    → _execute_plan()
      → AgentManager.execute_agent() [调用各专业agent]
    → _generate_final_response() [LLM汇总]
  → 统一回复
```

## 优势

1. **智能分解**：自动分析复杂需求，生成合理的执行计划
2. **灵活协调**：动态选择合适的专业agent完成各子任务
3. **鲁棒性强**：支持任务依赖检查和失败处理
4. **可扩展性**：新增agent自动可用，无需修改planner代码
5. **用户友好**：提供统一、自然的回复，屏蔽内部复杂性

## 未来扩展

1. **并行执行**：支持独立任务的并行执行，提高效率
2. **智能调整**：使用LLM智能决策失败后的调整策略
3. **学习优化**：根据历史执行记录优化规划策略
4. **用户确认**：重要步骤请求用户确认后继续
5. **进度反馈**：实时向用户反馈执行进度

## 测试

运行测试脚本：

```bash
python test_planner_agent.py
```

查看planner_agent如何处理复杂的跨域任务。
