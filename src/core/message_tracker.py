"""
消息追踪系统

为每一轮对话创建唯一的 msgId，并追踪整个流水线中的输入输出
"""
import uuid
import time
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from threading import Lock
from datetime import datetime
from pathlib import Path


@dataclass
class ModuleTrace:
    """模块追踪记录"""
    module_name: str                    # 模块名称
    timestamp: float                    # 时间戳
    event_type: str                     # 事件类型
    input_data: Optional[Dict[str, Any]] = None   # 输入数据
    output_data: Optional[Dict[str, Any]] = None  # 输出数据
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class MessageTrace:
    """消息完整追踪记录"""
    msg_id: str                         # 消息ID
    session_type: str                   # 会话类型: 'wakeword' 或 'text_input'
    start_time: float                   # 开始时间
    query: str = ""                     # 用户查询
    response: str = ""                  # 系统响应
    end_time: Optional[float] = None    # 结束时间
    traces: List[ModuleTrace] = field(default_factory=list)  # 各模块的追踪记录
    metadata: Dict[str, Any] = field(default_factory=dict)   # 元数据
    
    @property
    def duration_ms(self) -> float:
        """计算总耗时（毫秒）"""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000
    
    def add_trace(self, module_name: str, event_type: str,
                  input_data: Optional[Dict] = None,
                  output_data: Optional[Dict] = None,
                  **metadata):
        """添加模块追踪记录"""
        trace = ModuleTrace(
            module_name=module_name,
            timestamp=time.time(),
            event_type=event_type,
            input_data=input_data,
            output_data=output_data,
            metadata=metadata
        )
        self.traces.append(trace)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            'msg_id': self.msg_id,
            'session_type': self.session_type,
            'start_time': self.start_time,
            'start_time_str': datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            'query': self.query,
            'response': self.response,
            'end_time': self.end_time,
            'duration_ms': self.duration_ms,
            'traces': [trace.to_dict() for trace in self.traces],
            'metadata': self.metadata
        }
        if self.end_time:
            result['end_time_str'] = datetime.fromtimestamp(self.end_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        return result


class MessageTracker:
    """
    消息追踪器
    
    职责：
    1. 为每一轮对话生成唯一的 msgId
    2. 记录整个流水线中每个模块的输入输出
    3. 提供查询接口，可通过 msgId 查看完整处理链路
    4. 支持持久化存储
    """
    
    def __init__(self, log_dir: Optional[str] = None, enable_file_logging: bool = True):
        """
        初始化消息追踪器
        
        Args:
            log_dir: 日志目录路径
            enable_file_logging: 是否启用文件日志
        """
        self._traces: Dict[str, MessageTrace] = {}
        self._lock = Lock()
        self._enable_file_logging = enable_file_logging
        
        # 配置日志目录
        if log_dir:
            self._log_dir = Path(log_dir)
        else:
            self._log_dir = Path(__file__).parent.parent.parent / "logs" / "message_traces"
        
        if self._enable_file_logging:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            print(f"📝 消息追踪日志目录: {self._log_dir}")
    
    def create_message_id(self, session_type: str = "wakeword", **metadata) -> str:
        """
        创建新的消息ID并开始追踪
        
        Args:
            session_type: 会话类型 ('wakeword' 或 'text_input')
            **metadata: 元数据
            
        Returns:
            生成的消息ID
        """
        # 生成唯一ID
        msg_id = f"msg_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}"
        
        # 创建追踪记录
        trace = MessageTrace(
            msg_id=msg_id,
            session_type=session_type,
            start_time=time.time(),
            metadata=metadata
        )
        
        with self._lock:
            self._traces[msg_id] = trace
        
        print(f"🆔 创建新消息ID: {msg_id} (类型: {session_type})")
        return msg_id
    
    def add_trace(self, msg_id: str, module_name: str, event_type: str,
                  input_data: Optional[Dict] = None,
                  output_data: Optional[Dict] = None,
                  **metadata):
        """
        添加模块追踪记录
        
        Args:
            msg_id: 消息ID
            module_name: 模块名称
            event_type: 事件类型
            input_data: 输入数据
            output_data: 输出数据
            **metadata: 元数据
        """
        with self._lock:
            if msg_id not in self._traces:
                print(f"⚠️  未找到消息ID: {msg_id}")
                return
            
            trace = self._traces[msg_id]
            trace.add_trace(module_name, event_type, input_data, output_data, **metadata)
            
            # 简化的日志输出
            direction = "→" if input_data else "←" if output_data else "·"
            print(f"   {direction} [{module_name}] {event_type}")
    
    def update_query(self, msg_id: str, query: str):
        """更新查询内容"""
        with self._lock:
            if msg_id in self._traces:
                self._traces[msg_id].query = query
    
    def update_response(self, msg_id: str, response: str):
        """更新响应内容"""
        with self._lock:
            if msg_id in self._traces:
                self._traces[msg_id].response = response
    
    def complete_trace(self, msg_id: str):
        """
        完成追踪，记录结束时间并写入日志
        
        Args:
            msg_id: 消息ID
        """
        with self._lock:
            if msg_id not in self._traces:
                print(f"⚠️  未找到消息ID: {msg_id}")
                return
            
            trace = self._traces[msg_id]
            trace.end_time = time.time()
            
            # 打印摘要
            print(f"\n{'='*80}")
            print(f"✅ 消息追踪完成: {msg_id}")
            print(f"   类型: {trace.session_type}")
            print(f"   查询: {trace.query}")
            print(f"   响应: {trace.response[:100]}..." if len(trace.response) > 100 else f"   响应: {trace.response}")
            print(f"   总耗时: {trace.duration_ms:.2f}ms")
            print(f"   模块数: {len(trace.traces)}")
            print(f"{'='*80}\n")
            
            # 写入文件
            if self._enable_file_logging:
                self._write_to_file(trace)
    
    def get_trace(self, msg_id: str) -> Optional[MessageTrace]:
        """
        获取指定消息的追踪记录
        
        Args:
            msg_id: 消息ID
            
        Returns:
            追踪记录，如果不存在则返回None
        """
        with self._lock:
            return self._traces.get(msg_id)
    
    def get_recent_traces(self, count: int = 10) -> List[MessageTrace]:
        """
        获取最近的追踪记录
        
        Args:
            count: 返回数量
            
        Returns:
            追踪记录列表
        """
        with self._lock:
            traces = sorted(
                self._traces.values(),
                key=lambda t: t.start_time,
                reverse=True
            )
            return traces[:count]
    
    def _write_to_file(self, trace: MessageTrace):
        """将追踪记录写入文件"""
        try:
            # 按日期组织文件
            date_str = datetime.fromtimestamp(trace.start_time).strftime('%Y-%m-%d')
            log_file = self._log_dir / f"traces_{date_str}.jsonl"
            
            # 追加写入（JSONL格式）
            with open(log_file, 'a', encoding='utf-8') as f:
                json.dump(trace.to_dict(), f, ensure_ascii=False)
                f.write('\n')
                
        except Exception as e:
            print(f"❌ 写入追踪日志失败: {e}")
    
    def print_trace_summary(self, msg_id: str):
        """
        打印追踪记录摘要
        
        Args:
            msg_id: 消息ID
        """
        trace = self.get_trace(msg_id)
        if not trace:
            print(f"未找到消息ID: {msg_id}")
            return
        
        print(f"\n{'='*80}")
        print(f"消息追踪报告: {msg_id}")
        print(f"{'='*80}")
        print(f"会话类型: {trace.session_type}")
        print(f"开始时间: {datetime.fromtimestamp(trace.start_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        if trace.end_time:
            print(f"结束时间: {datetime.fromtimestamp(trace.end_time).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        print(f"总耗时: {trace.duration_ms:.2f}ms")
        print(f"用户查询: {trace.query}")
        print(f"系统响应: {trace.response}")
        print(f"\n流水线处理记录 (共{len(trace.traces)}步):")
        print(f"{'-'*80}")
        
        for i, module_trace in enumerate(trace.traces, 1):
            time_str = datetime.fromtimestamp(module_trace.timestamp).strftime('%H:%M:%S.%f')[:-3]
            print(f"\n{i}. [{time_str}] {module_trace.module_name} - {module_trace.event_type}")
            
            if module_trace.input_data:
                print(f"   输入: {json.dumps(module_trace.input_data, ensure_ascii=False, indent=6)}")
            
            if module_trace.output_data:
                print(f"   输出: {json.dumps(module_trace.output_data, ensure_ascii=False, indent=6)}")
            
            if module_trace.metadata:
                print(f"   元数据: {json.dumps(module_trace.metadata, ensure_ascii=False, indent=6)}")
        
        print(f"\n{'='*80}\n")
    
    def cleanup_old_traces(self, max_age_hours: int = 24):
        """
        清理旧的内存中的追踪记录
        
        Args:
            max_age_hours: 最大保留时间（小时）
        """
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        with self._lock:
            old_ids = [
                msg_id for msg_id, trace in self._traces.items()
                if trace.start_time < cutoff_time
            ]
            
            for msg_id in old_ids:
                del self._traces[msg_id]
            
            if old_ids:
                print(f"🧹 清理了 {len(old_ids)} 条旧的追踪记录")


# 全局单例
_global_tracker: Optional[MessageTracker] = None


def get_message_tracker() -> MessageTracker:
    """获取全局消息追踪器单例"""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = MessageTracker()
    return _global_tracker


def set_message_tracker(tracker: MessageTracker):
    """设置全局消息追踪器"""
    global _global_tracker
    _global_tracker = tracker
