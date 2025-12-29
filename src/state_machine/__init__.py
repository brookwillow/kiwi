"""
状态机模块 - 语音处理状态管理

统一管理唤醒、VAD、ASR的状态转换逻辑，与具体实现解耦
"""

from .types import (
    VoiceState,
    StateEvent,
    StateTransition,
    VoiceStateInfo,
    StateConfig,
    StateChangeResult
)
from .manager import VoiceStateManager

__all__ = [
    # 核心管理器
    'VoiceStateManager',
    
    # 类型定义
    'VoiceState',
    'StateEvent',
    'StateTransition',
    'VoiceStateInfo',
    'StateConfig',
    'StateChangeResult',
]

__version__ = '1.0.0'
