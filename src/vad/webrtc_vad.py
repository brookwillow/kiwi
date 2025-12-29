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
    
    def process_frame(self, audio_frame: np.ndarray) -> VADResult:
        """
        处理单帧音频
        
        Args:
            audio_frame: 音频帧数据 (int16)
        
        Returns:
            VAD检测结果
        """
        self.total_frames += 1
        
        # 转换为bytes（WebRTC VAD需要）
        audio_bytes = audio_frame.astype(np.int16).tobytes()
        
        # WebRTC VAD检测
        is_speech = self.vad.is_speech(audio_bytes, self.config.sample_rate)
        
        # 状态机处理
        result = self._update_state(is_speech, audio_bytes)
        
        return result
    
    def _update_state(self, is_speech: bool, audio_bytes: bytes) -> VADResult:
        """
        更新状态机 - 简化版本：VAD=1为BEGIN，VAD=0为END
        
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
                # 立即切换到语音状态
                self.state = VADState.SPEAKING
                event = VADEvent.SPEECH_START
                
                # 将缓冲区的音频和当前帧加入语音片段
                self.speech_frames = list(self.pre_speech_buffer)
                self.speech_frames.append(audio_bytes)
                
                self.speech_start_time = self.total_frames
                print(f"VAD: Speech started at frame {self.total_frames}")
            else:
                # 非语音帧加入预缓冲
                self.pre_speech_buffer.append(audio_bytes)
        
        elif self.state == VADState.SPEAKING:
            # 正在说话状态
            if is_speech:
                # 继续语音
                self.speech_frames.append(audio_bytes)
                event = VADEvent.SPEAKING
            else:
                # VAD=0，立即结束语音
                self.speech_frames.append(audio_bytes)  # 最后一帧也加入
                
                duration_ms = (len(self.speech_frames) * self.config.frame_duration_ms)
                
                # 检查语音长度是否足够
                if len(self.speech_frames) >= self.config.min_speech_frames:
                    self.state = VADState.IDLE
                    event = VADEvent.SPEECH_END
                    
                    # 拼接所有语音帧
                    audio_data = b''.join(self.speech_frames)
                    
                    print(f"VAD: Speech ended at frame {self.total_frames}, "
                          f"duration: {duration_ms}ms, "
                          f"frames: {len(self.speech_frames)}")
                else:
                    # 语音太短，丢弃
                    print(f"VAD: Speech too short ({duration_ms}ms), discarded")
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
        print("VAD: Reset")
