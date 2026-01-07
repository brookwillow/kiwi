"""
ASR模块适配器

将现有的 ASR引擎 包装成符合新架构的模块
"""
from typing import Optional, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from src.core.interfaces import IASRModule
from src.core.events import Event, EventType, ASREvent as ASREventType, ASRPayload
from src.asr import create_asr_engine, ASRConfig
from src.core.message_tracker import get_message_tracker


class ASRModuleAdapter(IASRModule):
    """
    ASR模块适配器
    
    职责：
    1. 包装 ASR引擎
    2. 接收语音结束事件并进行识别
    3. 异步处理识别任务
    4. 发布识别结果事件
    """
    
    def __init__(self, controller, config: Optional[ASRConfig] = None):
        """
        初始化ASR模块适配器
        
        Args:
            controller: SystemController 实例
            config: ASR配置
        """
        self._controller = controller
        self._config = config
        self._engine = None
        self._running = False
        self._enabled = True
        
        # 异步任务管理
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._current_task = None
        
        # 当前处理的消息ID
        self._current_msg_id: Optional[str] = None
        
        # 统计
        self._recognitions = 0
        self._successful_recognitions = 0
        self._failed_recognitions = 0
        self._total_latency_ms = 0.0
    
    @property
    def name(self) -> str:
        return "asr"
    
    def initialize(self) -> bool:
        """初始化ASR引擎"""
        if not self._config:
            print(f"⚠️ [{self.name}] 未提供配置，跳过初始化")
            return True
        
        try:
            # 创建ASR引擎
            self._engine = create_asr_engine(self._config)
            
            print(f"✅ [{self.name}] 初始化成功")
            print(f"   模型: {self._config.model}")
            print(f"   模型大小: {self._config.model_size}")
            print(f"   语言: {self._config.language}")
            return True
            
        except Exception as e:
            print(f"❌ [{self.name}] 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def start(self) -> bool:
        """启动ASR识别"""
        if not self._engine:
            print(f"⚠️ [{self.name}] 引擎未初始化，跳过启动")
            return True
        
        self._running = True
        self._enabled = True
        print(f"✅ [{self.name}] 已启动")
        return True
    
    def stop(self):
        """停止ASR识别"""
        self._running = False
        
        # 等待当前任务完成
        if self._current_task and not self._current_task.done():
            print(f"⏳ [{self.name}] 等待当前识别任务完成...")
            try:
                self._current_task.result(timeout=5.0)
            except Exception:
                pass
        
        print(f"✅ [{self.name}] 已停止")
    
    def cleanup(self):
        """清理资源"""
        # 关闭线程池
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
        
        self._engine = None
        print(f"✅ [{self.name}] 资源已清理")
    
    def handle_event(self, event: Event):
        """
        处理来自控制器的事件
        
        Args:
            event: 事件对象
        """
        if not self._engine or not self._running:
            return
        
        # 处理语音结束事件 -> 触发识别
        if event.type == EventType.VAD_SPEECH_END:
            if self._enabled:
                # 从事件中提取 msg_id
                if event.msg_id:
                    self._current_msg_id = event.msg_id
                
                # 使用强类型 payload 获取音频数据
                audio_data = event.payload.audio_data
                    
                if audio_data is not None:
                    self._start_recognition(audio_data)
        
        # 处理系统停止事件
        elif event.type == EventType.SYSTEM_STOP:
            self.stop()
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    # ==================== IASRModule 专用接口 ====================
    
    def recognize(self, audio_data: Any) -> Optional[dict]:
        """
        同步识别音频
        
        Args:
            audio_data: 音频数据
            
        Returns:
            识别结果
        """
        if not self._engine:
            return None
        
        try:
            import time
            start_time = time.time()
            
            # 确保bytes转为numpy数组
            if isinstance(audio_data, bytes):
                audio_data = np.frombuffer(audio_data, dtype=np.int16)
            elif not isinstance(audio_data, np.ndarray):
                audio_data = np.array(audio_data, dtype=np.int16)
            
            # 调用引擎识别
            result = self._engine.recognize(audio_data)
            
            latency_ms = (time.time() - start_time) * 1000
            
            return {
                'text': result.text if hasattr(result, 'text') else result,
                'confidence': getattr(result, 'confidence', 0.0),
                'latency_ms': latency_ms
            }
            
        except Exception as e:
            print(f"⚠️ [{self.name}] 识别异常: {e}")
            return None
    
    async def recognize_async(self, audio_data: Any) -> Optional[dict]:
        """
        异步识别音频
        
        Args:
            audio_data: 音频数据
            
        Returns:
            识别结果
        """
        if not self._engine:
            return None
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.recognize, audio_data)
    
    def enable(self):
        """启用识别"""
        self._enabled = True
        print(f"✅ [{self.name}] 识别已启用")
    
    def disable(self):
        """禁用识别"""
        self._enabled = False
        print(f"⏸️  [{self.name}] 识别已禁用")
    
    def is_busy(self) -> bool:
        """是否正在识别"""
        return self._current_task is not None and not self._current_task.done()
    
    # ==================== 内部方法 ====================
    
    def _start_recognition(self, audio_data: Any):
        """
        启动识别任务（异步）
        
        Args:
            audio_data: 音频数据
        """
        # 如果有正在进行的任务，取消它
        if self._current_task and not self._current_task.done():
            print(f"⚠️ [ASR] 跳过识别: 上一个任务还在运行中")
            return
        
        # 提交新任务
        self._recognitions += 1
        print(f"\n{'='*60}")
        print(f"🎙️  ASR: 开始识别 (第 {self._recognitions} 次)...")
        if self._current_msg_id:
            print(f"   消息ID: {self._current_msg_id}")
        print(f"{'='*60}")
        
        # 记录追踪
        if self._current_msg_id:
            tracker = get_message_tracker()
            tracker.add_trace(
                msg_id=self._current_msg_id,
                module_name=self.name,
                event_type="recognition_start",
                input_data={'audio_length': len(audio_data) if audio_data else 0}
            )
        
        # 发送ASR开始识别事件
        try:
            start_event = ASREventType(
                event_type=EventType.ASR_RECOGNITION_START,
                source=self.name,
                payload=ASRPayload(text="", confidence=0.0, is_partial=False),
                msg_id=self._current_msg_id or ""
            )
            self._controller.publish_event(start_event)
            print(f"📤 [ASR] 已发送 ASR_RECOGNITION_START 事件")
        except Exception as e:
            print(f"❌ [ASR] 发送ASR_RECOGNITION_START事件失败: {e}")
        
        self._current_task = self._executor.submit(self._recognize_and_publish, audio_data)
    
    def _recognize_and_publish(self, audio_data: Any):
        """
        识别并发布结果（在线程池中执行）
        
        Args:
            audio_data: 音频数据
        """
        try:
            # 执行识别
            result = self.recognize(audio_data)
            
            if result and result.get('text'):
                # 成功识别
                self._successful_recognitions += 1
                self._total_latency_ms += result['latency_ms']
                
                text = result['text'].strip()
                confidence = result.get('confidence', 0.0)
                latency_ms = result['latency_ms']
                
                print(f"\n{'='*60}")
                print(f"📝 [{self.name}] 识别成功!")
                print(f"   文本: {text}")
                print(f"   置信度: {confidence:.2f}")
                print(f"   耗时: {latency_ms:.0f}ms")
                if self._current_msg_id:
                    print(f"   消息ID: {self._current_msg_id}")
                
                # 记录追踪
                if self._current_msg_id:
                    tracker = get_message_tracker()
                    tracker.add_trace(
                        msg_id=self._current_msg_id,
                        module_name=self.name,
                        event_type="recognition_success",
                        output_data={
                            'text': text,
                            'confidence': confidence,
                            'latency_ms': latency_ms
                        }
                    )
                    tracker.update_query(self._current_msg_id, text)
                
                # 发布识别成功事件
                event = ASREventType(
                    event_type=EventType.ASR_RECOGNITION_SUCCESS,
                    source=self.name,
                    payload=ASRPayload(
                        text=text,
                        confidence=confidence,
                        is_partial=False,
                        latency_ms=latency_ms
                    ),
                    msg_id=self._current_msg_id
                )
                self._controller.publish_event(event)
                
                # 通知状态机
                from src.state_machine import StateEvent
                self._controller.handle_state_event(
                    StateEvent.RECOGNITION_SUCCESS,
                    {'text': text}
                )
                
            else:
                # 识别失败或结果为空
                self._failed_recognitions += 1
                print(f"⚠️ [{self.name}] 识别失败或结果为空")
                
                # 发布识别失败事件
                event = ASREventType(
                    event_type=EventType.ASR_RECOGNITION_FAILED,
                    source=self.name,
                    payload=ASRPayload(
                        text="",
                        confidence=0.0,
                        is_partial=False
                    ),
                    msg_id=self._current_msg_id or ""
                )
                self._controller.publish_event(event)
                
                # 通知状态机
                from src.state_machine import StateEvent
                self._controller.handle_state_event(StateEvent.RECOGNITION_FAILED)
        
        except Exception as e:
            # 识别异常
            self._failed_recognitions += 1
            print(f"❌ [{self.name}] 识别异常: {e}")
            import traceback
            traceback.print_exc()
            
            # 发布识别失败事件
            event = ASREventType(
                event_type=EventType.ASR_RECOGNITION_FAILED,
                source=self.name,
                payload=ASRPayload(
                    text=f"Error: {str(e)}",
                    confidence=0.0,
                    is_partial=False
                ),
                msg_id=self._current_msg_id or ""
            )
            self._controller.publish_event(event)
            
            # 通知状态机
            from src.state_machine import StateEvent
            self._controller.handle_state_event(StateEvent.RECOGNITION_FAILED)
    
    # ==================== 统计信息 ====================
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        avg_latency = (
            self._total_latency_ms / self._successful_recognitions 
            if self._successful_recognitions > 0 else 0.0
        )
        
        success_rate = (
            self._successful_recognitions / self._recognitions * 100.0
            if self._recognitions > 0 else 0.0
        )
        
        return {
            'total_recognitions': self._recognitions,
            'successful_recognitions': self._successful_recognitions,
            'failed_recognitions': self._failed_recognitions,
            'success_rate': success_rate,
            'average_latency_ms': avg_latency,
            'enabled': self._enabled,
            'is_running': self._running,
            'has_active_task': self._current_task and not self._current_task.done(),
            'has_engine': self._engine is not None
        }
