"""
ASR 模块工厂
"""
from .base import ASREngine
from .types import ASRConfig
from .whisper_engine import WhisperEngine
from .exceptions import ASRError


def create_asr_engine(config: ASRConfig) -> ASREngine:
    """
    创建 ASR 引擎
    
    Args:
        config: ASR 配置
        
    Returns:
        ASR 引擎实例
        
    Raises:
        ASRError: 不支持的模型类型
    """
    if config.model == "whisper":
        return WhisperEngine(config)
    else:
        raise ASRError(f"Unsupported ASR model: {config.model}")
