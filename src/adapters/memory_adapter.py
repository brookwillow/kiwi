from src.core.interfaces import IMemoryModule
from src.core.events import Event, EventType, LongTermMemory
from src.memory.memory import MemoryManager
from src.config_manager import get_config

class MemoryModuleAdapter(IMemoryModule):

    """Memory模块适配器"""
    
    def __init__(self, controller, api_key: str = None):
        """初始化Memory模块适配器
        
        Args:
            controller: 系统控制器
            api_key: 阿里百炼API密钥，用于生成长期记忆
        """
        self._name = "memory"
        self._controller = controller
        
        # 从配置文件读取长期记忆生成参数
        config = get_config()
        memory_settings = config.memory.settings
        long_term_config = memory_settings.get('long_term_generation', {})
        trigger_count = long_term_config.get('trigger_count', 10)
        max_history_rounds = long_term_config.get('max_history_rounds', 30)
        
        self._memory_manager = MemoryManager(
            api_key=api_key,
            trigger_count=trigger_count,
            max_history_rounds=max_history_rounds
        )
        self._running = False
        
        print(f"✅ [memory] 配置: 每{trigger_count}条对话触发长期记忆生成，最多使用{max_history_rounds}轮历史")


    """IMemoryModule 接口实现"""
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def initialize(self) -> bool:
        """初始化Memory模块"""
        print("✅ [memory] 初始化成功")
        return True
    
    def start(self) -> bool:
        """启动Memory模块"""
        self._running = True
        print("✅ [memory] 已启动")
        return True
    
    def stop(self):
        """停止Memory模块"""
        self._running = False
        print("✅ [memory] 已停止")

    def cleanup(self):
        """清理资源"""
        print("✅ [memory] 资源已清理")

    
    def handle_event(self, event):
        if not self._running or not self._memory_manager:
            return
        
        # Agent响应事件
        if event.type == EventType.GUI_UPDATE_TEXT:
            import threading
            # self._handle_asr_result(event)
            #thread = threading.Thread(target=self._handle_asr_result(event), daemon=True)
            thread = threading.Thread(target=self.add_short_term_memory, args=(event,), daemon=True)
            thread.start()
    
    def add_short_term_memory(self, event):
        """根据事件添加短期记忆条目"""
        print(f"✅ [memory] 处理事件: {event.type.value}")

        update_type = event.data.get('type', '')
        
        if update_type == 'agent_response':
            # 构建记忆数据字典
            memory_data = {
                'agent': event.data.get('agent', ''),
                'query': event.data.get('query', ''),
                'response': event.data.get('message', ''),
                'timestamp': event.timestamp,
                'success': event.data.get('success', False),
                'tools_used': event.data.get('tools_used', []),
                'data': event.data.get('data', {})
            }
            self._memory_manager.add_short_term_memory(memory_data)
          

    def get_short_term_memories(self, limit: int = 5) -> list:
        """获取最近的短期记忆条目（按时间顺序）"""
        return self._memory_manager.get_short_term_memories(max_count=limit)
    
    def get_related_short_term_memory(self, query: str, limit: int = 2) -> list:
        """获取与查询相关的短期记忆条目（基于向量相似度）"""
        return self._memory_manager.get_related_short_memories(query=query, max_count=limit)
    
    def get_related_long_term_memory(self, query: str = "") -> LongTermMemory:
        """获取相关的长期记忆（返回原始dict）"""
        return self._memory_manager.get_long_term_memory(return_raw=False)
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        return self._memory_manager.get_statistics()
    
    def generate_long_term_memory(self):
        """从短期记忆中生成长期记忆"""
        self._memory_manager._generate_long_term_memory()