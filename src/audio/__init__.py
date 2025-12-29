"""
录音模块

提供音频采集、设备管理和音频预处理功能
"""

from .types import AudioConfig, AudioFrame, RecorderStatus, AudioDevice
from .exceptions import (
    AudioError,
    AudioDeviceError,
    RecorderNotStartedError,
    ConfigError,
    BufferOverflowError
)
from .preprocessor import AudioPreprocessor
from .recorder import AudioRecorder

__all__ = [
    # 核心类
    'AudioRecorder',
    
    # 数据模型
    'AudioConfig',
    'AudioFrame',
    'RecorderStatus',
    'AudioDevice',
    
    # 异常
    'AudioError',
    'AudioDeviceError',
    'RecorderNotStartedError',
    'ConfigError',
    'BufferOverflowError',
    
    # 预处理
    'AudioPreprocessor',
]
