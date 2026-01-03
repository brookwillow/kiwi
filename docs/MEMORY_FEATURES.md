# 记忆系统优化功能说明

## 概述

本次优化为Kiwi语音助手添加了三个重要的记忆管理功能：

1. **长期记忆持久化** - 系统关闭后记忆不会丢失
2. **记忆管理页面** - 可视化管理所有记忆数据
3. **记忆召回显示** - 实时显示Agent使用的记忆上下文

## 功能详情

### 1. 长期记忆持久化

**功能说明**：
- 长期记忆（用户画像、偏好等）自动保存到JSON文件
- 系统启动时自动加载历史记忆
- 每次更新长期记忆时自动保存

**文件位置**：
```
./data/long_term_memory.json
```

**数据结构**：
```json
{
  "summary": "对话摘要",
  "profile": {
    "name": "用户姓名",
    "age": 30,
    "occupation": "职业",
    "father_name": "父亲姓名",
    "father_phone": "父亲电话"
  },
  "preferences": {
    "music": ["流行", "摇滚"],
    "food": ["川菜"]
  },
  "metadata": {
    "last_update": 1234567890.0,
    "update_count": 5
  }
}
```

**使用方式**：
- 无需手动操作，系统自动管理
- 启动时会显示：`📂 已加载历史长期记忆`
- 更新时会显示：`💾 长期记忆已保存到: ./data/long_term_memory.json`

### 2. 记忆管理页面

**打开方式**：
主界面点击 **"记忆管理"** 按钮（橙色）

**功能特性**：

#### 短期记忆Tab 📝
- **表格显示**：时间、查询、响应、Agent、操作
- **单个删除**：点击 🗑️ 按钮删除指定记忆
- **查看详情**：完整的查询和响应内容
- **自动刷新**：每2秒自动更新

#### 长期记忆Tab 💾
- **摘要显示**：对话总结
- **用户画像**：姓名、年龄、职业等
- **用户偏好**：音乐、美食、旅行等
- **元数据**：更新时间、更新次数

#### 操作按钮
1. **🔄 刷新** - 手动刷新记忆数据
2. **🗑️ 清空短期记忆** - 删除所有对话历史（保留长期记忆）
3. **⚠️ 清空所有记忆** - 删除全部记忆（包括长期记忆和向量数据库）

**统计信息**：
```
📊 统计: 短期记忆 10 条 | 向量库短期 10 条 | 向量库长期 5 条
```

### 3. 主界面记忆显示

**功能说明**：
当Agent执行时，主界面右侧会实时显示召回的记忆上下文

**显示区域**：
- **左侧：短期记忆** 📝
  - 最近记忆：按时间顺序的最新对话
  - 相关记忆：基于语义相似度的相关对话
  
- **右侧：长期记忆** 🧠
  - 用户画像
  - 用户偏好
  - 对话摘要

**显示格式**：
```
🧠 Agent: navigation_agent 的记忆召回
==================================================

📝 最近记忆 (3 条):
1. [16:30:15] 导航去公司...
   回复: 已开始导航...

🔍 相关记忆 (2 条):
1. [16:25:10] 导航到中关村...
   回复: 正在规划路线...
```

## 数据流程

```
用户查询
  ↓
Orchestrator 决策
  ↓
Agent Manager 召回记忆
  ├─ 最近记忆 (按时间)
  ├─ 相关记忆 (按相似度)
  └─ 长期记忆 (用户画像)
  ↓
发送到 GUI 显示
  ↓
Agent 执行
  ↓
保存新记忆
  ├─ 内存列表
  ├─ 向量数据库
  └─ JSON文件 (长期记忆)
```

## 技术细节

### 记忆类型

1. **短期记忆 (ShortTermMemory)**
   - 存储：内存列表 + ChromaDB向量库
   - 召回方式：
     - 时间顺序：最近5条
     - 语义相似度：最相关3条（阈值0.7）
   - 向量化：只使用用户query生成embedding

2. **长期记忆 (LongTermMemory)**
   - 存储：内存对象 + JSON文件 + ChromaDB向量库
   - 生成方式：每10条短期记忆触发LLM提取
   - 字段拆分：每个profile和preference字段独立存储向量

### AgentContext 结构

```python
@dataclass
class AgentContext:
    recent_memories: List[ShortTermMemory]    # 最近记忆
    related_memories: List[ShortTermMemory]   # 相关记忆
    long_term_memory: Optional[LongTermMemory]  # 长期记忆
    system_states: List[SystemState]          # 系统状态
    
    @property
    def short_term_memories(self):
        """向后兼容：合并所有短期记忆"""
        return recent_memories + related_memories  # 去重
```

### 向量数据库配置

- **数据库**: ChromaDB
- **路径**: `./data/chroma_db`
- **距离算法**: 余弦相似度 (cosine)
- **Embedding模型**: ollama bge-m3:latest (1024维)
- **Collections**:
  - `short_term_memories`: 对话记忆
  - `long_term_memories`: 用户画像字段

## 配置参数

在 `src/memory/memory.py` 中可调整：

```python
MemoryManager(
    api_key="...",                    # LLM API密钥
    trigger_count=10,                 # 触发长期记忆生成的对话数
    max_history_rounds=30,            # 生成时使用的最大历史轮数
    embedding_model="bge-m3:latest",  # Embedding模型
    db_path="./data/chroma_db",       # 向量库路径
    long_term_memory_file="./data/long_term_memory.json"  # 持久化文件
)
```

在召回时可调整：

```python
# 时间顺序召回
get_short_term_memories(max_count=5)

# 语义相似度召回
get_related_short_memories(
    query="...",
    max_count=3,
    similarity_threshold=0.7  # 0-1之间，越高越严格
)
```

## 使用建议

### 查看记忆
1. 使用"记忆管理"按钮查看所有记忆
2. 观察主界面的实时召回显示
3. 检查日志输出的记忆召回信息

### 清理记忆
1. **清空短期记忆**：删除对话历史，保留用户画像
2. **清空所有记忆**：完全重置，谨慎使用
3. **单个删除**：在记忆管理页面删除特定记忆

### 调优建议
1. **相似度阈值**：
   - 0.8+：只召回高度相关的
   - 0.7：默认值，平衡
   - 0.5-：召回更多可能相关的

2. **召回数量**：
   - 最近记忆：3-5条（保证连贯性）
   - 相关记忆：2-3条（避免噪音）

3. **触发频率**：
   - trigger_count：5-15条合适
   - 太少：频繁调用LLM
   - 太多：错过重要信息

## 故障排查

### 长期记忆未加载
- 检查文件是否存在：`./data/long_term_memory.json`
- 查看启动日志是否有加载提示
- 确认JSON格式正确

### 向量检索无结果
- 检查相似度阈值是否过高
- 确认ollama服务运行正常
- 查看embedding模型是否已下载

### GUI不显示记忆
- 确认agent_manager发送了记忆召回事件
- 检查GUI适配器的信号连接
- 查看控制台是否有错误日志

## 后续扩展

可能的改进方向：
1. 支持记忆搜索和过滤
2. 记忆导出和导入功能
3. 记忆重要性评分和优先级
4. 跨会话的记忆关联
5. 记忆可视化图谱
