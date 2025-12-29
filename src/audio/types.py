"""
音频数据结构定义
"""
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import time


@dataclass
class AudioConfig:
    """音频配置"""
    sample_rate: int = 16000        # 采样率 (Hz)
    channels: int = 1               # 声道数 (1=单声道, 2=立体声)
    chunk_size: int = 1024          # 每次读取的帧数
    format: str = "int16"           # 音频格式 (int16, float32)
    device_index: Optional[int] = None  # 设备索引 (None=默认设备)
    buffer_size: int = 10           # 缓冲区大小(秒)
    
    def validate(self):
        """验证配置参数"""
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if self.channels not in (1, 2):
            raise ValueError("channels must be 1 or 2")
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.format not in ("int16", "float32"):
            raise ValueError("format must be 'int16' or 'float32'")
        if self.buffer_size <= 0:
            raise ValueError("buffer_size must be positive")


@dataclass
class AudioFrame:
    """音频帧数据"""
    data: np.ndarray               # 音频数据数组
    sample_rate: int               # 采样率
    channels: int                  # 声道数
    timestamp: float               # 时间戳 (Unix时间)
    frame_id: int                  # 帧序号
    duration: float                # 音频时长(秒)
    
    @classmethod
    def create(cls, data: np.ndarray, sample_rate: int, channels: int, frame_id: int):
        """创建音频帧"""
        duration = len(data) / sample_rate / channels
        return cls(
            data=data,
            sample_rate=sample_rate,
            channels=channels,
            timestamp=time.time(),
            frame_id=frame_id,
            duration=duration
        )
    
    def __len__(self):
        """返回样本数"""
        return len(self.data)
    
    @property
    def num_samples(self) -> int:
        """样本数"""
        return len(self.data)
    
    @property
    def size_bytes(self) -> int:
        """字节数"""
        return self.data.nbytes


@dataclass
class RecorderStatus:
    """录音器状态信息"""
    is_recording: bool             # 是否正在录音
    device_name: str               # 设备名称
    buffer_usage: float            # 缓冲区使用率 (0.0-1.0)
    frames_captured: int           # 已捕获的帧数
    dropped_frames: int            # 丢帧数
    average_level: float           # 平均音量级别


@dataclass
class AudioDevice:
    """音频设备信息"""
    index: int                     # 设备索引
    name: str                      # 设备名称
    channels: int                  # 最大声道数
    sample_rate: int               # 默认采样率
    is_default: bool = False       # 是否为默认设备
    
    def __str__(self):
        default_tag = " [默认]" if self.is_default else ""
        return f"[{self.index}] {self.name} ({self.channels}ch, {self.sample_rate}Hz){default_tag}"
