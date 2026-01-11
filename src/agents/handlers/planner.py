"""
规划协调Agent - 处理复杂的跨域任务
将其他agents作为工具，进行任务规划和协调执行
"""
import json
import os
import logging
from typing import Dict, Any, List, Optional

from src.agents.base_classes import AgentResponse,SimpleAgentBase
from src.execution.tool_registry import ToolCategory
from src.core.events import AgentStatus
from src.llm import get_llm_manager


class PlannerAgent(SimpleAgentBase):
    """规划协调Agent - 处理需要多个agent协作的复杂任务"""
    
    def __init__(self, description: str, capabilities: list[str],
                 priority: int = 2, api_key: Optional[str] = None):
        super().__init__(name="planner_agent", description=description,
                        capabilities=capabilities, priority=priority)
        
        # 使用统一的LLM Manager
        self.llm_manager = get_llm_manager()
        self.model_name = None  # 使用配置中的默认模型
        
        # 初始化logger
        self.logger = logging.getLogger(self.name)
        
        self.available_agents: Dict[str, Dict[str, Any]] = {}
        self.current_plan: List[Dict[str, Any]] = []
        self.execution_history: List[Dict[str, Any]] = []
        
    def set_available_agents(self, agents_info: Dict[str, Dict[str, Any]]):
        """设置可用的agents信息"""
        self.available_agents = agents_info
        
    @property
    def tool_categories(self) -> List[ToolCategory]:
        """规划Agent不直接使用工具"""
        return []
    
    def can_handle(self, query: str) -> bool:
        """
        判断是否能处理该查询
        规划Agent处理复杂的、跨域的任务
        通常由orchestrator决策后调用
        """
        return True
    
    def handle(self, query: str, context: Optional[Dict[str, Any]] = None) -> AgentResponse:
        """
        处理复杂任务的主流程：
        1. 规划任务列表
        2. 依次执行任务
        3. 根据执行结果调整计划
        4. 汇总最终结果
        """

        self.logger.info(f"PlannerAgent开始处理复杂任务: {query}")
        
        # 检查是否是恢复执行（从 context 中恢复状态）
        is_resume = False
        if context and 'planner_state' in context:
            planner_state = context['planner_state']
            self.current_plan = planner_state.get('plan', [])
            self.execution_history = planner_state.get('execution_history', [])
            self._current_user_request = planner_state.get('original_query', query)
            is_resume = True
            self.logger.info(f"恢复执行 - 已完成 {len(self.execution_history)}/{len(self.current_plan)} 个任务")
        else:
            # 首次执行，重置状态
            self.current_plan = []
            self.execution_history = []
            self._current_user_request = query  # 保存原始查询供子任务使用
        
        # 阶段1: 生成任务计划（仅首次执行）
        if not is_resume:
            plan_result = self._generate_plan(query, context)
            if not plan_result["success"]:
                # 如果是"单个agent可以处理"的情况，返回友好的提示而不是错误
                reason = plan_result.get("reason", "")
                if reason == "单个agent可以处理":
                    return AgentResponse(
                        agent=self.name,
                        status=AgentStatus.COMPLETED,
                        query=query,
                        message="这个任务不需要复杂的规划，您可以直接向其他专门的助手提出具体需求。"
                    )
                else:
                    # 其他错误情况（JSON解析失败、验证失败等）
                    self.logger.error(f"任务规划失败: {reason}")
                    return AgentResponse(
                        agent=self.name,
                        status=AgentStatus.ERROR,
                        query=query,
                        message="抱歉，我无法为这个任务制定执行计划。"
                    )
            
            self.current_plan = plan_result["tasks"]
            self.logger.info(f"任务计划已生成，共{len(self.current_plan)}个步骤")
        
        # 阶段2: 执行任务计划
        execution_result = self._execute_plan(context, user_input=query if is_resume else None)
        
        # 如果有任务需要用户输入，返回 WAITING_INPUT 并保存状态
        if execution_result.get("waiting_input"):
            pending_task = execution_result.get("pending_task", {})
            return AgentResponse(
                agent=self.name,
                status=AgentStatus.WAITING_INPUT,
                query=query,
                message=pending_task.get("prompt", "请提供更多信息"),
                data={
                    "plan": self.current_plan,
                    "execution_history": self.execution_history,
                    "pending_task": pending_task,
                    # 保存状态，供下次恢复使用
                    "planner_state": {
                        "plan": self.current_plan,
                        "execution_history": self.execution_history,
                        "original_query": self._current_user_request
                    }
                }
            )
        
        # 阶段3: 生成最终回复
        final_response = self._generate_final_response(query, execution_result, context)
        
        return AgentResponse(
            agent=self.name,
            status=AgentStatus.COMPLETED if execution_result["all_success"] else AgentStatus.ERROR,
            query=query,
            message=final_response,
            data={
                "plan": self.current_plan,
                "execution_history": self.execution_history
            }
        )
    
    def _generate_plan(self, user_request: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        使用LLM生成任务执行计划
        """
        # 构建agents能力描述
        agents_description = self._build_agents_description()
        
        # 构建规划prompt
        planning_prompt = f"""你是一个任务规划专家。用户提出了一个复杂需求，你需要将其分解为多个子任务，并指定由哪个专门的agent来完成。

可用的agents及其能力：
{agents_description}

用户需求：{user_request}

请分析这个需求，制定一个任务执行计划。计划格式为JSON数组，每个任务包含：
- task_id: 任务编号（从1开始）
- description: 任务描述
- agent: 负责执行的agent名称
- depends_on: 依赖的任务ID列表（可选，如果该任务需要等待其他任务完成）

示例：
[
    {{"task_id": 1, "description": "查询当前位置到目的地的路线", "agent": "navigation_agent", "depends_on": []}},
    {{"task_id": 2, "description": "播放适合长途驾驶的音乐", "agent": "music_agent", "depends_on": []}},
    {{"task_id": 3, "description": "将空调设置为舒适温度", "agent": "vehicle_control_agent", "depends_on": []}}
]

请只返回JSON数组，不要包含其他文字。如果这个任务不需要分解（单个agent就能完成），返回空数组[]。"""

        try:
            # 调用LLM生成计划
            messages = [{"role": "user", "content": planning_prompt}]
            
            response = self.llm_manager.chat(
                messages=messages,
                model="qwen-plus",  # 任务规划使用qwen-plus
                temperature=0.7
            )
            
            plan_text = response.content.strip()
            self.logger.info(f"LLM生成的计划: {plan_text}")
            
            # 解析JSON
            # 移除可能的markdown代码块标记
            if "```json" in plan_text:
                plan_text = plan_text.split("```json")[1].split("```")[0].strip()
            elif "```" in plan_text:
                plan_text = plan_text.split("```")[1].split("```")[0].strip()
            
            tasks = json.loads(plan_text)
            
            # 如果返回空数组，说明不需要规划agent处理
            if not tasks:
                return {"success": False, "reason": "单个agent可以处理"}
            
            # 验证计划的有效性
            if not self._validate_plan(tasks):
                self.logger.error("生成的计划无效")
                return {"success": False, "reason": "计划验证失败"}
            
            return {"success": True, "tasks": tasks}
            
        except json.JSONDecodeError as e:
            self.logger.error(f"解析任务计划失败: {e}")
            return {"success": False, "reason": "计划格式错误"}
        except Exception as e:
            self.logger.error(f"生成任务计划失败: {e}")
            return {"success": False, "reason": str(e)}
    
    def _build_agents_description(self) -> str:
        """构建agents能力描述"""
        descriptions = []
        for agent_name, agent_info in self.available_agents.items():
            if agent_name == "planner_agent":  # 跳过自己
                continue
            description = agent_info.get("description", "")
            capabilities = agent_info.get("capabilities", [])
            cap_str = "、".join(capabilities) if capabilities else "通用任务"
            descriptions.append(f"- {agent_name}: {description} (能力: {cap_str})")
        
        return "\n".join(descriptions)
    
    def _validate_plan(self, tasks: List[Dict[str, Any]]) -> bool:
        """验证任务计划的有效性"""
        if not tasks:
            return False
        
        # 检查必需字段
        for task in tasks:
            if not all(key in task for key in ["task_id", "description", "agent"]):
                return False
            
            # 检查agent是否存在
            agent_name = task["agent"]
            if agent_name not in self.available_agents and agent_name != "chat_agent":
                self.logger.warning(f"未知的agent: {agent_name}")
                return False
        
        return True
    
    def _execute_plan(self, context: Optional[Dict[str, Any]], user_input: Optional[str] = None) -> Dict[str, Any]:
        """
        执行任务计划
        按照依赖关系依次执行，每次执行后评估是否需要调整计划
        
        Args:
            context: 上下文信息
            user_input: 用户补充的输入（恢复执行时）
        """
        # 找到已完成的任务
        completed_tasks = set()
        for record in self.execution_history:
            if record['status'] == 'completed':
                completed_tasks.add(record['task_id'])
        
        all_success = True
        
        # 获取agent_manager（从context中传入）
        agent_manager = context.get("agent_manager") if context else None
        if not agent_manager:
            self.logger.error("无法获取agent_manager")
            return {"all_success": False, "message": "系统错误：无法访问agent管理器"}
        
        # 找到待执行的任务（跳过已完成的）
        for task in self.current_plan:
            task_id = task["task_id"]
            
            # 跳过已完成的任务
            if task_id in completed_tasks:
                continue
            
            # 检查依赖是否完成
            depends_on = task.get("depends_on", [])
            if not all(dep in completed_tasks for dep in depends_on):
                self.logger.warning(f"任务{task_id}的依赖未完成，跳过")
                continue
            
            # 执行任务
            self.logger.info(f"执行任务{task_id}: {task['description']}")
            
            # 如果是恢复执行，将用户输入传递给当前任务
            task_context = context.copy() if context else {}
            if user_input:
                task_context['user_input'] = user_input
                self.logger.info(f"传递用户补充信息: {user_input}")
            
            result = self._execute_single_task(task, agent_manager, task_context)
            
            # 判断任务状态
            task_status = result.get("status", "error")
            
            # 记录执行历史
            self.execution_history.append({
                "task_id": task_id,
                "description": task["description"],
                "agent": task["agent"],
                "status": task_status,
                "response": result.get("response", ""),
                "error": result.get("error")
            })
            
            if task_status == "completed":
                completed_tasks.add(task_id)
                self.logger.info(f"任务{task_id}执行成功")
            elif task_status == "waiting_input":
                # 需要用户输入，终止执行并返回 WAITING_INPUT
                self.logger.info(f"任务{task_id}需要用户补充信息")
                return {
                    "all_success": False,
                    "waiting_input": True,
                    "completed_count": len(completed_tasks),
                    "total_count": len(self.current_plan),
                    "pending_task": {
                        "task_id": task_id,
                        "description": task["description"],
                        "prompt": result.get("response")
                    }
                }
            else:
                all_success = False
                self.logger.error(f"任务{task_id}执行失败: {result.get('error')}")
                
                # 评估是否需要调整计划
                should_continue = self._evaluate_and_adjust(task_id, result, context)
                if not should_continue:
                    self.logger.info("根据执行结果，终止后续任务")
                    break
        
        return {
            "all_success": all_success,
            "completed_count": len(completed_tasks),
            "total_count": len(self.current_plan)
        }
    
    def _execute_single_task(
        self, 
        task: Dict[str, Any], 
        agent_manager: Any,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """执行单个任务"""
        agent_name = task["agent"]
        task_description = task["description"]
        
        try:
            # 构建增强的上下文，包含：
            # 1. 原始用户查询（用于提取槽位信息）
            # 2. 已执行任务的历史（依赖任务的结果）
            # 3. 当前任务描述
            enhanced_context = context.copy() if context else {}
            
            # 添加原始查询到上下文（如果存在）
            if 'original_query' not in enhanced_context and hasattr(self, '_current_user_request'):
                enhanced_context['original_query'] = self._current_user_request
            
            # 添加已完成任务的执行历史
            enhanced_context['execution_history'] = self.execution_history.copy()
            
            # 添加当前任务信息
            enhanced_context['current_task'] = {
                'task_id': task['task_id'],
                'description': task_description,
                'depends_on': task.get('depends_on', [])
            }
            
            # 构建完整的查询文本，包含任务描述和上下文提示
            # 这样子agent的LLM可以从原始查询中提取槽位信息
            full_query = task_description
            if 'original_query' in enhanced_context:
                full_query = f"{task_description}\n\n[原始用户需求]: {enhanced_context['original_query']}"
            
            # 如果有依赖任务的结果，也添加到查询中
            if task.get('depends_on'):
                dependent_results = []
                for dep_id in task['depends_on']:
                    for history in self.execution_history:
                        # 判断任务是否成功完成
                        if history['task_id'] == dep_id and history['status'] == 'completed':
                            dependent_results.append(f"- {history['description']}: {history['response']}")
                
                if dependent_results:
                    full_query += "\n\n[相关任务结果]:\n" + "\n".join(dependent_results)
            
            # 调用agent_manager执行任务
            result = agent_manager.execute_agent(agent_name, full_query, enhanced_context)
            
            # 判断执行状态：
            # - COMPLETED: 任务完成
            # - WAITING_INPUT: 需要用户补充信息（不是失败）
            # - ERROR: 执行错误
            status_value = result.status.value if hasattr(result.status, 'value') else str(result.status)
            
            return {
                "status": status_value,
                "response": result.message,
                "error": None if result.status == AgentStatus.COMPLETED else result.message
            }
            
        except Exception as e:
            self.logger.error(f"执行任务时出错: {e}")
            return {
                "status": "error",
                "response": "",
                "error": str(e)
            }
    
    def _evaluate_and_adjust(
        self, 
        failed_task_id: int, 
        result: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """
        评估执行结果，决定是否调整计划
        返回True表示继续执行，False表示终止
        """
        # 简化版：如果失败不是关键任务，继续执行
        # 未来可以用LLM来智能判断
        
        # 找到失败的任务
        failed_task = None
        for task in self.current_plan:
            if task["task_id"] == failed_task_id:
                failed_task = task
                break
        
        if not failed_task:
            return True
        
        # 检查后续任务是否依赖这个失败的任务
        has_dependent = False
        for task in self.current_plan:
            if failed_task_id in task.get("depends_on", []):
                has_dependent = True
                break
        
        # 如果有依赖，终止执行
        if has_dependent:
            self.logger.warning(f"任务{failed_task_id}失败且有依赖任务，终止执行")
            return False
        
        # 否则继续执行
        self.logger.info(f"任务{failed_task_id}失败但无依赖，继续执行其他任务")
        return True
    
    def _generate_final_response(
        self,
        user_request: str,
        execution_result: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        根据执行历史生成最终的统一回复
        """
        # 构建执行摘要
        summary_parts = []
        for record in self.execution_history:
            # 判断任务是否成功完成
            status_icon = "✓" if record['status'] == 'completed' else "✗"
            summary_parts.append(f"{status_icon} {record['description']}: {record['response']}")
        
        execution_summary = "\n".join(summary_parts)
        
        # 使用LLM生成自然的最终回复
        final_prompt = f"""你是一个智能助手。用户提出了一个复杂需求，你已经通过多个步骤完成了处理。

用户需求：{user_request}

执行过程：
{execution_summary}

请根据执行结果，生成一个自然、友好的回复，总结任务完成情况。如果全部成功，简洁地确认。如果部分失败，说明哪些完成了，哪些遇到问题。"""

        try:
            messages = [{"role": "user", "content": final_prompt}]
            
            response = self.llm_manager.chat(
                messages=messages,
                model="qwen-plus",  # 任务规划使用qwen-plus
                temperature=0.7
            )
            
            final_response = response.content.strip()
            return final_response
            
        except Exception as e:
            self.logger.error(f"生成最终回复失败: {e}")
            # 降级：返回简单的摘要
            completed = execution_result["completed_count"]
            total = execution_result["total_count"]
            if execution_result["all_success"]:
                return f"好的，我已经完成了所有{total}项任务。"
            else:
                return f"我完成了{completed}/{total}项任务，部分任务遇到了问题。"
