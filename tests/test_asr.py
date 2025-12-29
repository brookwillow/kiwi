"""
ASR 模块测试示例
"""
import numpy as np
import time
from src.asr import create_asr_engine, ASRConfig


def generate_test_audio(duration: float = 3.0, sample_rate: int = 16000) -> np.ndarray:
    """生成测试音频（静音）"""
    num_samples = int(duration * sample_rate)
    # 生成低噪声音频
    audio = np.random.randn(num_samples).astype(np.float32) * 0.01
    return audio


def test_basic_recognition():
    """测试基础识别"""
    print("=== 测试基础识别 ===\n")
    
    # 创建配置
    config = ASRConfig(
        model="whisper",
        language="zh",
        model_size="base"
    )
    
    # 创建引擎
    print("初始化 ASR 引擎...")
    asr = create_asr_engine(config)
    print("引擎初始化完成\n")
    
    # 生成测试音频
    print("生成测试音频...")
    audio = generate_test_audio(duration=3.0)
    
    # 识别
    print("开始识别...")
    result = asr.recognize(audio, sample_rate=16000)
    
    print(f"\n识别结果:")
    print(f"  文本: {result.text or '(空)'}")
    print(f"  语言: {result.language}")
    print(f"  置信度: {result.confidence:.2f}")
    print(f"  音频时长: {result.duration:.2f}s")
    print(f"  处理时间: {result.processing_time:.2f}s")
    print(f"  分段数: {result.num_segments}")
    print()


def test_with_audio_recorder():
    """测试与录音模块集成"""
    print("=== 测试录音+ASR集成 ===\n")
    
    try:
        from src.audio import AudioRecorder, AudioConfig as AudioCfg
        
        # 创建录音器
        audio_config = AudioCfg(
            sample_rate=16000,
            channels=1,
            chunk_size=1024
        )
        recorder = AudioRecorder(audio_config)
        
        # 创建ASR引擎
        asr_config = ASRConfig(
            model="whisper",
            language="zh",
            model_size="base"
        )
        asr = create_asr_engine(asr_config)
        
        print("开始录音，请说话...")
        print("将录制 3 秒后进行识别")
        print("-" * 50)
        
        recorder.start()
        
        # 收集音频
        audio_buffer = []
        frame_count = 0
        target_frames = 50  # 约 3 秒
        
        for frame in recorder.stream():
            audio_buffer.append(frame.data)
            frame_count += 1
            
            if frame_count % 10 == 0:
                print(f"录音中... {frame_count}/{target_frames} 帧")
            
            if frame_count >= target_frames:
                break
        
        recorder.stop()
        print("录音完成\n")
        
        # 拼接音频
        audio = np.concatenate(audio_buffer)
        
        # 识别
        print("正在识别...")
        result = asr.recognize(audio, sample_rate=16000)
        
        print(f"\n识别结果:")
        print(f"  文本: {result.text or '(未识别到语音)'}")
        print(f"  置信度: {result.confidence:.2f}")
        print(f"  处理时间: {result.processing_time:.2f}s")
        
        if result.segments:
            print(f"\n分段信息:")
            for seg in result.segments:
                print(f"  [{seg.start:.2f}s - {seg.end:.2f}s] {seg.text}")
        
        print()
    
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


def test_batch_recognition():
    """测试批量识别"""
    print("=== 测试批量识别 ===\n")
    
    config = ASRConfig(model="whisper", language="zh", model_size="tiny")
    asr = create_asr_engine(config)
    
    # 生成多段音频
    audio_list = [
        generate_test_audio(1.0),
        generate_test_audio(2.0),
        generate_test_audio(1.5),
    ]
    
    print(f"批量识别 {len(audio_list)} 段音频...")
    results = asr.recognize_batch(audio_list, sample_rate=16000)
    
    for i, result in enumerate(results):
        print(f"\n音频 {i+1}:")
        print(f"  时长: {result.duration:.2f}s")
        print(f"  文本: {result.text or '(空)'}")
    
    print()


def test_config_validation():
    """测试配置验证"""
    print("=== 测试配置验证 ===\n")
    
    # 正常配置
    try:
        config = ASRConfig(model="whisper", model_size="base")
        config.validate()
        print("✅ 正常配置验证通过")
    except Exception as e:
        print(f"❌ 配置验证失败: {e}")
    
    # 错误的模型
    try:
        config = ASRConfig(model="invalid_model")
        config.validate()
        print("❌ 应该抛出异常")
    except ValueError as e:
        print(f"✅ 正确捕获错误: {e}")
    
    # 错误的模型大小
    try:
        config = ASRConfig(model_size="invalid_size")
        config.validate()
        print("❌ 应该抛出异常")
    except ValueError as e:
        print(f"✅ 正确捕获错误: {e}")
    
    print()


if __name__ == "__main__":
    try:
        # 测试配置验证
        test_config_validation()
        
        # 测试基础识别
        test_basic_recognition()
        
        # 测试批量识别
        # test_batch_recognition()
        
        # 测试录音集成（需要麦克风）
        # test_with_audio_recorder()
        
        print("✅ 测试完成!")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
