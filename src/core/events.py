"""
核心事件系统

定义系统中各模块间通信的事件类型
使用强类型 Payload 确保模块间协议清晰
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, Dict, List
import time


# ============================================================================
# 基础枚举定义
# ============================================================================

class SessionAction(str, Enum):
    """会话操作类型"""
    NEW = "new"           # 新建会话
    RESUME = "resume"     # 恢复会话
    COMPLETE = "complete" # 完成会话


# ============================================================================
# Payload 类定义 - 定义各事件的数据结构
# ============================================================================

@dataclass
class AudioFramePayload:
    """音频帧载荷"""
    frame_data: bytes
    sample_rate: int
    channels: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'frame_data': self.frame_data,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'frame_size': len(self.frame_data)
        }


@dataclass
class WakewordPayload:
    """唤醒词载荷"""
    keyword: str
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'keyword': self.keyword,
            'confidence': self.confidence
        }


@dataclass
class VADPayload:
    """VAD事件载荷"""
    audio_data: Optional[bytes] = None
    duration_ms: float = 0.0
    is_speech: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'audio_data': self.audio_data,
            'duration_ms': self.duration_ms,
            'is_speech': self.is_speech,
            'has_audio': self.audio_data is not None
        }


@dataclass
class ASRPayload:
    """ASR识别载荷"""
    text: str
    confidence: float = 0.0
    is_partial: bool = False
    latency_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'text': self.text,
            'confidence': self.confidence,
            'is_partial': self.is_partial
        }
        if self.latency_ms is not None:
            result['latency_ms'] = self.latency_ms
        return result


@dataclass
class StateChangePayload:
    """状态变化载荷"""
    from_state: str
    to_state: str
    reason: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'from_state': self.from_state,
            'to_state': self.to_state,
            'reason': self.reason
        }


@dataclass
class AgentRequestPayload:
    """Agent请求载荷"""
    agent_name: str
    query: str
    context: Dict[str, Any] = field(default_factory=dict)
    decision: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'agent_name': self.agent_name,
            'query': self.query,
            'context': self.context,
            'decision': self.decision
        }


@dataclass
class SessionInfo:
    """会话信息"""
    session_id: str
    session_action: SessionAction = SessionAction.NEW
    priority: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'session_id': self.session_id,
            'session_action': self.session_action.value
        }
        if self.priority is not None:
            result['priority'] = self.priority
        return result


class AgentStatus(str, Enum):
    """Agent响应状态"""
    WAITING_INPUT = "waiting_input"  # 等待用户输入（会话Agent）
    COMPLETED = "completed"          # 会话完成（会话Agent）
    ERROR = "error"                  # 执行出错


@dataclass
class AgentResponsePayload:
    """
    Agent响应载荷
    
    包含Agent执行结果的业务数据：
    - agent: Agent名称
    - query: 原始查询
    - message: 响应消息（面向用户的文本，包括完成消息或等待输入提示）
    - status: 响应状态（WAITING_INPUT/COMPLETED/ERROR）
    - data: 额外的业务数据（可选）
    """
    agent: str                          # Agent名称
    query: str                          # 原始查询
    message: str                        # 响应消息
    status: AgentStatus                 # 状态
    data: Optional[Dict[str, Any]] = None  # 额外的业务数据
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'agent': self.agent,
            'query': self.query,
            'message': self.message,
            'status': self.status.value,
        }
        if self.data is not None:
            result['data'] = self.data
        return result
    
    @property
    def success(self) -> bool:
        """判断是否成功"""
        return self.status == AgentStatus.COMPLETED
    
    def is_waiting_input(self) -> bool:
        """判断是否等待用户输入"""
        return self.status == AgentStatus.WAITING_INPUT
    
    def is_completed(self) -> bool:
        """判断是否完成"""
        return self.status == AgentStatus.COMPLETED
    
    def is_error(self) -> bool:
        """判断是否有错误"""
        return self.status == AgentStatus.ERROR


# ============================================================================
# 事件类型枚举
# ============================================================================


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
    
    # === Agent事件 ===
    AGENT_DISPATCH_REQUEST = "agent_dispatch_request"  # Agent分发请求
    AGENT_RESPONSE = "agent_response"                  # Agent响应


@dataclass
class Event:
    """
    事件基类 - 只包含所有事件共有的字段
    
    字段说明：
    - type: 事件类型
    - source: 事件源（模块名）
    - timestamp: 事件时间戳
    - payload: 事件载荷（强类型 Payload 对象，包含该事件的所有业务数据）
    """
    type: EventType                 # 事件类型
    source: str                     # 事件源（模块名）
    timestamp: float                # 时间戳
    payload: Optional[Any] = None   # 事件载荷（强类型 Payload 对象）
    
    @classmethod
    def create(cls, event_type: EventType, source: str, payload: Any = None):
        """创建事件"""
        return cls(
            type=event_type,
            source=source,
            timestamp=time.time(),
            payload=payload
        )
    
    def __repr__(self):
        return f"Event(type={self.type.value}, source={self.source}, timestamp={self.timestamp:.3f})"


@dataclass
class ConversationEvent(Event):
    """
    对话事件基类 - 用于处理需要对话上下文的事件
    
    对话追踪字段说明：
    - msg_id: 消息追踪ID，用于跨模块链路追踪（生命周期：一次完整的请求处理流程）【必选】
    - session_id: 会话ID，用于多轮对话会话管理（生命周期：整个对话会话，可能跨多次请求）
    - session_action: 会话操作类型（NEW: 新建会话, RESUME: 恢复会话, COMPLETE: 完成会话）
    
    注意：msg_id 有默认值是为了满足 dataclass 继承规则，但在实际使用中必须提供有效值
    """
    msg_id: str = ""                             # 消息追踪ID（链路追踪）【必选】
    session_id: Optional[str] = None             # 会话ID（会话管理）
    session_action: Optional[SessionAction] = None  # 会话操作类型
    
    def get_session_info(self) -> Optional[SessionInfo]:
        """获取会话信息"""
        if self.session_id:
            return SessionInfo(
                session_id=self.session_id,
                session_action=self.session_action or SessionAction.NEW
            )
        return None


class AudioFrameEvent(Event):
    """音频帧事件"""
    
    def __init__(self, source: str, payload: AudioFramePayload):
        super().__init__(
            type=EventType.AUDIO_FRAME_READY,
            source=source,
            timestamp=time.time(),
            payload=payload
        )


class WakewordEvent(ConversationEvent):
    """唤醒词事件 - 对话开始事件"""
    
    def __init__(self, source: str, payload: WakewordPayload, msg_id: str):
        super().__init__(
            type=EventType.WAKEWORD_DETECTED,
            source=source,
            timestamp=time.time(),
            payload=payload,
            msg_id=msg_id
        )


class VADEvent(ConversationEvent):
    """VAD事件 - 对话中的语音检测事件"""
    
    def __init__(self, event_type: EventType, source: str, payload: VADPayload, msg_id: str):
        super().__init__(
            type=event_type,
            source=source,
            timestamp=time.time(),
            payload=payload,
            msg_id=msg_id
        )


class ASREvent(ConversationEvent):
    """ASR事件 - 对话中的语音识别事件"""
    
    def __init__(self, event_type: EventType, source: str, payload: ASRPayload, msg_id: str):
        super().__init__(
            type=event_type,
            source=source,
            timestamp=time.time(),
            payload=payload,
            msg_id=msg_id
        )


class StateChangeEvent(Event):
    """状态变化事件"""
    
    def __init__(self, source: str, payload: StateChangePayload):
        super().__init__(
            type=EventType.STATE_CHANGED,
            source=source,
            timestamp=time.time(),
            payload=payload
        )



class AgentRequestEvent(ConversationEvent):
    """Agent请求事件 - 对话相关事件"""
    
    def __init__(self, source: str, payload: AgentRequestPayload, msg_id: str,
                 session_id: Optional[str] = None, session_action: SessionAction = SessionAction.NEW):
        super().__init__(
            type=EventType.AGENT_DISPATCH_REQUEST,
            source=source,
            timestamp=time.time(),
            payload=payload,
            msg_id=msg_id,
            session_id=session_id,
            session_action=session_action
        )


class AgentResponseEvent(ConversationEvent):
    """Agent响应事件 - 对话相关事件"""
    
    def __init__(self, source: str, payload: AgentResponsePayload, msg_id: str):
        super().__init__(
            type=EventType.AGENT_RESPONSE,
            source=source,
            timestamp=time.time(),
            payload=payload,
            msg_id=msg_id
        )


# 向后兼容：AgentResponse 作为 AgentResponsePayload 的别名
AgentResponse = AgentResponsePayload
