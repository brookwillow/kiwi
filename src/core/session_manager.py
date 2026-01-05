"""
会话管理器 - 支持多轮对话和会话栈

负责管理Agent的执行上下文，支持暂停/恢复、会话嵌套等功能
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid


@dataclass
class AgentSession:
    """Agent会话状态"""
    session_id: str                          # 会话ID
    agent_name: str                          # Agent名称
    state: str                               # 状态: running, waiting_input, paused, completed, error
    context: Dict[str, Any] = field(default_factory=dict)  # 上下文数据
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())
    
    # 等待用户输入的提示
    pending_prompt: Optional[str] = None
    # 期望的输入类型
    expected_input_type: Optional[str] = None
    
    # 优先级：数字越大优先级越高
    priority: int = 0
    
    # 是否允许被打断
    interruptible: bool = True
    
    def update(self, **kwargs):
        """更新会话"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now().timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'session_id': self.session_id,
            'agent_name': self.agent_name,
            'state': self.state,
            'context': self.context,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'pending_prompt': self.pending_prompt,
            'expected_input_type': self.expected_input_type,
            'priority': self.priority,
            'interruptible': self.interruptible
        }


class SessionManager:
    """会话管理器 - 支持会话栈"""
    
    def __init__(self):
        self._sessions: Dict[str, AgentSession] = {}
        # 用户的会话栈（支持多个会话嵌套）
        self._user_session_stack: Dict[str, List[str]] = {}  # user_id -> [session_id]
    
    def create_session(self, agent_name: str, user_id: str = "default", 
                      priority: int = 2) -> AgentSession:
        """
        创建新会话，如果当前有活跃会话，则根据优先级决定是否打断
        
        Args:
            agent_name: Agent名称
            user_id: 用户ID
            priority: 优先级（1/2/3）
                     3: 最高优先级，不可被打断
                     2: 中等优先级，可被更高优先级打断
                     1: 最低优先级，可被任何更高优先级打断
            
        Returns:
            创建的会话，如果无法创建则返回None
            
        行为：
        - 如果没有活跃会话，直接创建
        - 如果有活跃会话且新会话优先级更高：
          * 当前会话优先级<3，则暂停当前会话
          * 当前会话优先级=3，则拒绝创建新会话
        - 如果新会话优先级不够高，则拒绝创建
        """
        # 检查当前活跃会话
        current_session = self.get_active_session(user_id)
        if current_session:
            print(f"[SessionManager] 尝试创建会话 [{agent_name}] (优先级{priority})")
            print(f"[SessionManager] {current_session.session_id}, {current_session.state}")
            # 有活跃会话，检查优先级
            if priority > current_session.priority:
                # 新会话优先级更高
                if current_session.priority < 3:
                    # 当前会话优先级<3，可被打断
                    print(f"⏸️  暂停会话 [{current_session.agent_name}] (优先级{current_session.priority}) "
                          f"以启动更高优先级会话 [{agent_name}] (优先级{priority})")
                    current_session.update(state="paused")
                else:
                    # 当前会话优先级=3，不可打断
                    print(f"🚫 会话 [{current_session.agent_name}] (优先级{current_session.priority}) 不可被打断，"
                          f"拒绝创建新会话 [{agent_name}]")
                    return None
            else:
                # 新会话优先级不够高，拒绝创建
                print(f"🚫 当前会话 [{current_session.agent_name}] 优先级({current_session.priority}) "
                      f">= 新会话 [{agent_name}] 优先级({priority})，拒绝创建")
                return None
        
        # 判断是否可被打断（只有优先级3不可被打断）
        interruptible = (priority < 3)
        
        # 创建新会话
        session_id = str(uuid.uuid4())
        session = AgentSession(
            session_id=session_id,
            agent_name=agent_name,
            state="running",
            priority=priority,
            interruptible=interruptible
        )
        self._sessions[session_id] = session
        
        # 将会话压入栈
        if user_id not in self._user_session_stack:
            self._user_session_stack[user_id] = []
        self._user_session_stack[user_id].append(session_id)
        
        can_interrupt_str = "不可打断" if priority == 3 else "可打断"
        print(f"✅ 创建会话 [{agent_name}] (优先级{priority}, {can_interrupt_str})")
        
        return session
    
    def get_active_session(self, user_id: str = "default") -> Optional[AgentSession]:
        """
        获取用户当前活跃的会话（栈顶）
        
        Args:
            user_id: 用户ID
            
        Returns:
            活跃会话，如果没有则返回None
        """
        stack = self._user_session_stack.get(user_id, [])

        # 打印整个stack的内容
        if stack:
            for pos, session_id in enumerate(stack):
                # 根据ID获取会话对象
                session = self._sessions.get(session_id)
                # 打印位置（栈底→栈顶）+ 会话信息
                print(f" 123 栈位置{pos}: {session if session else f'会话{session_id}不存在'}", {session.agent_name if session else 'N/A'}, session_id)
                
        # 从栈顶开始查找第一个活跃的会话
        while stack:
            session_id = stack[-1]
            session = self._sessions.get(session_id)
            
            # 如果会话不存在或已完成/错误，从栈中移除
            if not session or session.state in ['completed', 'error']:
                stack.pop()
                continue
            
            # 返回活跃的会话（running, waiting_input, paused）
            return session
        
        return None
    
    def pause_current_session(self, user_id: str = "default") -> Optional[AgentSession]:
        """
        暂停当前会话（但不移出栈）
        
        Args:
            user_id: 用户ID
            
        Returns:
            暂停的会话，如果无法暂停则返回None
        """
        session = self.get_active_session(user_id)
        if session and session.interruptible:
            session.update(state="paused")
            return session
        return None
    
    def resume_top_session(self, user_id: str = "default") -> Optional[AgentSession]:
        """
        恢复栈顶会话
        
        Args:
            user_id: 用户ID
            
        Returns:
            恢复的会话
        """
        session = self.get_active_session(user_id)
        if session and session.state == "paused":
            session.update(state="running")
        return session
    
    def pop_session(self, user_id: str = "default") -> Optional[AgentSession]:
        """
        弹出并完成当前会话
        
        Args:
            user_id: 用户ID
            
        Returns:
            弹出的会话
        """
        stack = self._user_session_stack.get(user_id, [])
        if stack:
            session_id = stack.pop()
            session = self._sessions.get(session_id)
            if session:
                session.update(state="completed")
            return session
        return None
    
    def get_session_stack(self, user_id: str = "default") -> List[AgentSession]:
        """
        获取用户的会话栈
        
        Args:
            user_id: 用户ID
            
        Returns:
            会话栈列表
        """
        stack = self._user_session_stack.get(user_id, [])
        return [self._sessions[sid] for sid in stack if sid in self._sessions]
    
    def wait_for_input(self, session_id: str, prompt: str, expected_type: str = "text"):
        """
        标记会话等待用户输入
        
        Args:
            session_id: 会话ID
            prompt: 提示语
            expected_type: 期望的输入类型
        """
        if session_id in self._sessions:
            self._sessions[session_id].update(
                state="waiting_input",
                pending_prompt=prompt,
                expected_input_type=expected_type
            )
    
    def resume_session(self, session_id: str, user_input: str):
        """
        恢复会话，传入用户输入
        
        Args:
            session_id: 会话ID
            user_input: 用户输入
            
        Returns:
            恢复的会话
        """
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.update(
                state="running",
                pending_prompt=None
            )
            # 将用户输入添加到上下文
            session.context['last_user_input'] = user_input
            return session
        return None
    
    def complete_session(self, session_id: str, user_id: str = "default"):
        """
        完成会话
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
        """
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.update(state="completed")
            
            # 从栈中移除
            stack = self._user_session_stack.get(user_id, [])
            if session_id in stack:
                stack.remove(session_id)
                print(f"✅ 完成会话 [{session.agent_name}] (session_id: {session_id[:8]}...)")
                print(f"   栈中剩余会话: {len(stack)} 个")
            else:
                print(f"⚠️  会话 {session_id[:8]} 不在栈中 (可能已被移除)")
            
            # 如果栈中还有暂停的会话，自动恢复栈顶会话
            if stack:
                top_session = self._sessions.get(stack[-1])
                if top_session and top_session.state == "paused":
                    top_session.update(state="running")
                    print(f"🔄 自动恢复会话 [{top_session.agent_name}] (session_id: {top_session.session_id[:8]}...)")
            else:
                print(f"   当前栈为空，没有需要恢复的会话")
    
    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """
        获取会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话对象
        """
        return self._sessions.get(session_id)
    
    def clear_user_sessions(self, user_id: str = "default"):
        """
        清除用户的所有会话
        
        Args:
            user_id: 用户ID
        """
        stack = self._user_session_stack.get(user_id, [])
        for session_id in stack:
            if session_id in self._sessions:
                del self._sessions[session_id]
        self._user_session_stack[user_id] = []
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'total_sessions': len(self._sessions),
            'active_users': len(self._user_session_stack),
            'sessions_by_state': {
                state: sum(1 for s in self._sessions.values() if s.state == state)
                for state in ['running', 'waiting_input', 'paused', 'completed', 'error']
            }
        }


# 全局实例
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """获取会话管理器单例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def reset_session_manager():
    """重置会话管理器（主要用于测试）"""
    global _session_manager
    _session_manager = SessionManager()
