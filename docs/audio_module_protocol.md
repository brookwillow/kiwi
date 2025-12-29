# 录音模块协议设计

## 模块概述

录音模块负责从 macOS 系统实时采集音频流，为后续的唤醒、VAD、ASR 等模块提供音频数据。

## 接口设计

### 1. 初始化接口

#### `AudioRecorder.__init__(config: AudioConfig)`

**功能**: 初始化录音模块

**输入参数**:
```python
class AudioConfig:
    sample_rate: int = 16000        # 采样率 (Hz)
    channels: int = 1               # 声道数 (1=单声道, 2=立体声)
    chunk_size: int = 1024          # 每次读取的帧数
    format: str = "int16"           # 音频格式 (int16, float32)
    device_index: int = None        # 设备索引 (None=默认设备)
    buffer_size: int = 10           # 缓冲区大小(秒)
```

**输出**: AudioRecorder 实例

**异常**:
- `AudioDeviceError`: 音频设备不可用
- `ConfigError`: 配置参数无效

---

### 2. 启动录音接口

#### `AudioRecorder.start() -> bool`

**功能**: 启动音频采集

**输入**: 无

**输出**: 
- `True`: 启动成功
- `False`: 启动失败

**副作用**:
- 开始从麦克风采集音频
- 启动内部缓冲区
- 触发 `on_start` 回调

---

### 3. 停止录音接口

#### `AudioRecorder.stop() -> bool`

**功能**: 停止音频采集

**输入**: 无

**输出**:
- `True`: 停止成功
- `False`: 停止失败

**副作用**:
- 停止音频采集
- 清空缓冲区
- 触发 `on_stop` 回调

---

### 4. 读取音频数据接口

#### `AudioRecorder.read(timeout: float = None) -> AudioFrame`

**功能**: 读取一帧音频数据（阻塞模式）

**输入参数**:
- `timeout`: 超时时间(秒)，None=永久等待

**输出**:
```python
class AudioFrame:
    data: np.ndarray           # 音频数据数组
    sample_rate: int           # 采样率
    channels: int              # 声道数
    timestamp: float           # 时间戳 (Unix时间)
    frame_id: int              # 帧序号
    duration: float            # 音频时长(秒)
```

**异常**:
- `TimeoutError`: 超时未读取到数据
- `RecorderNotStartedError`: 录音未启动

---

### 5. 流式读取接口

#### `AudioRecorder.stream() -> Iterator[AudioFrame]`

**功能**: 以生成器方式持续读取音频流

**输入**: 无

**输出**: 音频帧迭代器

**使用示例**:
```python
recorder = AudioRecorder(config)
recorder.start()

for frame in recorder.stream():
    # 处理音频帧
    process_audio(frame)
```

---

### 6. 异步读取接口

#### `AudioRecorder.read_async(callback: Callable[[AudioFrame], None])`

**功能**: 注册回调函数，异步接收音频数据

**输入参数**:
```python
def callback(frame: AudioFrame) -> None:
    """
    音频帧回调函数
    Args:
        frame: 音频帧数据
    """
    pass
```

**输出**: 无

**副作用**:
- 每当有新的音频帧时，自动调用回调函数
- 回调在独立线程中执行

---

### 7. 状态查询接口

#### `AudioRecorder.is_recording() -> bool`

**功能**: 查询录音状态

**输出**:
- `True`: 正在录音
- `False`: 未录音

---

#### `AudioRecorder.get_status() -> RecorderStatus`

**功能**: 获取详细状态信息

**输出**:
```python
class RecorderStatus:
    is_recording: bool         # 是否正在录音
    device_name: str           # 设备名称
    buffer_usage: float        # 缓冲区使用率 (0.0-1.0)
    frames_captured: int       # 已捕获的帧数
    dropped_frames: int        # 丢帧数
    average_level: float       # 平均音量级别
```

---

### 8. 设备管理接口

#### `AudioRecorder.list_devices() -> List[AudioDevice]`

**功能**: 列出所有可用的音频输入设备（静态方法）

**输出**:
```python
class AudioDevice:
    index: int                 # 设备索引
    name: str                  # 设备名称
    channels: int              # 最大声道数
    sample_rate: int           # 默认采样率
    is_default: bool           # 是否为默认设备
```

---

#### `AudioRecorder.set_device(device_index: int) -> bool`

**功能**: 切换音频输入设备（需要先停止录音）

**输入**: 设备索引

**输出**:
- `True`: 切换成功
- `False`: 切换失败

---

### 9. 音频预处理接口

#### `AudioRecorder.set_preprocessor(preprocessor: AudioPreprocessor)`

**功能**: 设置音频预处理器

**输入**:
```python
class AudioPreprocessor:
    def process(self, frame: AudioFrame) -> AudioFrame:
        """
        处理音频帧
        Args:
            frame: 原始音频帧
        Returns:
            处理后的音频帧
        """
        pass
```

**支持的预处理**:
- 降噪 (Noise Reduction)
- 自动增益控制 (AGC)
- 回声消除 (AEC)
- 高通/低通滤波

---

### 10. 回调事件接口

#### `AudioRecorder.on(event: str, callback: Callable)`

**功能**: 注册事件监听器

**支持的事件**:
```python
# 录音开始
@recorder.on('start')
def on_start():
    print("录音已启动")

# 录音停止
@recorder.on('stop')
def on_stop():
    print("录音已停止")

# 音频数据就绪
@recorder.on('data')
def on_data(frame: AudioFrame):
    print(f"收到音频帧: {frame.frame_id}")

# 缓冲区溢出
@recorder.on('overflow')
def on_overflow():
    print("警告: 缓冲区溢出")

# 设备断开
@recorder.on('device_lost')
def on_device_lost():
    print("音频设备已断开")

# 错误事件
@recorder.on('error')
def on_error(error: Exception):
    print(f"错误: {error}")
```

---

## 数据流设计

### 音频数据流向

```
硬件麦克风
    ↓
系统音频驱动 (CoreAudio on macOS)
    ↓
PyAudio/sounddevice 底层库
    ↓
AudioRecorder 内部缓冲区
    ↓
预处理器 (可选)
    ↓
AudioFrame 输出
    ↓
下游模块 (唤醒/VAD/ASR)
```

### 线程模型

```
主线程
    ├─ 初始化和配置
    └─ API 调用

采集线程
    ├─ 从设备读取原始音频
    └─ 写入环形缓冲区

处理线程 (可选)
    ├─ 从缓冲区读取
    ├─ 预处理
    └─ 触发回调/返回数据
```

---

## 性能要求

### 实时性

- **延迟**: 音频采集延迟 < 50ms
- **处理延迟**: 预处理延迟 < 10ms
- **总延迟**: 从麦克风到输出 < 100ms

### 稳定性

- **丢帧率**: < 0.1%
- **缓冲区溢出**: 在正常负载下不应发生
- **CPU 占用**: < 5% (单核)

### 资源占用

- **内存**: < 50MB
- **缓冲区**: 默认 10 秒音频 (约 320KB @ 16kHz)

---

## 配置示例

### 基础配置

```yaml
audio:
  sample_rate: 16000        # 16kHz 适合语音识别
  channels: 1               # 单声道
  chunk_size: 1024          # 约 64ms @ 16kHz
  format: int16             # 16位整数
  device_index: null        # 使用默认设备
  buffer_size: 10           # 10秒缓冲
```

### 高质量配置

```yaml
audio:
  sample_rate: 48000        # 高采样率
  channels: 2               # 立体声
  chunk_size: 2048
  format: float32
  buffer_size: 5
  
  # 预处理配置
  preprocessing:
    noise_reduction: true
    agc: true
    high_pass_filter: 80    # Hz
```

---

## 使用示例

### 示例 1: 基础使用

```python
from src.audio import AudioRecorder, AudioConfig

# 创建配置
config = AudioConfig(
    sample_rate=16000,
    channels=1,
    chunk_size=1024
)

# 初始化录音器
recorder = AudioRecorder(config)

# 启动录音
recorder.start()

# 读取音频
try:
    while True:
        frame = recorder.read(timeout=1.0)
        print(f"Frame {frame.frame_id}: {len(frame.data)} samples")
except KeyboardInterrupt:
    pass

# 停止录音
recorder.stop()
```

### 示例 2: 流式处理

```python
recorder = AudioRecorder(config)
recorder.start()

# 使用生成器
for frame in recorder.stream():
    # 发送到唤醒模块
    wakeword_detector.feed(frame)
    
    # 发送到 VAD
    vad_result = vad.process(frame)
    
    if should_stop:
        break

recorder.stop()
```

### 示例 3: 异步回调

```python
def audio_callback(frame: AudioFrame):
    """处理音频帧"""
    # 推送到下游模块
    audio_pipeline.push(frame)

recorder = AudioRecorder(config)
recorder.read_async(audio_callback)
recorder.start()

# 主线程可以做其他事情
while running:
    time.sleep(0.1)

recorder.stop()
```

### 示例 4: 事件监听

```python
recorder = AudioRecorder(config)

@recorder.on('start')
def on_start():
    print("录音开始")
    gui.update_status("录音中")

@recorder.on('data')
def on_data(frame):
    # 更新音量指示器
    level = np.abs(frame.data).mean()
    gui.update_volume(level)

@recorder.on('error')
def on_error(error):
    print(f"错误: {error}")
    gui.show_error(str(error))

recorder.start()
```

---

## 错误处理

### 异常类型

```python
class AudioError(Exception):
    """音频模块基础异常"""
    pass

class AudioDeviceError(AudioError):
    """音频设备相关错误"""
    pass

class RecorderNotStartedError(AudioError):
    """录音未启动错误"""
    pass

class ConfigError(AudioError):
    """配置错误"""
    pass

class BufferOverflowError(AudioError):
    """缓冲区溢出错误"""
    pass
```

### 错误处理策略

1. **设备丢失**: 
   - 触发 `device_lost` 事件
   - 尝试重新连接
   - 失败后抛出异常

2. **缓冲区溢出**:
   - 触发 `overflow` 事件
   - 丢弃旧数据
   - 记录警告日志

3. **配置错误**:
   - 初始化时立即抛出
   - 提供详细错误信息

---

## 与下游模块的接口

### 唤醒模块接口

```python
# 录音模块输出
frame: AudioFrame

# 唤醒模块输入
wakeword_detector.feed(frame.data, frame.sample_rate)
```

### VAD 模块接口

```python
# 录音模块输出
frame: AudioFrame

# VAD 模块输入
vad_result = vad.process(
    audio=frame.data,
    sample_rate=frame.sample_rate
)
```

### ASR 模块接口

```python
# 累积多帧音频
audio_buffer = []
for frame in recorder.stream():
    audio_buffer.append(frame.data)
    
    if should_recognize:
        # 拼接音频
        audio = np.concatenate(audio_buffer)
        
        # ASR 识别
        text = asr.recognize(audio, sample_rate=16000)
        audio_buffer.clear()
```

---

## 测试要点

### 单元测试

- [ ] 初始化配置验证
- [ ] 启动/停止状态切换
- [ ] 音频帧数据完整性
- [ ] 时间戳连续性
- [ ] 缓冲区管理
- [ ] 设备切换功能
- [ ] 异常处理

### 集成测试

- [ ] 与唤醒模块集成
- [ ] 与 VAD 模块集成
- [ ] 与 GUI 模块集成
- [ ] 长时间运行稳定性

### 性能测试

- [ ] 延迟测试
- [ ] 丢帧率测试
- [ ] CPU/内存占用测试
- [ ] 缓冲区压力测试

---

## 实现优先级

### P0 (必须实现)
- 基础初始化和配置
- 启动/停止功能
- 同步读取接口
- AudioFrame 数据结构
- 基础错误处理

### P1 (重要)
- 流式读取接口
- 异步回调接口
- 设备列表和切换
- 状态查询
- 事件系统

### P2 (可选)
- 音频预处理
- 高级配置选项
- 性能优化
- 完善的事件监听

---

## 注意事项

1. **线程安全**: 所有公共接口必须是线程安全的
2. **资源释放**: 确保 stop() 时正确释放所有资源
3. **采样率匹配**: 输出采样率必须与配置一致
4. **时间戳精度**: 使用高精度时间戳，误差 < 1ms
5. **缓冲区设计**: 使用环形缓冲区避免频繁内存分配
6. **跨平台**: 考虑未来扩展到 Linux/Windows 的可能性
