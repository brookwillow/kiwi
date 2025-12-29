"""
录音模块测试示例
"""
import time
from src.audio import AudioRecorder, AudioConfig


def test_basic_usage():
    """测试基础使用"""
    print("=== 测试基础使用 ===")
    
    # 创建配置
    config = AudioConfig(
        sample_rate=16000,
        channels=1,
        chunk_size=1024
    )
    
    # 初始化录音器
    recorder = AudioRecorder(config)
    
    # 启动录音
    print("启动录音...")
    recorder.start()
    
    # 读取几帧数据
    for i in range(5):
        frame = recorder.read(timeout=1.0)
        print(f"帧 {frame.frame_id}: {len(frame.data)} 样本, 时长 {frame.duration:.3f}s")
    
    # 停止录音
    recorder.stop()
    print("录音已停止\n")


def test_stream_mode():
    """测试流式模式"""
    print("=== 测试流式模式 ===")
    
    config = AudioConfig(sample_rate=16000, channels=1)
    recorder = AudioRecorder(config)
    recorder.start()
    
    print("流式读取 5 帧...")
    count = 0
    for frame in recorder.stream():
        print(f"帧 {frame.frame_id}: {len(frame.data)} 样本")
        count += 1
        if count >= 5:
            break
    
    recorder.stop()
    print("流式读取完成\n")


def test_async_callback():
    """测试异步回调"""
    print("=== 测试异步回调 ===")
    
    frame_count = [0]  # 使用列表以便在回调中修改
    
    def audio_callback(frame):
        frame_count[0] += 1
        if frame_count[0] <= 5:
            print(f"异步回调: 帧 {frame.frame_id}")
    
    config = AudioConfig(sample_rate=16000, channels=1)
    recorder = AudioRecorder(config)
    recorder.read_async(audio_callback)
    recorder.start()
    
    # 等待接收几帧
    print("等待异步回调...")
    time.sleep(2)
    
    recorder.stop()
    print(f"共收到 {frame_count[0]} 帧\n")


def test_event_listeners():
    """测试事件监听"""
    print("=== 测试事件监听 ===")
    
    config = AudioConfig(sample_rate=16000, channels=1)
    recorder = AudioRecorder(config)
    
    @recorder.on('start')
    def on_start():
        print("事件: 录音已启动")
    
    @recorder.on('stop')
    def on_stop():
        print("事件: 录音已停止")
    
    @recorder.on('data')
    def on_data(frame):
        if frame.frame_id < 3:
            print(f"事件: 收到帧 {frame.frame_id}")
    
    recorder.start()
    time.sleep(1)
    recorder.stop()
    print()


def test_device_list():
    """测试设备列表"""
    print("=== 可用音频输入设备 ===")
    devices = AudioRecorder.list_devices()
    for device in devices:
        print(device)
    print()


def test_status():
    """测试状态查询"""
    print("=== 测试状态查询 ===")
    
    config = AudioConfig(sample_rate=16000, channels=1)
    recorder = AudioRecorder(config)
    
    print("启动前:", "录音中" if recorder.is_recording() else "未录音")
    
    recorder.start()
    print("启动后:", "录音中" if recorder.is_recording() else "未录音")
    
    # 读取一些数据
    for _ in range(3):
        recorder.read()
    
    status = recorder.get_status()
    print(f"设备: {status.device_name}")
    print(f"已捕获帧数: {status.frames_captured}")
    print(f"缓冲区使用率: {status.buffer_usage:.1%}")
    print(f"平均音量: {status.average_level:.4f}")
    
    recorder.stop()
    print()


def test_context_manager():
    """测试上下文管理器"""
    print("=== 测试上下文管理器 ===")
    
    config = AudioConfig(sample_rate=16000, channels=1)
    
    with AudioRecorder(config) as recorder:
        print("在 with 块中录音...")
        for i in range(3):
            frame = recorder.read()
            print(f"帧 {frame.frame_id}")
    
    print("已自动停止\n")


if __name__ == "__main__":
    # 运行所有测试
    try:
        test_device_list()
        test_basic_usage()
        test_stream_mode()
        test_async_callback()
        test_event_listeners()
        test_status()
        test_context_manager()
        
        print("✅ 所有测试完成!")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
