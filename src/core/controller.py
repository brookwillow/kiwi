"""
系统控制器 - 中央总线

负责管理所有模块的生命周期、事件分发和状态协调
采用中介者模式，模块间不直接通信，所有通信通过控制器进行
"""
from typing import Dict, List, Callable, Optional, Any
from collections import defaultdict, deque
import threading
import time

from .interfaces import IModule
from .events import Event, EventType
from ..state_machine import VoiceStateManager, StateConfig, StateEvent, VoiceState


class SystemController:
    """
    系统总控制器 - 中央总线
    
    职责：
    1. 管理所有模块的生命周期（初始化、启动、停止、清理）
    2. 作为模块间通信的中介（事件分发）
    3. 协调状态机和各模块的工作流
    4. 处理超时和异常情况
    5. 统一日志和监控
    
    设计原则：
    - 模块间不直接调用，通过事件通信
    - 控制器负责所有模块的协调
    - 状态机独立管理状态转换逻辑
    - GUI只负责展示，不包含业务逻辑
    """
    
    def __init__(self, debug: bool = False):
        """
        初始化系统控制器
        
        Args:
            debug: 是否开启调试模式
        """
        self.debug = debug
        
        # 模块注册表
        self._modules: Dict[str, IModule] = {}
        
        # 事件订阅表 {EventType: [callback1, callback2, ...]}
        self._event_subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        
        # 事件队列
        self._event_queue: deque = deque(maxlen=1000)
        
        # 状态机
        self._state_manager: Optional[VoiceStateManager] = None
        
        # 运行状态
        self._running = False
        self._lock = threading.RLock()
        
        # 统计信息
        self._stats = {
            'events_processed': 0,
            'events_dropped': 0,
            'errors': 0,
            'start_time': 0
        }
        
        if self.debug:
            print("🚀 SystemController 初始化完成")
    
    # ==================== 模块管理 ====================
    
    def register_module(self, module: IModule):
        """
        注册模块
        
        Args:
            module: 实现IModule接口的模块
        """
        with self._lock:
            module_name = module.name
            if module_name in self._modules:
                raise ValueError(f"模块 '{module_name}' 已经注册")
            
            self._modules[module_name] = module
            
            if self.debug:
                print(f"📦 注册模块: {module_name}")
    
    def unregister_module(self, module_name: str):
        """
        注销模块
        
        Args:
            module_name: 模块名称
        """
        with self._lock:
            if module_name in self._modules:
                module = self._modules[module_name]
                if module.is_running:
                    module.stop()
                module.cleanup()
                del self._modules[module_name]
                
                if self.debug:
                    print(f"📤 注销模块: {module_name}")
    
    def get_module(self, module_name: str) -> Optional[IModule]:
        """获取模块"""
        return self._modules.get(module_name)
    
    def list_modules(self) -> List[str]:
        """列出所有已注册的模块"""
        return list(self._modules.keys())
    
    # ==================== 生命周期管理 ====================
    
    def initialize_all(self, state_config: Optional[StateConfig] = None) -> bool:
        """
        初始化所有模块
        
        Args:
            state_config: 状态机配置
            
        Returns:
            是否全部初始化成功
        """
        if self.debug:
            print("\n" + "="*60)
            print("🔧 开始初始化所有模块")
            print("="*60)
        
        # 初始化状态机
        if state_config is None:
            state_config = StateConfig(
                enable_wakeword=True,
                wakeword_timeout=10.0,
                max_vad_end_count=3,
                debug=self.debug
            )
        
        self._state_manager = VoiceStateManager(state_config)
        if self.debug:
            print("✅ 状态机初始化成功")
        
        # 初始化所有模块
        success = True
        for name, module in self._modules.items():
            try:
                if self.debug:
                    print(f"\n初始化模块: {name}")
                
                if not module.initialize():
                    print(f"❌ 模块 '{name}' 初始化失败")
                    success = False
                else:
                    if self.debug:
                        print(f"✅ 模块 '{name}' 初始化成功")
            except Exception as e:
                print(f"❌ 模块 '{name}' 初始化异常: {e}")
                import traceback
                traceback.print_exc()
                success = False
        
        if self.debug:
            print("\n" + "="*60)
            if success:
                print("🎉 所有模块初始化完成")
            else:
                print("⚠️ 部分模块初始化失败")
            print("="*60 + "\n")
        
        return success
    
    def start_all(self) -> bool:
        """
        启动所有模块
        
        Returns:
            是否全部启动成功
        """
        if self._running:
            print("⚠️ 系统已在运行")
            return False
        
        if self.debug:
            print("\n" + "="*60)
            print("▶️  启动所有模块")
            print("="*60)
        
        # 启动所有模块
        success = True
        for name, module in self._modules.items():
            try:
                if self.debug:
                    print(f"启动模块: {name}")
                
                if not module.start():
                    print(f"❌ 模块 '{name}' 启动失败")
                    success = False
                else:
                    if self.debug:
                        print(f"✅ 模块 '{name}' 启动成功")
            except Exception as e:
                print(f"❌ 模块 '{name}' 启动异常: {e}")
                success = False
        
        if success:
            self._running = True
            self._stats['start_time'] = time.time()
            
            # 发布系统启动事件
            self.publish_event(Event.create(EventType.SYSTEM_START, "system"))
            
            if self.debug:
                print("\n" + "="*60)
                print("✅ 系统启动成功")
                print("="*60 + "\n")
        
        return success
    
    def stop_all(self):
        """停止所有模块"""
        if not self._running:
            return
        
        if self.debug:
            print("\n" + "="*60)
            print("⏹️  停止所有模块")
            print("="*60)
        
        # 发布系统停止事件
        self.publish_event(Event.create(EventType.SYSTEM_STOP, "system"))
        
        # 停止所有模块（逆序）
        for name in reversed(list(self._modules.keys())):
            module = self._modules[name]
            try:
                if self.debug:
                    print(f"停止模块: {name}")
                module.stop()
            except Exception as e:
                print(f"⚠️ 模块 '{name}' 停止异常: {e}")
        
        self._running = False
        
        if self.debug:
            print("\n" + "="*60)
            print("✅ 系统已停止")
            print("="*60 + "\n")
    
    def cleanup_all(self):
        """清理所有模块"""
        if self.debug:
            print("🧹 清理所有模块")
        
        for name in reversed(list(self._modules.keys())):
            module = self._modules[name]
            try:
                module.cleanup()
            except Exception as e:
                print(f"⚠️ 模块 '{name}' 清理异常: {e}")
        
        self._modules.clear()
        self._event_subscribers.clear()
        self._event_queue.clear()
    
    # ==================== 事件系统 ====================
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """
        订阅事件
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        with self._lock:
            # 避免重复订阅
            if callback not in self._event_subscribers[event_type]:
                self._event_subscribers[event_type].append(callback)
                
                if self.debug:
                    print(f"📥 订阅事件: {event_type.value}")
            else:
                if self.debug:
                    print(f"⚠️ 重复订阅事件已忽略: {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]):
        """
        取消订阅
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        with self._lock:
            if event_type in self._event_subscribers:
                if callback in self._event_subscribers[event_type]:
                    self._event_subscribers[event_type].remove(callback)
    
    def publish_event(self, event: Event):
        """
        发布事件
        
        Args:
            event: 事件对象
        """
        with self._lock:
            # 记录事件
            self._event_queue.append(event)
            self._stats['events_processed'] += 1
            
            if self.debug and event.type != EventType.AUDIO_FRAME_READY:
                # 音频帧事件太频繁，不打印
                print(f"📡 事件发布: {event}")
        
        # 通知订阅者
        subscribers = self._event_subscribers.get(event.type, [])
        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                print(f"⚠️ 事件处理异常 [{event.type.value}]: {e}")
                self._stats['errors'] += 1
        
        # 分发到各模块
        for module in self._modules.values():
            try:
                module.handle_event(event)
            except Exception as e:
                if self.debug:
                    print(f"⚠️ 模块 '{module.name}' 处理事件异常: {e}")
    
    # ==================== 状态管理 ====================
    
    def get_state_manager(self) -> Optional[VoiceStateManager]:
        """获取状态机管理器"""
        return self._state_manager
    
    def get_current_state(self) -> Optional[VoiceState]:
        """获取当前状态"""
        if self._state_manager:
            info = self._state_manager.get_state_info()
            return info.current_state
        return None
    
    def handle_state_event(self, state_event: StateEvent, metadata: Optional[dict] = None):
        """
        处理状态事件
        
        Args:
            state_event: 状态事件
            metadata: 事件元数据
        """
        if not self._state_manager:
            return
        
        result = self._state_manager.handle_event(state_event, metadata)
        
        if result.success:
            # 发布状态变化事件
            from .events import StateChangeEvent
            event = StateChangeEvent(
                source="state_machine",
                from_state=result.previous_state.value,
                to_state=result.current_state.value,
                reason=result.message
            )
            self.publish_event(event)
            
            # 根据状态变化结果执行操作
            if result.should_reset_wakeword:
                # 通知唤醒词模块重置
                self.publish_event(Event.create(EventType.WAKEWORD_RESET, "system"))
            
            if result.should_trigger_asr:
                # 触发ASR识别的标志，具体由VAD模块传递音频数据
                pass
    
    def check_timeout(self):
        """检查状态超时"""
        if self._state_manager:
            result = self._state_manager.check_timeout()
            if result:
                # 发布超时事件
                self.publish_event(Event.create(EventType.WAKEWORD_TIMEOUT, "system"))
    
    # ==================== 统计信息 ====================
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        uptime = time.time() - self._stats['start_time'] if self._running else 0
        
        return {
            'running': self._running,
            'uptime_seconds': uptime,
            'modules_count': len(self._modules),
            'modules': list(self._modules.keys()),
            'events_processed': self._stats['events_processed'],
            'events_dropped': self._stats['events_dropped'],
            'errors': self._stats['errors'],
            'event_queue_size': len(self._event_queue),
            'current_state': self.get_current_state().value if self.get_current_state() else "unknown"
        }
    
    def print_status(self):
        """打印系统状态"""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("📊 系统状态")
        print("="*60)
        print(f"运行状态: {'🟢 运行中' if stats['running'] else '🔴 已停止'}")
        print(f"运行时间: {stats['uptime_seconds']:.1f}秒")
        print(f"当前状态: {stats['current_state']}")
        print(f"模块数量: {stats['modules_count']}")
        print(f"已注册模块: {', '.join(stats['modules'])}")
        print(f"处理事件: {stats['events_processed']}")
        print(f"事件队列: {stats['event_queue_size']}")
        print(f"错误次数: {stats['errors']}")
        print("="*60 + "\n")
    
    # ==================== 工作流协调 ====================
    
    def on_audio_frame(self, frame_data: Any, sample_rate: int):
        """
        处理音频帧（由音频模块调用）
        
        Args:
            frame_data: 音频数据
            sample_rate: 采样率
        """
        from .events import AudioFrameEvent
        
        # 发布音频帧事件
        event = AudioFrameEvent("audio", frame_data, sample_rate)
        self.publish_event(event)
        
        # 定期检查超时
        if self._stats['events_processed'] % 10 == 0:  # 每10帧检查一次
            self.check_timeout()
    
    @property
    def is_running(self) -> bool:
        """系统是否正在运行"""
        return self._running
