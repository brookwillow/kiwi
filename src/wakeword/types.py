"""
唤醒词模块的数据类型定义
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class WakeWordState(Enum):
    """唤醒词状态"""
    IDLE = "idle"           # 未唤醒
    TRIGGERED = "triggered"  # 已唤醒


@dataclass
class WakeWordConfig:
    """唤醒词配置"""
    # 采样率
    sample_rate: int = 16000
    
    # 唤醒词模型列表（可以同时检测多个唤醒词）
    models: list[str] = None
    
    # 检测阈值（0-1，越高越严格）
    threshold: float = 0.5
    
    # 唤醒后的静默时间（秒）- 避免重复触发
    cooldown_seconds: float = 3.0
    
    def __post_init__(self):
        """初始化默认值"""
        if self.models is None:
            # 默认为空，让OpenWakeWord自动下载和使用默认模型
            self.models = []


@dataclass
class WakeWordResult:
    """唤醒词检测结果"""
    is_detected: bool                   # 是否检测到唤醒词
    keyword: Optional[str] = None       # 检测到的唤醒词名称
    confidence: float = 0.0             # 置信度（0-1）
    state: WakeWordState = WakeWordState.IDLE  # 当前状态
