"""
唤醒词工厂类
"""
from .base import BaseWakeWord
from .openwakeword_engine import OpenWakeWord
from .types import WakeWordConfig
from .exceptions import WakeWordInitError


class WakeWordFactory:
    """唤醒词工厂"""
    
    _engines = {
        "openwakeword": OpenWakeWord,
    }
    
    @classmethod
    def create(cls, engine_type: str = "openwakeword", config: WakeWordConfig = None) -> BaseWakeWord:
        """
        创建唤醒词检测器实例
        
        Args:
            engine_type: 引擎类型
            config: 唤醒词配置
        
        Returns:
            唤醒词检测器实例
        """
        if engine_type not in cls._engines:
            raise WakeWordInitError(f"Unknown wake word engine: {engine_type}")
        
        if config is None:
            config = WakeWordConfig()
        
        engine_class = cls._engines[engine_type]
        return engine_class(config)
    
    @classmethod
    def register_engine(cls, name: str, engine_class: type):
        """
        注册新的唤醒词引擎
        
        Args:
            name: 引擎名称
            engine_class: 引擎类
        """
        cls._engines[name] = engine_class
    
    @classmethod
    def list_engines(cls) -> list[str]:
        """
        列出所有可用的唤醒词引擎
        
        Returns:
            引擎名称列表
        """
        return list(cls._engines.keys())
