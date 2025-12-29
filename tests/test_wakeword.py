"""
唤醒词模块测试脚本
"""
import numpy as np
import sounddevice as sd
from src.wakeword import WakeWordFactory, WakeWordConfig


def test_wakeword_basic():
    """测试基本唤醒词功能"""
    print("=" * 60)
    print("测试唤醒词检测")
    print("=" * 60)
    
    # 创建唤醒词配置
    config = WakeWordConfig(
        sample_rate=16000,
        models=[],  # 使用默认模型
        threshold=0.5,
        cooldown_seconds=3.0
    )
    
    print(f"\n配置信息:")
    print(f"  采样率: {config.sample_rate} Hz")
    print(f"  唤醒词模型: {config.models}")
    print(f"  检测阈值: {config.threshold}")
    print(f"  冷却时间: {config.cooldown_seconds}秒")
    print()
    
    # 创建唤醒词检测器
    wakeword = WakeWordFactory.create("openwakeword", config)
    print()
    
    # 实时音频检测
    print("🎤 开始实时检测唤醒词...")
    print("   请对着麦克风说 'Hey Jarvis' 来触发唤醒")
    print("   按 Ctrl+C 停止\n")
    
    def audio_callback(indata, frames, time, status):
        """音频回调函数"""
        if status:
            print(f"状态: {status}")
        
        # 转换为float32格式
        audio_data = indata[:, 0].astype(np.float32)
        
        # 检测唤醒词
        result = wakeword.detect(audio_data)
        
        if result.is_detected:
            print(f"\n🔥 唤醒词触发！")
            print(f"   唤醒词: {result.keyword}")
            print(f"   置信度: {result.confidence:.2f}")
            print(f"   状态: {result.state.value}\n")
    
    try:
        # 打开音频流
        with sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype=np.float32,
            blocksize=1280,  # ~80ms @ 16kHz
            callback=audio_callback
        ):
            print("按 Enter 键停止...")
            input()
    except KeyboardInterrupt:
        print("\n\n✅ 测试结束")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


def test_wakeword_engines():
    """测试唤醒词引擎列表"""
    print("\n" + "=" * 60)
    print("测试唤醒词引擎列表")
    print("=" * 60)
    
    engines = WakeWordFactory.list_engines()
    print(f"可用的唤醒词引擎: {engines}")
    
    for engine_name in engines:
        print(f"\n创建 '{engine_name}' 引擎...")
        config = WakeWordConfig()
        wakeword = WakeWordFactory.create(engine_name, config)
        print(f"  ✅ 引擎类型: {type(wakeword).__name__}")


if __name__ == "__main__":
    # 先测试引擎列表
    test_wakeword_engines()
    
    print("\n\n")
    
    # 测试实时检测
    test_wakeword_basic()
    
    print("\n" + "=" * 60)
    print("🎉 所有测试完成！")
    print("=" * 60)
