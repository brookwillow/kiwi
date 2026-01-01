import time
import json
from typing import List, Optional, Dict, Any
from src.core.events import ShortTermMemory, LongTermMemory



class MemoryManager:
    def __init__(self, api_key: Optional[str] = None, 
                 trigger_count: int = 10,
                 max_history_rounds: int = 30):
        """初始化MemoryManager
        
        Args:
            api_key: 阿里百炼API密钥，用于生成长期记忆
            trigger_count: 每积累多少条短期记忆触发一次长期记忆生成
            max_history_rounds: 生成长期记忆时最多使用多少轮对话历史
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
        
        # 如果提供了API密钥，初始化LLM客户端
        if api_key:
            from openai import OpenAI
            self.llm_client = OpenAI(
                api_key=api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
    
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
        
        # 每积累指定数量的短期记忆，自动生成一次长期记忆
        if len(self.memories) % self.trigger_count == 0 and len(self.memories) > 0:
            print(f"📊 已累积{len(self.memories)}条短期记忆，触发长期记忆生成...")
            self._generate_long_term_memory()
    
    def get_short_term_memories(self, max_count: int = 5):
        """获取短期记忆（通用接口）
        """
        try:
            # 直接获取最近的对话记忆
            short_memories = self.memories[-max_count:] if self.memories else []
            print(f"Retrieved {len(short_memories)} short term memories")

            return short_memories
        except Exception as e:
            print(f"获取短期记忆失败: {e}")
            return []
    
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
    
    def get_statistics(self) -> dict:
        """获取统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'total_memories': len(self.memories),
            'short_term_count': len(self.memories)
        }
    
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
1. 分析对话历史，提取用户的身份信息（如姓名、年龄、职业、住址、家庭成员等）
2. 提取用户的个人兴趣和喜好（如音乐类型、运动爱好、饮食偏好等）
3. 生成用户对话的总体摘要
4. 如果当前已有用户画像和偏好信息，请在现有基础上更新和补充，不要覆盖已有的准确信息
5. 只提取对话中明确提到的信息，不要猜测或推断

**输出格式（必须是有效的JSON）：**
{{
    "summary": "用户对话的总体摘要，100字以内",
    "profile": {{
        "name": "用户姓名（如果提到）",
        "age": 用户年龄（如果提到，数字类型）,
        "gender": "性别（如果提到）",
        "occupation": "职业（如果提到）",
        "location": "居住地址（如果提到）",
        "family": ["家庭成员信息"],
        "other_facts": ["其他个人事实信息"]
    }},
    "preferences": {{
        "music": ["音乐类型偏好"],
        "food": ["饮食偏好"],
        "sports": ["运动爱好"],
        "travel": ["旅行偏好"],
        "language": "语言偏好",
        "other_interests": ["其他兴趣爱好"]
    }}
}}

注意：
- 如果某个字段没有提到，请设置为空字符串、空数组或null
- 只输出JSON，不要包含任何其他文字说明
- 确保JSON格式正确，可以被解析
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


