#!/usr/bin/env python3
"""
事件系统 Payload 测试脚本

验证所有事件类型的 Payload 功能
"""

import sys
sys.path.insert(0, '/Users/wangjie/project/other/kiwi')

from src.core.events import (
    Event, EventType, SessionAwareEvent,
    AudioFrameEvent, AudioFramePayload,
    WakewordEvent, WakewordPayload,
    VADEvent, VADPayload,
    ASREvent, ASRPayload,
    StateChangeEvent, StateChangePayload,
    AgentRequestEvent, AgentRequestPayload
)


def test_audio_frame_event():
    """测试 AudioFrameEvent"""
    print("\n" + "="*60)
    print("测试 AudioFrameEvent")
    print("="*60)
    
    payload = AudioFramePayload(
        frame_data=b"fake_audio_data",
        sample_rate=16000,
        channels=1
    )
    
    event = AudioFrameEvent(
        source="audio",
        payload=payload
    )
    
    # 验证 payload
    assert event.payload.frame_data == b"fake_audio_data"
    assert event.payload.sample_rate == 16000
    assert event.payload.channels == 1
    
    # 验证向后兼容的 data
    assert event.data['frame_data'] == b"fake_audio_data"
    assert event.data['sample_rate'] == 16000
    
    # 验证不是 SessionAwareEvent
    assert not isinstance(event, SessionAwareEvent)
    
    print("✅ AudioFrameEvent 测试通过")
    print(f"   - payload.sample_rate = {event.payload.sample_rate}")
    print(f"   - data['sample_rate'] = {event.data['sample_rate']}")


def test_wakeword_event():
    """测试 WakewordEvent"""
    print("\n" + "="*60)
    print("测试 WakewordEvent")
    print("="*60)
    
    payload = WakewordPayload(
        keyword="小智",
        confidence=0.95
    )
    
    event = WakewordEvent(
        source="wakeword",
        payload=payload
    )
    
    # 验证 payload
    assert event.payload.keyword == "小智"
    assert event.payload.confidence == 0.95
    
    # 验证向后兼容
    assert event.data['keyword'] == "小智"
    assert event.data['confidence'] == 0.95
    
    print("✅ WakewordEvent 测试通过")
    print(f"   - payload.keyword = {event.payload.keyword}")
    print(f"   - payload.confidence = {event.payload.confidence}")


def test_vad_event():
    """测试 VADEvent"""
    print("\n" + "="*60)
    print("测试 VADEvent")
    print("="*60)
    
    # 测试语音开始
    payload_start = VADPayload(
        audio_data=None,
        duration_ms=0,
        is_speech=True
    )
    
    event_start = VADEvent(
        event_type=EventType.VAD_SPEECH_START,
        source="vad",
        payload=payload_start
    )
    
    assert event_start.payload.is_speech == True
    assert event_start.payload.audio_data is None
    
    # 测试语音结束
    payload_end = VADPayload(
        audio_data=b"speech_audio",
        duration_ms=1500,
        is_speech=False
    )
    
    event_end = VADEvent(
        event_type=EventType.VAD_SPEECH_END,
        source="vad",
        payload=payload_end
    )
    
    assert event_end.payload.is_speech == False
    assert event_end.payload.duration_ms == 1500
    assert event_end.data['audio_data'] == b"speech_audio"
    
    print("✅ VADEvent 测试通过")
    print(f"   - speech_start.payload.is_speech = {event_start.payload.is_speech}")
    print(f"   - speech_end.payload.duration_ms = {event_end.payload.duration_ms}")


def test_asr_event():
    """测试 ASREvent"""
    print("\n" + "="*60)
    print("测试 ASREvent")
    print("="*60)
    
    # 测试成功识别
    payload_success = ASRPayload(
        text="你好",
        confidence=0.95,
        is_partial=False,
        latency_ms=150
    )
    
    event_success = ASREvent(
        event_type=EventType.ASR_RECOGNITION_SUCCESS,
        source="asr",
        payload=payload_success
    )
    
    assert event_success.payload.text == "你好"
    assert event_success.payload.confidence == 0.95
    assert event_success.payload.is_partial == False
    assert event_success.payload.latency_ms == 150
    
    # 验证向后兼容
    assert event_success.data['text'] == "你好"
    assert event_success.data['confidence'] == 0.95
    
    # 测试失败识别
    payload_failed = ASRPayload(
        text="",
        confidence=0.0,
        is_partial=False
    )
    
    event_failed = ASREvent(
        event_type=EventType.ASR_RECOGNITION_FAILED,
        source="asr",
        payload=payload_failed
    )
    
    assert event_failed.payload.text == ""
    assert event_failed.payload.confidence == 0.0
    
    print("✅ ASREvent 测试通过")
    print(f"   - success.payload.text = {event_success.payload.text}")
    print(f"   - success.payload.latency_ms = {event_success.payload.latency_ms}")


def test_state_change_event():
    """测试 StateChangeEvent"""
    print("\n" + "="*60)
    print("测试 StateChangeEvent")
    print("="*60)
    
    payload = StateChangePayload(
        from_state="idle",
        to_state="listening",
        reason="唤醒词检测"
    )
    
    event = StateChangeEvent(
        source="state_machine",
        payload=payload
    )
    
    assert event.payload.from_state == "idle"
    assert event.payload.to_state == "listening"
    assert event.payload.reason == "唤醒词检测"
    
    # 验证向后兼容
    assert event.data['from_state'] == "idle"
    assert event.data['to_state'] == "listening"
    
    print("✅ StateChangeEvent 测试通过")
    print(f"   - payload.from_state = {event.payload.from_state}")
    print(f"   - payload.to_state = {event.payload.to_state}")


def test_agent_request_event():
    """测试 AgentRequestEvent (SessionAwareEvent)"""
    print("\n" + "="*60)
    print("测试 AgentRequestEvent (SessionAwareEvent)")
    print("="*60)
    
    payload = AgentRequestPayload(
        agent_name="music_agent",
        query="播放音乐",
        context={},
        decision={
            'selected_agent': 'music_agent',
            'confidence': 0.95,
            'reasoning': '用户想听音乐'
        }
    )
    
    event = AgentRequestEvent(
        source="orchestrator",
        payload=payload,
        session_id="sess_123",
        session_action="new"
    )
    
    # 验证 payload
    assert event.payload.agent_name == "music_agent"
    assert event.payload.query == "播放音乐"
    assert event.payload.decision['confidence'] == 0.95
    
    # 验证是 SessionAwareEvent
    assert isinstance(event, SessionAwareEvent)
    assert event.session_id == "sess_123"
    assert event.session_action == "new"
    
    # 验证 get_session_info
    session_info = event.get_session_info()
    assert session_info is not None
    assert session_info.session_id == "sess_123"
    assert session_info.session_action == "new"
    
    # 验证向后兼容
    assert event.data['agent_name'] == "music_agent"
    assert event.data['query'] == "播放音乐"
    
    print("✅ AgentRequestEvent 测试通过")
    print(f"   - payload.agent_name = {event.payload.agent_name}")
    print(f"   - session_id = {event.session_id}")
    print(f"   - isinstance(SessionAwareEvent) = {isinstance(event, SessionAwareEvent)}")


def test_session_awareness():
    """测试会话感知功能"""
    print("\n" + "="*60)
    print("测试会话感知 (SessionAware)")
    print("="*60)
    
    # AudioFrameEvent 不应该是 SessionAwareEvent
    audio_event = AudioFrameEvent(
        source="audio",
        payload=AudioFramePayload(
            frame_data=b"data",
            sample_rate=16000
        )
    )
    assert not isinstance(audio_event, SessionAwareEvent)
    print("✅ AudioFrameEvent 不是 SessionAwareEvent")
    
    # AgentRequestEvent 应该是 SessionAwareEvent
    agent_event = AgentRequestEvent(
        source="orchestrator",
        payload=AgentRequestPayload(
            agent_name="test",
            query="test",
            context={},
            decision={}
        ),
        session_id="sess_456",
        session_action="resume"
    )
    assert isinstance(agent_event, SessionAwareEvent)
    assert agent_event.session_id == "sess_456"
    assert agent_event.session_action == "resume"
    print("✅ AgentRequestEvent 是 SessionAwareEvent")
    print(f"   - session_id = {agent_event.session_id}")
    print(f"   - session_action = {agent_event.session_action}")


def test_backward_compatibility():
    """测试向后兼容性"""
    print("\n" + "="*60)
    print("测试向后兼容性")
    print("="*60)
    
    payload = ASRPayload(
        text="测试",
        confidence=0.88,
        is_partial=False
    )
    
    event = ASREvent(
        event_type=EventType.ASR_RECOGNITION_SUCCESS,
        source="asr",
        payload=payload
    )
    
    # 新方式（推荐）
    text_new = event.payload.text
    conf_new = event.payload.confidence
    
    # 旧方式（向后兼容）
    text_old = event.data.get('text')
    conf_old = event.data.get('confidence')
    
    # 两种方式应该获得相同的值
    assert text_new == text_old == "测试"
    assert conf_new == conf_old == 0.88
    
    print("✅ 向后兼容性测试通过")
    print(f"   - payload.text = {text_new}")
    print(f"   - data['text'] = {text_old}")
    print("   ✅ 两种访问方式结果一致")


def main():
    """运行所有测试"""
    print("\n" + "🚀"*30)
    print("开始事件系统 Payload 测试")
    print("🚀"*30)
    
    try:
        test_audio_frame_event()
        test_wakeword_event()
        test_vad_event()
        test_asr_event()
        test_state_change_event()
        test_agent_request_event()
        test_session_awareness()
        test_backward_compatibility()
        
        print("\n" + "="*60)
        print("🎉 所有测试通过！")
        print("="*60)
        print("\n✅ Payload 系统工作正常")
        print("✅ 向后兼容性保持")
        print("✅ SessionAwareEvent 正确工作")
        print("✅ 类型安全得到保证")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
