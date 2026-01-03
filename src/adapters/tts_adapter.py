"""
TTS (Text-to-Speech) 模块适配器
使用系统自带的 TTS 功能进行语音播报
"""
import subprocess
import threading
import time
from typing import TYPE_CHECKING, Optional

from src.core.interfaces import IModule
from src.core.events import Event, EventType

if TYPE_CHECKING:
    from src.core.controller import SystemController


class TTSModuleAdapter(IModule):
    """TTS模块适配器 - 使用macOS系统自带的say命令"""
    
    def __init__(self, controller: 'SystemController'):
        """
        初始化TTS适配器
        
        Args:
            controller: 系统控制器
        """
        self._name = "tts"
        self._controller = controller
        self._running = False
        self._speaking = False
        self._current_process = None
        self._last_text: Optional[str] = None
        self._last_request_time: float = 0
        self._dedup_window: float = 1.0  # 防抖窗口: 1秒内相同文本只播报一次
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def initialize(self) -> bool:
        """初始化TTS模块"""
        try:
            # 检查系统是否支持say命令（macOS）
            result = subprocess.run(['which', 'say'], capture_output=True)
            if result.returncode != 0:
                print("⚠️ 系统不支持say命令，TTS功能将不可用（仅macOS支持）")
                return False
            
            print("✅ [tts] 初始化成功 (使用系统say命令)")
            return True
            
        except Exception as e:
            print(f"❌ TTS模块初始化失败: {e}")
            return False
    
    def start(self) -> bool:
        """启动模块"""
        self._running = True
        print("✅ [tts] 已启动")
        return True
    
    def stop(self):
        """停止模块"""
        self._running = False
        
        # 停止当前播报
        if self._current_process:
            try:
                if hasattr(self._current_process, 'poll') and self._current_process.poll() is None:
                    self._current_process.terminate()
            except Exception:
                pass
        
        self._speaking = False
        print("✅ [tts] 已停止")
    
    def cleanup(self):
        """清理资源"""
        # 停止但不重复打印日志
        if self._current_process:
            try:
                if hasattr(self._current_process, 'poll') and self._current_process.poll() is None:
                    self._current_process.terminate()
            except Exception:
                pass
        self._running = False
        self._speaking = False
        print("✅ [tts] 资源已清理")
    
    def handle_event(self, event: Event):
        """处理事件"""
        if not self._running:
            return
        
        if event.type == EventType.TTS_SPEAK_REQUEST:
            self._handle_speak_request(event)
        elif event.type == EventType.SYSTEM_STOP:
            self.stop()
    
    def _handle_speak_request(self, event: Event):
        """处理TTS播报请求"""
        # 检查是否处于评估模式
        if hasattr(self._controller, 'evaluation_mode') and self._controller.evaluation_mode:
            print(f"🔇 [TTS] 评估模式 - 跳过播报")
            return
        
        text = event.data.get('text', '')
        if not text:
            return
        
        # 防抖: 检查是否在短时间内收到相同文本的重复请求
        current_time = time.time()
        if (self._last_text == text and 
            current_time - self._last_request_time < self._dedup_window):
            print(f"⚠️ [TTS] 忽略重复请求 (防抖): {text[:30]}...")
            return
        
        # 更新防抖追踪
        self._last_text = text
        self._last_request_time = current_time
        
        # 在新线程中执行播报，避免阻塞
        thread = threading.Thread(target=self._speak_async, args=(text,))
        thread.daemon = True
        thread.start()
    
    def _speak_async(self, text: str):
        """异步执行语音播报"""
        try:
            # 发送播报开始事件
            self._publish_speak_start(text)
            self._speaking = True
            
            # 使用macOS的say命令进行播报
            # -v Ting-Ting 使用中文女声
            # -r 180 设置语速（默认175，范围10-500）
            self._current_process = subprocess.Popen(
                ['say', '-v', 'Ting-Ting', '-r', '200', text],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # 等待进程完成
            self._current_process.wait()
            
            # 发送播报完成事件
            self._speaking = False
            self._publish_speak_end(text)
            
        except Exception as e:
            print(f"❌ [TTS] 播报失败: {e}")
            self._speaking = False
            self._publish_speak_error(text, str(e))
    
    def _publish_speak_start(self, text: str):
        """发布播报开始事件"""
        event = Event.create(
            event_type=EventType.TTS_SPEAK_START,
            source=self._name,
            data={'text': text}
        )
        self._controller.publish_event(event)
        print(f"🔊 [TTS] 开始播报: {text}")
    
    def _publish_speak_end(self, text: str):
        """发布播报完成事件"""
        event = Event.create(
            event_type=EventType.TTS_SPEAK_END,
            source=self._name,
            data={'text': text}
        )
        self._controller.publish_event(event)
        print(f"✅ [TTS] 播报完成: {text}")
    
    def _publish_speak_error(self, text: str, error: str):
        """发布播报错误事件"""
        event = Event.create(
            event_type=EventType.TTS_SPEAK_ERROR,
            source=self._name,
            data={'text': text, 'error': error}
        )
        self._controller.publish_event(event)
    
    def is_speaking(self) -> bool:
        """是否正在播报"""
        return self._speaking
