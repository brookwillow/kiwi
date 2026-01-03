"""
Agent 模块适配器
负责监听Agent分发请求事件，调用agent_manager执行Agent，并发布结果
"""
from typing import TYPE_CHECKING, Optional

from src.core.interfaces import IModule
from src.core.events import Event, EventType
from src.core.message_tracker import get_message_tracker
from src.agents.base import AgentResponse
from typing import List, Dict, Any

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
    
    def _handle_agent_dispatch(self, event: Event):
        """
        处理Agent分发请求
        
        Args:
            event: 分发请求事件
        """
        try:
            data = event.data
            agent_name = data.get('agent_name')
            query = data.get('query')
            msg_id = event.msg_id
            
            if not agent_name or not query:
                print("⚠️ [AgentAdapter] 无效的分发请求")
                return
            
            print(f"\n{'='*60}")
            print(f"🤖 [AgentAdapter] 处理分发请求: {agent_name}")
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
            
            # 调用agent_manager执行Agent
            response = self._agent_manager.execute_agent(
                agent_name=agent_name,
                query=query,
                context=data
            )
            
            print(f"💬 [AgentAdapter] Agent响应: {response.message}")
            print(f"{'='*60}\n")
            
            # 记录Agent响应
            if msg_id:
                tracker.add_trace(
                    msg_id=msg_id,
                    module_name=agent_name,
                    event_type="agent_response",
                    output_data={
                        'message': response.message,
                        'success': response.success,
                        'data': response.data
                    }
                )
                tracker.update_response(msg_id, response.message)
            
            # 发布Agent响应事件到GUI
            self._publish_agent_response(response, msg_id)
            
            # 如果Agent执行成功，发布TTS播报请求
            if response.success and response.message:
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
        gui_event = Event.create(
            event_type=EventType.GUI_UPDATE_TEXT,
            source=self._name,
            msg_id=msg_id,
            data={
                'type': 'agent_response',
                'agent': response.agent,
                'query': response.query,
                'message': response.message,
                'success': response.success,
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
            msg_id=msg_id,
            data={
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