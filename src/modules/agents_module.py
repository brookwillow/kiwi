"""
Agents 模块 - 管理所有可用的Agent
从配置文件加载Agent信息
"""
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.core.interfaces import IModule
from src.core.events import Event, EventType


class AgentsModule(IModule):
    """Agents模块 - 提供可用Agent列表"""
    
    def __init__(self, config_path: str = "config/agents_config.yaml"):
        """
        初始化Agents模块
        
        Args:
            config_path: Agent配置文件路径
        """
        self._name = "agents"
        self._running = False
        self._agents: List[Dict[str, Any]] = []
        self._config_path = config_path
        
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def initialize(self) -> bool:
        """初始化 - 从配置文件加载Agents"""
        try:
            config_file = Path(self._config_path)
            if not config_file.exists():
                print(f"❌ Agent配置文件不存在: {self._config_path}")
                return False
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self._agents = config.get('agents', [])
            print(f"✅ Agents模块初始化: 加载了 {len(self._agents)} 个Agent")
            
            for agent in self._agents:
                status = "✓" if agent.get('enabled', True) else "✗"
                print(f"   {status} {agent['name']}: {agent['description']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Agents模块初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start(self) -> bool:
        """启动模块"""
        self._running = True
        print("✅ Agents模块启动成功")
        return True
    
    def stop(self):
        """停止模块"""
        self._running = False
        print("🛑 Agents模块已停止")
    
    def cleanup(self):
        """清理资源"""
        self._agents.clear()
    
    def handle_event(self, event: Event):
        """处理事件（Agents模块不需要处理事件）"""
        pass
    
    # ==================== Agents数据访问接口 ====================
    
    def get_available_agents(self) -> List[Dict[str, Any]]:
        """
        获取所有可用（已启用）的Agent列表
        
        Returns:
            Agent列表，每个Agent包含：name, description, capabilities, enabled
        """
        return [agent for agent in self._agents if agent.get('enabled', True)]
    
    def get_all_agents(self) -> List[Dict[str, Any]]:
        """获取所有Agent（包括未启用的）"""
        return self._agents.copy()
    
    def get_agent_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取Agent信息"""
        for agent in self._agents:
            if agent.get('name') == name:
                return agent.copy()
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        enabled_count = sum(1 for a in self._agents if a.get('enabled', True))
        return {
            'total_agents': len(self._agents),
            'enabled_agents': enabled_count,
            'disabled_agents': len(self._agents) - enabled_count,
            'agent_count': enabled_count  # 兼容orchestrator的调用
        }
