"""
ASR 引擎基类
"""
from abc import ABC, abstractmethod
from typing import List, Iterator
import numpy as np

from .types import ASRConfig, ASRResult


class ASREngine(ABC):
    """ASR 引擎抽象基类"""
    
    def __init__(self, config: ASRConfig):
        """
        初始化 ASR 引擎
        
        Args:
            config: ASR 配置
        """
        config.validate()
        self.config = config
    
    @abstractmethod
    def recognize(self, audio: np.ndarray, sample_rate: int = 16000) -> ASRResult:
        """
        识别音频
        
        Args:
            audio: 音频数据
            sample_rate: 采样率
            
        Returns:
            识别结果
        """
        pass
    
    def recognize_batch(self, audio_list: List[np.ndarray], sample_rate: int = 16000) -> List[ASRResult]:
        """
        批量识别
        
        Args:
            audio_list: 音频列表
            sample_rate: 采样率
            
        Returns:
            识别结果列表
        """
        results = []
        for audio in audio_list:
            result = self.recognize(audio, sample_rate)
            results.append(result)
        return results
    
    def recognize_stream(self, audio_stream: Iterator[np.ndarray], sample_rate: int = 16000) -> Iterator[ASRResult]:
        """
        流式识别
        
        Args:
            audio_stream: 音频流
            sample_rate: 采样率
            
        Yields:
            识别结果
        """
        for audio in audio_stream:
            result = self.recognize(audio, sample_rate)
            yield result
