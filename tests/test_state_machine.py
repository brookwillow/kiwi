"""
状态机模块测试

测试语音处理状态机的状态转换逻辑
"""
import time
from src.state_machine import (
    VoiceStateManager, VoiceState, StateEvent,
    StateConfig, StateChangeResult
)


def print_section(title: str):
    """打印测试章节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def test_basic_state_transitions():
    """测试基本状态转换"""
    print_section("1. 基本状态转换测试")
    
    # 创建状态机（启用唤醒词）
    config = StateConfig(
        enable_wakeword=True,
        wakeword_timeout=10.0,
        max_vad_end_count=3,
        debug=True
    )
    manager = VoiceStateManager(config)
    
    # 初始状态应该是IDLE
    info = manager.get_state_info()
    assert info.current_state == VoiceState.IDLE, "初始状态应为IDLE"
    assert not info.is_wakeword_detected, "初始未检测到唤醒词"
    print(f"✅ 初始状态: {info.current_state.value}")
    
    # 触发唤醒词
    result = manager.handle_event(StateEvent.WAKEWORD_TRIGGERED)
    assert result.success, "唤醒词触发应成功"
    assert result.current_state == VoiceState.WAKEWORD_DETECTED, "应转换到WAKEWORD_DETECTED"
    print(f"✅ 唤醒词触发成功: {result.message}")
    
    # 检查唤醒状态
    info = manager.get_state_info()
    assert info.is_wakeword_detected, "应检测到唤醒词"
    print(f"✅ 当前状态: {info.current_state.value}, 已唤醒: {info.is_wakeword_detected}")
    
    print("\n✅ 基本状态转换测试通过")


def test_vad_flow_with_wakeword():
    """测试带唤醒词的VAD流程"""
    print_section("2. 带唤醒词的VAD流程测试")
    
    config = StateConfig(
        enable_wakeword=True,
        wakeword_timeout=10.0,
        max_vad_end_count=3,
        debug=True
    )
    manager = VoiceStateManager(config)
    
    # 1. 触发唤醒词
    result = manager.handle_event(StateEvent.WAKEWORD_TRIGGERED)
    print(f"步骤1: {result.message}")
    
    # 2. 语音开始
    result = manager.handle_event(StateEvent.SPEECH_START)
    assert result.success, "语音开始应成功"
    assert result.current_state == VoiceState.SPEECH_DETECTED
    print(f"步骤2: {result.message}")
    
    # 3. 第一次语音结束
    result = manager.handle_event(StateEvent.SPEECH_END)
    assert result.success, "语音结束应成功"
    assert result.should_start_timeout, "第一次VAD END应启动超时计时"
    assert result.should_trigger_asr, "应触发ASR识别"
    info = manager.get_state_info()
    assert info.vad_end_count == 1, "VAD END计数应为1"
    assert info.is_timeout_active(), "超时计时器应已启动"
    print(f"步骤3: {result.message}, 超时: {info.is_timeout_active()}")
    
    # 4. 第二次语音开始
    result = manager.handle_event(StateEvent.SPEECH_START)
    print(f"步骤4: {result.message}")
    
    # 5. 第二次语音结束
    result = manager.handle_event(StateEvent.SPEECH_END)
    info = manager.get_state_info()
    assert info.vad_end_count == 2, "VAD END计数应为2"
    print(f"步骤5: {result.message}, 计数: {info.vad_end_count}")
    
    # 6. 第三次语音结束（达到最大次数）
    result = manager.handle_event(StateEvent.SPEECH_END)
    assert result.should_reset_wakeword, "应重置唤醒词"
    info = manager.get_state_info()
    assert info.current_state == VoiceState.IDLE, "应返回IDLE"
    assert not info.is_wakeword_detected, "唤醒状态应被重置"
    assert info.vad_end_count == 0, "计数应重置为0"
    print(f"步骤6: {result.message}")
    
    print("\n✅ 带唤醒词的VAD流程测试通过")


def test_timeout_handling():
    """测试超时处理"""
    print_section("3. 超时处理测试")
    
    config = StateConfig(
        enable_wakeword=True,
        wakeword_timeout=2.0,  # 2秒超时（测试用）
        max_vad_end_count=3,
        debug=True
    )
    manager = VoiceStateManager(config)
    
    # 1. 触发唤醒词
    manager.handle_event(StateEvent.WAKEWORD_TRIGGERED)
    print("步骤1: 触发唤醒词")
    
    # 2. 语音结束（启动超时计时）
    manager.handle_event(StateEvent.SPEECH_START)
    result = manager.handle_event(StateEvent.SPEECH_END)
    assert result.should_start_timeout, "应启动超时计时"
    
    info = manager.get_state_info()
    print(f"步骤2: 超时计时已启动，剩余时间: {info.get_remaining_time():.1f}秒")
    
    # 3. 等待超时
    print("步骤3: 等待2秒...")
    time.sleep(2.1)
    
    # 4. 检查超时
    result = manager.check_timeout()
    assert result is not None, "应检测到超时"
    assert result.success, "超时处理应成功"
    assert result.current_state == VoiceState.IDLE, "应返回IDLE"
    
    info = manager.get_state_info()
    assert not info.is_wakeword_detected, "唤醒状态应被重置"
    print(f"步骤4: {result.message}")
    
    print("\n✅ 超时处理测试通过")


def test_without_wakeword():
    """测试不启用唤醒词的流程"""
    print_section("4. 无唤醒词模式测试")
    
    config = StateConfig(
        enable_wakeword=False,  # 不启用唤醒词
        enable_vad=True,
        enable_asr=True,
        debug=True
    )
    manager = VoiceStateManager(config)
    
    # 1. 直接语音开始（无需唤醒词）
    result = manager.handle_event(StateEvent.SPEECH_START)
    assert result.success, "无唤醒词模式下语音开始应成功"
    print(f"步骤1: {result.message}")
    
    # 2. 语音结束
    result = manager.handle_event(StateEvent.SPEECH_END)
    assert result.success, "语音结束应成功"
    assert result.should_trigger_asr, "应触发ASR识别"
    assert not result.should_start_timeout, "无唤醒词模式不应启动超时"
    print(f"步骤2: {result.message}")
    
    # 3. 识别成功后应返回IDLE
    result = manager.handle_event(StateEvent.RECOGNITION_SUCCESS, {'text': '你好'})
    info = manager.get_state_info()
    assert info.current_state == VoiceState.IDLE, "识别完成应返回IDLE"
    print(f"步骤3: {result.message}")
    
    print("\n✅ 无唤醒词模式测试通过")


def test_state_callbacks():
    """测试状态变化回调"""
    print_section("5. 状态变化回调测试")
    
    callback_count = [0]  # 使用列表来在闭包中修改
    
    def state_callback(result: StateChangeResult):
        callback_count[0] += 1
        print(f"   📢 回调触发 #{callback_count[0]}: {result.event.value} -> {result.current_state.value}")
    
    config = StateConfig(enable_wakeword=True, debug=False)
    manager = VoiceStateManager(config)
    manager.register_callback(state_callback)
    
    # 触发几个事件
    manager.handle_event(StateEvent.WAKEWORD_TRIGGERED)
    manager.handle_event(StateEvent.SPEECH_START)
    manager.handle_event(StateEvent.SPEECH_END)
    
    assert callback_count[0] == 3, f"应触发3次回调，实际: {callback_count[0]}"
    print(f"\n✅ 状态变化回调测试通过，共触发 {callback_count[0]} 次")


def test_transition_history():
    """测试状态转换历史"""
    print_section("6. 状态转换历史测试")
    
    config = StateConfig(enable_wakeword=True, debug=False)
    manager = VoiceStateManager(config)
    
    # 执行一系列状态转换
    manager.handle_event(StateEvent.WAKEWORD_TRIGGERED)  # idle -> wakeword
    manager.handle_event(StateEvent.SPEECH_START)        # wakeword -> speech
    manager.handle_event(StateEvent.SPEECH_END)          # speech -> speech (第一次END，不改变状态)
    manager.handle_event(StateEvent.RECOGNITION_START)   # speech -> recognizing
    manager.handle_event(StateEvent.RESET)               # recognizing -> idle
    
    # 获取转换历史（只有状态改变才记录）
    history = manager.get_transition_history(limit=10)
    # 实际转换：idle->wakeword, wakeword->speech, speech->recognizing, recognizing->idle = 4次
    assert len(history) == 4, f"应有4条转换记录，实际: {len(history)}"
    
    print("转换历史:")
    for i, transition in enumerate(history, 1):
        print(f"  {i}. {transition.from_state.value} -> {transition.to_state.value} "
              f"[{transition.event.value}]")
    
    print("\n✅ 状态转换历史测试通过")


def test_reset_and_force_idle():
    """测试重置和强制空闲"""
    print_section("7. 重置和强制空闲测试")
    
    config = StateConfig(enable_wakeword=True, debug=True)
    manager = VoiceStateManager(config)
    
    # 1. 进入复杂状态
    manager.handle_event(StateEvent.WAKEWORD_TRIGGERED)
    manager.handle_event(StateEvent.SPEECH_START)
    info = manager.get_state_info()
    print(f"当前状态: {info.current_state.value}, 已唤醒: {info.is_wakeword_detected}")
    
    # 2. 强制空闲
    result = manager.handle_event(StateEvent.FORCE_IDLE)
    assert result.success, "强制空闲应成功"
    info = manager.get_state_info()
    assert info.current_state == VoiceState.IDLE, "应返回IDLE"
    assert not info.is_wakeword_detected, "唤醒状态应清除"
    print(f"强制空闲后: {info.current_state.value}")
    
    # 3. 再次进入状态
    manager.handle_event(StateEvent.WAKEWORD_TRIGGERED)
    manager.handle_event(StateEvent.SPEECH_START)
    
    # 4. 重置
    result = manager.handle_event(StateEvent.RESET)
    assert result.success, "重置应成功"
    info = manager.get_state_info()
    assert info.current_state == VoiceState.IDLE, "应返回IDLE"
    print(f"重置后: {info.current_state.value}")
    
    print("\n✅ 重置和强制空闲测试通过")


def test_asr_flow():
    """测试ASR识别流程"""
    print_section("8. ASR识别流程测试")
    
    config = StateConfig(enable_wakeword=True, debug=True)
    manager = VoiceStateManager(config)
    
    # 完整流程：唤醒 -> 语音 -> 识别
    manager.handle_event(StateEvent.WAKEWORD_TRIGGERED)
    manager.handle_event(StateEvent.SPEECH_START)
    manager.handle_event(StateEvent.SPEECH_END)
    
    # 开始识别
    result = manager.handle_event(StateEvent.RECOGNITION_START)
    assert result.success, "开始识别应成功"
    assert result.current_state == VoiceState.RECOGNIZING
    print(f"识别状态: {result.current_state.value}")
    
    # 识别成功
    result = manager.handle_event(StateEvent.RECOGNITION_SUCCESS, {'text': '打开空调'})
    assert result.success, "识别成功应成功"
    info = manager.get_state_info()
    # 唤醒模式下，识别成功后应继续监听
    assert info.current_state == VoiceState.LISTENING, "应继续监听"
    assert info.is_wakeword_detected, "应保持唤醒状态"
    print(f"识别成功后: {result.message}")
    
    # 识别失败测试
    manager.handle_event(StateEvent.SPEECH_START)
    manager.handle_event(StateEvent.SPEECH_END)
    manager.handle_event(StateEvent.RECOGNITION_START)
    result = manager.handle_event(StateEvent.RECOGNITION_FAILED)
    assert result.success, "识别失败应成功处理"
    print(f"识别失败: {result.message}")
    
    print("\n✅ ASR识别流程测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("  🧪 状态机模块测试")
    print("="*60)
    
    tests = [
        ("基本状态转换", test_basic_state_transitions),
        ("带唤醒词的VAD流程", test_vad_flow_with_wakeword),
        ("超时处理", test_timeout_handling),
        ("无唤醒词模式", test_without_wakeword),
        ("状态变化回调", test_state_callbacks),
        ("状态转换历史", test_transition_history),
        ("重置和强制空闲", test_reset_and_force_idle),
        ("ASR识别流程", test_asr_flow),
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
        print("\n🎉 所有测试通过！状态机模块工作正常。\n")
    else:
        print(f"\n⚠️ 有 {failed} 个测试失败，请检查。\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
