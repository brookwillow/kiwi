"""
系统控制器测试

测试SystemController的核心功能
"""
import time
from src.core import (
    SystemController, Event, EventType,
    IModule
)


class DummyModule(IModule):
    """测试用虚拟模块"""
    
    def __init__(self, name: str):
        self._name = name
        self._initialized = False
        self._running = False
        self._events_received = []
    
    @property
    def name(self) -> str:
        return self._name
    
    def initialize(self) -> bool:
        print(f"  [{self._name}] initialize()")
        self._initialized = True
        return True
    
    def start(self) -> bool:
        print(f"  [{self._name}] start()")
        self._running = True
        return True
    
    def stop(self):
        print(f"  [{self._name}] stop()")
        self._running = False
    
    def cleanup(self):
        print(f"  [{self._name}] cleanup()")
        self._initialized = False
    
    def handle_event(self, event: Event):
        # 记录接收到的事件（过滤音频帧）
        if event.type != EventType.AUDIO_FRAME_READY:
            self._events_received.append(event)
            print(f"  [{self._name}] 接收事件: {event.type.value}")
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def get_events_count(self) -> int:
        return len(self._events_received)


def test_module_registration():
    """测试模块注册"""
    print("\n" + "="*60)
    print("测试1: 模块注册")
    print("="*60)
    
    controller = SystemController(debug=False)
    
    # 注册模块
    module1 = DummyModule("module1")
    module2 = DummyModule("module2")
    
    controller.register_module(module1)
    controller.register_module(module2)
    
    # 验证
    modules = controller.list_modules()
    assert len(modules) == 2
    assert "module1" in modules
    assert "module2" in modules
    
    print("✅ 模块注册测试通过")


def test_lifecycle():
    """测试生命周期管理"""
    print("\n" + "="*60)
    print("测试2: 生命周期管理")
    print("="*60)
    
    controller = SystemController(debug=True)
    
    module1 = DummyModule("audio")
    module2 = DummyModule("vad")
    
    controller.register_module(module1)
    controller.register_module(module2)
    
    # 初始化
    print("\n>>> 初始化所有模块")
    success = controller.initialize_all()
    assert success
    assert module1._initialized
    assert module2._initialized
    
    # 启动
    print("\n>>> 启动所有模块")
    success = controller.start_all()
    assert success
    assert module1.is_running
    assert module2.is_running
    assert controller.is_running
    
    # 停止
    print("\n>>> 停止所有模块")
    controller.stop_all()
    assert not module1.is_running
    assert not module2.is_running
    assert not controller.is_running
    
    print("\n✅ 生命周期管理测试通过")


def test_event_system():
    """测试事件系统"""
    print("\n" + "="*60)
    print("测试3: 事件系统")
    print("="*60)
    
    controller = SystemController(debug=True)
    
    module1 = DummyModule("sender")
    module2 = DummyModule("receiver")
    
    controller.register_module(module1)
    controller.register_module(module2)
    
    # 发布事件
    print("\n>>> 发布测试事件")
    event = Event.create(EventType.WAKEWORD_DETECTED, "sender", data={'keyword': 'kiwi'})
    controller.publish_event(event)
    
    # 验证接收
    time.sleep(0.1)
    assert module2.get_events_count() > 0
    
    print(f"module2 接收到 {module2.get_events_count()} 个事件")
    print("\n✅ 事件系统测试通过")


def test_event_subscription():
    """测试事件订阅"""
    print("\n" + "="*60)
    print("测试4: 事件订阅")
    print("="*60)
    
    controller = SystemController(debug=True)
    
    callback_count = [0]  # 使用列表以便在闭包中修改
    
    def on_wakeword(event):
        callback_count[0] += 1
        print(f"  回调函数被触发: {event.type.value}")
    
    # 订阅事件
    print("\n>>> 订阅 WAKEWORD_DETECTED 事件")
    controller.subscribe(EventType.WAKEWORD_DETECTED, on_wakeword)
    
    # 发布事件
    print("\n>>> 发布事件")
    event = Event.create(EventType.WAKEWORD_DETECTED, "test")
    controller.publish_event(event)
    
    time.sleep(0.1)
    
    assert callback_count[0] == 1
    print(f"\n回调函数被调用 {callback_count[0]} 次")
    print("✅ 事件订阅测试通过")


def test_statistics():
    """测试统计信息"""
    print("\n" + "="*60)
    print("测试5: 统计信息")
    print("="*60)
    
    controller = SystemController(debug=False)
    
    module = DummyModule("test")
    controller.register_module(module)
    controller.initialize_all()
    controller.start_all()
    
    # 发布一些事件
    for i in range(5):
        event = Event.create(EventType.SYSTEM_START, "test")
        controller.publish_event(event)
    
    # 获取统计
    stats = controller.get_statistics()
    
    print(f"\n统计信息:")
    print(f"  运行状态: {stats['running']}")
    print(f"  模块数量: {stats['modules_count']}")
    print(f"  处理事件: {stats['events_processed']}")
    print(f"  当前状态: {stats['current_state']}")
    
    assert stats['running'] == True
    assert stats['modules_count'] == 1
    assert stats['events_processed'] >= 5
    
    controller.print_status()
    
    controller.stop_all()
    
    print("✅ 统计信息测试通过")


def test_state_integration():
    """测试状态机集成"""
    print("\n" + "="*60)
    print("测试6: 状态机集成")
    print("="*60)
    
    from src.state_machine import StateConfig, StateEvent
    
    controller = SystemController(debug=True)
    
    # 初始化（会创建状态机）
    config = StateConfig(enable_wakeword=True, debug=True)
    controller.initialize_all(config)
    
    # 获取状态机
    state_manager = controller.get_state_manager()
    assert state_manager is not None
    
    # 获取初始状态
    state = controller.get_current_state()
    print(f"\n初始状态: {state.value}")
    
    # 触发状态事件
    print("\n>>> 触发唤醒事件")
    controller.handle_state_event(StateEvent.WAKEWORD_TRIGGERED)
    
    # 检查状态变化
    new_state = controller.get_current_state()
    print(f"新状态: {new_state.value}")
    
    assert new_state.value == "wakeword"
    
    print("\n✅ 状态机集成测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🧪" + "="*58 + "🧪")
    print("  系统控制器测试")
    print("🧪" + "="*58 + "🧪")
    
    tests = [
        ("模块注册", test_module_registration),
        ("生命周期管理", test_lifecycle),
        ("事件系统", test_event_system),
        ("事件订阅", test_event_subscription),
        ("统计信息", test_statistics),
        ("状态机集成", test_state_integration),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ 测试失败: {name}")
            print(f"   错误: {e}")
            failed += 1
        except Exception as e:
            print(f"\n💥 测试异常: {name}")
            print(f"   异常: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # 测试总结
    print("\n" + "="*60)
    print(f"  测试总结")
    print("="*60)
    print(f"✅ 通过: {passed}/{len(tests)}")
    print(f"❌ 失败: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 所有测试通过！SystemController 工作正常。\n")
    else:
        print(f"\n⚠️ 有 {failed} 个测试失败，请检查。\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
