# 向量记忆功能使用指南

## 功能概述

系统已集成向量嵌入和向量数据库（ChromaDB），支持基于语义相似度的记忆召回。

### 主要特性

1. **自动向量化**: 所有短期和长期记忆会自动生成向量嵌入
2. **语义检索**: 支持基于语义相似度检索相关记忆
3. **持久化存储**: 使用ChromaDB进行本地持久化存储
4. **智能召回**: 根据用户查询自动召回最相关的历史记忆

## 技术栈

- **Embedding模型**: ollama `bge-m3:latest`
- **向量数据库**: ChromaDB
- **存储路径**: `./data/chroma_db/`

## 安装依赖

```bash
# 安装chromadb
pip install chromadb>=0.4.0

# 确保ollama已安装并拉取bge-m3模型
ollama pull bge-m3:latest
```

## 使用方法

### 1. 初始化MemoryManager

```python
from src.memory.memory import MemoryManager

# 使用默认配置
memory_manager = MemoryManager(
    embedding_model="bge-m3:latest",  # ollama embedding模型
    db_path="./data/chroma_db"        # 向量数据库存储路径
)
```

### 2. 添加短期记忆（自动向量化）

```python
# 添加对话记忆
memory_manager.add_short_term_memory({
    "query": "今天天气怎么样？",
    "response": "今天天气晴朗，温度25度。",
    "timestamp": time.time(),
    "agent": "weather_agent",
    "success": True
})
```

记忆会自动：
- 生成embedding向量
- 存储到ChromaDB
- 保存在内存列表中

### 3. 语义检索记忆

#### 基于相似度检索

```python
# 传入query参数，启用语义检索
memories = memory_manager.get_short_term_memories(
    max_count=5,
    query="今天会下雨吗？"  # 会召回天气相关的记忆
)

for memory in memories:
    print(f"Query: {memory.query}")
    print(f"Response: {memory.response}")
```

#### 获取最近记忆

```python
# 不传query参数，返回最近的记忆
recent_memories = memory_manager.get_short_term_memories(max_count=5)
```

### 4. 在Agent中使用

在Agent或Orchestrator中，记忆检索会自动使用语义相似度：

```python
# agent_manager.py 或 orchestrator.py
def _get_short_term_memories(self, query: str, max_count: int = 5):
    memory_module = self.controller.get_module('memory')
    if memory_module:
        # query参数会自动用于语义检索
        return memory_module.get_short_term_memories(max_count, query=query)
    return []
```

## 工作原理

### 短期记忆流程

```
用户对话 
  ↓
添加到内存列表
  ↓
生成文本表示: "用户: {query}\n助手: {response}"
  ↓
调用ollama bge-m3生成embedding向量
  ↓
存储到ChromaDB (id, embedding, document, metadata)
  ↓
可通过语义相似度检索
```

### 长期记忆流程

```
累积N条短期记忆
  ↓
LLM提取用户画像、偏好
  ↓
生成长期记忆文本
  ↓
生成embedding向量
  ↓
更新ChromaDB中的长期记忆
```

### 语义检索流程

```
用户查询
  ↓
生成query的embedding向量
  ↓
在ChromaDB中计算相似度
  ↓
返回Top-K最相似的记忆
  ↓
转换为ShortTermMemory对象
```

## 配置说明

### MemoryManager参数

```python
MemoryManager(
    api_key: Optional[str] = None,          # 阿里百炼API密钥（用于长期记忆生成）
    trigger_count: int = 10,                # 每N条短期记忆触发长期记忆生成
    max_history_rounds: int = 30,           # 长期记忆生成时使用的最大对话轮数
    embedding_model: str = "bge-m3:latest", # Ollama embedding模型
    db_path: str = "./data/chroma_db"       # ChromaDB存储路径
)
```

## 测试

运行测试脚本验证功能：

```bash
python test_vector_memory.py
```

测试内容包括：
- 向量数据库初始化
- 记忆添加和向量化
- 语义相似度检索
- 最近记忆获取

## 数据存储

### 存储结构

```
./data/chroma_db/
├── chroma.sqlite3           # ChromaDB主数据库
└── [collection_data]/       # 集合数据
    ├── short_term_memories/ # 短期记忆向量
    └── long_term_memories/  # 长期记忆向量
```

### 记忆条目结构

**短期记忆**:
- **ID**: `stm_{timestamp_ms}`
- **Document**: "用户: {query}\n助手: {response}"
- **Metadata**: query, response, timestamp, agent, success

**长期记忆**:
- **ID**: `ltm_latest` (固定ID，始终保留最新)
- **Document**: 摘要 + 用户画像 + 偏好信息
- **Metadata**: summary, profile, preferences, last_update

## 性能优化

1. **向量维度**: bge-m3模型生成1024维向量
2. **相似度计算**: 使用余弦相似度
3. **索引**: ChromaDB自动维护HNSW索引
4. **缓存**: 内存中保留最近记忆列表

## 注意事项

1. **Ollama服务**: 确保ollama服务正在运行
2. **模型下载**: 首次使用需下载bge-m3模型（约2GB）
3. **存储空间**: 向量数据会占用磁盘空间，注意定期清理
4. **异常处理**: 如果embedding生成失败，会降级到基于时间的检索

## 故障排查

### 问题1: "无法生成embedding"

```
⚠️ 生成embedding失败: connection refused
```

**解决方案**:
```bash
# 启动ollama服务
ollama serve

# 验证模型是否存在
ollama list | grep bge-m3
```

### 问题2: ChromaDB初始化失败

```
❌ 向量数据库初始化失败: ...
```

**解决方案**:
```bash
# 创建数据目录
mkdir -p ./data/chroma_db

# 检查权限
chmod -R 755 ./data
```

### 问题3: 检索结果不准确

**可能原因**:
- 记忆数量太少
- query描述不够清晰
- embedding模型未正确加载

**解决方案**:
- 增加max_count参数
- 提供更详细的query描述
- 验证embedding模型正常工作

## 示例代码

完整示例请参考 `test_vector_memory.py`

## 更新日志

### v1.0.0 (2026-01-03)
- ✅ 集成ollama bge-m3 embedding模型
- ✅ 添加ChromaDB向量数据库
- ✅ 实现短期记忆自动向量化
- ✅ 实现长期记忆向量存储
- ✅ 支持基于语义相似度的记忆召回
- ✅ 更新Agent和Orchestrator支持语义检索
