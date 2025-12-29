"""
唤醒词模块适配器

将现有的 WakeWordEngine 包装成符合新架构的模块
"""
from typing import Optional, Dict, Any
import numpy as np

from src.core.interfaces import IWakewordModule
from src.core.events import Event, EventType, WakewordEvent
from src.wakeword import WakeWordFactory, WakeWordConfig, WakeWordResult, WakeWordState


class WakewordModuleAdapter(IWakewordModule):
    """
    唤醒词模块适配器
    
    职责：
    1. 包装 WakeWordEngine
    2. 接收音频帧事件并进行检测
    3. 检测到唤醒词后发布事件
    4. 响应重置事件
    """
    
    def __init__(self, controller, config: Optional[WakeWordConfig] = None):
        """
        初始化唤醒词模块适配器
        
        Args:
            controller: SystemController 实例
            config: 唤醒词配置
        """
        self._controller = controller
        self._config = config
        self._engine = None
        self._running = False
        self._enabled = True  # 是否启用检测
        
        # 统计
        self._detections = 0
        self._frames_processed = 0
    
    @property
    def name(self) -> str:
        return "wakeword"
    
    def initialize(self) -> bool:
        """初始化唤醒词引擎"""
        if not self._config:
            print(f"⚠️ [{self.name}] 未提供配置，跳过初始化")
            return True
        
        try:
            # 创建唤醒词引擎
            self._engine = WakeWordFactory.create("openwakeword", self._config)
            
            print(f"✅ [{self.name}] 初始化成功")
            print(f"   模型: {self._config.models}")
            print(f"   阈值: {self._config.threshold}")
            return True
            
        except Exception as e:
            print(f"❌ [{self.name}] 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start(self) -> bool:
        """启动唤醒词检测"""
        if not self._engine:
            print(f"⚠️ [{self.name}] 引擎未初始化，跳过启动")
            return True  # 允许系统继续运行
        
        self._running = True
        self._enabled = True
        print(f"✅ [{self.name}] 已启动")
        return True
    
    def stop(self):
        """停止唤醒词检测"""
        self._running = False
        print(f"✅ [{self.name}] 已停止")
    
    def cleanup(self):
        """清理资源"""
        self._engine = None
        print(f"✅ [{self.name}] 资源已清理")
    
    def handle_event(self, event: Event):
        """
        处理来自控制器的事件
        
        Args:
            event: 事件对象
        """
        if not self._engine or not self._running:
            return
        
        # 处理音频帧事件 - 只在IDLE状态处理
        if event.type == EventType.AUDIO_FRAME_READY:
            if self._enabled and self._should_process_audio():
                self._process_audio_frame(event.data, event.metadata.get('sample_rate', 16000))
        
        # 处理重置事件
        elif event.type == EventType.WAKEWORD_RESET:
            self.reset()
        
        # 处理系统停止事件
        elif event.type == EventType.SYSTEM_STOP:
            self.stop()
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    # ==================== IWakewordModule 专用接口 ====================
    
    def detect(self, audio_data: Any) -> Optional[dict]:
        """
        检测唤醒词
        
        Args:
            audio_data: 音频数据
            
        Returns:
            检测结果
        """
        if not self._engine:
            return None
        
        try:
            # 确保是 numpy 数组
            if not isinstance(audio_data, np.ndarray):
                audio_data = np.array(audio_data, dtype=np.float32)
            
            # 进行检测
            result = self._engine.detect(audio_data)
            
            return {
                'detected': result.is_detected,
                'keyword': result.keyword if result.is_detected else '',
                'confidence': result.confidence,
                'state': result.state.value
            }
            
        except Exception as e:
            print(f"⚠️ [{self.name}] 检测异常: {e}")
            return None
    
    def _should_process_audio(self) -> bool:
        """
        判断是否应该处理音频帧
        
        注意：唤醒词检测应该一直工作，不受状态机限制。
        只要没有VAD或ASR模块在处理，就继续监听唤醒词。
        """
        if not self._controller:
            return True
        
        current_state = self._controller.get_current_state()
        if not current_state:
            return True
        
        # 在以下状态可以处理音频帧：
        # - IDLE: 空闲状态，等待唤醒词
        # - WAKEWORD_DETECTED: 唤醒词检测到，但没有VAD/ASR推进状态
        #   （这允许连续检测唤醒词，如果用户只启用了唤醒词模块）
        from src.state_machine import VoiceState
        return current_state in (VoiceState.IDLE, VoiceState.WAKEWORD_DETECTED)
    
    def reset(self):
        """重置唤醒词检测状态"""
        if self._engine:
            self._engine.reset()
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
        处理音频帧
        
        Args:
            audio_data: 音频数据
            sample_rate: 采样率
        """
        self._frames_processed += 1
        
        # 检测唤醒词
        result = self.detect(audio_data)
        
        if result and result['detected']:
            self._detections += 1
            
            print(f"\n{'='*60}")
            print(f"🎯 唤醒词检测: {result['keyword']} (置信度: {result['confidence']:.2f})")
            print(f"{'='*60}")
            
            # 发布唤醒词检测事件
            event = WakewordEvent(
                source=self.name,
                keyword=result['keyword'],
                confidence=result['confidence']
            )
            self._controller.publish_event(event)
            
            # 通知状态机
            from src.state_machine import StateEvent
            self._controller.handle_state_event(StateEvent.WAKEWORD_TRIGGERED)
    
    # ==================== 统计信息 ====================
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            'frames_processed': self._frames_processed,
            'detections': self._detections,
            'enabled': self._enabled,
            'is_running': self._running,
            'has_engine': self._engine is not None
        }
