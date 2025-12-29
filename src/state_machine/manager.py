"""
语音状态机管理器

统一管理唤醒、VAD、ASR的状态转换逻辑，与具体实现解耦
"""
import time
from typing import Optional, Callable, List
from collections import deque

from .types import (
    VoiceState, StateEvent, StateTransition, VoiceStateInfo,
    StateConfig, StateChangeResult
)


class VoiceStateManager:
    """
    语音处理状态机管理器
    
    职责：
    1. 管理语音处理的整体状态（空闲、监听、识别等）
    2. 处理状态转换逻辑
    3. 管理超时和计数器
    4. 解耦状态管理与具体模块（wakeword/vad/asr）实现
    
    特点：
    - 与具体模块解耦，只管理状态转换
    - 线程安全的状态管理
    - 支持状态变化回调
    - 记录状态转换历史
    """
    
    def __init__(self, config: Optional[StateConfig] = None):
        """
        初始化状态机管理器
        
        Args:
            config: 状态机配置
        """
        self.config = config or StateConfig()
        
        # 当前状态
        self._current_state = VoiceState.IDLE
        self._state_enter_time = time.time()
        
        # 唤醒相关
        self._wakeword_detected = False
        self._wakeword_timeout_at = 0.0  # 超时时间戳
        self._vad_end_count = 0
        
        # 状态转换历史
        self._transition_history: deque = deque(maxlen=100)
        
        # 状态变化回调
        self._state_change_callbacks: List[Callable[[StateChangeResult], None]] = []
        
        if self.config.debug:
            print(f"🎯 状态机初始化完成 - 初始状态: {self._current_state.value}")
    
    # ==================== 公共接口 ====================
    
    def get_state_info(self) -> VoiceStateInfo:
        """
        获取当前状态信息
        
        Returns:
            当前状态信息
        """
        last_transition = self._transition_history[-1] if self._transition_history else None
        state_duration = time.time() - self._state_enter_time
        
        return VoiceStateInfo(
            current_state=self._current_state,
            is_wakeword_enabled=self.config.enable_wakeword,
            is_wakeword_detected=self._wakeword_detected,
            wakeword_timeout_at=self._wakeword_timeout_at,
            vad_end_count=self._vad_end_count,
            last_transition=last_transition,
            state_duration=state_duration
        )
    
    def handle_event(self, event: StateEvent, metadata: Optional[dict] = None) -> StateChangeResult:
        """
        处理状态事件
        
        Args:
            event: 状态事件
            metadata: 事件附加数据
        
        Returns:
            状态变化结果
        """
        previous_state = self._current_state
        
        # 根据当前状态和事件决定新状态
        result = self._process_event(event, metadata)
        
        # 更新result中的previous_state
        result.previous_state = previous_state
        
        # 如果状态发生变化，记录转换
        if result.success and result.current_state != previous_state:
            self._record_transition(previous_state, result.current_state, event, metadata)
            self._state_enter_time = time.time()
        
        # 触发回调
        if result.success:
            self._notify_callbacks(result)
        
        if self.config.debug:
            self._log_state_change(result)
        
        return result
    
    def check_timeout(self) -> Optional[StateChangeResult]:
        """
        检查并处理超时
        
        Returns:
            如果发生超时，返回状态变化结果；否则返回None
        """
        info = self.get_state_info()
        
        # 检查唤醒超时
        if info.is_timeout_expired():
            if self.config.debug:
                print(f"⏰ 唤醒超时 - 已持续 {self.config.wakeword_timeout}秒")
            return self.handle_event(StateEvent.WAKEWORD_TIMEOUT)
        
        return None
    
    def reset(self):
        """重置状态机到初始状态"""
        result = self.handle_event(StateEvent.RESET)
        if self.config.debug:
            print(f"🔄 状态机已重置")
    
    def register_callback(self, callback: Callable[[StateChangeResult], None]):
        """
        注册状态变化回调
        
        Args:
            callback: 回调函数，接收StateChangeResult参数
        """
        self._state_change_callbacks.append(callback)
    
    def get_transition_history(self, limit: int = 10) -> List[StateTransition]:
        """
        获取状态转换历史
        
        Args:
            limit: 返回的最大记录数
        
        Returns:
            状态转换记录列表
        """
        return list(self._transition_history)[-limit:]
    
    # ==================== 内部实现 ====================
    
    def _process_event(self, event: StateEvent, metadata: Optional[dict]) -> StateChangeResult:
        """
        处理事件并返回结果
        
        Args:
            event: 状态事件
            metadata: 事件附加数据
        
        Returns:
            状态变化结果
        """
        current = self._current_state
        
        # 唤醒词事件
        if event == StateEvent.WAKEWORD_TRIGGERED:
            return self._handle_wakeword_triggered()
        
        elif event == StateEvent.WAKEWORD_RESET:
            return self._handle_wakeword_reset()
        
        elif event == StateEvent.WAKEWORD_TIMEOUT:
            return self._handle_wakeword_timeout()
        
        # VAD事件
        elif event == StateEvent.SPEECH_START:
            return self._handle_speech_start()
        
        elif event == StateEvent.SPEECH_END:
            return self._handle_speech_end(metadata)
        
        elif event == StateEvent.SILENCE_DETECTED:
            return self._handle_silence_detected()
        
        # ASR事件
        elif event == StateEvent.RECOGNITION_START:
            return self._handle_recognition_start()
        
        elif event == StateEvent.RECOGNITION_SUCCESS:
            return self._handle_recognition_success(metadata)
        
        elif event == StateEvent.RECOGNITION_FAILED:
            return self._handle_recognition_failed()
        
        # 系统控制事件
        elif event == StateEvent.RESET:
            return self._handle_reset()
        
        elif event == StateEvent.FORCE_IDLE:
            return self._handle_force_idle()
        
        else:
            return StateChangeResult(
                success=False,
                previous_state=current,
                current_state=current,
                event=event,
                message=f"未知事件: {event.value}"
            )
    
    def _handle_wakeword_triggered(self) -> StateChangeResult:
        """处理检测到唤醒词"""
        if not self.config.enable_wakeword:
            return self._create_result(False, StateEvent.WAKEWORD_TRIGGERED, "唤醒词未启用")
        
        if self._wakeword_detected:
            return self._create_result(False, StateEvent.WAKEWORD_TRIGGERED, "已在唤醒状态")
        
        # 转换到唤醒状态
        self._wakeword_detected = True
        self._vad_end_count = 0
        self._wakeword_timeout_at = 0.0
        self._current_state = VoiceState.WAKEWORD_DETECTED
        
        return self._create_result(
            True, StateEvent.WAKEWORD_TRIGGERED,
            "检测到唤醒词，进入监听状态",
            should_reset_wakeword=False
        )
    
    def _handle_wakeword_reset(self) -> StateChangeResult:
        """处理重置唤醒状态"""
        if not self._wakeword_detected:
            return self._create_result(False, StateEvent.WAKEWORD_RESET, "未在唤醒状态")
        
        self._wakeword_detected = False
        self._vad_end_count = 0
        self._wakeword_timeout_at = 0.0
        self._current_state = VoiceState.IDLE
        
        return self._create_result(
            True, StateEvent.WAKEWORD_RESET,
            "唤醒状态已重置",
            should_reset_wakeword=True
        )
    
    def _handle_wakeword_timeout(self) -> StateChangeResult:
        """处理唤醒超时"""
        if not self._wakeword_detected:
            return self._create_result(False, StateEvent.WAKEWORD_TIMEOUT, "未在唤醒状态")
        
        self._wakeword_detected = False
        self._vad_end_count = 0
        self._wakeword_timeout_at = 0.0
        self._current_state = VoiceState.TIMEOUT
        
        # 立即返回IDLE
        self._current_state = VoiceState.IDLE
        
        return self._create_result(
            True, StateEvent.WAKEWORD_TIMEOUT,
            f"唤醒超时({self.config.wakeword_timeout}秒)，返回空闲",
            should_reset_wakeword=True
        )
    
    def _handle_speech_start(self) -> StateChangeResult:
        """处理语音开始"""
        # 如果启用唤醒词，需要先检测到唤醒词
        if self.config.enable_wakeword and not self._wakeword_detected:
            return self._create_result(False, StateEvent.SPEECH_START, "未检测到唤醒词")
        
        self._current_state = VoiceState.SPEECH_DETECTED
        
        return self._create_result(
            True, StateEvent.SPEECH_START,
            "检测到语音开始"
        )
    
    def _handle_speech_end(self, metadata: Optional[dict]) -> StateChangeResult:
        """处理语音结束"""
        # VAD END计数增加（仅在唤醒模式下）
        if self.config.enable_wakeword and self._wakeword_detected:
            self._vad_end_count += 1
            
            # 检查是否达到最大次数（通常配置为1，一次就返回IDLE）
            if self._vad_end_count >= self.config.max_vad_end_count:
                self._wakeword_detected = False
                self._vad_end_count = 0
                self._wakeword_timeout_at = 0.0
                self._current_state = VoiceState.IDLE
                
                return self._create_result(
                    True, StateEvent.SPEECH_END,
                    f"达到最大VAD END次数({self.config.max_vad_end_count})，返回空闲",
                    should_reset_wakeword=True,
                    should_trigger_asr=True
                )
            
            # 未达到最大次数（当max_vad_end_count>1时）
            # 第一次VAD END，启动超时计时器
            if self._vad_end_count == 1 and self._wakeword_timeout_at == 0.0:
                self._wakeword_timeout_at = time.time() + self.config.wakeword_timeout
            
            self._current_state = VoiceState.LISTENING
            return self._create_result(
                True, StateEvent.SPEECH_END,
                f"语音结束({self._vad_end_count}/{self.config.max_vad_end_count})，继续监听",
                should_start_timeout=(self._vad_end_count == 1),
                should_trigger_asr=True
            )
        
        # 非唤醒模式，直接触发识别
        self._current_state = VoiceState.LISTENING
        return self._create_result(
            True, StateEvent.SPEECH_END,
            "语音结束，准备识别",
            should_trigger_asr=True
        )
    
    def _handle_silence_detected(self) -> StateChangeResult:
        """处理检测到静音"""
        if self.config.enable_wakeword and self._wakeword_detected:
            self._current_state = VoiceState.LISTENING
        else:
            self._current_state = VoiceState.IDLE
        
        return self._create_result(
            True, StateEvent.SILENCE_DETECTED,
            "检测到静音"
        )
    
    def _handle_recognition_start(self) -> StateChangeResult:
        """处理开始识别"""
        self._current_state = VoiceState.RECOGNIZING
        
        return self._create_result(
            True, StateEvent.RECOGNITION_START,
            "开始ASR识别"
        )
    
    def _handle_recognition_success(self, metadata: Optional[dict]) -> StateChangeResult:
        """处理识别成功"""
        text = metadata.get('text', '') if metadata else ''
        
        # 识别成功后，根据是否启用唤醒词决定状态
        if self.config.enable_wakeword and self._wakeword_detected:
            self._current_state = VoiceState.LISTENING
            message = f"识别成功: {text}，继续监听"
        else:
            self._current_state = VoiceState.IDLE
            message = f"识别成功: {text}"
        
        return self._create_result(
            True, StateEvent.RECOGNITION_SUCCESS,
            message
        )
    
    def _handle_recognition_failed(self) -> StateChangeResult:
        """处理识别失败"""
        if self.config.enable_wakeword and self._wakeword_detected:
            self._current_state = VoiceState.LISTENING
        else:
            self._current_state = VoiceState.IDLE
        
        return self._create_result(
            True, StateEvent.RECOGNITION_FAILED,
            "识别失败"
        )
    
    def _handle_reset(self) -> StateChangeResult:
        """处理重置"""
        self._wakeword_detected = False
        self._vad_end_count = 0
        self._wakeword_timeout_at = 0.0
        self._current_state = VoiceState.IDLE
        
        return self._create_result(
            True, StateEvent.RESET,
            "状态机已重置",
            should_reset_wakeword=True
        )
    
    def _handle_force_idle(self) -> StateChangeResult:
        """处理强制回到空闲"""
        self._wakeword_detected = False
        self._vad_end_count = 0
        self._wakeword_timeout_at = 0.0
        self._current_state = VoiceState.IDLE
        
        return self._create_result(
            True, StateEvent.FORCE_IDLE,
            "强制返回空闲状态",
            should_reset_wakeword=True
        )
    
    def _create_result(
        self,
        success: bool,
        event: StateEvent,
        message: str,
        should_reset_wakeword: bool = False,
        should_start_timeout: bool = False,
        should_trigger_asr: bool = False
    ) -> StateChangeResult:
        """创建状态变化结果"""
        return StateChangeResult(
            success=success,
            previous_state=self._current_state,
            current_state=self._current_state,
            event=event,
            message=message,
            should_reset_wakeword=should_reset_wakeword,
            should_start_timeout=should_start_timeout,
            should_trigger_asr=should_trigger_asr
        )
    
    def _record_transition(
        self,
        from_state: VoiceState,
        to_state: VoiceState,
        event: StateEvent,
        metadata: Optional[dict]
    ):
        """记录状态转换"""
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            event=event,
            timestamp=time.time(),
            metadata=metadata
        )
        self._transition_history.append(transition)
    
    def _notify_callbacks(self, result: StateChangeResult):
        """通知所有回调"""
        for callback in self._state_change_callbacks:
            try:
                callback(result)
            except Exception as e:
                if self.config.debug:
                    print(f"⚠️ 状态变化回调异常: {e}")
    
    def _log_state_change(self, result: StateChangeResult):
        """记录状态变化"""
        if result.success:
            if result.previous_state != result.current_state:
                print(f"🔄 [{result.event.value}] {result.previous_state.value} → {result.current_state.value}: {result.message}")
            else:
                print(f"📌 [{result.event.value}] {result.current_state.value}: {result.message}")
        else:
            print(f"❌ [{result.event.value}] 失败: {result.message}")
