"""
音频预处理器基类
"""
from abc import ABC, abstractmethod
from .types import AudioFrame


class AudioPreprocessor(ABC):
    """音频预处理器抽象基类"""
    
    @abstractmethod
    def process(self, frame: AudioFrame) -> AudioFrame:
        """
        处理音频帧
        
        Args:
            frame: 原始音频帧
            
        Returns:
            处理后的音频帧
        """
        pass
    
    def __call__(self, frame: AudioFrame) -> AudioFrame:
        """支持直接调用"""
        return self.process(frame)
