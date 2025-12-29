"""
Whisper ASR 引擎实现
"""
import numpy as np
import time
from typing import Optional
import warnings

from .base import ASREngine
from .types import ASRConfig, ASRResult, Segment
from .exceptions import ModelNotFoundError, RecognitionError, AudioFormatError

# 延迟导入 whisper，避免启动时加载
_whisper = None


def _get_whisper():
    """延迟加载 whisper 模块"""
    global _whisper
    if _whisper is None:
        try:
            import whisper
            _whisper = whisper
        except ImportError:
            raise ModelNotFoundError(
                "Whisper not installed. Install with: pip install openai-whisper"
            )
    return _whisper


class WhisperEngine(ASREngine):
    """Whisper ASR 引擎"""
    
    def __init__(self, config: ASRConfig):
        """
        初始化 Whisper 引擎
        
        Args:
            config: ASR 配置
        """
        super().__init__(config)
        
        # 加载模型
        self.model = self._load_model()
        
        # 识别选项
        self.decode_options = {
            "language": config.language,
            "beam_size": config.beam_size,
            "temperature": config.temperature,
            "initial_prompt": config.initial_prompt,
        }
    
    def _load_model(self):
        """加载 Whisper 模型"""
        try:
            whisper = _get_whisper()
            
            # 自动选择设备
            device = self._get_device()
            
            # 加载模型
            print(f"Loading Whisper model: {self.config.model_size}...")
            
            # MPS 虽然能加载 sparse tensor，但不支持 sparse tensor 的运算
            # Whisper 模型包含 sparse tensor，因此无法在 MPS 上运行
            # 解决方案：检测到 MPS 时，强制使用 CPU
            if device == "mps":
                print("Note: Whisper models contain sparse tensors which are not fully supported by MPS")
                print("Using CPU for stable inference (MPS sparse operations not yet implemented)")
                device = "cpu"
            
            model = whisper.load_model(self.config.model_size, device=device)
            print(f"Model loaded successfully on {device}")
            
            # 更新配置中的实际设备
            self.config.device = device
            
            return model
            
        except Exception as e:
            raise ModelNotFoundError(f"Failed to load Whisper model: {e}")
    
    def _get_device(self) -> str:
        """获取运行设备"""
        import torch
        
        if self.config.device != "auto":
            return self.config.device
        
        # 自动选择最佳设备
        # 优先级: MPS > CUDA > CPU
        if torch.backends.mps.is_available():
            print("Detected Apple Silicon GPU (MPS), using MPS for acceleration")
            return "mps"
        elif torch.cuda.is_available():
            print("Detected CUDA GPU, using CUDA for acceleration")
            return "cuda"
        else:
            print("No GPU detected, using CPU")
            return "cpu"
    
    def recognize(self, audio: np.ndarray, sample_rate: int = 16000) -> ASRResult:
        """
        识别音频
        
        Args:
            audio: 音频数据
            sample_rate: 采样率
            
        Returns:
            识别结果
        """
        try:
            start_time = time.time()
            
            # 预处理音频
            audio = self._preprocess_audio(audio, sample_rate)
            
            # 计算音频时长
            duration = len(audio) / 16000.0
            
            # 如果音频太短，返回空结果
            if duration < 0.1:
                return ASRResult(
                    text="",
                    language=self.config.language,
                    confidence=0.0,
                    duration=duration,
                    processing_time=time.time() - start_time
                )
            
            # 调用 Whisper 识别
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = self.model.transcribe(
                    audio,
                    **self.decode_options
                )
            
            processing_time = time.time() - start_time
            
            # 解析结果
            return self._parse_result(result, duration, processing_time)
        
        except Exception as e:
            raise RecognitionError(f"Recognition failed: {e}")
    
    def _preprocess_audio(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        预处理音频
        
        Args:
            audio: 原始音频
            sample_rate: 采样率
            
        Returns:
            处理后的音频
        """
        # 转换为 float32
        if audio.dtype == np.int16:
            audio = audio.astype(np.float32) / 32768.0
        elif audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        
        # Whisper 需要 16kHz
        if sample_rate != 16000:
            audio = self._resample(audio, sample_rate, 16000)
        
        # 确保是单声道
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        
        return audio
    
    def _resample(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """
        重采样音频
        
        Args:
            audio: 原始音频
            orig_sr: 原始采样率
            target_sr: 目标采样率
            
        Returns:
            重采样后的音频
        """
        if orig_sr == target_sr:
            return audio
        
        # 简单的线性插值重采样
        duration = len(audio) / orig_sr
        target_length = int(duration * target_sr)
        
        indices = np.linspace(0, len(audio) - 1, target_length)
        resampled = np.interp(indices, np.arange(len(audio)), audio)
        
        return resampled.astype(np.float32)
    
    def _parse_result(self, result: dict, duration: float, processing_time: float) -> ASRResult:
        """
        解析 Whisper 结果
        
        Args:
            result: Whisper 返回的结果
            duration: 音频时长
            processing_time: 处理时间
            
        Returns:
            ASR 结果
        """
        # 提取文本
        text = result.get("text", "").strip()
        
        # 繁体转简体
        text = self._convert_to_simplified(text)
        
        # 提取语言
        language = result.get("language", self.config.language)
        
        # 提取分段信息
        segments = []
        raw_segments = result.get("segments", [])
        
        total_confidence = 0.0
        for i, seg in enumerate(raw_segments):
            segment_text = seg.get("text", "").strip()
            # 分段文本也转换为简体
            segment_text = self._convert_to_simplified(segment_text)
            
            segment = Segment(
                id=i,
                start=seg.get("start", 0.0),
                end=seg.get("end", 0.0),
                text=segment_text,
                confidence=self._calculate_confidence(seg)
            )
            segments.append(segment)
            total_confidence += segment.confidence
        
        # 计算整体置信度
        confidence = total_confidence / len(segments) if segments else 0.0
        
        return ASRResult(
            text=text,
            language=language,
            confidence=confidence,
            segments=segments,
            duration=duration,
            processing_time=processing_time
        )
    
    def _convert_to_simplified(self, text: str) -> str:
        """
        将繁体中文转换为简体中文
        
        Args:
            text: 输入文本
            
        Returns:
            简体中文文本
        """
        if not text:
            return text
        
        try:
            # 使用 zhconv 进行转换（更简单可靠）
            import zhconv
            return zhconv.convert(text, 'zh-cn')
        except ImportError:
            # 如果没有 zhconv，使用内置的简单映射
            return self._simple_t2s(text)
        except Exception as e:
            # 转换失败时返回原文本
            print(f"Warning: Failed to convert text to simplified Chinese: {e}")
            return text
    
    def _simple_t2s(self, text: str) -> str:
        """
        简单的繁简转换（基于常用字映射）
        
        Args:
            text: 输入文本
            
        Returns:
            转换后的文本
        """
        # 常用繁体到简体映射表
        t2s_map = {
            '無': '无', '會': '会', '來': '来', '過': '过', '們': '们',
            '個': '个', '這': '这', '那': '那', '裡': '里', '邊': '边',
            '說': '说', '話': '话', '時': '时', '間': '间', '樣': '样',
            '點': '点', '從': '从', '對': '对', '為': '为', '與': '与',
            '給': '给', '關': '关', '開': '开', '學': '学', '現': '现',
            '見': '见', '覺': '觉', '認': '认', '識': '识', '讓': '让',
            '幾': '几', '處': '处', '應': '应', '該': '该', '導': '导',
            '種': '种', '經': '经', '長': '长', '門': '门', '問': '问',
            '間': '间', '陽': '阳', '陰': '阴', '電': '电', '腦': '脑',
            '網': '网', '頁': '页', '線': '线', '務': '务', '業': '业',
            '產': '产', '資': '资', '際': '际', '術': '术', '據': '据',
            '標': '标', '準': '准', '確': '确', '質': '质', '體': '体',
            '總': '总', '統': '统', '義': '义', '議': '议', '論': '论',
            '調': '调', '運': '运', '進': '进', '連': '连', '選': '选',
            '還': '还', '錯': '错', '難': '难', '題': '题', '類': '类',
            '願': '愿', '顯': '显', '風': '风', '養': '养', '餘': '余',
        }
        
        result = []
        for char in text:
            result.append(t2s_map.get(char, char))
        return ''.join(result)
    
    def _calculate_confidence(self, segment: dict) -> float:
        """
        计算分段置信度
        
        Args:
            segment: Whisper 分段信息
            
        Returns:
            置信度 (0.0-1.0)
        """
        # Whisper 返回的是 avg_logprob 和 no_speech_prob
        avg_logprob = segment.get("avg_logprob", -1.0)
        no_speech_prob = segment.get("no_speech_prob", 1.0)
        
        # 转换为置信度
        # avg_logprob 通常在 -1 到 0 之间，越接近0越好
        # no_speech_prob 越小越好
        confidence = np.exp(avg_logprob) * (1 - no_speech_prob)
        
        return float(np.clip(confidence, 0.0, 1.0))
