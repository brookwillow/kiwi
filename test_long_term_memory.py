"""
测试长期记忆生成功能
"""
import os
import time
from src.memory.memory import MemoryManager

def test_long_term_memory_generation():
    """测试从短期记忆生成长期记忆"""
    
    # 从环境变量获取API key
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ 请设置DASHSCOPE_API_KEY环境变量")
        return
    
    # 创建MemoryManager，配置参数
    memory_manager = MemoryManager(
        api_key=api_key,
        trigger_count=10,  # 每10条触发一次
        max_history_rounds=30  # 最多使用30轮历史
    )
    
    print(f"📋 配置: 每{memory_manager.trigger_count}条对话触发一次，最多使用{memory_manager.max_history_rounds}轮历史\n")
    
    # 模拟添加一些对话记忆
    conversations = [
        {
            "query": "你好，我叫张伟",
            "response": "你好张伟！很高兴认识你。",
            "agent": "chat_agent",
            "timestamp": time.time(),
            "success": True
        },
        {
            "query": "我住在北京海淀区",
            "response": "好的，记住了，您住在北京海淀区。",
            "agent": "chat_agent",
            "timestamp": time.time(),
            "success": True
        },
        {
            "query": "我是一名软件工程师",
            "response": "了解了，您是软件工程师。",
            "agent": "chat_agent",
            "timestamp": time.time(),
            "success": True
        },
        {
            "query": "我今年30岁",
            "response": "好的，您今年30岁。",
            "agent": "chat_agent",
            "timestamp": time.time(),
            "success": True
        },
        {
            "query": "我喜欢听流行音乐和摇滚乐",
            "response": "明白了，您喜欢流行音乐和摇滚乐。",
            "agent": "chat_agent",
            "timestamp": time.time(),
            "success": True
        },
        {
            "query": "周末喜欢去爬山",
            "response": "很好的爱好！爬山对身体很有益。",
            "agent": "chat_agent",
            "timestamp": time.time(),
            "success": True
        },
        {
            "query": "我平时喜欢吃川菜",
            "response": "川菜很美味，我记住了您的口味偏好。",
            "agent": "chat_agent",
            "timestamp": time.time(),
            "success": True
        },
        {
            "query": "我有一个女儿，今年5岁",
            "response": "原来您有一个5岁的女儿，真好！",
            "agent": "chat_agent",
            "timestamp": time.time(),
            "success": True
        },
        {
            "query": "我喜欢去日本旅游",
            "response": "日本是个很不错的旅游目的地。",
            "agent": "chat_agent",
            "timestamp": time.time(),
            "success": True
        },
        {
            "query": "我通常使用中文交流",
            "response": "好的，我会继续使用中文和您交流。",
            "agent": "chat_agent",
            "timestamp": time.time(),
            "success": True
        }
    ]
    
    print("📝 开始添加短期记忆...")
    for i, conv in enumerate(conversations, 1):
        memory_manager.add_short_term_memory(conv)
        print(f"   已添加第{i}条记忆")
        time.sleep(0.1)
    
    print("\n" + "="*60)
    print("📊 短期记忆统计:")
    stats = memory_manager.get_statistics()
    print(f"   总计: {stats['total_memories']}条")
    
    print("\n" + "="*60)
    print("🧠 长期记忆内容:")
    long_term = memory_manager.get_long_term_memory(return_raw=True)
    print(f"   摘要: {long_term.get('summary', '')}")
    print(f"   用户画像: {long_term.get('profile', {})}")
    print(f"   偏好信息: {long_term.get('preferences', {})}")
    print("="*60)

if __name__ == "__main__":
    test_long_term_memory_generation()
