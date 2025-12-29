"""
基于WebRTC VAD的实现
"""
import numpy as np
import webrtcvad
from collections import deque
from typing import Optional
from .base import BaseVAD
from .types import VADConfig, VADResult, VADState, VADEvent


class WebRTCVAD(BaseVAD):
    """基于WebRTC的VAD实现"""
    
    def __init__(self, config: VADConfig):
        """
        初始化WebRTC VAD
        
        Args:
            config: VAD配置
        """
        super().__init__(config)
        
        # 创建WebRTC VAD实例
        self.vad = webrtcvad.Vad(config.aggressiveness)
        
        # 状态管理
        self.state = VADState.IDLE
        self.silence_frames_count = 0  # 连续静音帧计数
        self.speech_frames_count = 0   # 连续语音帧计数
        
        # 语音片段收集
        self.speech_frames = []  # 当前语音片段的所有帧
        
        # 循环缓冲区，用于保存语音前的音频
        self.pre_speech_buffer = deque(maxlen=config.pre_speech_frames)
        
        # 统计信息
        self.total_frames = 0
        self.speech_start_time = None
        
        # 唤醒后延迟处理（从配置读取）
        self.wakeword_detected = False
        self.frames_since_wakeword = 0
        self.wakeword_delay_frames = config.wakeword_delay_frames
        
        # 语音结束判定 - 需要较长的静音间隔（从配置读取）
        self.silence_timeout_frames = config.vad_end_silence_frames
    
    def process_frame(self, audio_frame: np.ndarray) -> VADResult:
        """
        处理单帧音频
        
        Args:
            audio_frame: 音频帧数据 (int16)
        
        Returns:
            VAD检测结果
        """
        self.total_frames += 1
        
        # 如果唤醒后还在延迟期内，跳过VAD处理
        if self.wakeword_detected:
            self.frames_since_wakeword += 1
            if self.frames_since_wakeword < self.wakeword_delay_frames:
                # 延迟期内，返回静音结果
                return VADResult(
                    is_speech=False,
                    confidence=0.0,
                    state=self.state,
                    event=None,
                    audio_data=None,
                    duration_ms=0
                )
        
        # 转换为bytes（WebRTC VAD需要）
        audio_bytes = audio_frame.astype(np.int16).tobytes()
        
        # WebRTC VAD检测
        is_speech = self.vad.is_speech(audio_bytes, self.config.sample_rate)
        
        # 状态机处理
        result = self._update_state(is_speech, audio_bytes)
        
        return result
    
    def _update_state(self, is_speech: bool, audio_bytes: bytes) -> VADResult:
        """
        更新状态机 - 新逻辑：
        1. 唤醒后500ms才开始监听VAD
        2. VAD=1为语音开始
        3. VAD=0后需要较长静音间隔（1秒）才算真正结束
        4. 一次VAD结束后立即重置为未唤醒
        
        Args:
            is_speech: 当前帧是否是语音
            audio_bytes: 音频数据
        
        Returns:
            VAD检测结果
        """
        event = None
        audio_data = None
        duration_ms = 0
        
        if self.state == VADState.IDLE:
            # 空闲状态
            if is_speech:
                # VAD=1，语音开始
                self.state = VADState.SPEAKING
                event = VADEvent.SPEECH_START
                
                # 将缓冲区的音频和当前帧加入语音片段
                self.speech_frames = list(self.pre_speech_buffer)
                self.speech_frames.append(audio_bytes)
                
                self.silence_frames_count = 0
                self.speech_start_time = self.total_frames
                print(f"VAD: Speech started at frame {self.total_frames}")
            else:
                # 非语音帧加入预缓冲
                self.pre_speech_buffer.append(audio_bytes)
        
        elif self.state == VADState.SPEAKING:
            # 正在说话状态
            self.speech_frames.append(audio_bytes)
            
            if is_speech:
                # VAD=1，继续语音，重置静音计数
                self.silence_frames_count = 0
                event = VADEvent.SPEAKING
            else:
                # VAD=0，增加静音计数，但不立即结束
                self.silence_frames_count += 1
                
                # 只有静音时间超过阈值才算真正结束
                if self.silence_frames_count >= self.silence_timeout_frames:
                    duration_ms = (len(self.speech_frames) * self.config.frame_duration_ms)
                    
                    # 检查语音长度是否足够
                    if len(self.speech_frames) >= self.config.min_speech_frames:
                        self.state = VADState.IDLE
                        event = VADEvent.SPEECH_END
                        
                        # 拼接所有语音帧
                        audio_data = b''.join(self.speech_frames)
                        
                        print(f"VAD: Speech ended at frame {self.total_frames}, "
                              f"duration: {duration_ms:.0f}ms, "
                              f"frames: {len(self.speech_frames)}, "
                              f"silence: {self.silence_frames_count}")
                        
                        # 一次VAD结束后重置唤醒标志和VAD状态
                        self.wakeword_detected = False
                        self.frames_since_wakeword = 0
                        print("VAD: Reset to IDLE after speech end")
                    else:
                        # 语音太短，丢弃
                        print(f"VAD: Speech too short ({duration_ms:.0f}ms), discarded")
                        self.state = VADState.IDLE
                    
                    # 重置
                    self.speech_frames = []
                    self.silence_frames_count = 0
                    self.speech_frames_count = 0
                    self.speech_start_time = None
        
        return VADResult(
            is_speech=is_speech,
            confidence=1.0 if is_speech else 0.0,
            state=self.state,
            event=event,
            audio_data=audio_data,
            duration_ms=duration_ms
        )
    
    def reset(self):
        """重置VAD状态"""
        self.state = VADState.IDLE
        self.silence_frames_count = 0
        self.speech_frames_count = 0
        self.speech_frames = []
        self.pre_speech_buffer.clear()
        self.total_frames = 0
        self.speech_start_time = None
        self.wakeword_detected = False
        self.frames_since_wakeword = 0
        print("VAD: Reset")
    
    def on_wakeword_detected(self):
        """唤醒词检测到时调用，启动延迟"""
        self.wakeword_detected = True
        self.frames_since_wakeword = 0
        delay_ms = self.wakeword_delay_frames * self.config.frame_duration_ms
        print(f"VAD: Wakeword detected, starting {self.wakeword_delay_frames} frames ({delay_ms:.0f}ms) delay")
