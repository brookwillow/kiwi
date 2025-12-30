# Orchestrator 集成说明

## 概述

Orchestrator模块已成功集成到Kiwi语音助手系统中，负责接收ASR识别结果并智能选择合适的Agent进行处理。

## 架构设计

```
ASR模块 → ASR_RECOGNITION_SUCCESS事件 → SystemController → Orchestrator → Agent分发
```

### 核心组件

1. **AgentsModule** (`src/agents/module.py`)
   - 从`config/agents_config.yaml`加载Agent配置
   - 提供可用Agent列表给Orchestrator

2. **OrchestratorModuleAdapter** (`src/adapters/orchestrator_adapter.py`)
   - 监听`ASR_RECOGNITION_SUCCESS`事件
   - 调用Orchestrator进行决策
   - 分发任务给对应的Agent

3. **Orchestrator核心** (`src/orchestrator/`)
   - 召回短期记忆（对话历史）
   - 召回长期记忆（用户画像）
   - 获取系统状态
   - 调用LLM进行Agent选择决策

## 配置文件

### 1. Agents配置 (`config/agents_config.yaml`)

定义所有可用的Agent：

```yaml
agents:
  - name: "music_agent"
    description: "音乐播放和控制Agent"
    enabled: true
    capabilities:
      - "播放音乐"
      - "暂停音乐"
      - "调节音量"
  
  - name: "navigation_agent"
    description: "导航和路线规划Agent"
    enabled: true
    capabilities:
      - "路线规划"
      - "实时导航"
  
  # ... 更多Agent
```

### 2. Orchestrator配置 (`config/orchestrator_config.yaml`)

```yaml
orchestrator:
  llm:
    provider: "dashscope"
    model: "qwen-plus"
    temperature: 0.3
  
  decision:
    use_mock_llm: false  # 是否使用模拟LLM
    default_agent: "chat_agent"
```

## 使用方式

### 1. 启动完整系统

```bash
# 设置API Key（可选，不设置则使用模拟LLM）
export DASHSCOPE_API_KEY='your-api-key'

# 启动GUI系统
python main.py
```

系统会自动：
1. 加载Agents配置
2. 初始化Orchestrator
3. 监听ASR识别结果
4. 进行智能决策和分发

### 2. 测试Orchestrator集成

```bash
# 模拟ASR事件测试
python test_orchestrator_integration.py
```

### 3. 单独测试Orchestrator

```bash
# 测试Orchestrator逻辑（不依赖完整系统）
python test_orchestrator.py
```

## 工作流程

1. **语音识别**
   - 用户说话 → VAD检测 → ASR识别 → 生成`ASR_RECOGNITION_SUCCESS`事件

2. **Orchestrator决策**
   ```python
   ASR事件 → Orchestrator接收
   ↓
   召回上下文（记忆、状态、Agent列表）
   ↓
   调用LLM决策（或使用模拟LLM）
   ↓
   返回决策结果（Agent名称、置信度、理由）
   ```

3. **Agent分发**
   - Orchestrator将任务分发给选定的Agent
   - Agent执行具体任务
   - 返回执行结果

## 示例输出

```
============================================================
🎯 Orchestrator收到ASR结果: 播放周杰伦的晴天
   置信度: 0.95

============================================================
📊 Orchestrator 决策结果
============================================================
用户查询: 播放周杰伦的晴天
选中Agent: music_agent
置信度: 0.90
决策理由: 检测到关键词'播放'，选择music_agent
============================================================

📍 决策结果:
   选择Agent: music_agent
   置信度: 0.90
   理由: 检测到关键词'播放'，选择music_agent
============================================================

🚀 [分发] music_agent <- '播放周杰伦的晴天'
```

## LLM模式

### 模拟LLM模式（默认）

- 基于关键词匹配进行决策
- 无需API Key
- 适合开发和测试

### 真实LLM模式（阿里百炼通义千问）

```bash
# 1. 设置环境变量
export DASHSCOPE_API_KEY='your-api-key'

# 2. 修改配置
# config/orchestrator_config.yaml
use_mock_llm: false

# 3. 启动系统
python main.py
```

## 扩展Agent

在`config/agents_config.yaml`中添加新的Agent：

```yaml
agents:
  - name: "your_new_agent"
    description: "你的Agent描述"
    enabled: true
    capabilities:
      - "功能1"
      - "功能2"
```

无需修改代码，Orchestrator会自动识别新的Agent。

## 调试

启用详细日志：

```python
# 创建Controller时
controller = SystemController(debug=True)
```

查看完整的事件流和决策过程。

## 下一步

- [ ] 实现真实的Agent执行模块
- [ ] 添加Memory模块存储对话历史
- [ ] 添加Perception模块获取系统状态
- [ ] 实现Agent执行结果反馈
- [ ] 添加多轮对话支持
