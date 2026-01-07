"""
GUI模块适配器

将GUI组件接入新架构的事件系统
"""
from typing import Optional, Callable
from PyQt5.QtCore import QObject, pyqtSignal

from src.core.interfaces import IGUIModule
from src.core.events import Event, EventType, AgentStatus


class GUIModuleAdapter(QObject):
    """
    GUI模块适配器
    
    职责：
    1. 接收系统事件并转换为Qt信号
    2. 将Qt信号发送给GUI组件
    3. 管理GUI的生命周期
    
    注意：继承QObject以支持Qt信号/槽机制
    注意：不直接继承IGUIModule以避免元类冲突，但实现其所有方法
    """
    
    # Qt信号定义（用于线程安全的GUI更新）
    wakeword_detected_signal = pyqtSignal(dict)      # 唤醒词检测
    vad_speech_start_signal = pyqtSignal(dict)       # 语音开始
    vad_speech_end_signal = pyqtSignal(dict)         # 语音结束
    asr_start_signal = pyqtSignal(dict)              # ASR开始识别
    asr_result_signal = pyqtSignal(dict)             # ASR识别结果
    asr_error_signal = pyqtSignal(str)               # ASR识别错误
    state_changed_signal = pyqtSignal(dict)          # 状态变化
    audio_frame_signal = pyqtSignal(dict)            # 音频帧（用于波形显示）
    orchestrator_decision_signal = pyqtSignal(dict)  # Orchestrator决策结果
    agent_response_signal = pyqtSignal(dict)         # Agent响应结果
    memory_recall_signal = pyqtSignal(dict)          # 记忆召回事件
    
    _instance_counter = 0  # 类变量，用于追踪实例
    
    def __init__(self, controller):
        """
        初始化GUI模块适配器
        
        Args:
            controller: SystemController 实例
        """
        QObject.__init__(self)  # 初始化QObject
        
        GUIModuleAdapter._instance_counter += 1
        self._instance_id = GUIModuleAdapter._instance_counter
        
        self._controller = controller
        self._running = False
        
        # 事件处理函数映射
        self._event_handlers = {
            EventType.WAKEWORD_DETECTED: self._on_wakeword_detected,
            EventType.VAD_SPEECH_START: self._on_vad_speech_start,
            EventType.VAD_SPEECH_END: self._on_vad_speech_end,
            EventType.ASR_RECOGNITION_START: self._on_asr_start,
            EventType.ASR_RECOGNITION_SUCCESS: self._on_asr_success,
            EventType.ASR_RECOGNITION_FAILED: self._on_asr_failed,
            EventType.STATE_CHANGED: self._on_state_changed,
            EventType.AUDIO_FRAME_READY: self._on_audio_frame,
            EventType.GUI_UPDATE_TEXT: self._on_gui_update_text,
        }
    
    @property
    def name(self) -> str:
        return "gui"
    
    def initialize(self) -> bool:
        """初始化GUI模块"""
        print(f"✅ [{self.name}] 初始化成功")
        return True
    
    def start(self) -> bool:
        """启动GUI模块"""
        if self._running:
            print(f"⚠️ [{self.name}#{self._instance_id}] 已经在运行，跳过重复启动")
            return True
        
        self._running = True
        
        # GUI适配器作为模块已经会接收所有事件（通过handle_event）
        # 不需要再通过subscribe订阅，否则会收到重复事件
        
        print(f"✅ [{self.name}#{self._instance_id}] 已启动")
        return True
    
    def stop(self):
        """停止GUI模块"""
        if not self._running:
            return
        
        self._running = False
        
        # 不需要取消订阅，因为我们没有使用subscribe
        
        print(f"✅ [{self.name}#{self._instance_id}] 已停止")
    
    def cleanup(self):
        """清理资源"""
        print(f"✅ [{self.name}] 资源已清理")
    
    def handle_event(self, event: Event):
        """
        处理来自控制器的事件
        
        Args:
            event: 事件对象
        """
        if not self._running:
            print(f"⚠️ [{self.name}#{self._instance_id}] 已停止，忽略事件: {event.type.value}")
            return
        
        # 根据事件类型调用相应的处理函数
        handler = self._event_handlers.get(event.type)
        if handler:
            handler(event)
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    # ==================== IGUIModule 专用接口 ====================
    
    def update_display(self, data: dict):
        """
        更新显示
        
        Args:
            data: 显示数据
        """
        # GUI适配器不需要主动更新，而是响应事件
        pass
    
    def show_message(self, message: str, level: str = "info"):
        """
        显示消息
        
        Args:
            message: 消息内容
            level: 消息级别 (info/warning/error)
        """
        print(f"[{level.upper()}] {message}")
    
    # ==================== 事件处理函数 ====================
    
    def _on_wakeword_detected(self, event: Event):
        """处理唤醒词检测事件"""
        data = {
            'keyword': event.payload.keyword,
            'confidence': event.payload.confidence,
            'timestamp': event.timestamp
        }
        self.wakeword_detected_signal.emit(data)
    
    def _on_vad_speech_start(self, event: Event):
        """处理语音开始事件"""
        data = {
            'timestamp': event.timestamp
        }
        self.vad_speech_start_signal.emit(data)
    
    def _on_vad_speech_end(self, event: Event):
        """处理语音结束事件"""
        data = {
            'duration_ms': event.payload.duration_ms if event.payload else 0,
            'timestamp': event.timestamp
        }
        self.vad_speech_end_signal.emit(data)
    
    def _on_asr_start(self, event: Event):
        """处理ASR开始识别事件"""
        data = {
            'timestamp': event.timestamp
        }
        self.asr_start_signal.emit(data)
    
    def _on_asr_success(self, event: Event):
        """处理ASR识别成功事件"""
        data = {
            'text': event.payload.text,
            'confidence': event.payload.confidence,
            'latency_ms': event.payload.latency_ms,
            'timestamp': event.timestamp
        }
        self.asr_result_signal.emit(data)
    
    def _on_asr_failed(self, event: Event):
        """处理ASR识别失败事件"""
        # ASR失败事件可能没有 payload，或者 payload 中包含错误信息
        error = 'Unknown error'
        if event.payload and hasattr(event.payload, 'text'):
            error = event.payload.text or error
        self.asr_error_signal.emit(error)
    
    def _on_state_changed(self, event: Event):
        """处理状态变化事件"""
        data = {
            'old_state': event.payload.from_state if event.payload else '',
            'new_state': event.payload.to_state if event.payload else '',
            'timestamp': event.timestamp
        }
        self.state_changed_signal.emit(data)
    
    def _on_audio_frame(self, event: Event):
        """处理音频帧事件（用于波形显示）"""
        # 注意：这个事件频率很高，谨慎处理
        # 使用新的 Payload 模式获取数据
        if not event.payload:
            return
        
        data = {
            'audio_data': event.payload.frame_data,
            'sample_rate': event.payload.sample_rate,
            'timestamp': event.timestamp
        }
        # 只在GUI需要更新时发送信号
        if self._running and event.payload.frame_data is not None:
            self.audio_frame_signal.emit(data)
    
    def _on_gui_update_text(self, event: Event):
        """处理GUI文本更新事件（包括Orchestrator决策结果和Agent响应）"""
        # GUI_UPDATE_TEXT 使用 payload 传递数据
        if not event.payload or not isinstance(event.payload, dict):
            return
        
        update_type = event.payload.get('type', '')
        
        # 处理Orchestrator决策结果
        if update_type == 'orchestrator_decision':
            decision_data = {
                'query': event.payload.get('query', ''),
                'agent': event.payload.get('agent', ''),
                'confidence': event.payload.get('confidence', 0.0),
                'reasoning': event.payload.get('reasoning', ''),
                'parameters': event.payload.get('parameters', {}),
                'timestamp': event.timestamp
            }
            self.orchestrator_decision_signal.emit(decision_data)
        
        # 处理Agent响应结果
        elif update_type == 'agent_response':
            response_data = {
                'agent': event.payload.get('agent', ''),
                'message': event.payload.get('message', ''),
                'status': event.payload.get('status', AgentStatus.COMPLETED),
                'data': event.payload.get('data', {}),
                'timestamp': event.timestamp
            }
            self.agent_response_signal.emit(response_data)
        
        # 处理记忆召回事件
        elif event.payload.get('event_type') == 'memory_recall':
            recall_data = {
                'agent_name': event.payload.get('agent_name', ''),
                'recent_memories': event.payload.get('recent_memories', []),
                'related_memories': event.payload.get('related_memories', []),
                'long_term_memory': event.payload.get('long_term_memory', {}),
                'timestamp': event.timestamp
            }
            self.memory_recall_signal.emit(recall_data)
    
    # ==================== 统计信息 ====================
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            'is_running': self._running,
            'subscribed_events': len(self._event_handlers)
        }
    
    # ==================== 信号连接辅助方法 ====================
    
    def connect_wakeword_handler(self, handler: Callable):
        """连接唤醒词检测处理器"""
        self.wakeword_detected_signal.connect(handler)
    
    def connect_vad_start_handler(self, handler: Callable):
        """连接语音开始处理器"""
        self.vad_speech_start_signal.connect(handler)
    
    def connect_vad_end_handler(self, handler: Callable):
        """连接语音结束处理器"""
        self.vad_speech_end_signal.connect(handler)
    
    def connect_asr_start_handler(self, handler: Callable):
        """连接ASR开始处理器"""
        self.asr_start_signal.connect(handler)
    
    def connect_asr_result_handler(self, handler: Callable):
        """连接ASR结果处理器"""
        self.asr_result_signal.connect(handler)
    
    def connect_asr_error_handler(self, handler: Callable):
        """连接ASR错误处理器"""
        self.asr_error_signal.connect(handler)
    
    def connect_state_changed_handler(self, handler: Callable):
        """连接状态变化处理器"""
        self.state_changed_signal.connect(handler)
    
    
    def connect_memory_recall_handler(self, handler: Callable):
        """连接记忆召回处理器"""
        self.memory_recall_signal.connect(handler)
    def connect_audio_frame_handler(self, handler: Callable):
        """连接音频帧处理器"""
        self.audio_frame_signal.connect(handler)
    
    def connect_orchestrator_decision_handler(self, handler: Callable):
        """连接Orchestrator决策处理器"""
        self.orchestrator_decision_signal.connect(handler)
    
    def connect_agent_response_handler(self, handler: Callable):
        """连接Agent响应处理器"""
        self.agent_response_signal.connect(handler)
