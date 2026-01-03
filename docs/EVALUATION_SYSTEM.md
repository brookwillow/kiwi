# 评估系统文档

## 概述

Kiwi语音助手的评估系统用于自动化测试和评估系统性能，包括Agent选择准确率和响应质量评估。

## 功能特性

### 1. 测试数据集
- **位置**: `data/test_cases.jsonl`
- **格式**: JSONL（每行一个JSON对象）
- **测试用例数量**: 107个
- **覆盖类别**:
  - 天气查询 (8个)
  - 音乐控制 (14个)
  - 导航服务 (18个)
  - 电话功能 (6个)
  - 车辆控制 (24个)
  - 车辆状态 (10个)
  - 任务规划 (10个)
  - 通用对话 (17个)

### 2. 评估引擎
- **核心模块**: `src/evaluation/evaluator.py`
- **主要组件**:
  - `TestCase`: 测试用例数据结构
  - `SystemEvaluator`: 评估执行器
  - `QwenEvaluator`: 使用Qwen Plus模型进行响应质量评估
  - `EvaluationResult`: 评估结果统计

### 3. 评估界面
- **GUI模块**: `src/evaluation/evaluation_window.py`
- **功能**:
  - 测试用例列表展示
  - 实时进度显示
  - 通过率统计
  - 详细结果查看
  - 结果导出

## 使用方法

### 启动评估

1. 启动主GUI应用
   ```bash
   python main.py
   ```

2. 点击 "🔍 性能评估" 按钮打开评估窗口

3. 点击 "开始评估" 运行所有测试用例

### 查看结果

- **实时查看**: 评估过程中实时显示进度和通过率
- **详细信息**: 点击任意测试用例查看详细评估信息
- **导出报告**: 点击 "导出结果" 保存评估报告

### 评估报告位置

评估结果自动保存到：
```
logs/evaluation_results/evaluation_YYYYMMDD_HHMMSS.json
```

## 评估指标

### 1. Agent准确率
- 衡量系统是否选择了正确的Agent处理用户请求
- 计算公式: `正确选择的Agent数 / 总测试用例数`

### 2. 响应通过率
- 使用Qwen Plus模型评估响应质量
- 判断实际响应是否符合预期响应类型
- 计算公式: `通过评估的响应数 / 总测试用例数`

### 3. 总体通过率
- 同时满足Agent正确和响应通过的用例比例
- 计算公式: `完全通过的用例数 / 总测试用例数`

### 4. 平均响应时间
- 每个测试用例的平均处理时间（毫秒）
- 包括ASR、Orchestrator决策、Agent执行的总时间

## 评估模式特性

### 禁用TTS播放
评估模式下自动禁用TTS播放，优势：
- 加快评估速度（无需等待语音播报）
- 避免干扰（静默运行）
- 只需等待文本响应即可进行评估

### 智能等待机制
- 使用轮询方式等待Agent响应完成
- 最多等待5秒，每100ms检查一次
- 检测到响应后立即进行评估
- 避免超时或提前评估的问题

## 测试用例格式

```json
{
  "query": "用户查询文本",
  "expected_agent": "预期的Agent名称",
  "expected_response": "预期响应类型描述",
  "category": "测试类别"
}
```

### 支持的Agent类型
- `weather_agent`: 天气查询
- `music_agent`: 音乐控制
- `navigation_agent`: 导航服务
- `phone_agent`: 电话功能
- `vehicle_control_agent`: 车辆控制
- `vehicle_status_agent`: 车辆状态查询
- `planner_agent`: 任务规划
- `chat_agent`: 通用对话

## 添加新测试用例

编辑 `data/test_cases.jsonl`，每行添加一个JSON对象：

```bash
echo '{"query": "新的测试查询", "expected_agent": "agent_name", "expected_response": "预期响应描述", "category": "类别"}' >> data/test_cases.jsonl
```

## Qwen Plus评估

系统使用阿里云Qwen Plus模型评估响应质量：

### 配置API密钥
```bash
export DASHSCOPE_API_KEY="your_api_key_here"
```

### 评估逻辑
- 比较实际响应与预期响应类型
- 判断实际响应是否满足预期需求
- 提供评估理由和建议

### 降级方案
如果未配置API密钥，系统会使用基于规则的简单评估。

## 技术架构

### 消息追踪集成
评估系统完全集成了消息追踪系统（msgId），可以：
- 追踪每个测试用例的完整处理流程
- 记录各模块的输入输出
- 分析性能瓶颈
- 调试问题

### 事件驱动
- 通过发布ASR_RECOGNITION_SUCCESS事件触发评估
- 利用现有的事件处理管道
- 无需修改核心业务逻辑

### 并发安全
- 使用线程池执行评估
- GUI线程和评估线程分离
- 实时更新进度信息

## 性能优化

1. **并发执行**: 评估在独立线程中运行，不阻塞GUI
2. **禁用TTS**: 评估模式下跳过语音播报
3. **智能等待**: 轮询检查而非固定延迟
4. **批量处理**: 一次性加载所有测试用例

## 故障排查

### 评估失败
- 检查系统是否正常启动
- 确认所有Agent已注册
- 查看日志文件中的错误信息

### 响应评估失败
- 检查DASHSCOPE_API_KEY是否配置
- 验证网络连接
- 查看Qwen Plus API调用是否成功

### 超时问题
- 增加等待时间（修改evaluator.py中的max_wait）
- 检查Agent执行是否异常缓慢
- 确认消息追踪是否正常工作

## 未来改进

- [ ] 支持并行评估多个测试用例
- [ ] 添加性能基准对比
- [ ] 支持自定义评估规则
- [ ] 生成更详细的HTML报告
- [ ] 集成CI/CD自动化测试
- [ ] 支持A/B测试不同配置

## 相关文档

- [消息追踪系统](MESSAGE_TRACKING.md)
- [Agent架构](AGENT_ARCHITECTURE.md)
- [Orchestrator](ORCHESTRATOR.md)
