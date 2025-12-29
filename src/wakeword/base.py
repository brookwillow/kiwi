"""
唤醒词基类定义
"""
from abc import ABC, abstractmethod
import numpy as np
from .types import WakeWordResult, WakeWordConfig


class BaseWakeWord(ABC):
    """唤醒词检测基类"""
    
    def __init__(self, config: WakeWordConfig):
        """
        初始化唤醒词检测器
        
        Args:
            config: 唤醒词配置
        """
        self.config = config
    
    @abstractmethod
    def detect(self, audio_data: np.ndarray) -> WakeWordResult:
        """
        检测音频中的唤醒词
        
        Args:
            audio_data: 音频数据 (float32, -1 to 1)
        
        Returns:
            唤醒词检测结果
        """
        pass
    
    @abstractmethod
    def reset(self):
        """重置检测器状态"""
        pass
