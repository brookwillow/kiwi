import time
import json
import ollama
import chromadb
from chromadb.config import Settings
from typing import List, Optional, Dict, Any
from src.core.events import ShortTermMemory, LongTermMemory



class MemoryManager:
    def __init__(self, api_key: Optional[str] = None, 
                 trigger_count: int = 10,
                 max_history_rounds: int = 30,
                 embedding_model: str = "bge-m3:latest",
                 db_path: str = "./data/chroma_db",
                 long_term_memory_file: str = "./data/long_term_memory.json"):
        """初始化MemoryManager
        
        Args:
            api_key: 阿里百炼API密钥，用于生成长期记忆
            trigger_count: 每积累多少条短期记忆触发一次长期记忆生成
            max_history_rounds: 生成长期记忆时最多使用多少轮对话历史
            embedding_model: ollama embedding模型名称
            db_path: chromadb数据库存储路径
            long_term_memory_file: 长期记忆持久化文件路径
        """
        self.memories = []
        self.long_term_memory_data = {
            "summary": "",
            "profile": {},
            "preferences": {},
            "metadata": {}
        }
        self.api_key = api_key
        self.llm_client = None
        self.trigger_count = trigger_count
        self.max_history_rounds = max_history_rounds
        self.long_term_memory_file = long_term_memory_file
        
        # 向量数据库配置
        self.embedding_model = embedding_model
        self.db_path = db_path
        
        # 加载历史长期记忆
        self._load_long_term_memory()
        
        # 初始化ChromaDB
        self._init_vector_db()
        
        # 如果提供了API密钥，初始化LLM客户端
        if api_key:
            from openai import OpenAI
            self.llm_client = OpenAI(
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
    
    def _init_vector_db(self):
        """初始化向量数据库"""
        try:
            self.chroma_client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # 检查并重建collection（如果距离函数不匹配）
            try:
                # 尝试获取现有collection
                existing_short = self.chroma_client.get_collection("short_term_memories")
                # 检查距离函数
                if existing_short.metadata.get("hnsw:space") != "cosine":
                    print("⚠️  检测到旧的短期记忆collection使用L2距离，删除并重建...")
                    self.chroma_client.delete_collection("short_term_memories")
                    existing_short = None
            except:
                existing_short = None
            
            try:
                existing_long = self.chroma_client.get_collection("long_term_memories")
                if existing_long.metadata.get("hnsw:space") != "cosine":
                    print("⚠️  检测到旧的长期记忆collection使用L2距离，删除并重建...")
                    self.chroma_client.delete_collection("long_term_memories")
                    existing_long = None
            except:
                existing_long = None
            
            # 创建或获取短期记忆collection（使用余弦相似度）
            self.short_term_collection = self.chroma_client.get_or_create_collection(
                name="short_term_memories",
                metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
            )
            
            # 创建或获取长期记忆collection（使用余弦相似度）
            self.long_term_collection = self.chroma_client.get_or_create_collection(
                name="long_term_memories",
                metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
            )
            
            print(f"✅ 向量数据库初始化成功 (路径: {self.db_path})")
            print(f"   距离算法: 余弦相似度 (cosine)")
            print(f"   短期记忆数: {self.short_term_collection.count()}")
            print(f"   长期记忆数: {self.long_term_collection.count()}")
            
        except Exception as e:
            print(f"❌ 向量数据库初始化失败: {e}")
            self.chroma_client = None
            self.short_term_collection = None
            self.long_term_collection = None
    
    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """使用ollama生成文本的embedding向量
        
        Args:
            text: 输入文本
            
        Returns:
            embedding向量列表，失败返回None
        """
        try:
            response = ollama.embeddings(
                model=self.embedding_model,
                prompt=text
            )
            return response['embedding']
        except Exception as e:
            print(f"⚠️ 生成embedding失败: {e}")
            return None
    
    def add_short_term_memory(self, event: dict):
        """添加对话记录"""

        memory = ShortTermMemory(
            query=event.get('query', ''),
            response=event.get('response', ''),
            timestamp=event.get('timestamp', time.time()),
            agent=event.get('agent', ''),
            tools_used=event.get('tools_used', []),
            description=f"用户查询: {event.get('query', '')} | 系统响应: {event.get('response', '')}",
            success=event.get('success', True),
            metadata=event.get('data', {})
        )
        print(f"Adding conversation: memory={memory}")
        self.memories.append(memory)
        
        # 存储到向量数据库
        self._store_short_term_memory_to_vector_db(memory)
        
        # 每积累指定数量的短期记忆，自动生成一次长期记忆
        if len(self.memories) % self.trigger_count == 0 and len(self.memories) > 0:
            print(f"📊 已累积{len(self.memories)}条短期记忆，触发长期记忆生成...")
            self._generate_long_term_memory()
    
    def _store_short_term_memory_to_vector_db(self, memory: ShortTermMemory):
        """将短期记忆存储到向量数据库
        
        Args:
            memory: 短期记忆对象
        """
        if not self.short_term_collection:
            return
        
        try:
            # 只使用用户查询做向量化（因为我们主要基于用户意图检索）
            # 这样相同的查询会有接近1.0的相似度
            text = memory.query
            
            # 生成embedding
            embedding = self._generate_embedding(text)
            if not embedding:
                return
            
            # 生成唯一ID
            memory_id = f"stm_{int(memory.timestamp * 1000)}"
            
            # 存储到向量数据库
            # document存储完整信息用于展示，但embedding只基于query
            self.short_term_collection.add(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[f"用户: {memory.query}\n助手: {memory.response}"],  # 完整文本用于展示
                metadatas=[{
                    "query": memory.query,
                    "response": memory.response,
                    "timestamp": memory.timestamp,
                    "agent": memory.agent,
                    "success": memory.success
                }]
            )
            
        except Exception as e:
            print(f"⚠️ 存储短期记忆到向量数据库失败: {e}")
    
    def get_short_term_memories(self, max_count: int = 5):
        """获取短期记忆（按时间顺序）
        
        Args:
            max_count: 最多返回的记忆数量
        
        Returns:
            短期记忆列表（按时间顺序，最近的在后）
        """
        try:
            # 直接获取最近的对话记忆
            short_memories = self.memories[-max_count:] if self.memories else []
            print(f"Retrieved {len(short_memories)} short term memories (by time)")
            return short_memories
        except Exception as e:
            print(f"获取短期记忆失败: {e}")
            return []
    
    def get_related_short_memories(self, query: str, max_count: int = 5, similarity_threshold: float = 0.7):
        """基于向量相似度获取相关记忆（语义检索）
        
        Args:
            query: 查询文本，用于语义相似度检索
            max_count: 最多返回的记忆数量
            similarity_threshold: 相似度阈值（0-1），默认0.7，只返回相似度超过此值的记忆
        
        Returns:
            短期记忆列表（按相似度排序，最相关的在前），如果向量数据库不可用则返回空列表
        """
        try:
            # 如果向量数据库可用，使用语义相似度召回
            if self.short_term_collection:
                return self._retrieve_memories_by_similarity(
                    query=query,
                    collection=self.short_term_collection,
                    max_count=max_count,
                    similarity_threshold=similarity_threshold
                )
            else:
                print("⚠️ 向量数据库不可用，返回空列表")
                return []
        except Exception as e:
            print(f"⚠️ 语义检索失败: {e}，返回空列表")
            return []
    
    def _retrieve_memories_by_similarity(self, query: str, collection, max_count: int = 5, 
                                       similarity_threshold: float = 0.7) -> List[ShortTermMemory]:
        """基于向量相似度检索记忆
        
        Args:
            query: 查询文本
            collection: chromadb collection
            max_count: 最多返回数量
            similarity_threshold: 相似度阈值（0-1），使用余弦相似度时，阈值越高越相似
                                 默认0.7表示只返回相似度>0.7的结果
            
        Returns:
            短期记忆列表
        """
        try:
            # 生成query的embedding
            query_embedding = self._generate_embedding(query)
            if not query_embedding:
                print("⚠️ 无法生成查询embedding，使用最近记忆")
                return self.memories[-max_count:] if self.memories else []
            
            # 在向量数据库中搜索最相似的记忆
            # 查询更多结果以便过滤
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=max_count * 2  # 查询2倍数量，便于阈值过滤后还有足够结果
            )
            
            # 转换为ShortTermMemory对象，并应用相似度阈值
            memories = []
            if results['metadatas'] and results['metadatas'][0] and results['distances']:
                for i, metadata in enumerate(results['metadatas'][0]):
                    distance = results['distances'][0][i]
                    
                    # ChromaDB使用cosine距离时: 余弦相似度 = 1 - 余弦距离
                    # 余弦距离范围 [0, 2]，余弦相似度范围 [-1, 1]
                    # 距离越小越相似
                    similarity = 1 - distance
                    
                    # 应用阈值过滤
                    if similarity < similarity_threshold:
                        print(f"   ⏭️  跳过低相似度记忆: {metadata.get('query', '')[:30]}... (相似度: {similarity:.4f}, 距离: {distance:.4f})")
                        continue
                    
                    # 如果已经收集够数量，停止
                    if len(memories) >= max_count:
                        break
                    
                    memory = ShortTermMemory(
                        query=metadata.get('query', ''),
                        response=metadata.get('response', ''),
                        timestamp=metadata.get('timestamp', 0),
                        agent=metadata.get('agent', ''),
                        tools_used=[],
                        description=f"用户查询: {metadata.get('query', '')} | 系统响应: {metadata.get('response', '')}",
                        success=metadata.get('success', True),
                        metadata={}
                    )
                    memories.append(memory)
            
            print(f"🔍 基于语义相似度检索到 {len(memories)} 条相关记忆 (阈值: {similarity_threshold})")
            print(f"   查询内容: {query}")
            # 打印召回的内容和相似度分数
            if memories:
                for i, memory in enumerate(memories):
                    # 需要找到这个memory在原始results中的位置
                    for j, metadata in enumerate(results['metadatas'][0]):
                        if (metadata.get('timestamp') == memory.timestamp and 
                            metadata.get('query') == memory.query):
                            distance = results['distances'][0][j]
                            similarity = 1 - distance
                            print(f"   {i+1}. [{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(memory.timestamp))}] "
                                  f"用户: {memory.query[:50]}... | 相似度: {similarity:.4f}")
                            break
            return memories
            
        except Exception as e:
            print(f"⚠️ 向量检索失败: {e}，使用最近记忆")
            return self.memories[-max_count:] if self.memories else []
    
    def get_long_term_memory(self, return_raw: bool = False):
        """获取长期记忆（通用接口）
        
        Args:
            return_raw: 是否返回原始dict格式（True）还是LongTermMemory对象（False）
            
        Returns:
            LongTermMemory对象或dict 或 None
        """
        try:
            # 如果需要原始格式，直接返回
            if return_raw:
                return self.long_term_memory_data
            
            # 转换为LongTermMemory对象
            return LongTermMemory(
                summary=self.long_term_memory_data.get('summary', ''),
                user_profile=self.long_term_memory_data.get('profile', {}),
                preferences=self.long_term_memory_data.get('preferences', {}),
                metadata=self.long_term_memory_data.get('metadata', {})
            )
        except Exception as e:
            print(f"获取长期记忆失败: {e}")
            return None
        
    def get_related_long_term_memory(self, query: str = "") -> Optional[LongTermMemory]:
        """获取相关的长期记忆（目前直接返回全部长期记忆）
        
        Args:
            query: 查询文本（预留参数，当前未使用）
            
        Returns:
            LongTermMemory对象 或 None
        """
        try:
            # 目前不基于query过滤，直接返回全部长期记忆
            return LongTermMemory(
                summary=self.long_term_memory_data.get('summary', ''),
                user_profile=self.long_term_memory_data.get('profile', {}),
                preferences=self.long_term_memory_data.get('preferences', {}),
                metadata=self.long_term_memory_data.get('metadata', {})
            )
        except Exception as e:
            print(f"获取相关长期记忆失败: {e}")
            return None
    
    def get_statistics(self) -> dict:
        """获取统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'total_memories': len(self.memories),
            'short_term_count': len(self.memories)
        }
    
    def _save_long_term_memory(self):
        """保存长期记忆到文件"""
        try:
            import os
            # 确保目录存在
            os.makedirs(os.path.dirname(self.long_term_memory_file), exist_ok=True)
            
            with open(self.long_term_memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.long_term_memory_data, f, ensure_ascii=False, indent=2)
            
            print(f"💾 长期记忆已保存到: {self.long_term_memory_file}")
        except Exception as e:
            print(f"⚠️  保存长期记忆失败: {e}")
    
    def _load_long_term_memory(self):
        """从文件加载长期记忆"""
        try:
            import os
            if os.path.exists(self.long_term_memory_file):
                with open(self.long_term_memory_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    self.long_term_memory_data = loaded_data
                
                print(f"📂 已加载历史长期记忆")
                if self.long_term_memory_data.get('summary'):
                    print(f"   摘要: {self.long_term_memory_data['summary'][:50]}...")
                if self.long_term_memory_data.get('profile'):
                    print(f"   用户画像字段: {len(self.long_term_memory_data['profile'])} 个")
                if self.long_term_memory_data.get('preferences'):
                    print(f"   用户偏好字段: {len(self.long_term_memory_data['preferences'])} 个")
            else:
                print("📝 未找到历史长期记忆，将创建新的记忆")
        except Exception as e:
            print(f"⚠️  加载长期记忆失败: {e}，将使用空记忆")
    
    def _generate_long_term_memory(self):
        """使用模型，从短期记忆中抽取关键信息，生成长期记忆摘要、用户画像、偏好等"""
        
        if not self.llm_client:
            print("⚠️  未配置LLM客户端，无法生成长期记忆")
            return
        
        if not self.memories:
            print("⚠️  没有短期记忆，无法生成长期记忆")
            return
        
        try:
            # 只使用最近的N轮对话，避免历史过长
            recent_memories = self.memories[-self.max_history_rounds:] if len(self.memories) > self.max_history_rounds else self.memories
            
            # 构建对话历史
            conversations = []
            for memory in recent_memories:
                conversations.append({
                    "user": memory.query,
                    "assistant": memory.response,
                    "timestamp": memory.timestamp
                })
            
            print(f"🔍 使用最近{len(recent_memories)}轮对话生成长期记忆...")
            
            # 构建提示词
            prompt = f"""你是一个专业的用户画像分析师，负责从用户的对话历史中提取关键信息，生成用户的长期记忆。

**对话历史：**
{json.dumps(conversations, ensure_ascii=False, indent=2)}

**当前用户画像：**
{json.dumps(self.long_term_memory_data.get('profile', {}), ensure_ascii=False, indent=2)}

**当前用户偏好：**
{json.dumps(self.long_term_memory_data.get('preferences', {}), ensure_ascii=False, indent=2)}

**任务要求：**
1. 分析对话历史，提取用户的身份信息（如姓名、年龄、职业、住址等）
2. 提取家庭成员信息时，每个成员单独作为一个字段，格式如：father_name、father_phone、mother_name、mother_phone等
3. 提取用户的个人兴趣和喜好（如音乐类型、运动爱好、饮食偏好等）
4. 生成用户对话的总体摘要
5. 如果当前已有用户画像和偏好信息，请在现有基础上更新和补充，不要覆盖已有的准确信息
6. 只提取对话中明确提到的信息，不要猜测或推断

**输出格式（必须是有效的JSON）：**
{{
    "summary": "当前提供的对话历史的摘要，100字以内",
    "profile": {{
        "name": "用户姓名（如果提到）",
        "age": 用户年龄（如果提到，数字类型）,
        "gender": "性别（如果提到）",
        "occupation": "职业（如果提到）",
        "location": "居住地址（如果提到）",
        "father_name": "父亲姓名（如果提到）",
        "father_phone": "父亲电话（如果提到）",
        "mother_name": "母亲姓名（如果提到）",
        "mother_phone": "母亲电话（如果提到）",
    }},
    "preferences": {{
        "music": ["音乐类型偏好"],
        "food": ["饮食偏好"],
        "sports": ["运动爱好"],
        "travel": ["旅行偏好"],
        "language": "语言偏好",
    }}
}}

注意：
- 如果某个字段没有提到，请设置为空字符串、空数组或null
- 只输出JSON，不要包含任何其他文字说明
- 确保JSON格式正确，可以被解析
- profile中根据实际家庭成员灵活添加字段，如son_name、daughter_name、wife_name等
- preferences 中的字段根据对话内容灵活调整，可以添加新的字段
- 家庭成员信息每个成员单独存储，不要使用列表
"""
            
            print("🔍 正在从短期记忆中提取长期记忆...")
            
            # 调用LLM
            completion = self.llm_client.chat.completions.create(
                model="qwen-plus",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的用户画像分析系统，擅长从对话中提取用户的关键信息。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # 解析响应
            response_text = completion.choices[0].message.content
            extracted_data = json.loads(response_text)
            
            # 合并更新长期记忆
            self._merge_long_term_memory(extracted_data)
            
            # 存储到向量数据库
            self._store_long_term_memory_to_vector_db()
            
            # 保存到文件
            self._save_long_term_memory()
            
            print("✅ 长期记忆生成成功")
            print(f"   摘要: {self.long_term_memory_data.get('summary', '')}")
            print(f"   用户画像: {json.dumps(self.long_term_memory_data.get('profile', {}), ensure_ascii=False)}")
            print(f"   偏好信息: {json.dumps(self.long_term_memory_data.get('preferences', {}), ensure_ascii=False)}")
            
        except Exception as e:
            print(f"❌ 生成长期记忆失败: {e}")
    
    def _merge_long_term_memory(self, new_data: Dict[str, Any]):
        """合并新提取的长期记忆数据到现有数据中
        
        Args:
            new_data: 新提取的数据
        """
        # 更新摘要
        if new_data.get('summary'):
            self.long_term_memory_data['summary'] = new_data['summary']
        
        # 合并用户画像（不覆盖已有的非空值）
        if 'profile' in new_data:
            for key, value in new_data['profile'].items():
                if value and (not self.long_term_memory_data['profile'].get(key) or value != ""):
                    self.long_term_memory_data['profile'][key] = value
        
        # 合并偏好信息（累积列表，去重）
        if 'preferences' in new_data:
            for key, value in new_data['preferences'].items():
                if isinstance(value, list):
                    # 对于列表类型，累积并去重
                    existing = self.long_term_memory_data['preferences'].get(key, [])
                    if not isinstance(existing, list):
                        existing = []
                    combined = list(set(existing + value))
                    if combined:
                        self.long_term_memory_data['preferences'][key] = combined
                elif value:
                    # 对于其他类型，直接更新
                    self.long_term_memory_data['preferences'][key] = value
        
        # 更新元数据
        self.long_term_memory_data['metadata']['last_update'] = time.time()
        self.long_term_memory_data['metadata']['update_count'] = \
            self.long_term_memory_data['metadata'].get('update_count', 0) + 1
    
    def _store_long_term_memory_to_vector_db(self):
        """将长期记忆存储到向量数据库
        
        设计：
        1. 清空所有现有的长期记忆
        2. 将summary、profile和preferences的每个字段拆分为独立的记忆条目
        3. 每个条目单独生成embedding，便于精确检索
        """
        if not self.long_term_collection:
            return
        
        try:
            # 1. 清空所有现有的长期记忆
            print("🗑️  清空现有长期记忆...")
            try:
                # 获取所有ID并删除
                existing = self.long_term_collection.get()
                if existing['ids']:
                    self.long_term_collection.delete(ids=existing['ids'])
                    print(f"   已删除 {len(existing['ids'])} 条旧记忆")
            except Exception as e:
                print(f"   清空失败: {e}")
            
            # 2. 准备新的记忆条目
            memory_items = []
            
            # 2.1 存储摘要
            summary = self.long_term_memory_data.get('summary', '')
            if summary:
                memory_items.append({
                    'id': 'ltm_summary',
                    'text': f"用户对话摘要: {summary}",
                    'metadata': {
                        'type': 'summary',
                        'content': summary,
                        'last_update': self.long_term_memory_data.get('metadata', {}).get('last_update', 0)
                    }
                })
            
            # 2.2 存储用户画像的每个字段
            profile = self.long_term_memory_data.get('profile', {})
            for key, value in profile.items():
                if value:  # 只存储非空值
                    memory_items.append({
                        'id': f'ltm_profile_{key}',
                        'text': f"用户{key}: {value}",
                        'metadata': {
                            'type': 'profile',
                            'field': key,
                            'content': json.dumps(value) if isinstance(value, (list, dict)) else str(value),
                            'last_update': self.long_term_memory_data.get('metadata', {}).get('last_update', 0)
                        }
                    })
            
            # 2.3 存储用户偏好的每个字段
            preferences = self.long_term_memory_data.get('preferences', {})
            for key, value in preferences.items():
                if value:  # 只存储非空值
                    # 格式化显示
                    if isinstance(value, list):
                        display_value = ', '.join(str(v) for v in value)
                    else:
                        display_value = str(value)
                    
                    memory_items.append({
                        'id': f'ltm_preferences_{key}',
                        'text': f"用户偏好-{key}: {display_value}",
                        'metadata': {
                            'type': 'preferences',
                            'field': key,
                            'content': json.dumps(value) if isinstance(value, (list, dict)) else str(value),
                            'last_update': self.long_term_memory_data.get('metadata', {}).get('last_update', 0)
                        }
                    })
            
            # 3. 批量生成embedding并存储
            if memory_items:
                ids = []
                embeddings = []
                documents = []
                metadatas = []
                
                print(f"📝 准备存储 {len(memory_items)} 条长期记忆子项...")
                
                for item in memory_items:
                    # 生成embedding
                    embedding = self._generate_embedding(item['text'])
                    if embedding:
                        ids.append(item['id'])
                        embeddings.append(embedding)
                        documents.append(item['text'])
                        metadatas.append(item['metadata'])
                
                # 批量插入
                if ids:
                    self.long_term_collection.add(
                        ids=ids,
                        embeddings=embeddings,
                        documents=documents,
                        metadatas=metadatas
                    )
                    print(f"✅ 长期记忆已存储到向量数据库 (共 {len(ids)} 条子项)")
                    print(f"   - 摘要: 1 条")
                    print(f"   - 用户画像: {len([i for i in metadatas if i['type'] == 'profile'])} 条")
                    print(f"   - 用户偏好: {len([i for i in metadatas if i['type'] == 'preferences'])} 条")
                else:
                    print("⚠️  没有有效的长期记忆可存储")
            else:
                print("⚠️  长期记忆数据为空")
            
        except Exception as e:
            print(f"⚠️ 存储长期记忆到向量数据库失败: {e}")


