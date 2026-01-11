"""
LLM配置管理

负责加载和解析配置文件
"""
import os
import yaml
import re
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

from .utils.errors import LLMConfigError


@dataclass
class ModelConfig:
    """模型配置"""
    name: str                    # 模型标识名（如 qwen-plus）
    provider: str                # 所属Provider（dashscope/ollama）
    model_name: str              # 实际模型名（传给Provider的名称）
    description: str = ""        # 模型描述
    model_type: str = "chat"     # 模型类型（chat/embedding）


@dataclass
class ProviderConfig:
    """Provider配置"""
    name: str
    config: Dict[str, Any]


@dataclass
class LLMConfig:
    """LLM完整配置"""
    models: Dict[str, ModelConfig]           # 所有可用模型
    scenarios: Dict[str, str]                # 场景到模型的映射
    providers: Dict[str, ProviderConfig]     # Provider配置
    fallback_enabled: bool                   # 是否启用降级
    model_fallback: Dict[str, str]           # 模型级别的降级映射
    logging_level: str
    log_requests: bool
    log_responses: bool


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为 config/llm_config.yaml
        """
        if config_path is None:
            # 默认配置文件路径
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "llm_config.yaml"
        
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self) -> LLMConfig:
        """加载配置文件"""
        if not self.config_path.exists():
            raise LLMConfigError(f"配置文件不存在: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
            
            if not raw_config or 'llm' not in raw_config:
                raise LLMConfigError("配置文件格式错误: 缺少'llm'节点")
            
            llm_config = raw_config['llm']
            
            # 解析模型配置
            models = {}
            for model_name, model_conf in llm_config.get('models', {}).items():
                resolved_conf = self._resolve_env_vars(model_conf)
                models[model_name] = ModelConfig(
                    name=model_name,
                    provider=resolved_conf.get('provider'),
                    model_name=resolved_conf.get('model_name'),
                    description=resolved_conf.get('description', ''),
                    model_type=resolved_conf.get('type', 'chat')
                )
            
            # 解析场景配置
            scenarios = llm_config.get('scenarios', {})
            
            # 解析provider配置
            providers = {}
            for provider_name, provider_config in llm_config.get('providers', {}).items():
                resolved_config = self._resolve_env_vars(provider_config)
                providers[provider_name] = ProviderConfig(
                    name=provider_name,
                    config=resolved_config
                )
            
            # 构建配置对象
            fallback = llm_config.get('fallback', {})
            logging = llm_config.get('logging', {})
            
            return LLMConfig(
                models=models,
                scenarios=scenarios,
                providers=providers,
                fallback_enabled=fallback.get('enabled', True),
                model_fallback=fallback.get('model_fallback', {}),
                logging_level=logging.get('level', 'INFO'),
                log_requests=logging.get('log_requests', False),
                log_responses=logging.get('log_responses', False)
            )
            
        except yaml.YAMLError as e:
            raise LLMConfigError(f"配置文件解析失败: {e}")
        except Exception as e:
            raise LLMConfigError(f"加载配置文件失败: {e}")
    
    def _resolve_env_vars(self, config: Any) -> Any:
        """
        递归解析配置中的环境变量
        
        支持格式:
        - ${VAR_NAME} - 必须存在的环境变量
        - ${VAR_NAME:default} - 带默认值的环境变量
        """
        if isinstance(config, dict):
            return {k: self._resolve_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._resolve_env_vars(item) for item in config]
        elif isinstance(config, str):
            # 查找环境变量模式
            pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
            
            def replace_env_var(match):
                var_name = match.group(1)
                default_value = match.group(2)
                
                env_value = os.getenv(var_name)
                
                if env_value is not None:
                    return env_value
                elif default_value is not None:
                    return default_value
                else:
                    # 环境变量不存在且没有默认值
                    return ""  # 返回空字符串，由Provider判断是否可用
            
            return re.sub(pattern, replace_env_var, config)
        else:
            return config
    
    def get_config(self) -> LLMConfig:
        """获取配置对象"""
        return self._config
    
    def get_provider_config(self, provider_name: str) -> Optional[ProviderConfig]:
        """获取指定Provider的配置"""
        return self._config.providers.get(provider_name)
    
    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """获取指定模型的配置"""
        return self._config.models.get(model_name)
    
    def get_scenario_model(self, scenario: str) -> str:
        """获取场景对应的模型名"""
        return self._config.scenarios.get(scenario, self._config.scenarios.get('default', 'qwen-plus'))
    
    def get_model_fallback(self, model_name: str) -> Optional[str]:
        """获取模型的降级目标"""
        return self._config.model_fallback.get(model_name)
    
    def reload(self):
        """重新加载配置"""
        self._config = self._load_config()
    
    # 便捷属性访问
    @property
    def models(self) -> Dict[str, ModelConfig]:
        """获取所有模型配置"""
        return self._config.models
    
    @property
    def scenarios(self) -> Dict[str, str]:
        """获取所有场景配置"""
        return self._config.scenarios
    
    @property
    def providers(self) -> Dict[str, ProviderConfig]:
        """获取所有Provider配置"""
        return self._config.providers
    
    @property
    def fallback(self) -> Dict[str, Any]:
        """获取降级配置"""
        return {
            "enabled": self._config.fallback_enabled,
            "model_fallback": self._config.model_fallback
        }
