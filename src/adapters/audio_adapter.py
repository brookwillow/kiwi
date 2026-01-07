"""
音频模块适配器

将现有的 AudioRecorder 包装成符合新架构的模块
"""
from typing import Optional, Callable, Any, List
import numpy as np

from src.core.interfaces import IAudioModule
from src.core.events import Event, EventType, AudioFrameEvent
from src.audio import AudioRecorder, AudioConfig, AudioFrame


class AudioModuleAdapter(IAudioModule):
    """
    音频模块适配器
    
    职责：
    1. 包装 AudioRecorder
    2. 将音频帧转换为事件发布到控制器
    3. 响应系统事件（如设备切换）
    """
    
    def __init__(self, controller, config: Optional[AudioConfig] = None):
        """
        初始化音频模块适配器
        
        Args:
            controller: SystemController 实例
            config: 音频配置
        """
        self._controller = controller
        self._config = config or AudioConfig()
        self._recorder: Optional[AudioRecorder] = None
        self._running = False
        self._frame_callback: Optional[Callable] = None
        
        # 统计
        self._frames_processed = 0
    
    @property
    def name(self) -> str:
        return "audio"
    
    def initialize(self) -> bool:
        """初始化音频模块"""
        try:
            # 创建 AudioRecorder
            self._recorder = AudioRecorder(self._config)
            
            # 使用异步读取方式设置回调
            self._recorder.read_async(self._on_audio_frame)
            
            print(f"✅ [{self.name}] 初始化成功")
            print(f"   采样率: {self._config.sample_rate}")
            print(f"   块大小: {self._config.chunk_size}")
            return True
            
        except Exception as e:
            print(f"❌ [{self.name}] 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start(self) -> bool:
        """启动音频采集"""
        if not self._recorder:
            print(f"❌ [{self.name}] 未初始化")
            return False
        
        try:
            if self._recorder.start():
                self._running = True
                print(f"✅ [{self.name}] 启动成功")
                print(f"🎙️  开始录音...")
                return True
            else:
                print(f"❌ [{self.name}] 启动失败")
                return False
                
        except Exception as e:
            print(f"❌ [{self.name}] 启动异常: {e}")
            return False
    
    def stop(self):
        """停止音频采集"""
        if self._recorder:
            self._recorder.stop()
            self._running = False
            print(f"🛑 录音已停止")
            print(f"✅ [{self.name}] 已停止")
    
    def cleanup(self):
        """清理资源"""
        if self._recorder:
            self._recorder.stop()
            self._recorder = None
            print(f"✅ [{self.name}] 资源已清理")
    
    def handle_event(self, event: Event):
        """
        处理来自控制器的事件
        
        Args:
            event: 事件对象
        """
        # 音频模块通常不需要处理其他模块的事件
        # 但可以响应系统控制事件
        if event.type == EventType.SYSTEM_STOP:
            self.stop()
        elif event.type == EventType.AUDIO_DEVICE_CHANGED:
            # 处理设备切换
            device_id = event.payload.get('device_id') if event.payload else None
            if device_id is not None:
                self.set_device(device_id)
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    # ==================== IAudioModule 专用接口 ====================
    
    def set_audio_callback(self, callback: Callable[[Any], None]):
        """设置音频帧回调（除了发送到控制器外的额外回调）"""
        self._frame_callback = callback
    
    def get_available_devices(self) -> list:
        """获取可用设备列表"""
        if self._recorder:
            return self._recorder.list_devices()
        return []
    
    def set_device(self, device_id: int):
        """设置音频设备"""
        if self._recorder:
            # 需要重启录音器
            was_running = self._running
            if was_running:
                self.stop()
            
            # 更新配置
            self._config.device_index = device_id
            
            # 重新创建录音器
            self.initialize()
            
            if was_running:
                self.start()
            
            print(f"✅ [{self.name}] 已切换到设备 {device_id}")
    
    # ==================== 内部方法 ====================
    
    def _on_audio_frame(self, frame: AudioFrame):
        """
        音频帧回调（由 AudioRecorder 调用）
        
        Args:
            frame: 音频帧
        """
        from src.core.events import AudioFrameEvent, AudioFramePayload
        
        self._frames_processed += 1
        
        # 直接发布音频帧事件（符合事件驱动架构）
        if self._controller:
            event = AudioFrameEvent(
                source=self.name,
                payload=AudioFramePayload(
                    frame_data=frame.data,
                    sample_rate=self._config.sample_rate,
                    channels=1
                )
            )
            self._controller.publish_event(event)
            
            # 定期检查超时
            if self._frames_processed % 10 == 0:  # 每10帧检查一次
                self._controller.check_timeout()
        
        # 如果有额外的回调，也调用它
        if self._frame_callback:
            try:
                self._frame_callback(frame)
            except Exception as e:
                print(f"⚠️ [{self.name}] 回调异常: {e}")
    
    # ==================== 统计信息 ====================
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        stats = {
            'frames_processed': self._frames_processed,
            'is_running': self._running,
            'sample_rate': self._config.sample_rate,
            'chunk_size': self._config.chunk_size,
        }
        
        if self._recorder:
            recorder_status = self._recorder.get_status()
            stats.update({
                'frames_captured': recorder_status.frames_captured,
                'dropped_frames': recorder_status.dropped_frames,
                'buffer_usage': recorder_status.buffer_usage,
                'average_level': recorder_status.average_level,
            })
        
        return stats
