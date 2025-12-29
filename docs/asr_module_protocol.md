# ASR 模块协议设计

## 模块概述

ASR (Automatic Speech Recognition) 模块负责将音频转换为文本。支持多种ASR引擎，提供统一的接口。

## 接口设计

### 1. 初始化接口

#### `ASREngine.__init__(config: ASRConfig)`

**功能**: 初始化ASR引擎

**输入参数**:
```python
class ASRConfig:
    model: str = "whisper"          # 模型类型 (whisper, azure, google, local)
    language: str = "zh"            # 识别语言
    model_size: str = "base"        # 模型大小 (tiny, base, small, medium, large)
    device: str = "cpu"             # 运行设备 (cpu, cuda)
    beam_size: int = 5              # 束搜索大小
    temperature: float = 0.0        # 采样温度
    vad_filter: bool = True         # 是否使用VAD过滤
    initial_prompt: str = None      # 初始提示词
```

**输出**: ASREngine 实例

**异常**:
- `ASRError`: ASR引擎初始化失败
- `ModelNotFoundError`: 模型文件未找到

---

### 2. 识别接口

#### `ASREngine.recognize(audio: np.ndarray, sample_rate: int = 16000) -> ASRResult`

**功能**: 识别音频并返回文本

**输入参数**:
- `audio`: 音频数据数组 (numpy array)
- `sample_rate`: 采样率

**输出**:
```python
class ASRResult:
    text: str                      # 识别文本
    language: str                  # 检测语言
    confidence: float              # 置信度 (0.0-1.0)
    segments: List[Segment]        # 分段信息
    duration: float                # 音频时长
    processing_time: float         # 处理时间
    
class Segment:
    id: int                        # 分段ID
    start: float                   # 开始时间(秒)
    end: float                     # 结束时间(秒)
    text: str                      # 分段文本
    confidence: float              # 置信度
```

---

### 3. 流式识别接口

#### `ASREngine.recognize_stream(audio_stream: Iterator[np.ndarray]) -> Iterator[ASRResult]`

**功能**: 流式识别音频

**输入**: 音频流迭代器

**输出**: 识别结果迭代器

---

### 4. 批量识别接口

#### `ASREngine.recognize_batch(audio_list: List[np.ndarray]) -> List[ASRResult]`

**功能**: 批量识别多段音频

**输入**: 音频数组列表

**输出**: 识别结果列表

---

## 数据流设计

```
音频数据 (AudioFrame)
    ↓
音频预处理 (重采样、格式转换)
    ↓
ASR引擎
    ↓
ASRResult (文本 + 元数据)
    ↓
下游模块 (编排者、GUI)
```

---

## 使用示例

### 基础使用

```python
from src.asr import ASREngine, ASRConfig

# 创建配置
config = ASRConfig(
    model="whisper",
    language="zh",
    model_size="base"
)

# 初始化引擎
asr = ASREngine(config)

# 识别音频
result = asr.recognize(audio_data, sample_rate=16000)
print(f"识别结果: {result.text}")
print(f"置信度: {result.confidence:.2f}")
```

### 与录音模块集成

```python
from src.audio import AudioRecorder, AudioConfig
from src.asr import ASREngine, ASRConfig

# 初始化录音器
audio_config = AudioConfig(sample_rate=16000, channels=1)
recorder = AudioRecorder(audio_config)

# 初始化ASR
asr_config = ASRConfig(model="whisper", language="zh")
asr = ASREngine(asr_config)

# 录音并识别
recorder.start()
audio_buffer = []

for frame in recorder.stream():
    audio_buffer.append(frame.data)
    
    # 累积足够的音频后识别
    if len(audio_buffer) >= 50:  # 约3秒
        audio = np.concatenate(audio_buffer)
        result = asr.recognize(audio)
        print(f"识别: {result.text}")
        audio_buffer.clear()
```

---

## 实现优先级

### P0 (必须实现)
- Whisper 引擎实现
- 基础识别接口
- ASRResult 数据结构
- 配置管理

### P1 (重要)
- 音频预处理
- 错误处理
- 性能优化

### P2 (可选)
- 流式识别
- 批量识别
- 多引擎支持
