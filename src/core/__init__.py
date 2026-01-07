"""
核心控制模块

提供系统总控制器、事件系统和模块接口
"""

from .controller import SystemController
from .events import Event, EventType, ConversationEvent
from .events import (
    AudioFrameEvent, WakewordEvent, VADEvent, 
    ASREvent, StateChangeEvent
)
from .interfaces import (
    IModule, IAudioModule, IWakewordModule,
    IVADModule, IASRModule, IStateModule, IGUIModule
)

__all__ = [
    # 核心控制器
    'SystemController',
    
    # 事件系统
    'Event',
    'EventType',
    'ConversationEvent',
    'AudioFrameEvent',
    'WakewordEvent',
    'VADEvent',
    'ASREvent',
    'StateChangeEvent',
    
    # 模块接口
    'IModule',
    'IAudioModule',
    'IWakewordModule',
    'IVADModule',
    'IASRModule',
    'IStateModule',
    'IGUIModule',
]

__version__ = '1.0.0'
