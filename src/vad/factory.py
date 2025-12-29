"""
VAD工厂类
"""
from .base import BaseVAD
from .webrtc_vad import WebRTCVAD
from .types import VADConfig
from .exceptions import VADInitError


class VADFactory:
    """VAD工厂"""
    
    _engines = {
        "webrtc": WebRTCVAD,
    }
    
    @classmethod
    def create(cls, engine_type: str = "webrtc", config: VADConfig = None) -> BaseVAD:
        """
        创建VAD实例
        
        Args:
            engine_type: VAD引擎类型
            config: VAD配置
        
        Returns:
            VAD实例
        """
        if engine_type not in cls._engines:
            raise VADInitError(f"Unknown VAD engine: {engine_type}")
        
        if config is None:
            config = VADConfig()
        
        engine_class = cls._engines[engine_type]
        return engine_class(config)
    
    @classmethod
    def register_engine(cls, name: str, engine_class: type):
        """
        注册新的VAD引擎
        
        Args:
            name: 引擎名称
            engine_class: 引擎类
        """
        cls._engines[name] = engine_class
    
    @classmethod
    def list_engines(cls) -> list[str]:
        """
        列出所有可用的VAD引擎
        
        Returns:
            引擎名称列表
        """
        return list(cls._engines.keys())
