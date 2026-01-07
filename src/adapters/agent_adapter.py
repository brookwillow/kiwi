"""
Agent 模块适配器
负责监听Agent分发请求事件，调用agent_manager执行Agent，并发布结果
"""
from typing import TYPE_CHECKING, Optional

from src.core.interfaces import IModule
from src.core.events import Event, EventType, AgentResponse, AgentRequestEvent
from src.core.events import AgentStatus
from src.core.message_tracker import get_message_tracker
from typing import List, Dict, Any
from src.core.session_manager import get_session_manager

if TYPE_CHECKING:
    from src.core.controller import SystemController


class AgentModuleAdapter(IModule):
    """Agent模块适配器"""
    
    def __init__(self, controller: 'SystemController', agent_manager):
        """
        初始化Agent适配器
        
        Args:
            controller: 系统控制器
            agent_manager: Agent管理器实例
        """
        self._name = "agent_adapter"
        self._controller = controller
        self._agent_manager = agent_manager
        self._running = False
        self._session_manager = get_session_manager()
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def initialize(self) -> bool:
        """初始化Agent适配器（包括初始化agent_manager）"""
        try:
            # 初始化agent_manager
            if not self._agent_manager.initialize():
                print(f"❌ Agent管理器初始化失败")
                return False
            
            print(f"✅ Agent适配器初始化成功")
            return True
            
        except Exception as e:
            print(f"❌ Agent适配器初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start(self) -> bool:
        """启动模块"""
        self._running = True
        print("✅ Agent适配器启动成功")
        return True
    
    def stop(self):
        """停止模块"""
        self._running = False
        print("🛑 Agent适配器已停止")
    
    def cleanup(self):
        """清理资源"""
        # 清理agent_manager的资源
        if self._agent_manager:
            self._agent_manager._agents.clear()
            self._agent_manager._agent_handlers.clear()
    
    def handle_event(self, event: Event):
        """
        处理事件 - 监听Agent分发请求
        
        Args:
            event: 事件对象
        """
        if not self._running:
            return
        
        # 处理Agent分发请求
        if event.type == EventType.AGENT_DISPATCH_REQUEST:
            import threading
            thread = threading.Thread(
                target=self._handle_agent_dispatch,
                args=(event,),
                daemon=True
            )
            thread.start()
    
    def _handle_agent_dispatch(self, event: AgentRequestEvent):
        """
        处理Agent分发请求
        
        Args:
            event: 分发请求事件
        """
        try:
            # 使用强类型 payload
            agent_name = event.payload.agent_name
            query = event.payload.query
            msg_id = event.msg_id
            session_id = event.session_id
            session_action = event.session_action
            
            if not agent_name or not query:
                print("⚠️ [AgentAdapter] 无效的分发请求")
                return
            
            print(f"\n{'='*60}")
            print(f"🤖 [AgentAdapter] 处理分发请求: {agent_name}")
            print(f"   [AgentAdapter]会话操作: {session_action}")
            print(f"   [AgentAdapter]会话ID: {session_id}")
            print(f"   查询: {query}")
            if msg_id:
                print(f"   消息ID: {msg_id}")
            
            # 记录追踪
            if msg_id:
                tracker = get_message_tracker()
                tracker.add_trace(
                    msg_id=msg_id,
                    module_name=self._name,
                    event_type="agent_execution_start",
                    input_data={'agent_name': agent_name, 'query': query}
                )
            
            # if session_action == 'new':
            #     # 获取 agent 配置，获取优先级
            #     agent_config = self._agent_manager.get_agent_by_name(agent_name)
            #     priority = agent_config.get('priority', 2) if agent_config else 2
                
            #     # 在 adapter 层创建 session（Agent 不再关心 session）
            #     session = self._session_manager.create_session(
            #         agent_name=agent_name,
            #         priority=priority
            #     )
                
            #     if session is None:
            #         # Session 创建失败（被更高优先级阻止）
            #         error_msg = "当前有更重要的任务正在执行，请稍后再试"
            #         print(f"🚫 [AgentAdapter] {error_msg}")
                    
            #         # 返回错误响应
            #         response = AgentResponse(
            #             agent=agent_name,
            #             query=query,
            #             message=error_msg,
            #             status=AgentStatus.ERROR,
            #             data={"reason": "blocked_by_higher_priority"}
            #         )
            #         self._publish_agent_response(response, msg_id)
            #         return
            
            #     print(f"✅ [AgentAdapter] 创建 session: {session.session_id[:8]}...")
            
            # 调用agent_manager执行Agent（Agent 不需要知道 session_id）
            response: AgentResponse = self._agent_manager.execute_agent(
                agent_name=agent_name,
                query=query,
                data=event.payload.decision  # 使用 payload 中的 decision
            )
            
            # 固定响应状态，避免动态属性问题
            response_status = response.status
     
            # 使用 name 属性进行比较（因为 AgentStatus 继承自 str 导致 == 比较有问题）
            status_name = response_status.name if isinstance(response_status, AgentStatus) else str(response_status)
            
            if status_name == "WAITING_INPUT":
                print(f"⏳ [AgentAdapter] Agent {agent_name} 等待用户输入...")
                self._session_manager.wait_for_input(
                    session_id=session_id,
                    prompt=response.message
                )
            elif status_name == "COMPLETED":
                # 任务完成，关闭 session
                print(f"✅ [AgentAdapter] 进入COMPLETED分支...")
                self._session_manager.complete_session(session_id)
                print(f"✅ [AgentAdapter] Session 已完成: {session_id}...")
            elif status_name == "ERROR":
                # 错误，关闭 session
                print(f"❌ [AgentAdapter] 进入ERROR分支...")
                self._session_manager.complete_session(session_id)
                print(f"❌ [AgentAdapter] Session 出错: {session_id}...")
            else:
                print(f"⚠️ [AgentAdapter] 未匹配任何状态分支，当前状态名称: {status_name}")
            
            print(f" [AgentAdapter] Agent响应: {response.message}")
            print(f" [AgentAdapter] 状态: {response.status.name}")
            
            # 记录Agent响应
            if msg_id:
                tracker.add_trace(
                    msg_id=msg_id,
                    module_name=agent_name,
                    event_type="agent_response",
                    output_data={
                        'message': response.message,
                        'success': response.status == AgentStatus.COMPLETED,
                        'data': response.data
                    }
                )
                tracker.update_response(msg_id, response.message)
            
            # 发布Agent响应事件到GUI
            self._publish_agent_response(response, msg_id)
            
            # 如果Agent执行成功，发布TTS播报请求
            if response.message:
                self._publish_tts_request(response.message, msg_id)
                
        except Exception as e:
            print(f"❌ [AgentAdapter] 处理分发请求失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _publish_agent_response(self, response: AgentResponse, msg_id: Optional[str] = None):
        """
        发布Agent响应事件到GUI
        
        Args:
            response: Agent响应
            msg_id: 消息ID
        """
        print(f"📢 [AgentAdapter] 发布Agent响应到GUI: {response.message}, 状态: {response.status}")
        gui_event = Event.create(
            event_type=EventType.GUI_UPDATE_TEXT,
            source=self._name,
            payload={
                'type': 'agent_response',
                'agent': response.agent,
                'query': response.query,
                'message': response.message,
                'status': response.status,
                'data': response.data
            }
        )
        self._controller.publish_event(gui_event)
    
    def _publish_tts_request(self, text: str, msg_id: Optional[str] = None):
        """
        发布TTS播报请求
        
        Args:
            text: 播报文本
            msg_id: 消息ID
        """
        tracker = get_message_tracker()
        
        tts_event = Event.create(
            event_type=EventType.TTS_SPEAK_REQUEST,
            source=self._name,
            payload={
                'text': text,
                'priority': 'high'
            }
        )
        self._controller.publish_event(tts_event)
        print(f"🔊 [TTS] 请求播报: {text}")
        
        # 记录追踪
        if msg_id:
            tracker.add_trace(
                msg_id=msg_id,
                module_name="tts",
                event_type="tts_request",
                input_data={'text': text}
            )
            # 完成整个消息追踪
            tracker.complete_trace(msg_id)
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        return self._agent_manager.get_statistics()


    def get_available_agents(self) -> List[Dict[str, Any]]:
        return self._agent_manager.get_available_agents()

    def get_all_agents(self) -> List[Dict[str, Any]]:
        return self._agent_manager.get_all_agents()

    def get_agent_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        return self._agent_manager.get_agent_by_name(name)