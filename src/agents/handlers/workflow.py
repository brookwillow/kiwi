"""
Workflow Agent - 工作流构建Agent示例

演示如何实现多步骤工作流，支持中间步骤暂停和恢复
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json
from src.agents.base_classes import SessionAgentBase, AgentResponse
from src.core.session_manager import AgentSession


@dataclass
class WorkflowStep:
    """工作流步骤"""
    step_id: str                        # 步骤ID
    step_type: str                      # 步骤类型：agent_call, condition, loop, etc.
    description: str                    # 步骤描述
    params: Dict[str, Any]              # 步骤参数
    status: str = "pending"             # pending, running, completed, failed
    result: Optional[Any] = None        # 执行结果
    
    # 参数收集状态
    required_params: List[str] = field(default_factory=list)
    collected_params: Dict[str, Any] = field(default_factory=dict)
    
    def is_params_complete(self) -> bool:
        """检查参数是否收集完整"""
        return all(param in self.collected_params for param in self.required_params)
    
    def get_missing_params(self) -> List[str]:
        """获取缺失的参数"""
        return [p for p in self.required_params if p not in self.collected_params]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'step_id': self.step_id,
            'step_type': self.step_type,
            'description': self.description,
            'params': self.params,
            'status': self.status,
            'result': self.result,
            'required_params': self.required_params,
            'collected_params': self.collected_params
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'WorkflowStep':
        """从字典创建"""
        return WorkflowStep(
            step_id=data['step_id'],
            step_type=data['step_type'],
            description=data['description'],
            params=data['params'],
            status=data['status'],
            result=data.get('result'),
            required_params=data['required_params'],
            collected_params=data['collected_params']
        )


@dataclass
class WorkflowContext:
    """工作流上下文"""
    workflow_id: str
    steps: List[WorkflowStep]
    current_step_index: int = 0
    global_variables: Dict[str, Any] = field(default_factory=dict)
    
    def get_current_step(self) -> Optional[WorkflowStep]:
        """获取当前步骤"""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None
    
    def move_next(self):
        """移动到下一步"""
        self.current_step_index += 1
    
    def is_completed(self) -> bool:
        """工作流是否完成"""
        return self.current_step_index >= len(self.steps)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'workflow_id': self.workflow_id,
            'current_step_index': self.current_step_index,
            'global_variables': self.global_variables,
            'steps': [s.to_dict() for s in self.steps]
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'WorkflowContext':
        """从字典创建"""
        return WorkflowContext(
            workflow_id=data['workflow_id'],
            steps=[WorkflowStep.from_dict(s) for s in data['steps']],
            current_step_index=data['current_step_index'],
            global_variables=data['global_variables']
        )


class WorkflowAgent(SessionAgentBase):
    """工作流构建Agent"""
    
    def __init__(self):
        super().__init__(
            name="workflow_agent",
            description="负责执行多步骤工作流，协调多个任务",
            capabilities=["工作流", "多步骤", "任务编排"]
        )
    
    async def _new_process(self, query: str, msg_id: str, session: AgentSession) -> AgentResponse:
        """新工作流处理"""
        print(f"📋 [{self.name}] 生成工作流...")
        
        # 1. 使用规则或LLM生成工作流步骤
        workflow_steps = await self._generate_workflow(query)
        
        if not workflow_steps:
            return self.error_response(session.session_id, "无法生成工作流")
        
        # 2. 创建工作流上下文
        workflow_ctx = WorkflowContext(
            workflow_id=session.session_id,
            steps=workflow_steps
        )
        
        # 3. 保存到会话上下文
        session.context['workflow'] = workflow_ctx.to_dict()
        session.context['execution_mode'] = 'step_by_step'
        
        print(f"📋 [{self.name}] 工作流包含 {len(workflow_steps)} 个步骤")
        
        # 4. 开始执行
        return await self._execute_workflow(workflow_ctx, session)
    
    async def _resume_process(self, query: str, msg_id: str, 
                             session_id: str, context: Dict) -> AgentResponse:
        """恢复工作流执行"""
        print(f"🔄 [{self.name}] 恢复工作流...")
        
        # 1. 恢复工作流上下文
        workflow_ctx = WorkflowContext.from_dict(context['workflow'])
        current_step = workflow_ctx.get_current_step()
        
        if not current_step:
            return self.error_response(session_id, "工作流已完成或出错")
        
        # 2. 将用户输入作为缺失参数的值
        missing_params = current_step.get_missing_params()
        if missing_params:
            param_name = missing_params[0]  # 当前询问的参数
            param_value = self._extract_param_value(query, param_name)
            
            # 更新参数
            current_step.collected_params[param_name] = param_value
            print(f"📝 [{self.agent_id}] 收集参数 {param_name} = {param_value}")
        
        # 3. 继续执行工作流
        session = self.session_manager.get_session(session_id)
        if not session:
            return self.error_response(session_id, "会话不存在")
        
        session.context['workflow'] = workflow_ctx.to_dict()
        
        return await self._execute_workflow(workflow_ctx, session)
    
    async def _execute_workflow(self, workflow_ctx: WorkflowContext, 
                                session: AgentSession) -> AgentResponse:
        """执行工作流（支持中间暂停）"""
        while not workflow_ctx.is_completed():
            current_step = workflow_ctx.get_current_step()
            
            if not current_step:
                break
            
            print(f"▶️  [{self.name}] 执行步骤 {current_step.step_id}: {current_step.description}")
            
            # 1. 检查步骤参数是否完整
            if not current_step.is_params_complete():
                missing_params = current_step.get_missing_params()
                next_param = missing_params[0]
                
                # 更新会话上下文
                session.context['workflow'] = workflow_ctx.to_dict()
                session.context['waiting_param'] = next_param
                
                # 询问用户
                prompt = self._generate_param_prompt(current_step, next_param)
                return self.ask_user(
                    session.session_id,
                    prompt,
                    expected_type=self._get_param_type(next_param)
                )
            
            # 2. 参数完整，执行步骤
            try:
                current_step.status = "running"
                result = await self._execute_step(current_step, workflow_ctx)
                current_step.status = "completed"
                current_step.result = result
                
                # 将结果保存到全局变量
                workflow_ctx.global_variables[f'step_{current_step.step_id}_result'] = result
                
                print(f"✅ [{self.name}] 步骤完成: {current_step.description}")
                
            except Exception as e:
                current_step.status = "failed"
                print(f"❌ [{self.name}] 步骤失败: {e}")
                
                return self.error_response(
                    session.session_id,
                    f"步骤 {current_step.description} 执行失败: {str(e)}"
                )
            
            # 3. 移动到下一步
            workflow_ctx.move_next()
        
        # 工作流完成
        message = self._generate_completion_message(workflow_ctx)
        return self.complete_session(session.session_id, workflow_ctx.to_dict(), message)
    
    async def _generate_workflow(self, query: str) -> List[WorkflowStep]:
        """
        生成工作流步骤（简化版，实际应该调用LLM）
        
        Args:
            query: 用户查询
            
        Returns:
            工作流步骤列表
        """
        # 这里使用简单规则，实际应该调用LLM分析query
        
        # 示例：如果查询包含"订酒店"和"叫车"
        if "酒店" in query or "宾馆" in query:
            return [
                WorkflowStep(
                    step_id="step_1",
                    step_type="booking",
                    description="预订酒店",
                    params={"service": "hotel"},
                    required_params=["city", "check_in_date", "check_out_date"]
                )
            ]
        
        # 默认返回简单的工作流
        return [
            WorkflowStep(
                step_id="step_1",
                step_type="task",
                description="执行任务",
                params={},
                required_params=[]
            )
        ]
    
    async def _execute_step(self, step: WorkflowStep, ctx: WorkflowContext) -> Any:
        """
        执行单个步骤
        
        Args:
            step: 工作流步骤
            ctx: 工作流上下文
            
        Returns:
            执行结果
        """
        # 这里简化处理，实际应该根据step_type调用不同的服务
        if step.step_type == "booking":
            return {
                "success": True,
                "order_id": "ORDER_12345",
                "message": "预订成功"
            }
        
        return {"success": True}
    
    def _generate_param_prompt(self, step: WorkflowStep, param_name: str) -> str:
        """生成参数询问提示"""
        prompts = {
            "city": f"在执行'{step.description}'时，请问是哪个城市？",
            "check_in_date": f"请问入住日期是？",
            "check_out_date": f"请问退房日期是？",
            "pickup_location": f"请问上车地点是？",
            "pickup_time": f"请问用车时间是？",
            "destination": f"请问目的地是？"
        }
        return prompts.get(param_name, f"请提供 {param_name}")
    
    def _get_param_type(self, param_name: str) -> str:
        """获取参数类型"""
        type_mapping = {
            "city": "location",
            "check_in_date": "date",
            "check_out_date": "date",
            "pickup_location": "location",
            "pickup_time": "datetime",
            "destination": "location"
        }
        return type_mapping.get(param_name, "text")
    
    def _extract_param_value(self, query: str, param_name: str) -> Any:
        """
        从用户输入中提取参数值
        
        Args:
            query: 用户输入
            param_name: 参数名
            
        Returns:
            参数值
        """
        # 简化处理，直接返回用户输入
        # 实际应该使用NER或LLM提取
        return query.strip()
    
    def _generate_completion_message(self, workflow_ctx: WorkflowContext) -> str:
        """生成完成消息"""
        completed_steps = [s for s in workflow_ctx.steps if s.status == "completed"]
        return f"工作流已完成，共成功执行了 {len(completed_steps)} 个步骤"
