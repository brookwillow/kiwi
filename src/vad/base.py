"""
VAD基类定义
"""
from abc import ABC, abstractmethod
import numpy as np
from typing import Optional
from .types import VADResult, VADConfig


class BaseVAD(ABC):
    """VAD基类"""
    
    def __init__(self, config: VADConfig):
        """
        初始化VAD
        
        Args:
            config: VAD配置
        """
        self.config = config
    
    @abstractmethod
    def process_frame(self, audio_frame: np.ndarray) -> VADResult:
        """
        处理单帧音频
        
        Args:
            audio_frame: 音频帧数据 (int16)
        
        Returns:
            VAD检测结果
        """
        pass
    
    @abstractmethod
    def reset(self):
        """重置VAD状态"""
        pass
    
    def process_audio(self, audio_data: np.ndarray) -> list[VADResult]:
        """
        处理音频数据（可能包含多帧）
        
        Args:
            audio_data: 音频数据 (int16)
        
        Returns:
            VAD检测结果列表
        """
        results = []
        frame_size = self.config.frame_size
        
        # 按帧处理
        for i in range(0, len(audio_data), frame_size):
            frame = audio_data[i:i + frame_size]
            
            # 如果帧长度不足，补零
            if len(frame) < frame_size:
                frame = np.pad(frame, (0, frame_size - len(frame)), mode='constant')
            
            result = self.process_frame(frame)
            results.append(result)
        
        return results
