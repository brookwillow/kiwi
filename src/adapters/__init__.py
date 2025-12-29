"""
模块适配器包

提供所有模块的适配器实现，将现有模块接入新的事件驱动架构
"""
from .audio_adapter import AudioModuleAdapter
from .wakeword_adapter import WakewordModuleAdapter
from .vad_adapter import VADModuleAdapter
from .asr_adapter import ASRModuleAdapter
from .gui_adapter import GUIModuleAdapter

__all__ = [
    'AudioModuleAdapter',
    'WakewordModuleAdapter',
    'VADModuleAdapter',
    'ASRModuleAdapter',
    'GUIModuleAdapter',
]
