"""
模块接口定义

定义所有模块必须实现的统一接口
"""
from abc import ABC, abstractmethod
from typing import Optional, Callable, Any
from .events import Event


class IModule(ABC):
    """模块基础接口"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """模块名称"""
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化模块
        
        Returns:
            是否初始化成功
        """
        pass
    
    @abstractmethod
    def start(self) -> bool:
        """
        启动模块
        
        Returns:
            是否启动成功
        """
        pass
    
    @abstractmethod
    def stop(self):
        """停止模块"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """清理资源"""
        pass
    
    @abstractmethod
    def handle_event(self, event: Event):
        """
        处理事件
        
        Args:
            event: 接收到的事件
        """
        pass
    
    @property
    @abstractmethod
    def is_running(self) -> bool:
        """模块是否正在运行"""
        pass


class IAudioModule(IModule):
    """音频模块接口"""
    
    @abstractmethod
    def set_audio_callback(self, callback: Callable[[Any], None]):
        """
        设置音频帧回调
        
        Args:
            callback: 音频帧回调函数
        """
        pass
    
    @abstractmethod
    def get_available_devices(self) -> list:
        """获取可用设备列表"""
        pass
    
    @abstractmethod
    def set_device(self, device_id: int):
        """设置音频设备"""
        pass


class IWakewordModule(IModule):
    """唤醒词模块接口"""
    
    @abstractmethod
    def detect(self, audio_data: Any) -> Optional[dict]:
        """
        检测唤醒词
        
        Args:
            audio_data: 音频数据
            
        Returns:
            检测结果 {'detected': bool, 'keyword': str, 'confidence': float}
        """
        pass
    
    @abstractmethod
    def reset(self):
        """重置唤醒词检测状态"""
        pass


class IVADModule(IModule):
    """VAD模块接口"""
    
    @abstractmethod
    def process_frame(self, audio_data: Any) -> Optional[dict]:
        """
        处理音频帧
        
        Args:
            audio_data: 音频数据
            
        Returns:
            VAD结果 {'is_speech': bool, 'event': str, 'audio_data': bytes, 'duration_ms': float}
        """
        pass
    
    @abstractmethod
    def reset(self):
        """重置VAD状态"""
        pass


class IASRModule(IModule):
    """ASR模块接口"""
    
    @abstractmethod
    def recognize(self, audio_data: Any, sample_rate: int) -> Optional[dict]:
        """
        识别语音
        
        Args:
            audio_data: 音频数据
            sample_rate: 采样率
            
        Returns:
            识别结果 {'text': str, 'confidence': float, 'success': bool}
        """
        pass
    
    @abstractmethod
    def is_busy(self) -> bool:
        """是否正在识别"""
        pass


class IStateModule(IModule):
    """状态机模块接口"""
    
    @abstractmethod
    def get_current_state(self) -> str:
        """获取当前状态"""
        pass
    
    @abstractmethod
    def transition_to(self, new_state: str, reason: str = "") -> bool:
        """
        转换到新状态
        
        Args:
            new_state: 新状态
            reason: 转换原因
            
        Returns:
            是否转换成功
        """
        pass
    
    @abstractmethod
    def can_transition(self, from_state: str, to_state: str) -> bool:
        """检查是否可以转换"""
        pass


class IGUIModule(IModule):
    """GUI模块接口"""
    
    @abstractmethod
    def update_status(self, status: str):
        """更新状态显示"""
        pass
    
    @abstractmethod
    def update_waveform(self, data: Any):
        """更新波形显示"""
        pass
    
    @abstractmethod
    def update_text(self, text: str, text_type: str = "result"):
        """
        更新文本显示
        
        Args:
            text: 文本内容
            text_type: 文本类型 (result/partial/error)
        """
        pass
    
    @abstractmethod
    def show_error(self, message: str):
        """显示错误信息"""
        pass
