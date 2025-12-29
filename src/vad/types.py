"""
VAD模块的数据类型定义
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class VADState(Enum):
    """VAD状态"""
    IDLE = "idle"           # 空闲，未检测到语音
    SPEAKING = "speaking"   # 正在说话
    SILENCE = "silence"     # 静音（说话后的静音）


class VADEvent(Enum):
    """VAD事件类型"""
    SPEECH_START = "speech_start"  # 语音开始
    SPEECH_END = "speech_end"      # 语音结束
    SPEAKING = "speaking"          # 持续说话中


@dataclass
class VADConfig:
    """VAD配置"""
    # 采样率（必须是8000, 16000, 32000, 48000之一）
    sample_rate: int = 16000
    
    # 帧长度（ms）- 必须是10, 20, 30之一
    frame_duration_ms: int = 30
    
    # VAD模式（0-3，越大越激进）
    # 0: 质量模式（最不容易误判）
    # 1: 低比特率模式
    # 2: 激进模式
    # 3: 非常激进模式（最容易检测到语音）
    aggressiveness: int = 2
    
    # 静音超时时间（ms）- 连续静音多久后认为语音结束
    silence_timeout_ms: int = 800
    
    # 语音前缓冲（ms）- 保留语音开始前多少ms的音频
    pre_speech_buffer_ms: int = 300
    
    # 最小语音长度（ms）- 少于此长度的语音会被忽略
    min_speech_duration_ms: int = 300
    
    # 唤醒后延迟（ms）- 唤醒词检测后多久开始VAD检测
    wakeword_delay_ms: int = 500
    
    # VAD结束判定静音时长（ms）- VAD=0后需要持续多久才算真正结束
    vad_end_silence_ms: int = 1000
    
    def __post_init__(self):
        """验证配置参数"""
        if self.sample_rate not in [8000, 16000, 32000, 48000]:
            raise ValueError(f"sample_rate must be 8000, 16000, 32000, or 48000, got {self.sample_rate}")
        
        if self.frame_duration_ms not in [10, 20, 30]:
            raise ValueError(f"frame_duration_ms must be 10, 20, or 30, got {self.frame_duration_ms}")
        
        if not 0 <= self.aggressiveness <= 3:
            raise ValueError(f"aggressiveness must be 0-3, got {self.aggressiveness}")
    
    @property
    def frame_size(self) -> int:
        """每帧的采样点数"""
        return int(self.sample_rate * self.frame_duration_ms / 1000)
    
    @property
    def silence_frames(self) -> int:
        """静音超时对应的帧数"""
        return int(self.silence_timeout_ms / self.frame_duration_ms)
    
    @property
    def pre_speech_frames(self) -> int:
        """语音前缓冲对应的帧数"""
        return int(self.pre_speech_buffer_ms / self.frame_duration_ms)
    
    @property
    def min_speech_frames(self) -> int:
        """最小语音长度对应的帧数"""
        return int(self.min_speech_duration_ms / self.frame_duration_ms)
    
    @property
    def wakeword_delay_frames(self) -> int:
        """唤醒后延迟对应的帧数"""
        return int(self.wakeword_delay_ms / self.frame_duration_ms)
    
    @property
    def vad_end_silence_frames(self) -> int:
        """VAD结束判定静音时长对应的帧数"""
        return int(self.vad_end_silence_ms / self.frame_duration_ms)


@dataclass
class VADResult:
    """VAD检测结果"""
    is_speech: bool                    # 是否是语音
    confidence: float                  # 置信度（0-1）
    state: VADState                    # 当前状态
    event: Optional[VADEvent] = None   # 事件类型
    audio_data: Optional[bytes] = None # 音频数据（仅在事件发生时）
    duration_ms: float = 0             # 持续时间（ms）
