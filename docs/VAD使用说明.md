# VAD模块使用说明

## 概述

VAD（Voice Activity Detection，语音活动检测）模块用于检测音频流中的语音片段，只在检测到实际语音时才进行后续处理（如ASR识别），可以有效提高系统效率和识别准确度。

## 功能特点

- ✅ 基于WebRTC VAD算法，成熟稳定
- ✅ 自动检测语音开始和结束
- ✅ 支持语音前缓冲，避免丢失语音开头
- ✅ 可配置的静音超时和最小语音长度
- ✅ 实时处理，低延迟
- ✅ 完整的状态管理和事件通知

## 工作流程

```
音频流 → VAD检测 → 语音片段 → ASR识别
          ↓
      静音/非语音
          ↓
        丢弃
```

## 配置说明

在 `config/system_config.yaml` 中配置VAD参数：

```yaml
modules:
  vad:
    enabled: true                    # 是否启用VAD
    frame_duration_ms: 30            # 帧长度（10/20/30ms）
    aggressiveness: 2                # VAD激进程度（0-3）
    silence_timeout_ms: 800          # 静音超时（ms）
    pre_speech_buffer_ms: 300        # 语音前缓冲（ms）
    min_speech_duration_ms: 300      # 最小语音长度（ms）
```

### 参数说明

| 参数 | 说明 | 可选值 | 推荐值 |
|------|------|--------|--------|
| `frame_duration_ms` | 每帧时长 | 10, 20, 30 | 30 |
| `aggressiveness` | 激进程度，越大越容易检测到语音 | 0-3 | 2 |
| `silence_timeout_ms` | 连续静音多久后认为语音结束 | 任意 | 800 |
| `pre_speech_buffer_ms` | 保留语音开始前多少ms的音频 | 任意 | 300 |
| `min_speech_duration_ms` | 最小语音长度，短于此值会被忽略 | 任意 | 300 |

### 激进程度（aggressiveness）选择

- **0（质量模式）**：最不容易误判，适合安静环境
- **1（低比特率模式）**：平衡模式
- **2（激进模式）**：推荐使用，适合大多数场景
- **3（非常激进）**：最容易检测到语音，但也容易误判

## 使用方法

### 1. 基本使用

```python
from src.vad import VADFactory, VADConfig, VADEvent
import numpy as np

# 创建配置
config = VADConfig(
    sample_rate=16000,
    frame_duration_ms=30,
    aggressiveness=2,
    silence_timeout_ms=800
)

# 创建VAD引擎
vad = VADFactory.create("webrtc", config)

# 处理音频帧（需要是int16格式）
audio_frame = np.zeros(480, dtype=np.int16)  # 30ms @ 16kHz
result = vad.process_frame(audio_frame)

# 检查事件
if result.event == VADEvent.SPEECH_START:
    print("语音开始")
elif result.event == VADEvent.SPEECH_END:
    print(f"语音结束，时长: {result.duration_ms}ms")
    # 获取完整的语音片段
    audio_data = result.audio_data
```

### 2. 与ASR集成

```python
# 在音频回调中
def on_audio_frame(frame):
    # VAD检测
    vad_result = vad.process_frame(frame.data)
    
    # 只在语音结束时进行ASR识别
    if vad_result.event == VADEvent.SPEECH_END:
        # 将语音片段送去识别
        audio_data = vad_result.audio_data
        asr_result = asr_engine.recognize(audio_data, sample_rate)
        print(f"识别结果: {asr_result.text}")
```

### 3. GUI集成

在GUI中启用VAD：

1. 启动应用：`python run_audio_visualizer.py`
2. 勾选 **"启用 VAD 检测"** 复选框
3. 勾选 **"启用 ASR 识别"** 复选框（需要先加载ASR模型）
4. 点击 **"开始录音"**
5. 开始说话，VAD会自动检测语音片段并进行识别

### 4. 查看VAD状态

GUI中会实时显示：
- **VAD状态图表**：红色=检测到语音，灰色=静音
- **控制台输出**：显示语音开始/结束事件和时长

## VAD事件说明

| 事件 | 说明 | 何时触发 |
|------|------|----------|
| `SPEECH_START` | 语音开始 | 连续2帧检测到语音 |
| `SPEAKING` | 持续说话中 | 语音状态的每一帧 |
| `SPEECH_END` | 语音结束 | 连续N帧静音（N由silence_timeout_ms决定） |

## 状态机

```
     开始
      ↓
   [IDLE] ←──────────┐
      ↓               │
   检测到语音         │
      ↓               │
[SPEAKING]           │
      ↓               │
   连续静音           │
      ↓               │
   语音结束 ──────────┘
```

## 性能调优

### 降低延迟
- 减小 `silence_timeout_ms`（如500ms）
- 减小 `pre_speech_buffer_ms`（如200ms）

### 提高准确度
- 增大 `min_speech_duration_ms`（如500ms），过滤短音
- 降低 `aggressiveness`（如1），减少误判

### 适应噪音环境
- 提高 `aggressiveness`（如3）
- 增大 `silence_timeout_ms`（如1000ms）

## 测试

运行测试脚本：

```bash
python test_vad.py
```

## 工作模式

系统支持3种工作模式：

- **模式1（完整模式）**：录音 → 唤醒词 → VAD → ASR
- **模式2（跳过唤醒）**：录音 → VAD → ASR ✅ 推荐
- **模式3（直接ASR）**：录音 → ASR

在 `config/system_config.yaml` 中设置：

```yaml
working_mode: 2  # 使用VAD模式
```

## 注意事项

1. **采样率限制**：WebRTC VAD只支持 8000, 16000, 32000, 48000 Hz
2. **帧长度限制**：只支持 10, 20, 30 ms
3. **数据格式**：输入必须是 int16 格式的音频数据
4. **静音检测**：环境噪音可能影响检测，建议调整激进程度
5. **最小语音长度**：太短的语音会被过滤，避免误识别

## 常见问题

### Q: VAD检测不到语音？
A: 尝试提高 `aggressiveness` 参数（2→3）

### Q: VAD误把噪音当成语音？
A: 尝试降低 `aggressiveness` 参数（2→1），或增大 `min_speech_duration_ms`

### Q: 语音开头被截断？
A: 增大 `pre_speech_buffer_ms` 参数（如500ms）

### Q: 语音结束太慢？
A: 减小 `silence_timeout_ms` 参数（如500ms）

### Q: 短语音被忽略？
A: 减小 `min_speech_duration_ms` 参数（如200ms）

## 扩展开发

可以添加自定义VAD引擎：

```python
from src.vad import BaseVAD, VADFactory

class MyVAD(BaseVAD):
    def process_frame(self, audio_frame):
        # 实现你的VAD算法
        pass
    
    def reset(self):
        # 重置状态
        pass

# 注册引擎
VADFactory.register_engine("my_vad", MyVAD)

# 使用
vad = VADFactory.create("my_vad", config)
```

## 相关文档

- [系统架构说明](README.md)
- [ASR模块说明](docs/asr.md)
- [录音模块说明](docs/audio.md)
