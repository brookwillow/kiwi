"""
基于OpenWakeWord的唤醒词实现
"""
import numpy as np
import time
import os
from pathlib import Path
from typing import Optional
from openwakeword.model import Model as OpenWakeWordModel
from .base import BaseWakeWord
from .types import WakeWordConfig, WakeWordResult, WakeWordState


class OpenWakeWord(BaseWakeWord):
    """基于OpenWakeWord的唤醒词检测"""
    
    def __init__(self, config: WakeWordConfig):
        """
        初始化OpenWakeWord检测器
        
        Args:
            config: 唤醒词配置
        """
        super().__init__(config)
        
        print(f"正在初始化唤醒词引擎...")
        
        # 设置模型目录为项目下的models/wakeword
        project_root = Path(__file__).parent.parent.parent
        model_dir = project_root / "models" / "wakeword"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"   模型目录: {model_dir}")
        
        # 只加载唤醒词模型文件（排除辅助模型）
        # OpenWakeWord的唤醒词模型通常以 *_v0.1.onnx 命名
        excluded_models = {
            'melspectrogram.onnx',
            'embedding_model.onnx', 
            'silero_vad.onnx'
        }
        
        all_files = list(model_dir.glob("*.tflite")) + list(model_dir.glob("*.onnx"))
        model_files = []
        
        for f in all_files:
            # 排除辅助模型，只保留唤醒词模型
            if f.name not in excluded_models:
                # 唤醒词模型通常包含版本号 (如 alexa_v0.1.onnx)
                if '_v' in f.name and f.name.endswith('.onnx'):
                    model_files.append(f)
        
        if not model_files:
            print(f"   ⚠️  未找到唤醒词模型文件")
            print(f"   找到的文件: {[f.name for f in all_files]}")
            print(f"   请确保模型文件名格式为: *_v0.1.onnx (如 alexa_v0.1.onnx)")
            raise FileNotFoundError(f"No wake word model files found in {model_dir}")
        
        print(f"   找到 {len(model_files)} 个唤醒词模型:")
        for f in model_files:
            print(f"     - {f.name}")
        
        # 创建OpenWakeWord模型，指定自定义模型路径
        self.model = OpenWakeWordModel(
            wakeword_models=[str(f) for f in model_files],
            inference_framework='onnx'
        )
        
        # 状态管理
        self.state = WakeWordState.IDLE
        self.last_trigger_time = 0
        
        # 获取实际加载的模型
        loaded_models = list(self.model.models.keys())
        
        print(f"✅ 唤醒词引擎初始化成功")
        print(f"   已加载的唤醒词: {loaded_models}")
        print(f"   检测阈值: {config.threshold}")
    
    def detect(self, audio_data: np.ndarray) -> WakeWordResult:
        """
        检测音频中的唤醒词
        
        Args:
            audio_data: 音频数据 (float32, -1 to 1)
        
        Returns:
            唤醒词检测结果
        """
        # 检查冷却时间
        current_time = time.time()
        if self.state == WakeWordState.TRIGGERED:
            if current_time - self.last_trigger_time < self.config.cooldown_seconds:
                # 还在冷却期
                return WakeWordResult(
                    is_detected=False,
                    state=self.state
                )
            else:
                # 冷却期结束，重置状态
                self.state = WakeWordState.IDLE
        
        # 确保音频是float32格式
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        
        # OpenWakeWord需要16bit的音频数据
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        # 进行检测
        predictions = self.model.predict(audio_int16)
        
        # 过滤掉非字符串的键（一些辅助模型会返回数字键）
        predictions = {k: v for k, v in predictions.items() if isinstance(k, str) and not k.isdigit()}
        
        # 找出最高置信度（用于调试）
        if predictions:
            max_keyword = max(predictions.items(), key=lambda x: x[1])
            max_confidence = max_keyword[1]
        else:
            max_confidence = 0.0
        
        # 检查是否有唤醒词被触发
        for keyword, score in predictions.items():
            if score >= self.config.threshold:
                # 检测到唤醒词
                self.state = WakeWordState.TRIGGERED
                self.last_trigger_time = current_time
                
                print(f"🎯 唤醒词: {keyword} (置信度: {score:.2f}, 阈值: {self.config.threshold:.2f})")
                
                return WakeWordResult(
                    is_detected=True,
                    keyword=keyword,
                    confidence=score,
                    state=self.state
                )
        
        # 未检测到唤醒词，但返回最高置信度用于调试
        return WakeWordResult(
            is_detected=False,
            confidence=max_confidence,
            state=self.state
        )
    
    def reset(self):
        """重置检测器状态"""
        self.state = WakeWordState.IDLE
        self.last_trigger_time = 0
        self.model.reset()
