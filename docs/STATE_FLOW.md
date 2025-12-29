# Kiwi 语音助手状态流程

## 状态定义

系统现在有以下8种状态：

1. **ready** - 就绪状态（等待唤醒）
2. **wake up** - 唤醒词检测到
3. **vad begin** - 语音活动开始
4. **vad end** - 语音活动结束
5. **asr recognizing** - ASR识别中
6. **orchestrator deciding** - Orchestrator决策中
7. **agent running** - Agent执行中
8. **ready** - 完成后回到就绪状态

## 完整状态流转

```
ready
  ↓ (检测到唤醒词)
wake up
  ↓ (VAD检测到语音)
vad begin
  ↓ (语音活动中...)
vad begin
  ↓ (检测到静音)
vad end
  ↓ (开始ASR识别)
asr recognizing ← ASR处理中
  ↓ (识别完成)
orchestrator deciding ← Orchestrator决策中
  ↓ (决策完成)
agent running ← Agent执行中
  ↓ (Agent执行完成，3秒后)
ready
```

## 事件与状态映射

| 事件 | 触发状态 | 说明 |
|------|---------|------|
| `WAKEWORD_DETECTED` | wake up | 唤醒词被检测到 |
| `VAD_SPEECH_START` | vad begin | 开始检测到语音活动 |
| `VAD_SPEECH_END` | vad end | 语音活动结束 |
| `ASR_RECOGNITION_START` | asr recognizing | ASR开始识别 ✨ |
| `ASR_RECOGNITION_SUCCESS` | orchestrator deciding | 识别成功，Orchestrator开始决策 ✨ |
| `GUI_UPDATE_TEXT` (orchestrator_decision) | agent running | Orchestrator决策完成，Agent开始执行 |
| `Agent完成` (定时器) | ready | Agent执行完成，回到就绪 |

## 异常处理

- **ASR识别失败** → 直接回到 `ready`
- **系统错误** → 显示错误信息，保持当前状态或回到 `ready`

## 代码实现位置

### ASR适配器
- `_start_recognition()` - 发送 `ASR_RECOGNITION_START` 事件 ✨

### GUI事件处理
- `on_wakeword_detected()` - 设置状态为 "wake up"
- `on_vad_speech_start()` - 设置状态为 "vad begin"
- `on_vad_speech_end()` - 设置状态为 "vad end"
- `on_asr_start()` - 设置状态为 "asr recognizing" ✨
- `on_asr_result()` - 设置状态为 "orchestrator deciding" ✨修改
- `on_orchestrator_decision()` - 设置状态为 "agent running"
- `_on_agent_complete()` - 设置状态为 "ready"

### 时序控制
- Agent执行完成：使用 `QTimer.singleShot(3000, ...)` 模拟3秒执行时间
- 后续可替换为真实的Agent执行完成事件

## 示例日志

```
Status: ready
  ↓ 说"小智小智"
Status: wake up
  ↓ 开始说话
Status: vad begin
  ↓ 说话结束
Status: vad end
  ↓ ASR开始处理
Status: asr recognizing ← 新增
  ↓ 识别完成：给我推荐一首好听的歌曲
Status: orchestrator deciding ← 新增
  ↓ Orchestrator决策：music_agent
Status: agent running
  ↓ Agent执行中...
  ↓ (3秒后完成)
Status: ready
```

## 下一步优化

1. ✅ 添加ASR识别中状态
2. ✅ 添加Agent运行中状态
3. 🔲 实现真实的Agent执行和完成事件
4. 🔲 添加超时处理（如ASR超时、Agent超时）
5. 🔲 添加状态历史记录显示
