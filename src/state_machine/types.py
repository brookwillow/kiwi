"""
状态机类型定义

定义语音处理流程中的状态、事件和结果类型
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any
import time


class VoiceState(Enum):
    """语音处理总体状态"""
    IDLE = "idle"                       # 空闲（等待唤醒词）
    WAKEWORD_DETECTED = "wakeword"      # 检测到唤醒词
    LISTENING = "listening"             # 监听中（等待语音输入）
    SPEECH_DETECTED = "speech"          # 检测到语音
    RECOGNIZING = "recognizing"         # 识别中
    PROCESSING = "processing"           # 处理中
    TIMEOUT = "timeout"                 # 超时


class StateEvent(Enum):
    """状态转换事件"""
    # 唤醒相关
    WAKEWORD_TRIGGERED = "wakeword_triggered"       # 检测到唤醒词
    WAKEWORD_RESET = "wakeword_reset"              # 重置唤醒状态
    
    # VAD相关
    SPEECH_START = "speech_start"                   # 语音开始
    SPEECH_END = "speech_end"                       # 语音结束
    SILENCE_DETECTED = "silence_detected"           # 检测到静音
    
    # ASR相关
    RECOGNITION_START = "recognition_start"         # 开始识别
    RECOGNITION_SUCCESS = "recognition_success"     # 识别成功
    RECOGNITION_FAILED = "recognition_failed"       # 识别失败
    
    # 超时相关
    WAKEWORD_TIMEOUT = "wakeword_timeout"          # 唤醒超时
    SPEECH_TIMEOUT = "speech_timeout"              # 语音超时
    
    # 系统控制
    RESET = "reset"                                # 重置所有状态
    FORCE_IDLE = "force_idle"                      # 强制回到空闲


@dataclass
class StateTransition:
    """状态转换记录"""
    from_state: VoiceState              # 源状态
    to_state: VoiceState                # 目标状态
    event: StateEvent                   # 触发事件
    timestamp: float                    # 转换时间戳
    metadata: Optional[dict] = None     # 附加数据


@dataclass
class VoiceStateInfo:
    """语音状态信息"""
    current_state: VoiceState           # 当前状态
    is_wakeword_enabled: bool           # 是否启用唤醒词
    is_wakeword_detected: bool          # 是否已检测到唤醒词
    wakeword_timeout_at: float          # 唤醒超时时间戳（0表示未设置）
    vad_end_count: int                  # VAD结束计数
    last_transition: Optional[StateTransition] = None  # 最后一次状态转换
    state_duration: float = 0.0         # 当前状态持续时间
    
    def is_timeout_active(self) -> bool:
        """检查超时是否已激活"""
        return self.wakeword_timeout_at > 0
    
    def is_timeout_expired(self) -> bool:
        """检查是否已超时"""
        if not self.is_timeout_active():
            return False
        return time.time() >= self.wakeword_timeout_at
    
    def get_remaining_time(self) -> float:
        """获取剩余时间（秒）"""
        if not self.is_timeout_active():
            return 0.0
        remaining = self.wakeword_timeout_at - time.time()
        return max(0.0, remaining)


@dataclass
class StateConfig:
    """状态机配置"""
    # 唤醒相关
    enable_wakeword: bool = True        # 是否启用唤醒词检测
    wakeword_timeout: float = 10.0      # 唤醒超时时长（秒）
    max_vad_end_count: int = 1          # 最大VAD结束次数（1次即返回IDLE，允许连续唤醒）
    
    # VAD相关
    enable_vad: bool = True             # 是否启用VAD
    
    # ASR相关
    enable_asr: bool = True             # 是否启用ASR
    
    # 调试
    debug: bool = False                 # 是否打印调试信息


@dataclass
class StateChangeResult:
    """状态变化结果"""
    success: bool                       # 是否成功
    previous_state: VoiceState          # 之前的状态
    current_state: VoiceState           # 当前状态
    event: StateEvent                   # 触发事件
    message: str = ""                   # 结果消息
    should_reset_wakeword: bool = False # 是否应该重置唤醒词
    should_start_timeout: bool = False  # 是否应该启动超时计时
    should_trigger_asr: bool = False    # 是否应该触发ASR识别
