"""
ASR 模块 - 自动语音识别

提供音频转文本功能，支持多种ASR引擎
"""

from .types import ASRConfig, ASRResult, Segment
from .exceptions import ASRError, ModelNotFoundError, RecognitionError, AudioFormatError
from .base import ASREngine
from .whisper_engine import WhisperEngine
from .factory import create_asr_engine

__all__ = [
    # 工厂函数
    'create_asr_engine',
    
    # 引擎类
    'ASREngine',
    'WhisperEngine',
    
    # 数据类型
    'ASRConfig',
    'ASRResult',
    'Segment',
    
    # 异常
    'ASRError',
    'ModelNotFoundError',
    'RecognitionError',
    'AudioFormatError',
]
