"""
VAD模块适配器

将现有的 VAD引擎 包装成符合新架构的模块
"""
from typing import Optional, Dict, Any
import numpy as np
from collections import deque

from src.core.interfaces import IVADModule
from src.core.events import Event, EventType, VADEvent as VADEventType
from src.vad import VADFactory, VADConfig, VADResult, VADEvent, VADState
from src.core.message_tracker import get_message_tracker


class VADModuleAdapter(IVADModule):
    """
    VAD模块适配器
    
    职责：
    1. 包装 VAD引擎
    2. 接收音频帧事件并进行语音检测
    3. 检测到语音事件后发布事件
    4. 管理VAD帧缓冲（处理帧大小对齐）
    """
    
    def __init__(self, controller, config: Optional[VADConfig] = None):
        """
        初始化VAD模块适配器
        
        Args:
            controller: SystemController 实例
            config: VAD配置
        """
        self._controller = controller
        self._config = config
        self._engine = None
        self._running = False
        self._enabled = True
        
        # VAD帧缓冲（用于对齐帧大小）
        self._frame_buffer = []
        self._frame_size = 480  # 30ms @ 16kHz，会在初始化后更新
        
        # 当前处理的消息ID
        self._current_msg_id: Optional[str] = None
        
        # 统计
        self._frames_processed = 0
        self._speech_segments = 0
    
    @property
    def name(self) -> str:
        return "vad"
    
    def initialize(self) -> bool:
        """初始化VAD引擎"""
        if not self._config:
            print(f"⚠️ [{self.name}] 未提供配置，跳过初始化")
            return True
        
        try:
            # 创建VAD引擎
            self._engine = VADFactory.create("webrtc", self._config)
            self._frame_size = self._config.frame_size
            
            print(f"✅ [{self.name}] 初始化成功")
            print(f"   帧大小: {self._frame_size} 样本 ({self._config.frame_duration_ms}ms)")
            print(f"   激进度: {self._config.aggressiveness}")
            return True
            
        except Exception as e:
            print(f"❌ [{self.name}] 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start(self) -> bool:
        """启动VAD检测"""
        if not self._engine:
            print(f"⚠️ [{self.name}] 引擎未初始化，跳过启动")
            return True
        
        self._running = True
        self._enabled = True
        print(f"✅ [{self.name}] 已启动")
        return True
    
    def stop(self):
        """停止VAD检测"""
        self._running = False
        print(f"✅ [{self.name}] 已停止")
    
    def cleanup(self):
        """清理资源"""
        self._engine = None
        self._frame_buffer.clear()
        print(f"✅ [{self.name}] 资源已清理")
    
    def handle_event(self, event: Event):
        """
        处理来自控制器的事件
        
        Args:
            event: 事件对象
        """
        if not self._engine or not self._running:
            return
        
        # 处理唤醒词事件 - 启动VAD延迟
        if event.type == EventType.WAKEWORD_DETECTED:
            if hasattr(self._engine, 'on_wakeword_detected'):
                self._engine.on_wakeword_detected()
        
        # 处理唤醒词重置事件 - 重置VAD引擎
        elif event.type == EventType.WAKEWORD_RESET:
            self.reset()
        
        # 处理音频帧事件 - 只在非IDLE状态处理
        elif event.type == EventType.AUDIO_FRAME_READY:
            if self._enabled and self._should_process_audio():
                # 如果事件有msg_id，记录下来
                if event.msg_id:
                    self._current_msg_id = event.msg_id
                self._process_audio_frame(event.data, event.metadata.get('sample_rate', 16000))
        
        # 处理系统停止事件
        elif event.type == EventType.SYSTEM_STOP:
            self.stop()
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def _should_process_audio(self) -> bool:
        """判断是否应该处理音频帧（只在非IDLE状态处理）"""
        if not self._controller:
            return False
        
        current_state = self._controller.get_current_state()
        if not current_state:
            return False
        
        # 在这些状态下处理音频帧：唤醒后、监听中、语音检测中
        from src.state_machine import VoiceState
        return current_state in [
            VoiceState.WAKEWORD_DETECTED,
            VoiceState.LISTENING,
            VoiceState.SPEECH_DETECTED,
            VoiceState.RECOGNIZING
        ]
    
    # ==================== IVADModule 专用接口 ====================
    
    def process_frame(self, audio_data: Any) -> Optional[dict]:
        """
        处理音频帧
        
        Args:
            audio_data: 音频数据（int16格式）
            
        Returns:
            VAD结果
        """
        if not self._engine:
            return None
        
        try:
            # 确保是 int16 格式
            if isinstance(audio_data, np.ndarray):
                if audio_data.dtype != np.int16:
                    audio_data = (audio_data * 32768).astype(np.int16)
            else:
                audio_data = np.array(audio_data, dtype=np.int16)
            
            # 处理帧
            result = self._engine.process_frame(audio_data)
            
            return {
                'is_speech': result.is_speech,
                'event': result.event.value if result.event else 'none',
                'audio_data': result.audio_data,
                'duration_ms': result.duration_ms,
                'state': result.state.value
            }
            
        except Exception as e:
            print(f"⚠️ [{self.name}] 处理异常: {e}")
            return None
    
    def reset(self):
        """重置VAD状态"""
        if self._engine:
            self._engine.reset()
            self._frame_buffer.clear()
            print(f"🔄 [{self.name}] 状态已重置")
    
    def enable(self):
        """启用检测"""
        self._enabled = True
        print(f"✅ [{self.name}] 检测已启用")
    
    def disable(self):
        """禁用检测"""
        self._enabled = False
        print(f"⏸️  [{self.name}] 检测已禁用")
    
    # ==================== 内部方法 ====================
    
    def _process_audio_frame(self, audio_data: Any, sample_rate: int):
        """
        处理音频帧（处理帧大小对齐）
        
        Args:
            audio_data: 音频数据
            sample_rate: 采样率
        """
        # 确保是 int16 格式
        if isinstance(audio_data, np.ndarray):
            if audio_data.dtype != np.int16:
                audio_int16 = (audio_data * 32768).astype(np.int16)
            else:
                audio_int16 = audio_data
        else:
            audio_int16 = np.array(audio_data, dtype=np.int16)
        
        # 添加到缓冲区
        self._frame_buffer.extend(audio_int16)
        
        # 当累积了足够的样本时，进行VAD处理
        while len(self._frame_buffer) >= self._frame_size:
            # 提取一个VAD帧
            vad_frame = np.array(self._frame_buffer[:self._frame_size], dtype=np.int16)
            self._frame_buffer = self._frame_buffer[self._frame_size:]
            
            # 处理VAD帧
            result = self.process_frame(vad_frame)
            self._frames_processed += 1
            
            if result:
                # 处理VAD事件
                self._handle_vad_result(result)
    
    def _handle_vad_result(self, result: dict):
        """
        处理VAD结果
        
        Args:
            result: VAD结果字典
        """
        event_type = result.get('event', 'none')
        
        # 语音开始
        if event_type == 'speech_start':
            print(f"\n{'='*60}")
            print(f"🎤 [{self.name}] 语音开始")
            if self._current_msg_id:
                print(f"   消息ID: {self._current_msg_id}")
            
            # 记录追踪
            if self._current_msg_id:
                tracker = get_message_tracker()
                tracker.add_trace(
                    msg_id=self._current_msg_id,
                    module_name=self.name,
                    event_type="speech_start",
                    input_data={'event': 'audio_frame'}
                )
            
            # 发布事件
            event = VADEventType(
                EventType.VAD_SPEECH_START,
                source=self.name,
                msg_id=self._current_msg_id
            )
            self._controller.publish_event(event)
            
            # 通知状态机
            from src.state_machine import StateEvent
            self._controller.handle_state_event(StateEvent.SPEECH_START)
        
        # 语音结束
        elif event_type == 'speech_end':
            duration_ms = result.get('duration_ms', 0)
            audio_data = result.get('audio_data')
            
            self._speech_segments += 1
            print(f"\n{'='*60}")
            print(f"🔇 VAD: 语音结束 [第{self._speech_segments}段] (时长: {duration_ms:.0f}ms, 数据: {len(audio_data) if audio_data else 0} bytes)")
            if self._current_msg_id:
                print(f"   消息ID: {self._current_msg_id}")
            print(f"{'='*60}")
            
            # 记录追踪
            if self._current_msg_id:
                tracker = get_message_tracker()
                tracker.add_trace(
                    msg_id=self._current_msg_id,
                    module_name=self.name,
                    event_type="speech_end",
                    output_data={
                        'duration_ms': duration_ms,
                        'audio_length': len(audio_data) if audio_data else 0
                    }
                )
            
            # 发布事件
            event = VADEventType(
                EventType.VAD_SPEECH_END,
                source=self.name,
                audio_data=audio_data,
                duration_ms=duration_ms,
                msg_id=self._current_msg_id
            )
            self._controller.publish_event(event)
            
            # 通知状态机
            from src.state_machine import StateEvent
            self._controller.handle_state_event(StateEvent.SPEECH_END, {'audio_data': audio_data})
    
    # ==================== 统计信息 ====================
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            'frames_processed': self._frames_processed,
            'speech_segments': self._speech_segments,
            'enabled': self._enabled,
            'is_running': self._running,
            'frame_buffer_size': len(self._frame_buffer),
            'has_engine': self._engine is not None
        }
