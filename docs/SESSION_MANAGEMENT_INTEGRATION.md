# 多轮对话会话管理系统 - 集成指南

## 概述

本系统升级实现了完整的多轮对话和会话管理功能，支持：
- Agent可以暂停流程，询问用户补充信息
- 用户可以在等待输入时切换到新任务，完成后自动恢复原任务
- Workflow Agent可以在多个步骤中逐步收集信息
- 评估系统支持自动化测试多轮对话场景

## 已实现的模块

### 1. 会话管理器 (src/core/session_manager.py)
- `AgentSession`: 会话状态数据类
- `SessionManager`: 会话管理器，支持会话栈、暂停/恢复
- `get_session_manager()`: 获取全局单例

### 2. Orchestrator升级 (src/orchestrator/orchestrator.py)
已添加功能：
- 自动检测活跃会话
- LLM意图分类（判断用户是回答问题还是新请求）
- 支持会话恢复和暂停
- 支持会话嵌套（会话栈）

### 3. 增强的Agent基类 (src/agents/session_aware_base.py)
- `SessionAwareAgent`: 支持多轮对话的Agent基类
  - `_new_process()`: 处理新会话
  - `_resume_process()`: 恢复会话
  - `ask_user()`: 询问用户并暂停
  - `complete_session()`: 完成会话

- `SimpleAgent`: 不需要多轮对话的简单Agent基类

### 4. Workflow Agent示例 (src/agents/handlers/workflow.py)
完整的工作流Agent实现，展示了：
- 多步骤工作流管理
- 中间步骤参数收集
- 步骤间状态保持
- 自动恢复和继续执行

## 需要集成的部分

### 1. Agent Adapter改造

需要修改 `src/adapters/agent_adapter.py` 的 `_handle_agent_dispatch` 方法来支持不同的响应类型：

\`\`\`python
def _handle_agent_dispatch(self, event: Event):
    """处理Agent分发请求（支持会话管理）"""
    try:
        data = event.data
        agent_name = data.get('agent_name')
        query = data.get('query')
        msg_id = event.msg_id
        
        # ... 原有的追踪记录代码 ...
        
        # 调用agent_manager执行Agent（传递会话信息）
        response = self._agent_manager.execute_agent(
            agent_name=agent_name,
            query=query,
            context=data  # 包含session_id, context等信息
        )
        
        # 检查响应类型
        if isinstance(response, dict):
            response_status = response.get('status')
            
            if response_status == 'waiting_input':
                # Agent在等待用户输入，播放TTS后暂停
                self._handle_waiting_input(response, msg_id)
                return
            
            elif response_status == 'completed':
                # Agent执行完成
                self._handle_completed(response, msg_id)
                return
            
            elif response_status == 'error':
                # Agent执行错误
                self._handle_error(response, msg_id)
                return
        
        # 兼容旧的AgentResponse格式
        # ... 原有的处理逻辑 ...
        
    except Exception as e:
        # ... 错误处理 ...

def _handle_waiting_input(self, response: Dict, msg_id: Optional[str]):
    """处理等待用户输入"""
    prompt = response.get('prompt', '')
    
    # 记录追踪
    if msg_id:
        tracker = get_message_tracker()
        tracker.add_trace(msg_id, self._name, "agent_waiting_input", 
                         output_data={'prompt': prompt})
        tracker.update_response(msg_id, prompt)
    
    # 播放TTS（如果不在评估模式）
    if prompt and not self._controller.evaluation_mode:
        self._publish_tts_request(prompt, msg_id)

def _handle_completed(self, response: Dict, msg_id: Optional[str]):
    """处理完成的响应"""
    message = response.get('response', '')
    
    # 记录追踪
    if msg_id:
        tracker = get_message_tracker()
        tracker.add_trace(msg_id, response.get('agent'), "agent_response",
                         output_data={'message': message, 'success': True})
        tracker.update_response(msg_id, message)
    
    # 播放TTS
    if message and not self._controller.evaluation_mode:
        self._publish_tts_request(message, msg_id)
\`\`\`

### 2. Agent Manager改造

需要修改 `src/agents/agent_manager.py` 的 `execute_agent` 方法来支持会话信息传递：

\`\`\`python
def execute_agent(self, agent_name: str, query: str, context: Dict = None) -> Any:
    """
    执行Agent（支持会话恢复）
    
    Args:
        agent_name: Agent名称
        query: 查询内容
        context: 上下文，包含：
            - session_id: 会话ID（如果是恢复会话）
            - is_resuming: 是否恢复会话
            - context: 会话上下文数据
    """
    agent = self._agents.get(agent_name)
    if not agent:
        return self._create_error_response(f"Agent '{agent_name}' 不存在")
    
    try:
        # 检查是否是支持会话的Agent
        if hasattr(agent, 'process'):
            # 新的SessionAwareAgent
            session_id = context.get('session_id') if context else None
            session_context = context.get('context') if context else None
            
            # 异步调用（如果需要）
            if asyncio.iscoroutinefunction(agent.process):
                import asyncio
                return asyncio.run(agent.process(
                    query, 
                    msg_id="",  # 从context获取
                    session_id=session_id,
                    context=session_context
                ))
            else:
                return agent.process(query, "", session_id, session_context)
        
        # 旧的Agent（兼容）
        return agent.handle(query, context)
        
    except Exception as e:
        return self._create_error_response(str(e))
\`\`\`

### 3. 评估系统改造

已在 `src/evaluation/evaluator.py` 中的 `_run_single_case` 方法中添加多轮对话支持的注释和结构，具体实现：

\`\`\`python
def _run_single_case(self, test_case: TestCase):
    """运行单个测试用例（支持多轮对话）"""
    # ... 原有代码 ...
    
    # 等待agent处理完成 - 支持多轮对话
    max_wait = 5.0
    check_interval = 0.1
    elapsed = 0
    conversation_rounds = 0
    max_rounds = 10  # 最多10轮对话
    
    while elapsed < max_wait and conversation_rounds < max_rounds:
        time.sleep(check_interval)
        elapsed += check_interval
        
        trace = tracker.get_trace(msg_id)
        if trace and trace.response:
            # 检查是否需要多轮对话
            if self._is_waiting_input(trace):
                conversation_rounds += 1
                
                # 生成mock输入
                mock_input = self._generate_mock_input(test_case, trace)
                if mock_input:
                    # 模拟用户继续输入
                    msg_id = self._simulate_user_input(mock_input, tracker)
                    test_case.msg_id = msg_id
                    elapsed = 0  # 重置等待时间
                    continue
            
            # 正常完成
            time.sleep(0.2)
            break
    
    # ... 原有的结果处理代码 ...

def _is_waiting_input(self, trace) -> bool:
    """检查是否在等待用户输入"""
    for module_trace in trace.traces:
        if module_trace.event_type == "agent_waiting_input":
            return True
    return False

def _simulate_user_input(self, user_input: str, tracker) -> str:
    """模拟用户输入"""
    new_msg_id = tracker.create_message_id(session_type="evaluation")
    tracker.update_query(new_msg_id, user_input)
    
    event = Event.create(
        event_type=EventType.ASR_RECOGNITION_SUCCESS,
        source="evaluator",
        msg_id=new_msg_id,
        data={'text': user_input, 'confidence': 1.0}
    )
    
    self.controller.publish_event(event)
    return new_msg_id
\`\`\`

## 如何创建支持多轮对话的Agent

### 示例1：简单的预订Agent

\`\`\`python
from src.agents.session_aware_base import SessionAwareAgent
from src.core.session_manager import AgentSession

class HotelBookingAgent(SessionAwareAgent):
    def __init__(self):
        super().__init__(
            agent_id="hotel_booking_agent",
            agent_type="booking",
            description="酒店预订助手"
        )
    
    async def _new_process(self, query: str, msg_id: str, 
                          session: AgentSession) -> Dict:
        """新会话：开始收集信息"""
        # 初始化上下文
        session.context['intent'] = {}
        session.context['step'] = 'collect_city'
        
        # 询问城市
        return self.ask_user(
            session.session_id,
            "请问您想在哪个城市预订酒店？",
            "location"
        )
    
    async def _resume_process(self, query: str, msg_id: str,
                             session_id: str, context: Dict) -> Dict:
        """恢复会话：继续收集信息"""
        intent = context.get('intent', {})
        step = context.get('step')
        
        session = self.session_manager.get_session(session_id)
        
        if step == 'collect_city':
            # 保存城市信息
            intent['city'] = query
            session.context['intent'] = intent
            session.context['step'] = 'collect_date'
            
            # 询问日期
            return self.ask_user(
                session_id,
                f"好的，{query}。请问什么时候入住？",
                "date"
            )
        
        elif step == 'collect_date':
            # 保存日期信息
            intent['date'] = query
            
            # 信息完整，执行预订
            result = await self._book_hotel(intent)
            
            return self.complete_session(
                session_id,
                result,
                f"已为您预订{intent['city']}的酒店，入住时间{intent['date']}"
            )
        
        return self.error_response(session_id, "未知步骤")
    
    async def _book_hotel(self, intent: Dict) -> Dict:
        """执行实际预订"""
        # 调用预订服务...
        return {"order_id": "12345"}
\`\`\`

### 示例2：使用Workflow Agent

\`\`\`python
# Workflow Agent会自动处理多步骤流程
# 只需要在配置中注册即可使用

from src.agents.handlers.workflow import WorkflowAgent

# 注册到agent_manager
agent_manager.register_agent(WorkflowAgent())
\`\`\`

## 测试场景

### 场景1：简单的多轮对话
\`\`\`
用户: "帮我订个酒店"
系统: "请问您想在哪个城市预订酒店？"
用户: "上海"
系统: "好的，上海。请问什么时候入住？"
用户: "明天"
系统: "已为您预订上海的酒店，入住时间明天"
\`\`\`

### 场景2：中途切换意图
\`\`\`
用户: "帮我订个酒店"
系统: "请问您想在哪个城市预订酒店？"
用户: "打开车窗"              # 新意图
系统: [暂停预订会话，打开车窗]
系统: "车窗已打开。回到之前的话题，请问您想在哪个城市订酒店？"
用户: "上海"
系统: [继续原会话] "好的，上海。请问什么时候入住？"
\`\`\`

### 场景3：Workflow多步骤
\`\`\`
用户: "帮我订酒店然后叫个车"
系统: [生成工作流：步骤1=订酒店，步骤2=叫车]
系统: "在执行'预订酒店'时，请问是哪个城市？"
用户: "上海"
系统: "请问入住日期是？"
用户: "明天"
系统: [完成步骤1] "酒店预订完成。请问上车地点是？"
用户: "酒店门口"
系统: "请问用车时间是？"
用户: "明天上午10点"
系统: "工作流已完成，已为您预订上海酒店并安排明天10点用车"
\`\`\`

## 下一步工作

1. ✅ 创建会话管理器模块
2. ✅ 改造Orchestrator支持会话检测
3. ✅ 创建SessionAwareAgent基类
4. ✅ 创建Workflow Agent示例
5. ⏳ 改造Agent Adapter支持不同响应类型
6. ⏳ 改造Agent Manager支持会话信息传递
7. ⏳ 更新评估系统支持多轮对话测试
8. ⏳ 迁移现有Agent到新架构（可选，旧Agent仍可工作）

## 兼容性说明

- 旧的Agent（返回AgentResponse）仍然可以正常工作
- 新的Agent继承SessionAwareAgent后会自动获得多轮对话能力
- Orchestrator会自动识别Agent类型并选择合适的处理方式
- 系统支持新旧Agent混用

## 注意事项

1. **评估模式**: 在evaluation_mode下，TTS会被禁用，方便批量测试
2. **会话清理**: 长时间未活动的会话应该定期清理
3. **错误处理**: Agent应该正确处理异常，返回error状态
4. **超时管理**: 等待用户输入应该有超时机制
5. **并发控制**: 同一用户的多个会话需要通过会话栈管理

## FAQ

**Q: 如何让现有Agent支持多轮对话？**
A: 继承SessionAwareAgent类，实现_new_process和_resume_process方法。

**Q: 如何判断用户是回答问题还是新请求？**
A: Orchestrator会使用LLM自动判断，或使用简单规则（基于关键词）。

**Q: 会话什么时候自动清除？**
A: 当Agent调用complete_session()或session_manager.complete_session()时。

**Q: 如何测试多轮对话Agent？**
A: 在test_cases.jsonl中定义测试用例，评估系统会自动模拟多轮输入。

**Q: 会话栈的最大深度是多少？**
A: 目前没有硬性限制，但建议不超过5层，避免用户混淆。
