"""
录音器核心实现
"""
import numpy as np
import sounddevice as sd
import queue
import threading
import time
from typing import Optional, Callable, Iterator, List, Dict
from collections import defaultdict

from .types import AudioConfig, AudioFrame, RecorderStatus, AudioDevice
from .exceptions import (
    AudioError, AudioDeviceError, RecorderNotStartedError, 
    ConfigError, BufferOverflowError
)
from .preprocessor import AudioPreprocessor


class AudioRecorder:
    """音频录音器"""
    
    def __init__(self, config: AudioConfig):
        """
        初始化录音器
        
        Args:
            config: 音频配置
            
        Raises:
            ConfigError: 配置参数无效
            AudioDeviceError: 音频设备不可用
        """
        try:
            config.validate()
        except ValueError as e:
            raise ConfigError(f"Invalid config: {e}")
        
        self.config = config
        self._stream: Optional[sd.InputStream] = None
        self._is_recording = False
        self._frame_id = 0
        self._frames_captured = 0
        self._dropped_frames = 0
        
        # 缓冲区
        buffer_capacity = int(config.sample_rate * config.buffer_size / config.chunk_size)
        self._buffer = queue.Queue(maxsize=buffer_capacity)
        
        # 预处理器
        self._preprocessor: Optional[AudioPreprocessor] = None
        
        # 事件监听器
        self._event_listeners: Dict[str, List[Callable]] = defaultdict(list)
        
        # 异步回调
        self._async_callback: Optional[Callable[[AudioFrame], None]] = None
        self._callback_thread: Optional[threading.Thread] = None
        self._callback_running = False
        
        # 统计信息
        self._total_level = 0.0
        self._level_count = 0
        
        # 验证设备
        self._device_info = self._get_device_info()
    
    def _get_device_info(self) -> dict:
        """获取设备信息"""
        try:
            if self.config.device_index is None:
                device_info = sd.query_devices(kind='input')
            else:
                device_info = sd.query_devices(self.config.device_index)
            return device_info
        except Exception as e:
            raise AudioDeviceError(f"Failed to query device: {e}")
    
    def _audio_callback(self, indata, frames, time_info, status):
        """音频回调函数（在独立线程中调用）"""
        if status:
            self._trigger_event('error', Exception(f"Audio stream status: {status}"))
        
        try:
            # 复制数据
            audio_data = indata.copy().flatten()
            
            # 创建音频帧
            frame = AudioFrame.create(
                data=audio_data,
                sample_rate=self.config.sample_rate,
                channels=self.config.channels,
                frame_id=self._frame_id
            )
            
            # 预处理
            if self._preprocessor:
                frame = self._preprocessor.process(frame)
            
            # 计算音量
            level = np.abs(frame.data).mean()
            self._total_level += level
            self._level_count += 1
            
            # 放入缓冲区
            try:
                self._buffer.put_nowait(frame)
                self._frame_id += 1
                self._frames_captured += 1
                self._trigger_event('data', frame)
            except queue.Full:
                self._dropped_frames += 1
                self._trigger_event('overflow')
        
        except Exception as e:
            self._trigger_event('error', e)
    
    def start(self) -> bool:
        """
        启动音频采集
        
        Returns:
            True: 启动成功
            False: 启动失败
        """
        if self._is_recording:
            return False
        
        try:
            # 确定数据类型
            dtype = 'int16' if self.config.format == 'int16' else 'float32'
            
            # 创建音频流
            self._stream = sd.InputStream(
                device=self.config.device_index,
                channels=self.config.channels,
                samplerate=self.config.sample_rate,
                blocksize=self.config.chunk_size,
                dtype=dtype,
                callback=self._audio_callback
            )
            
            # 启动流
            self._stream.start()
            self._is_recording = True
            
            # 重置统计
            self._frame_id = 0
            self._frames_captured = 0
            self._dropped_frames = 0
            self._total_level = 0.0
            self._level_count = 0
            
            # 启动异步回调线程
            if self._async_callback:
                self._callback_running = True
                self._callback_thread = threading.Thread(
                    target=self._async_callback_worker,
                    daemon=True
                )
                self._callback_thread.start()
            
            self._trigger_event('start')
            return True
        
        except Exception as e:
            self._trigger_event('error', e)
            raise AudioDeviceError(f"Failed to start recording: {e}")
    
    def stop(self) -> bool:
        """
        停止音频采集
        
        Returns:
            True: 停止成功
            False: 停止失败
        """
        if not self._is_recording:
            return False
        
        try:
            # 停止异步回调线程
            if self._callback_thread:
                self._callback_running = False
                self._callback_thread.join(timeout=1.0)
                self._callback_thread = None
            
            # 停止并关闭流
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            
            self._is_recording = False
            
            # 清空缓冲区
            while not self._buffer.empty():
                try:
                    self._buffer.get_nowait()
                except queue.Empty:
                    break
            
            self._trigger_event('stop')
            return True
        
        except Exception as e:
            self._trigger_event('error', e)
            return False
    
    def read(self, timeout: Optional[float] = None) -> AudioFrame:
        """
        读取一帧音频数据（阻塞模式）
        
        Args:
            timeout: 超时时间(秒)，None=永久等待
            
        Returns:
            音频帧
            
        Raises:
            RecorderNotStartedError: 录音未启动
            TimeoutError: 超时未读取到数据
        """
        if not self._is_recording:
            raise RecorderNotStartedError("Recorder is not started")
        
        try:
            frame = self._buffer.get(timeout=timeout)
            return frame
        except queue.Empty:
            raise TimeoutError("Timeout waiting for audio data")
    
    def stream(self) -> Iterator[AudioFrame]:
        """
        以生成器方式持续读取音频流
        
        Yields:
            音频帧
        """
        while self._is_recording:
            try:
                frame = self.read(timeout=1.0)
                yield frame
            except TimeoutError:
                continue
            except RecorderNotStartedError:
                break
    
    def read_async(self, callback: Callable[[AudioFrame], None]):
        """
        注册回调函数，异步接收音频数据
        
        Args:
            callback: 音频帧回调函数
        """
        self._async_callback = callback
        
        # 如果已经在录音，启动回调线程
        if self._is_recording and not self._callback_running:
            self._callback_running = True
            self._callback_thread = threading.Thread(
                target=self._async_callback_worker,
                daemon=True
            )
            self._callback_thread.start()
    
    def _async_callback_worker(self):
        """异步回调工作线程"""
        while self._callback_running and self._is_recording:
            try:
                frame = self._buffer.get(timeout=0.1)
                if self._async_callback:
                    try:
                        self._async_callback(frame)
                    except Exception as e:
                        self._trigger_event('error', e)
            except queue.Empty:
                continue
    
    def is_recording(self) -> bool:
        """
        查询录音状态
        
        Returns:
            True: 正在录音
            False: 未录音
        """
        return self._is_recording
    
    def get_status(self) -> RecorderStatus:
        """
        获取详细状态信息
        
        Returns:
            状态信息
        """
        buffer_usage = self._buffer.qsize() / self._buffer.maxsize if self._buffer.maxsize > 0 else 0.0
        average_level = self._total_level / self._level_count if self._level_count > 0 else 0.0
        
        return RecorderStatus(
            is_recording=self._is_recording,
            device_name=self._device_info.get('name', 'Unknown'),
            buffer_usage=buffer_usage,
            frames_captured=self._frames_captured,
            dropped_frames=self._dropped_frames,
            average_level=average_level
        )
    
    @staticmethod
    def list_devices() -> List[AudioDevice]:
        """
        列出所有可用的音频输入设备
        
        Returns:
            设备列表
        """
        devices = []
        try:
            device_list = sd.query_devices()
            default_input = sd.query_devices(kind='input')
            default_index = default_input.get('index', -1) if isinstance(default_input, dict) else -1
            
            for idx, device in enumerate(device_list):
                if device['max_input_channels'] > 0:  # 只列出输入设备
                    audio_device = AudioDevice(
                        index=idx,
                        name=device['name'],
                        channels=device['max_input_channels'],
                        sample_rate=int(device['default_samplerate']),
                        is_default=(idx == default_index)
                    )
                    devices.append(audio_device)
        except Exception as e:
            raise AudioDeviceError(f"Failed to list devices: {e}")
        
        return devices
    
    def set_device(self, device_index: int) -> bool:
        """
        切换音频输入设备（需要先停止录音）
        
        Args:
            device_index: 设备索引
            
        Returns:
            True: 切换成功
            False: 切换失败
        """
        if self._is_recording:
            return False
        
        try:
            # 验证设备
            device_info = sd.query_devices(device_index)
            if device_info['max_input_channels'] == 0:
                return False
            
            self.config.device_index = device_index
            self._device_info = device_info
            return True
        except Exception:
            return False
    
    def set_preprocessor(self, preprocessor: AudioPreprocessor):
        """
        设置音频预处理器
        
        Args:
            preprocessor: 预处理器实例
        """
        self._preprocessor = preprocessor
    
    def on(self, event: str, callback: Callable):
        """
        注册事件监听器
        
        Args:
            event: 事件名称 ('start', 'stop', 'data', 'overflow', 'device_lost', 'error')
            callback: 回调函数
        """
        self._event_listeners[event].append(callback)
    
    def _trigger_event(self, event: str, *args, **kwargs):
        """触发事件"""
        for callback in self._event_listeners[event]:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                # 避免回调异常影响主流程
                print(f"Event callback error: {e}")
    
    def __enter__(self):
        """上下文管理器支持"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器支持"""
        self.stop()
    
    def __del__(self):
        """析构函数"""
        if self._is_recording:
            self.stop()
