"""
ASR 模块数据类型定义
"""
from dataclasses import dataclass, field
from typing import List, Optional
import time


@dataclass
class ASRConfig:
    """ASR 配置"""
    model: str = "whisper"              # 模型类型
    language: str = "zh"                # 识别语言
    model_size: str = "base"            # 模型大小 (tiny, base, small, medium, large)
    device: str = "auto"                # 运行设备 (auto, cpu, cuda, mps)
    beam_size: int = 5                  # 束搜索大小
    temperature: float = 0.0            # 采样温度
    vad_filter: bool = True             # 是否使用VAD过滤
    initial_prompt: Optional[str] = None  # 初始提示词
    
    def validate(self):
        """验证配置参数"""
        if self.model not in ("whisper", "azure", "google", "local"):
            raise ValueError(f"Unsupported model: {self.model}")
        
        if self.model_size not in ("tiny","tiny.en", "base","base.en"):
            raise ValueError(f"Invalid model_size: {self.model_size}")
        
        if self.device not in ("auto", "cpu", "cuda", "mps"):
            raise ValueError(f"Invalid device: {self.device}")


@dataclass
class Segment:
    """ASR 分段信息"""
    id: int                             # 分段ID
    start: float                        # 开始时间(秒)
    end: float                          # 结束时间(秒)
    text: str                           # 分段文本
    confidence: float                   # 置信度
    
    @property
    def duration(self) -> float:
        """分段时长"""
        return self.end - self.start


@dataclass
class ASRResult:
    """ASR 识别结果"""
    text: str                           # 识别文本
    language: str                       # 检测语言
    confidence: float                   # 整体置信度 (0.0-1.0)
    segments: List[Segment] = field(default_factory=list)  # 分段信息
    duration: float = 0.0               # 音频时长
    processing_time: float = 0.0        # 处理时间
    timestamp: float = field(default_factory=time.time)  # 时间戳
    
    @property
    def is_empty(self) -> bool:
        """是否为空结果"""
        return not self.text or self.text.strip() == ""
    
    @property
    def num_segments(self) -> int:
        """分段数量"""
        return len(self.segments)
    
    def __str__(self):
        return f"ASRResult(text='{self.text}', confidence={self.confidence:.2f}, segments={self.num_segments})"
