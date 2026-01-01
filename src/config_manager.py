"""
系统配置管理模块
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SystemConfig:
    """系统配置"""
    name: str
    version: str


@dataclass
class AudioConfig:
    """音频配置"""
    sample_rate: int
    channels: int
    chunk_size: int


@dataclass
class ModuleConfig:
    """模块配置"""
    enabled: bool
    settings: Dict[str, Any]


@dataclass
class Config:
    """完整配置"""
    system: SystemConfig
    audio: AudioConfig
    wakeword: ModuleConfig
    vad: ModuleConfig
    asr: ModuleConfig
    orchestrator: ModuleConfig
    memory: ModuleConfig
    working_mode: int
    
    @property
    def is_wakeword_enabled(self) -> bool:
        """是否启用唤醒词"""
        return self.wakeword.enabled and self.working_mode in [1]
    
    @property
    def is_vad_enabled(self) -> bool:
        """是否启用VAD"""
        return self.vad.enabled and self.working_mode in [1, 2]
    
    @property
    def is_asr_enabled(self) -> bool:
        """是否启用ASR"""
        return self.asr.enabled
    
    @property
    def pipeline_description(self) -> str:
        """获取当前流水线描述"""
        if self.working_mode == 1:
            return "完整模式: 录音 → 唤醒 → VAD → ASR"
        elif self.working_mode == 2:
            return "跳过唤醒: 录音 → VAD → ASR"
        elif self.working_mode == 3:
            return "直接ASR: 录音 → ASR"
        else:
            return "未知模式"


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为 config/system_config.yaml
        """
        if config_path is None:
            # 默认配置路径
            # __file__ 在 src/config_manager.py，所以 parent 是 src/，parent.parent 是项目根目录
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "system_config.yaml"
        
        self.config_path = Path(config_path)
        self.config = self.load_config()
    
    def load_config(self) -> Config:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # 解析配置
        system = SystemConfig(
            name=data['system']['name'],
            version=data['system']['version']
        )
        
        audio = AudioConfig(
            sample_rate=data['audio']['sample_rate'],
            channels=data['audio']['channels'],
            chunk_size=data['audio']['chunk_size']
        )
        
        # 模块配置
        wakeword = ModuleConfig(
            enabled=data['modules']['wakeword']['enabled'],
            settings={
                'models': data['modules']['wakeword'].get('models', []),
                'threshold': data['modules']['wakeword'].get('threshold', 0.5),
                'cooldown_seconds': data['modules']['wakeword'].get('cooldown_seconds', 3.0)
            }
        )
        
        vad = ModuleConfig(
            enabled=data['modules']['vad']['enabled'],
            settings={
                'frame_duration_ms': data['modules']['vad']['frame_duration_ms'],
                'aggressiveness': data['modules']['vad'].get('aggressiveness', 2),
                'silence_timeout_ms': data['modules']['vad']['silence_timeout_ms'],
                'pre_speech_buffer_ms': data['modules']['vad'].get('pre_speech_buffer_ms', 300),
                'min_speech_duration_ms': data['modules']['vad'].get('min_speech_duration_ms', 300),
                'min_volume_threshold': data['modules']['vad'].get('min_volume_threshold', 0.01)
            }
        )
        
        asr = ModuleConfig(
            enabled=data['modules']['asr']['enabled'],
            settings={
                'model': data['modules']['asr']['model'],
                'language': data['modules']['asr']['language'],
                'min_audio_duration_ms': data['modules']['asr'].get('min_audio_duration_ms', 500)
            }
        )
        
        # Orchestrator配置
        orchestrator_data = data['modules'].get('orchestrator', {})
        orchestrator = ModuleConfig(
            enabled=orchestrator_data.get('enabled', True),
            settings={
                'use_mock_llm': orchestrator_data.get('use_mock_llm', True),
                'default_agent': orchestrator_data.get('default_agent', 'chat_agent')
            }
        )
        
        # Memory配置
        memory_data = data['modules'].get('memory', {})
        memory = ModuleConfig(
            enabled=memory_data.get('enabled', True),
            settings={
                'max_short_term': memory_data.get('max_short_term', 100),
                'long_term_generation': memory_data.get('long_term_generation', {
                    'trigger_count': 10,
                    'max_history_rounds': 30
                })
            }
        )
        
        working_mode = data.get('working_mode', 3)
        
        return Config(
            system=system,
            audio=audio,
            wakeword=wakeword,
            vad=vad,
            asr=asr,
            orchestrator=orchestrator,
            memory=memory,
            working_mode=working_mode
        )
    
    def save_config(self):
        """保存配置到文件"""
        data = {
            'system': {
                'name': self.config.system.name,
                'version': self.config.system.version
            },
            'audio': {
                'sample_rate': self.config.audio.sample_rate,
                'channels': self.config.audio.channels,
                'chunk_size': self.config.audio.chunk_size
            },
            'modules': {
                'wakeword': {
                    'enabled': self.config.wakeword.enabled,
                    **self.config.wakeword.settings
                },
                'vad': {
                    'enabled': self.config.vad.enabled,
                    **self.config.vad.settings
                },
                'asr': {
                    'enabled': self.config.asr.enabled,
                    **self.config.asr.settings
                },
                'orchestrator': {
                    'enabled': self.config.orchestrator.enabled,
                    **self.config.orchestrator.settings
                }
            },
            'working_mode': self.config.working_mode
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    
    def set_working_mode(self, mode: int):
        """
        设置工作模式
        
        Args:
            mode: 工作模式 (1: 完整模式, 2: 跳过唤醒, 3: 直接ASR)
        """
        if mode not in [1, 2, 3]:
            raise ValueError("Invalid working mode. Must be 1, 2, or 3")
        
        self.config.working_mode = mode
        self.save_config()
    
    def enable_module(self, module_name: str, enabled: bool = True):
        """
        启用/禁用模块
        
        Args:
            module_name: 模块名称 ('wakeword', 'vad', 'asr')
            enabled: 是否启用
        """
        if module_name == 'wakeword':
            self.config.wakeword.enabled = enabled
        elif module_name == 'vad':
            self.config.vad.enabled = enabled
        elif module_name == 'asr':
            self.config.asr.enabled = enabled
        else:
            raise ValueError(f"Unknown module: {module_name}")
        
        self.save_config()
    
    def get_module_config(self, module_name: str) -> ModuleConfig:
        """获取模块配置"""
        if module_name == 'wakeword':
            return self.config.wakeword
        elif module_name == 'vad':
            return self.config.vad
        elif module_name == 'asr':
            return self.config.asr
        else:
            raise ValueError(f"Unknown module: {module_name}")
    
    def print_config(self):
        """打印当前配置"""
        print(f"=== {self.config.system.name} v{self.config.system.version} ===")
        print(f"\n工作模式: {self.config.pipeline_description}")
        print(f"\n音频配置:")
        print(f"  采样率: {self.config.audio.sample_rate} Hz")
        print(f"  声道数: {self.config.audio.channels}")
        print(f"  块大小: {self.config.audio.chunk_size}")
        print(f"\n模块状态:")
        print(f"  唤醒词: {'✅ 启用' if self.config.is_wakeword_enabled else '❌ 禁用'}")
        print(f"  VAD:   {'✅ 启用' if self.config.is_vad_enabled else '❌ 禁用'}")
        print(f"  ASR:   {'✅ 启用' if self.config.is_asr_enabled else '❌ 禁用'}")


# 全局配置实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager


def get_config() -> Config:
    """获取配置对象"""
    return get_config_manager().config
