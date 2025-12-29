"""
VAD 模块测试脚本
"""
import numpy as np
from src.vad import VADFactory, VADConfig, VADEvent


def test_vad_basic():
    """测试基本VAD功能"""
    print("=" * 60)
    print("测试 VAD 基本功能")
    print("=" * 60)
    
    # 创建VAD配置
    config = VADConfig(
        sample_rate=16000,
        frame_duration_ms=30,
        aggressiveness=2,
        silence_timeout_ms=800,
        pre_speech_buffer_ms=300,
        min_speech_duration_ms=300
    )
    
    print(f"配置信息:")
    print(f"  采样率: {config.sample_rate} Hz")
    print(f"  帧长度: {config.frame_duration_ms} ms ({config.frame_size} 样本)")
    print(f"  激进程度: {config.aggressiveness}")
    print(f"  静音超时: {config.silence_timeout_ms} ms ({config.silence_frames} 帧)")
    print(f"  语音前缓冲: {config.pre_speech_buffer_ms} ms ({config.pre_speech_frames} 帧)")
    print(f"  最小语音长度: {config.min_speech_duration_ms} ms ({config.min_speech_frames} 帧)")
    print()
    
    # 创建VAD引擎
    vad = VADFactory.create("webrtc", config)
    print("✅ VAD 引擎创建成功")
    print()
    
    # 模拟音频数据
    frame_size = config.frame_size
    
    # 1. 静音帧（前5帧）
    print("发送静音帧...")
    for i in range(5):
        silence_frame = np.zeros(frame_size, dtype=np.int16)
        result = vad.process_frame(silence_frame)
        if result.event:
            print(f"  帧 {i}: 事件 = {result.event.value}, 状态 = {result.state.value}")
    
    # 2. 语音帧（10帧）
    print("\n发送语音帧...")
    for i in range(10):
        # 生成模拟语音（1kHz正弦波）
        t = np.arange(frame_size) / config.sample_rate
        speech_frame = (np.sin(2 * np.pi * 1000 * t) * 16000).astype(np.int16)
        result = vad.process_frame(speech_frame)
        if result.event:
            print(f"  帧 {i+5}: 事件 = {result.event.value}, 状态 = {result.state.value}")
    
    # 3. 静音帧（触发语音结束）
    print(f"\n发送静音帧（触发语音结束，需要 {config.silence_frames} 帧）...")
    for i in range(config.silence_frames + 5):
        silence_frame = np.zeros(frame_size, dtype=np.int16)
        result = vad.process_frame(silence_frame)
        if result.event:
            print(f"  帧 {i+15}: 事件 = {result.event.value}, 状态 = {result.state.value}")
            if result.event == VADEvent.SPEECH_END:
                print(f"  📊 语音时长: {result.duration_ms:.0f} ms")
                print(f"  📦 音频数据大小: {len(result.audio_data)} 字节")
                break
    
    print("\n✅ 测试完成")


def test_vad_engines():
    """测试VAD引擎列表"""
    print("\n" + "=" * 60)
    print("测试 VAD 引擎列表")
    print("=" * 60)
    
    engines = VADFactory.list_engines()
    print(f"可用的 VAD 引擎: {engines}")
    
    for engine_name in engines:
        print(f"\n创建 '{engine_name}' 引擎...")
        vad = VADFactory.create(engine_name)
        print(f"  ✅ 引擎类型: {type(vad).__name__}")
        print(f"  ✅ 配置: {vad.config}")


if __name__ == "__main__":
    test_vad_basic()
    test_vad_engines()
    
    print("\n" + "=" * 60)
    print("🎉 所有测试完成！")
    print("=" * 60)
