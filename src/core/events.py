"""
核心事件系统

定义系统中各模块间通信的事件类型
"""
from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum


class EventType(Enum):
    """系统事件类型"""
    
    # === 系统控制事件 ===
    SYSTEM_START = "system_start"           # 系统启动
    SYSTEM_STOP = "system_stop"             # 系统停止
    SYSTEM_ERROR = "system_error"           # 系统错误
    
    # === 音频事件 ===
    AUDIO_FRAME_READY = "audio_frame_ready"     # 音频帧就绪
    AUDIO_DEVICE_CHANGED = "audio_device_changed"  # 设备变更
    AUDIO_ERROR = "audio_error"                 # 音频错误
    
    # === 唤醒词事件 ===
    WAKEWORD_DETECTED = "wakeword_detected"     # 检测到唤醒词
    WAKEWORD_TIMEOUT = "wakeword_timeout"       # 唤醒超时
    WAKEWORD_RESET = "wakeword_reset"          # 重置唤醒状态
    
    # === VAD事件 ===
    VAD_SPEECH_START = "vad_speech_start"       # 语音开始
    VAD_SPEECH_END = "vad_speech_end"          # 语音结束
    VAD_SPEAKING = "vad_speaking"              # 正在说话
    VAD_SILENCE = "vad_silence"                # 静音
    
    # === ASR事件 ===
    ASR_RECOGNITION_START = "asr_recognition_start"    # 开始识别
    ASR_RECOGNITION_SUCCESS = "asr_recognition_success"  # 识别成功
    ASR_RECOGNITION_FAILED = "asr_recognition_failed"   # 识别失败
    ASR_PARTIAL_RESULT = "asr_partial_result"         # 部分识别结果
    
    # === 状态机事件 ===
    STATE_CHANGED = "state_changed"             # 状态变化
    
    # === GUI事件 ===
    GUI_UPDATE_STATUS = "gui_update_status"     # 更新状态显示
    GUI_UPDATE_WAVEFORM = "gui_update_waveform"  # 更新波形
    GUI_UPDATE_TEXT = "gui_update_text"         # 更新文本
    GUI_COMMAND = "gui_command"                 # GUI命令
    
    # === TTS事件 ===
    TTS_SPEAK_REQUEST = "tts_speak_request"     # TTS播报请求
    TTS_SPEAK_START = "tts_speak_start"         # TTS开始播报
    TTS_SPEAK_END = "tts_speak_end"             # TTS播报完成
    TTS_SPEAK_ERROR = "tts_speak_error"         # TTS播报错误


@dataclass
class Event:
    """事件基类"""
    type: EventType                 # 事件类型
    source: str                     # 事件源（模块名）
    timestamp: float                # 时间戳
    data: Optional[Any] = None      # 事件数据
    metadata: Optional[dict] = None  # 元数据
    
    @classmethod
    def create(cls, event_type: EventType, source: str, data: Any = None, **metadata):
        """创建事件"""
        return cls(
            type=event_type,
            source=source,
            timestamp=time.time(),
            data=data,
            metadata=metadata or {}
        )
    
    def __repr__(self):
        return f"Event(type={self.type.value}, source={self.source}, timestamp={self.timestamp:.3f})"


@dataclass
class AudioFrameEvent(Event):
    """音频帧事件"""
    def __init__(self, source: str, frame_data: Any, sample_rate: int):
        super().__init__(
            type=EventType.AUDIO_FRAME_READY,
            source=source,
            timestamp=time.time(),
            data=frame_data,
            metadata={'sample_rate': sample_rate}
        )


@dataclass
class WakewordEvent(Event):
    """唤醒词事件"""
    def __init__(self, source: str, keyword: str, confidence: float):
        super().__init__(
            type=EventType.WAKEWORD_DETECTED,
            source=source,
            timestamp=time.time(),
            data={'keyword': keyword, 'confidence': confidence}
        )


@dataclass
class VADEvent(Event):
    """VAD事件"""
    def __init__(self, event_type: EventType, source: str, audio_data: Any = None, duration_ms: float = 0):
        super().__init__(
            type=event_type,
            source=source,
            timestamp=time.time(),
            data=audio_data,
            metadata={'duration_ms': duration_ms}
        )


@dataclass
class ASREvent(Event):
    """ASR事件"""
    def __init__(self, event_type: EventType, source: str, text: str = "", confidence: float = 0.0, latency_ms: float = 0.0):
        data = {'text': text, 'confidence': confidence}
        if latency_ms > 0:
            data['latency_ms'] = latency_ms
        
        super().__init__(
            type=event_type,
            source=source,
            timestamp=time.time(),
            data=data
        )


@dataclass
class StateChangeEvent(Event):
    """状态变化事件"""
    def __init__(self, source: str, from_state: str, to_state: str, reason: str = ""):
        super().__init__(
            type=EventType.STATE_CHANGED,
            source=source,
            timestamp=time.time(),
            data={'from_state': from_state, 'to_state': to_state, 'reason': reason}
        )



@dataclass
class ShortTermMemory:
    """短期记忆（对话历史）"""
    query: str                          # 用户查询
    response: str                       # 系统响应
    timestamp: float                    # 时间戳
    agent: str = ""                     # 处理该记忆的Agent名称
    tools_used: List[str] = field(default_factory=list)  # 使用的工具列表
    description: str = ""               # 文本化描述
    success: bool = True                # 记忆是否成功
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LongTermMemory:
    """长期记忆（用户画像和总结）"""
    summary: str                       # 对话摘要
    user_profile: Dict[str, Any]       # 用户画像
    preferences: Dict[str, Any]        # 用户偏好
    metadata: Dict[str, Any] = field(default_factory=dict)


class QueryType(Enum):
    """查询类型"""
    USER_QUERY = "user_query"          # 用户语音查询
    SYSTEM_EVENT = "system_event"      # 系统事件

@dataclass
class SystemState:
    """系统状态"""
    state_type: str                    # 状态类型（vehicle/music/navigation等）
    state_data: Dict[str, Any]         # 状态数据
    timestamp: float                   # 时间戳


@dataclass
class AgentInfo:
    """Agent信息"""
    name: str                          # Agent名称
    description: str                   # Agent描述
    capabilities: List[str]            # Agent能力列表
    enabled: bool = True               # 是否启用
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorInput:
    """Orchestrator输入"""
    query_type: QueryType              # 查询类型
    query_content: str                 # 查询内容
    timestamp: float                   # 时间戳
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestratorContext:
    """Orchestrator上下文"""
    input_query: OrchestratorInput     # 输入查询
    short_term_memories: List[ShortTermMemory]  # 短期记忆
    long_term_memory: Optional[LongTermMemory]  # 长期记忆
    system_states: List[SystemState]   # 系统状态
    available_agents: List[AgentInfo]  # 可用的Agents
    
    
@dataclass
class OrchestratorDecision:
    """Orchestrator决策结果"""
    selected_agent: str                # 选中的Agent名称
    confidence: float                  # 置信度
    reasoning: str                     # 决策理由
    parameters: Dict[str, Any] = field(default_factory=dict)  # 传递给Agent的参数
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentContext:
    """Agent上下文"""
    short_term_memories: List[ShortTermMemory]  # 短期记忆
    long_term_memory: Optional[LongTermMemory]  # 长期记忆
    system_states: List[SystemState]   # 系统状态