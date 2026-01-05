# 多轮对话会话管理系统升级

## 升级概述

本次升级为系统添加了完整的多轮对话和会话管理功能，使Agent能够：
- ✅ 在处理过程中询问用户补充信息
- ✅ 暂停当前流程，等待用户输入后继续
- ✅ 支持用户中途切换意图，完成后自动恢复原任务
- ✅ 支持复杂的多步骤工作流，逐步收集信息
- ✅ 支持会话嵌套（会话栈）

## 新增文件

### 1. 核心模块
- **src/core/session_manager.py** - 会话管理器
  - `AgentSession`: 会话状态数据类
  - `SessionManager`: 会话管理器，支持会话栈、暂停/恢复、状态追踪
  - `get_session_manager()`: 获取全局单例

### 2. Agent基类
- **src/agents/session_aware_base.py** - 支持多轮对话的Agent基类
  - `SessionAwareAgent`: 抽象基类，提供会话管理能力
  - `SimpleAgent`: 不需要多轮对话的简单Agent基类
  - 提供 `ask_user()`, `complete_session()`, `error_response()` 等方法

### 3. 示例Agent
- **src/agents/handlers/workflow.py** - 工作流Agent示例
  - 完整的多步骤工作流实现
  - 展示如何在多个步骤中收集信息
  - 支持步骤间状态保持和恢复

### 4. 文档
- **docs/SESSION_MANAGEMENT_INTEGRATION.md** - 详细的集成指南
  - 系统架构说明
  - 集成步骤
  - 代码示例
  - 测试场景
  - FAQ

## 修改的文件

### 1. Orchestrator
**src/orchestrator/orchestrator.py**
- ✅ 添加会话管理器引用
- ✅ 在 `process_query()` 中检测活跃会话
- ✅ 实现意图分类（判断用户是回答问题还是新请求）
- ✅ 支持会话恢复和暂停逻辑
- ✅ 添加 `_classify_user_intent()` 方法（使用LLM或规则）

### 2. 控制器（文档说明）
**需要改造 src/adapters/agent_adapter.py**
- 在 `_handle_agent_dispatch()` 中添加对不同响应类型的支持
- 添加 `_handle_waiting_input()` 方法处理等待输入状态
- 添加 `_handle_completed()` 和 `_handle_error()` 方法

### 3. Agent Manager（文档说明）
**需要改造 src/agents/agent_manager.py**
- 修改 `execute_agent()` 支持会话信息传递
- 支持新旧Agent混用

### 4. 评估系统（文档说明）
**src/evaluation/evaluator.py**
- 在 `_run_single_case()` 中添加多轮对话支持
- 添加 `_is_waiting_input()` 方法检测等待状态
- 添加 `_simulate_user_input()` 方法模拟用户输入
- 支持自动化测试多轮对话场景

## 核心功能

### 1. 会话状态管理
```python
from src.core.session_manager import get_session_manager

# 创建会话
session_manager = get_session_manager()
session = session_manager.create_session(
    agent_name="hotel_booking_agent",
    interruptible=True
)

# 标记等待输入
session_manager.wait_for_input(
    session.session_id,
    prompt="请问您想在哪个城市预订酒店？",
    expected_type="location"
)

# 恢复会话
session_manager.resume_session(session.session_id, "上海")

# 完成会话
session_manager.complete_session(session.session_id)
```

### 2. 创建支持多轮对话的Agent
```python
from src.agents.session_aware_base import SessionAwareAgent

class MyAgent(SessionAwareAgent):
    async def _new_process(self, query, msg_id, session):
        """处理新会话"""
        # 需要询问用户？
        return self.ask_user(
            session.session_id,
            "请问...？",
            "text"
        )
    
    async def _resume_process(self, query, msg_id, session_id, context):
        """恢复会话"""
        # 用户回答了，继续处理
        result = self.process_answer(query, context)
        return self.complete_session(
            session_id,
            result,
            "完成了！"
        )
```

### 3. Orchestrator自动处理会话
```python
# Orchestrator会自动：
# 1. 检测活跃会话
# 2. 判断用户意图（回答 vs 新请求）
# 3. 恢复会话或创建新会话
# 4. 管理会话栈

decision = orchestrator.process_query("上海")
# 如果有活跃会话在等待城市信息，会自动恢复该会话
```

## 使用场景

### 场景1：简单问答收集
```
用户: "帮我订个酒店"
→ Agent创建会话，询问："请问您想在哪个城市预订酒店？"
用户: "上海"
→ Agent恢复会话，继续："请问什么时候入住？"
用户: "明天"
→ Agent完成预订，返回结果
```

### 场景2：中途切换意图
```
用户: "帮我订个酒店"
→ Agent询问："请问您想在哪个城市预订酒店？"
用户: "打开车窗"  ← 新意图！
→ Orchestrator检测到新意图，暂停酒店预订会话
→ 创建新会话处理开窗请求
→ 完成后自动恢复酒店预订："回到之前的话题，请问您想在哪个城市订酒店？"
用户: "上海"
→ 继续原会话
```

### 场景3：多步骤工作流
```
用户: "帮我订酒店然后叫个车"
→ WorkflowAgent生成工作流
→ 步骤1：询问酒店信息（城市、日期）
→ 步骤2：询问用车信息（地点、时间）
→ 所有步骤完成，返回结果
```

## 技术特点

### 1. 会话栈机制
- 支持会话嵌套（用户可以在一个任务中切换到另一个任务）
- 自动管理会话的暂停和恢复
- 支持设置会话优先级和可打断性

### 2. 智能意图判断
- 使用LLM判断用户是回答问题还是提出新请求
- 降级到规则引擎（基于关键词）
- 可配置判断策略

### 3. 灵活的Agent架构
- 新旧Agent可以共存
- 简单Agent不需要改造
- 复杂Agent可以选择性升级

### 4. 完善的状态追踪
- 会话状态：running, waiting_input, paused, completed, error
- 支持会话上下文持久化
- 提供统计和监控接口

## 兼容性

- ✅ 完全向后兼容，旧Agent无需修改
- ✅ 新Agent继承SessionAwareAgent即可获得多轮对话能力
- ✅ Orchestrator自动识别Agent类型
- ✅ 评估系统同时支持新旧Agent测试

## 下一步工作

需要完成以下集成工作才能完全启用多轮对话功能：

1. **Agent Adapter改造** (高优先级)
   - 修改 `src/adapters/agent_adapter.py`
   - 添加对waiting_input状态的处理
   - 参考：docs/SESSION_MANAGEMENT_INTEGRATION.md

2. **Agent Manager改造** (高优先级)
   - 修改 `src/agents/agent_manager.py`
   - 支持会话信息传递
   - 参考：docs/SESSION_MANAGEMENT_INTEGRATION.md

3. **评估系统更新** (中优先级)
   - 修改 `src/evaluation/evaluator.py`
   - 添加多轮对话测试支持
   - 参考：docs/SESSION_MANAGEMENT_INTEGRATION.md

4. **现有Agent升级** (低优先级，可选)
   - 将需要多轮对话的Agent迁移到新架构
   - 例如：预订类Agent、配置类Agent

5. **测试用例添加** (中优先级)
   - 在 `data/test_cases.jsonl` 中添加多轮对话测试用例
   - 测试会话恢复、意图切换等场景

## 开发者指南

### 创建新的多轮对话Agent

1. 继承 `SessionAwareAgent`
2. 实现 `_new_process()` 方法（处理新会话）
3. 实现 `_resume_process()` 方法（恢复会话）
4. 使用 `ask_user()` 询问用户
5. 使用 `complete_session()` 完成会话

详细示例请参考：
- `src/agents/handlers/workflow.py`
- `docs/SESSION_MANAGEMENT_INTEGRATION.md`

### 测试多轮对话

```python
# 1. 创建测试用例
test_case = {
    "query": "帮我订个酒店",
    "expected_agent": "hotel_booking_agent",
    "expected_response": "已为您预订",
    "multi_turn": true,  # 标记为多轮对话
    "mock_inputs": ["上海", "明天"]  # 模拟的后续输入
}

# 2. 运行评估
evaluator.run_evaluation()
```

## 相关文档

- **docs/SESSION_MANAGEMENT_INTEGRATION.md** - 完整的集成指南
- **src/agents/session_aware_base.py** - Agent基类API文档
- **src/agents/handlers/workflow.py** - Workflow Agent示例代码

## 贡献者

- 2026-01-04: 初始实现会话管理系统

## 许可

与项目主体保持一致
