"""
Orchestrator 模块适配器
负责监听ASR事件，调用Orchestrator进行决策，并分发给对应的Agent
"""
import os
from typing import TYPE_CHECKING, Optional

from src.core.interfaces import IModule
from src.core.events import Event, EventType, ASREvent
from src.orchestrator import Orchestrator

if TYPE_CHECKING:
    from src.core.controller import SystemController


class OrchestratorModuleAdapter(IModule):
    """Orchestrator模块适配器"""
    
    def __init__(self, controller: 'SystemController', 
                 llm_api_key: Optional[str] = None,
                 use_mock_llm: bool = False):
        """
        初始化Orchestrator适配器
        
        Args:
            controller: 系统控制器
            llm_api_key: LLM API密钥（可选，从环境变量读取）
            use_mock_llm: 是否使用模拟LLM
        """
        self._name = "orchestrator"
        self._controller = controller
        self._orchestrator: Optional[Orchestrator] = None
        self._running = False
        
        # 获取API Key
        self._api_key = llm_api_key or os.getenv("DASHSCOPE_API_KEY")
        self._use_mock_llm = use_mock_llm
        
        # 如果没有API Key，自动使用模拟LLM
        if not self._api_key and not use_mock_llm:
            print("⚠️  未配置DASHSCOPE_API_KEY，将使用模拟LLM")
            self._use_mock_llm = True
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def initialize(self) -> bool:
        """初始化Orchestrator"""
        try:
            # 创建Orchestrator实例
            self._orchestrator = Orchestrator(
                controller=self._controller,
                llm_api_key=self._api_key,
                use_mock_llm=self._use_mock_llm
            )
            
            print(f"✅ Orchestrator模块初始化成功 (模拟LLM: {self._use_mock_llm})")
            return True
            
        except Exception as e:
            print(f"❌ Orchestrator模块初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start(self) -> bool:
        """启动模块"""
        if not self._orchestrator:
            print("❌ Orchestrator未初始化")
            return False
        
        self._running = True
        print("✅ Orchestrator模块启动成功")
        return True
    
    def stop(self):
        """停止模块"""
        self._running = False
        print("🛑 Orchestrator模块已停止")
    
    def cleanup(self):
        """清理资源"""
        self._orchestrator = None
    
    def handle_event(self, event: Event):
        """
        处理事件 - 监听ASR识别结果
        
        Args:
            event: 事件对象
        """
        if not self._running or not self._orchestrator:
            return
        
        # 只处理ASR识别成功事件
        if event.type == EventType.ASR_RECOGNITION_SUCCESS:
            self._handle_asr_result(event)
    
    def _handle_asr_result(self, event: ASREvent):
        """
        处理ASR识别结果
        
        Args:
            event: ASR事件
        """
        try:
            # 提取识别文本
            text = event.data.get('text', '').strip()
            confidence = event.data.get('confidence', 0.0)
            
            if not text:
                return
            
            print(f"\n{'='*60}")
            print(f"🎯 Orchestrator收到ASR结果: {text}")
            print(f"   置信度: {confidence:.2f}")
            
            # 调用Orchestrator进行决策
            decision = self._orchestrator.process_query(text)
            
            print(f"📍 决策结果:")
            print(f"   选择Agent: {decision.selected_agent}")
            print(f"   置信度: {decision.confidence:.2f}")
            print(f"   理由: {decision.reasoning}")
            if decision.parameters:
                print(f"   参数: {decision.parameters}")
            print(f"{'='*60}\n")
            
            # 发送GUI更新事件，显示决策结果
            self._publish_decision_to_gui(text, decision)
            
            # TODO: 这里可以发送事件给对应的Agent执行
            # 目前先打印日志，后续可以扩展
            self._dispatch_to_agent(decision.selected_agent, text, decision)
            
            # 模拟Agent响应（实际应该由Agent返回）
            agent_response = f"[{decision.selected_agent}] 已处理: {text}"
            self._orchestrator.record_agent_response(
                agent_name=decision.selected_agent,
                response=agent_response
            )
            
        except Exception as e:
            print(f"❌ Orchestrator处理ASR结果失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _publish_decision_to_gui(self, query: str, decision):
        """
        发布决策结果到GUI
        
        Args:
            query: 用户查询
            decision: 决策结果
        """
        from src.core.events import Event, EventType
        
        # 发送GUI更新事件
        gui_event = Event.create(
            event_type=EventType.GUI_UPDATE_TEXT,
            source=self._name,
            data={
                'type': 'orchestrator_decision',
                'query': query,
                'agent': decision.selected_agent,
                'confidence': decision.confidence,
                'reasoning': decision.reasoning,
                'parameters': decision.parameters
            }
        )
        self._controller.publish_event(gui_event)
    
    def _dispatch_to_agent(self, agent_name: str, query: str, decision):
        """
        分发任务给Agent
        
        Args:
            agent_name: Agent名称
            query: 用户查询
            decision: 决策结果
        """
        # TODO: 实现真实的Agent调度
        # 可以通过事件系统或直接调用Agent模块
        print(f"🚀 [分发] {agent_name} <- '{query}'")
        
        # 示例：可以发送一个AGENT_EXECUTE事件
        # agent_event = Event(
        #     type=EventType.AGENT_EXECUTE,
        #     source=self._name,
        #     data={
        #         'agent_name': agent_name,
        #         'query': query,
        #         'decision': decision
        #     }
        # )
        # self._controller.publish_event(agent_event)
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        if self._orchestrator:
            return self._orchestrator.get_statistics()
        return {}
