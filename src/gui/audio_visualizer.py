"""
GUI 模块 - Kiwi 智能语音系统可视化界面
"""
import sys
import numpy as np
from collections import deque
from typing import Optional
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QLabel, QComboBox, QTextEdit,
    QGroupBox, QCheckBox
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont

from src.audio import AudioRecorder, AudioConfig, AudioFrame
from src.asr import create_asr_engine, ASRConfig, ASRResult
from src.vad import VADFactory, VADConfig, VADResult, VADEvent
from src.wakeword import WakeWordFactory, WakeWordConfig, WakeWordResult, WakeWordState
from src.config_manager import get_config


class ASRWorker(QThread):
    """ASR 识别工作线程"""
    
    result_ready = pyqtSignal(ASRResult)  # 识别结果信号
    error_occurred = pyqtSignal(str)      # 错误信号
    
    def __init__(self, asr_engine, audio_data, sample_rate):
        super().__init__()
        self.asr_engine = asr_engine
        self.audio_data = audio_data
        self.sample_rate = sample_rate
    
    def run(self):
        """执行识别"""
        try:
            result = self.asr_engine.recognize(self.audio_data, self.sample_rate)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))


class AudioVisualizerWidget(QWidget):
    """Kiwi 智能语音系统可视化主窗口"""
    
    def __init__(self):
        super().__init__()
        self.recorder: Optional[AudioRecorder] = None
        self.asr_engine = None
        self.vad_engine = None
        self.wakeword_engine = None
        self.is_recording = False
        
        # 波形数据缓冲区
        self.waveform_buffer = deque(maxlen=16000)  # 1秒数据 @ 16kHz
        self.volume_history = deque(maxlen=100)     # 音量历史
        
        # 唤醒词相关
        self.enable_wakeword = False
        self.wakeword_detected = False  # 是否已检测到唤醒词
        import time
        self.wakeword_cooldown_until = 0  # 不使用冷却期
        self.vad_end_count = 0  # VAD END计数器（唤醒后最多3次）
        self.max_vad_end_count = 3  # 最大VAD END次数
        self.wakeword_timeout = 0  # 唤醒超时时间戳（第一次VAD END后10秒）
        self.wakeword_timeout_seconds = 10.0  # 唤醒超时时长
        
        # VAD 相关
        self.enable_vad = False
        self.vad_state_history = deque(maxlen=100)  # VAD状态历史
        self.vad_frame_buffer = []  # VAD帧缓冲区，用于累积到480样本
        self.vad_frame_size = 480   # 30ms @ 16kHz
        
        # ASR 相关
        self.enable_asr = False
        self.asr_audio_buffer = []
        self.asr_buffer_duration = 0.0
        self.asr_worker: Optional[ASRWorker] = None
        
        # 初始化UI
        self.init_ui()
        
        # 定时器用于更新显示
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.setInterval(50)  # 20 FPS
        
    def init_ui(self):
        """初始化UI组件"""
        self.setWindowTitle("Kiwi 智能语音系统")
        self.resize(1200, 800)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 标题
        title = QLabel("🦉 Kiwi 智能语音系统可视化")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # 控制面板
        control_layout = self.create_control_panel()
        main_layout.addLayout(control_layout)
        
        # 状态信息
        self.status_label = QLabel("状态: 就绪")
        self.status_label.setFont(QFont("Arial", 12))
        main_layout.addWidget(self.status_label)
        
        # 波形显示区域
        self.waveform_plot = self.create_waveform_plot()
        main_layout.addWidget(self.waveform_plot)
        
        # 音量历史显示
        self.volume_plot = self.create_volume_plot()
        main_layout.addWidget(self.volume_plot)
        
        # VAD 状态显示
        self.vad_plot = self.create_vad_plot()
        main_layout.addWidget(self.vad_plot)
        
        # ASR 结果显示区域
        asr_group = self.create_asr_panel()
        main_layout.addWidget(asr_group)
        
        # 统计信息
        self.stats_label = QLabel("统计信息: --")
        self.stats_label.setFont(QFont("Courier", 10))
        main_layout.addWidget(self.stats_label)
        
        self.setLayout(main_layout)
    
    def create_control_panel(self) -> QHBoxLayout:
        """创建控制面板"""
        layout = QHBoxLayout()
        
        # 设备选择
        layout.addWidget(QLabel("音频设备:"))
        self.device_combo = QComboBox()
        self.refresh_devices()
        layout.addWidget(self.device_combo)
        
        # 刷新设备按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh_devices)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        
        # 唤醒词开关
        self.wakeword_checkbox = QCheckBox("启用唤醒词检测")
        self.wakeword_checkbox.setFont(QFont("Arial", 12))
        self.wakeword_checkbox.stateChanged.connect(self.toggle_wakeword)
        layout.addWidget(self.wakeword_checkbox)
        
        # VAD 开关
        self.vad_checkbox = QCheckBox("启用 VAD 检测")
        self.vad_checkbox.setFont(QFont("Arial", 12))
        self.vad_checkbox.stateChanged.connect(self.toggle_vad)
        layout.addWidget(self.vad_checkbox)
        
        # ASR 开关
        self.asr_checkbox = QCheckBox("启用 ASR 识别")
        self.asr_checkbox.setFont(QFont("Arial", 12))
        self.asr_checkbox.stateChanged.connect(self.toggle_asr)
        layout.addWidget(self.asr_checkbox)
        
        layout.addStretch()
        
        # 启动/停止按钮
        self.start_btn = QPushButton("▶️ 启动监听")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.start_btn.clicked.connect(self.toggle_recording)
        layout.addWidget(self.start_btn)
        
        return layout
    
    def create_waveform_plot(self) -> pg.PlotWidget:
        """创建波形显示"""
        plot = pg.PlotWidget()
        plot.setTitle("实时音频波形", size="14pt")
        plot.setLabel('left', '振幅')
        plot.setLabel('bottom', '样本')
        plot.setYRange(-1.0, 1.0)
        plot.setBackground('w')
        plot.showGrid(x=True, y=True, alpha=0.3)
        
        # 波形曲线
        self.waveform_curve = plot.plot(pen=pg.mkPen(color='b', width=1.5))
        
        return plot
    
    def create_volume_plot(self) -> pg.PlotWidget:
        """创建音量历史显示"""
        plot = pg.PlotWidget()
        plot.setTitle("音量级别历史", size="14pt")
        plot.setLabel('left', '音量')
        plot.setLabel('bottom', '时间 (帧)')
        plot.setBackground('w')
        plot.showGrid(x=True, y=True, alpha=0.3)
        
        # 音量曲线
        self.volume_curve = plot.plot(
            pen=pg.mkPen(color='g', width=2),
            fillLevel=0,
            brush=(0, 255, 0, 100)
        )
        
        return plot
    
    def create_vad_plot(self) -> pg.PlotWidget:
        """创建VAD状态显示"""
        plot = pg.PlotWidget()
        plot.setTitle("VAD 语音活动检测", size="14pt")
        plot.setLabel('left', '状态 (0=静音, 1=语音)')
        plot.setLabel('bottom', '时间 (帧)')
        plot.setYRange(-0.1, 1.1)
        plot.setBackground('w')
        plot.showGrid(x=True, y=True, alpha=0.3)
        
        # VAD状态曲线
        self.vad_curve = plot.plot(
            pen=pg.mkPen(color='r', width=2),
            fillLevel=0,
            brush=(255, 0, 0, 100)
        )
        
        return plot
    
    def create_asr_panel(self) -> QGroupBox:
        """创建 ASR 结果显示面板"""
        group = QGroupBox("ASR 识别结果")
        group.setFont(QFont("Arial", 12, QFont.Bold))
        
        layout = QVBoxLayout()
        
        # 识别结果文本框
        self.asr_result_text = QTextEdit()
        self.asr_result_text.setReadOnly(True)
        self.asr_result_text.setFont(QFont("Arial", 12))
        self.asr_result_text.setPlaceholderText("识别结果将显示在这里...")
        self.asr_result_text.setMaximumHeight(150)
        layout.addWidget(self.asr_result_text)
        
        # 详细信息
        self.asr_detail_label = QLabel("")
        self.asr_detail_label.setFont(QFont("Courier", 9))
        layout.addWidget(self.asr_detail_label)
        
        group.setLayout(layout)
        return group
    
    def toggle_wakeword(self, state):
        """切换唤醒词开关"""
        self.enable_wakeword = (state == Qt.Checked)
        
        if self.enable_wakeword:
            # 初始化唤醒词引擎
            try:
                config = get_config()
                wakeword_settings = config.wakeword.settings
                
                wakeword_config = WakeWordConfig(
                    sample_rate=16000,
                    models=wakeword_settings.get('models', []),
                    threshold=wakeword_settings.get('threshold', 0.5),
                    cooldown_seconds=wakeword_settings.get('cooldown_seconds', 3.0)
                )
                
                self.wakeword_engine = WakeWordFactory.create("openwakeword", wakeword_config)
                self.wakeword_detected = False  # 重置唤醒状态
                print("✅ 唤醒词引擎初始化成功")
                
            except Exception as e:
                print(f"❌ 唤醒词引擎初始化失败: {e}")
                self.wakeword_checkbox.setChecked(False)
                self.enable_wakeword = False
                import traceback
                traceback.print_exc()
        else:
            self.wakeword_engine = None
            self.wakeword_detected = False
    
    def toggle_vad(self, state):
        """切换 VAD 开关"""
        self.enable_vad = (state == Qt.Checked)
        
        if self.enable_vad:
            # 初始化 VAD 引擎
            try:
                config = get_config()
                vad_settings = config.vad.settings
                
                vad_config = VADConfig(
                    sample_rate=16000,
                    frame_duration_ms=vad_settings.get('frame_duration_ms', 30),
                    aggressiveness=vad_settings.get('aggressiveness', 2),
                    silence_timeout_ms=vad_settings.get('silence_timeout_ms', 800),
                    pre_speech_buffer_ms=vad_settings.get('pre_speech_buffer_ms', 300),
                    min_speech_duration_ms=vad_settings.get('min_speech_duration_ms', 300)
                )
                
                self.vad_engine = VADFactory.create("webrtc", vad_config)
                self.vad_frame_size = vad_config.frame_size  # 更新VAD帧大小
                print("✅ VAD 引擎初始化成功")
                print(f"   VAD帧大小: {self.vad_frame_size} 样本 ({vad_config.frame_duration_ms}ms)")
                
            except Exception as e:
                print(f"❌ VAD 引擎初始化失败: {e}")
                self.vad_checkbox.setChecked(False)
                self.enable_vad = False
                import traceback
                traceback.print_exc()
        else:
            self.vad_engine = None
            self.vad_state_history.clear()
            self.vad_frame_buffer.clear()  # 清空VAD帧缓冲区
    
    def toggle_asr(self, state):
        """切换 ASR 开关"""
        self.enable_asr = (state == Qt.Checked)
        
        if self.enable_asr:
            # 初始化 ASR 引擎
            try:
                QApplication.processEvents()  # 强制更新UI
                
                config = get_config()
                asr_config = ASRConfig(
                    model=config.asr.settings['model'],
                    language=config.asr.settings['language'],
                    model_size='base',
                    device='auto'  # 自动选择最佳设备（MPS/CUDA/CPU）
                )
                self.asr_engine = create_asr_engine(asr_config)
                print("✅ ASR 引擎就绪")
                
            except Exception as e:
                print(f"❌ ASR加载失败: {e}")
                self.asr_checkbox.setChecked(False)
                self.enable_asr = False
                # 打印详细错误信息
                import traceback
                print("=" * 60)
                print("ASR 模型加载失败，详细错误信息：")
                traceback.print_exc()
                print("=" * 60)
        else:
            self.asr_engine = None
    
    def refresh_devices(self):
        """刷新音频设备列表"""
        self.device_combo.clear()
        try:
            devices = AudioRecorder.list_devices()
            for device in devices:
                label = f"[{device.index}] {device.name}"
                if device.is_default:
                    label += " [默认]"
                self.device_combo.addItem(label, device.index)
        except Exception as e:
            self.status_label.setText(f"错误: 无法获取设备列表 - {e}")
    
    def toggle_recording(self):
        """切换监听状态"""
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """启动监听"""
        try:
            # 获取选中的设备
            device_index = self.device_combo.currentData()
            
            # 创建配置
            config = AudioConfig(
                sample_rate=16000,
                channels=1,
                chunk_size=1024,
                device_index=device_index
            )
            
            # 创建音频处理器
            self.recorder = AudioRecorder(config)
            
            # 注册异步回调
            self.recorder.read_async(self.on_audio_frame)
            
            # 启动监听
            self.recorder.start()
            self.is_recording = True
            
            # 更新UI
            self.start_btn.setText("⏸️ 停止监听")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    font-size: 14px;
                    padding: 10px 20px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """)
            self.status_label.setText("状态: 🔴 监听中...")
            self.device_combo.setEnabled(False)
            
            # 清空缓冲区
            self.waveform_buffer.clear()
            self.volume_history.clear()
            self.asr_audio_buffer.clear()
            self.asr_buffer_duration = 0.0
            self.vad_frame_buffer.clear()  # 清空VAD帧缓冲区
            self.vad_state_history.clear()  # 清空VAD状态历史
            
            # 重置VAD引擎状态
            if self.vad_engine:
                self.vad_engine.reset()
            
            # 启动更新定时器
            self.timer.start()
            
        except Exception as e:
            self.status_label.setText(f"错误: {e}")
            import traceback
            traceback.print_exc()
    
    def stop_recording(self):
        """停止监听"""
        if self.recorder:
            self.recorder.stop()
            self.recorder = None
        
        self.is_recording = False
        
        # 更新UI
        self.start_btn.setText("▶️ 启动监听")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.status_label.setText("状态: 已停止")
        self.device_combo.setEnabled(True)
        
        # 停止更新定时器
        self.timer.stop()
    
    def on_audio_frame(self, frame: AudioFrame):
        """音频帧回调"""
        # 将数据添加到缓冲区
        # 归一化到 [-1, 1]
        if frame.data.dtype == np.int16:
            normalized_data = frame.data.astype(np.float32) / 32768.0
        else:
            normalized_data = frame.data
        
        self.waveform_buffer.extend(normalized_data)
        
        # 计算音量
        volume = np.abs(normalized_data).mean()
        self.volume_history.append(volume)
        
        # 检查唤醒超时（如果已唤醒且超时时间已设置）
        if self.enable_wakeword and self.wakeword_detected and self.wakeword_timeout > 0:
            import time
            current_time = time.time()
            if current_time >= self.wakeword_timeout:
                # 超时了，检查当前是否在说话
                is_currently_speaking = False
                if self.enable_vad and self.vad_engine:
                    # 检查VAD状态，如果正在说话则等待
                    is_currently_speaking = (self.vad_engine.state.value == 1)  # VADState.SPEAKING = 1
                
                if not is_currently_speaking:
                    # 不在说话，立即重置唤醒状态
                    from src.config_manager import get_config
                    config = get_config()
                    self.wakeword_detected = False
                    self.vad_end_count = 0
                    self.wakeword_timeout = 0
                    self.wakeword_cooldown_until = 0  # 不使用冷却期
                    # 重置唤醒词引擎状态，防止立即再次检测到
                    if self.wakeword_engine:
                        self.wakeword_engine.reset()
                    print(f"⏰ 唤醒超时({self.wakeword_timeout_seconds}秒)，重置唤醒状态")
                    self.status_label.setText("状态: ⭕ 等待唤醒词...")
        
        # 如果启用了唤醒词
        if self.enable_wakeword and self.wakeword_engine:
            # 未唤醒状态：检测唤醒词
            if not self.wakeword_detected:
                self._process_wakeword(frame, normalized_data)
            # 已唤醒状态：进行VAD/ASR处理
            else:
                # VAD 处理
                if self.enable_vad and self.vad_engine:
                    self._process_vad(frame)
                # 如果没有启用VAD，直接进行ASR（旧模式）
                elif self.enable_asr and self.asr_engine:
                    self._process_asr_direct(frame, normalized_data)
        # 如果未启用唤醒词，直接进行VAD/ASR处理
        else:
            # VAD 处理
            if self.enable_vad and self.vad_engine:
                self._process_vad(frame)
            # 如果没有启用VAD，直接进行ASR（旧模式）
            elif self.enable_asr and self.asr_engine:
                self._process_asr_direct(frame, normalized_data)
    
    def _process_wakeword(self, frame: AudioFrame, normalized_data: np.ndarray):
        """处理唤醒词检测"""
        import time
        
        # 唤醒词检测
        result = self.wakeword_engine.detect(normalized_data)
        
        # 检测到唤醒词
        if result.is_detected and not self.wakeword_detected:
            self.wakeword_detected = True
            self.vad_end_count = 0  # 重置VAD END计数器
            self.wakeword_timeout = 0  # 重置超时计时器
            self.status_label.setText(f"状态: 🎯 已唤醒 - {result.keyword}")
            # 重置VAD状态（开始新的会话）
            if self.vad_engine:
                self.vad_engine.reset()
        
        # 如果检测到唤醒词，在冷却时间后自动重置
        if self.wakeword_detected and result.state == WakeWordState.IDLE:
            # 冷却时间已过，重置唤醒状态
            if self.enable_vad or self.enable_asr:
                # 等待VAD/ASR处理完成后再重置
                pass  # 在VAD结束时重置
    
    def _process_vad(self, frame: AudioFrame):
        """处理 VAD 检测"""
        # VAD需要int16格式
        if frame.data.dtype != np.int16:
            audio_int16 = (frame.data * 32768).astype(np.int16)
        else:
            audio_int16 = frame.data
        
        # 将数据添加到VAD帧缓冲区
        self.vad_frame_buffer.extend(audio_int16)
        
        # 当累积了足够的样本时，进行VAD处理
        while len(self.vad_frame_buffer) >= self.vad_frame_size:
            # 提取一个VAD帧
            vad_frame = np.array(self.vad_frame_buffer[:self.vad_frame_size], dtype=np.int16)
            self.vad_frame_buffer = self.vad_frame_buffer[self.vad_frame_size:]
            
            # VAD 处理
            vad_result = self.vad_engine.process_frame(vad_frame)
            
            # 更新VAD状态显示
            self.vad_state_history.append(1.0 if vad_result.is_speech else 0.0)
            
            # 处理VAD事件
            if vad_result.event == VADEvent.SPEECH_START:
                print(f"🎤 语音开始")
                self.status_label.setText("状态: 🔴 检测到语音...")
            
            elif vad_result.event == VADEvent.SPEECH_END:
                print(f"🔇 语音结束 (时长: {vad_result.duration_ms:.0f}ms)")
                
                # VAD END计数增加
                if self.enable_wakeword and self.wakeword_detected:
                    self.vad_end_count += 1
                    print(f"📊 VAD END 计数: {self.vad_end_count}/{self.max_vad_end_count}")
                    
                    # 第一次VAD END，启动超时计时器
                    if self.vad_end_count == 1 and self.wakeword_timeout == 0:
                        import time
                        self.wakeword_timeout = time.time() + self.wakeword_timeout_seconds
                        print(f"⏱️ 启动唤醒超时计时器: {self.wakeword_timeout_seconds}秒")
                
                # 获取配置
                config = get_config()
                min_duration = config.asr.settings.get('min_audio_duration_ms', 500)
                min_volume = config.vad.settings.get('min_volume_threshold', 0.01)
                
                # 检查音频长度
                if vad_result.duration_ms < min_duration:
                    print(f"⚠️ 语音片段过短 ({vad_result.duration_ms:.0f}ms < {min_duration}ms)，跳过ASR识别")
                    # 检查是否达到最大VAD END次数
                    if self.enable_wakeword and self.wakeword_detected and self.vad_end_count >= self.max_vad_end_count:
                        import time
                        self.wakeword_detected = False
                        self.vad_end_count = 0
                        self.wakeword_timeout = 0  # 清除超时计时器
                        self.wakeword_cooldown_until = 0  # 不使用冷却期
                        # 重置唤醒词引擎状态，防止立即再次检测到
                        if self.wakeword_engine:
                            self.wakeword_engine.reset()
                        print(f"🔄 达到最大VAD END次数({self.max_vad_end_count})，重置唤醒状态")
                        self.status_label.setText("状态: ⭕ 等待唤醒词...")
                    continue
                
                # 检查音频音量（判断是否是有效人声）
                if vad_result.audio_data:
                    audio_int16 = np.frombuffer(vad_result.audio_data, dtype=np.int16)
                    audio_float = audio_int16.astype(np.float32) / 32768.0
                    avg_volume = np.abs(audio_float).mean()
                    
                    if avg_volume < min_volume:
                        print(f"⚠️ 音量过低 ({avg_volume:.4f} < {min_volume})，可能不是人声，跳过ASR识别")
                        # 检查是否达到最大VAD END次数
                        if self.enable_wakeword and self.wakeword_detected and self.vad_end_count >= self.max_vad_end_count:
                            import time
                            self.wakeword_detected = False
                            self.vad_end_count = 0
                            self.wakeword_timeout = 0  # 清除超时计时器
                            self.wakeword_cooldown_until = 0  # 不使用冷却期
                            # 重置唤醒词引擎状态，防止立即再次检测到
                            if self.wakeword_engine:
                                self.wakeword_engine.reset()
                            print(f"🔄 达到最大VAD END次数({self.max_vad_end_count})，重置唤醒状态")
                            self.status_label.setText("状态: ⭕ 等待唤醒词...")
                        continue
                    
                    print(f"✅ 音频有效 (音量: {avg_volume:.4f})，准备识别")
                
                self.status_label.setText("状态: 🔴 语音结束，处理中...")
                # 如果启用了ASR，将语音数据送去识别
                if self.enable_asr and self.asr_engine and vad_result.audio_data:
                    self._process_asr_from_vad(vad_result.audio_data, vad_result.duration_ms)
                
                # 检查是否达到最大VAD END次数，达到则重置唤醒状态
                if self.enable_wakeword and self.wakeword_detected and self.vad_end_count >= self.max_vad_end_count:
                    import time
                    self.wakeword_detected = False
                    self.vad_end_count = 0
                    self.wakeword_timeout = 0  # 清除超时计时器
                    self.wakeword_cooldown_until = 0  # 不使用冷却期
                    # 重置唤醒词引擎状态，防止立即再次检测到
                    if self.wakeword_engine:
                        self.wakeword_engine.reset()
                    print(f"🔄 达到最大VAD END次数({self.max_vad_end_count})，重置唤醒状态")
                    self.status_label.setText("状态: ⭕ 等待唤醒词...")
                    # 不立即修改status_label，让ASR的状态显示优先
    
    def _process_asr_from_vad(self, audio_bytes: bytes, duration_ms: float):
        """处理来自VAD的语音片段"""
        # 如果上一个识别还在进行，跳过
        if self.asr_worker is not None and self.asr_worker.isRunning():
            print("⚠️ 上一个识别还在进行，跳过")
            return
        
        # 转换为numpy数组
        audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        
        # 更新主状态
        self.status_label.setText(f"状态: 🔄 正在识别... ({duration_ms/1000:.1f}s)")
        
        # 启动识别线程
        self.asr_worker = ASRWorker(self.asr_engine, audio_float32, 16000)
        self.asr_worker.result_ready.connect(self.on_asr_result)
        self.asr_worker.error_occurred.connect(self.on_asr_error)
        self.asr_worker.start()
    
    def _process_asr_direct(self, frame: AudioFrame, normalized_data: np.ndarray):
        """直接处理 ASR 识别（不使用VAD）"""
        # 添加到 ASR 缓冲区
        self.asr_audio_buffer.append(normalized_data)
        self.asr_buffer_duration += frame.duration
        
        # 当累积了足够的音频（3秒），进行识别
        if self.asr_buffer_duration >= 3.0:
            # 如果上一个识别还在进行，跳过
            if self.asr_worker is not None and self.asr_worker.isRunning():
                return
            
            # 拼接音频
            audio_data = np.concatenate(self.asr_audio_buffer)
            
            # 启动识别线程
            self.asr_worker = ASRWorker(self.asr_engine, audio_data, 16000)
            self.asr_worker.result_ready.connect(self.on_asr_result)
            self.asr_worker.error_occurred.connect(self.on_asr_error)
            self.asr_worker.start()
            
    def on_asr_result(self, result: ASRResult):
        """认识结果回调"""
        if result.is_empty:
            # ASR完成后，如果启用了唤醒词，更新主状态
            if self.enable_wakeword:
                self.status_label.setText("状态: 等待唤醒词...")
            return
        
        # 如果启用了唤醒词，ASR完成后更新主状态
        if self.enable_wakeword:
            self.status_label.setText("状态: 等待唤醒词...")
        
        # 显示识别文本
        current_text = self.asr_result_text.toPlainText()
        if current_text:
            new_text = current_text + "\n" + result.text
        else:
            new_text = result.text
        self.asr_result_text.setText(new_text)
        
        # 滚动到底部
        self.asr_result_text.verticalScrollBar().setValue(
            self.asr_result_text.verticalScrollBar().maximum()
        )
        
        # 显示详细信息
        detail = (
            f"置信度: {result.confidence:.2f} | "
            f"时长: {result.duration:.2f}s | "
            f"处理: {result.processing_time:.2f}s | "
            f"分段: {result.num_segments}"
        )
        self.asr_detail_label.setText(detail)
    
    def on_asr_error(self, error: str):
        """ASR 错误回调"""
        print(f"❌ ASR识别失败: {error}")
    
    def update_display(self):
        """更新显示"""
        if not self.is_recording or not self.recorder:
            return
        
        # 更新波形
        if len(self.waveform_buffer) > 0:
            waveform_data = np.array(self.waveform_buffer)
            self.waveform_curve.setData(waveform_data)
        
        # 更新音量历史
        if len(self.volume_history) > 0:
            volume_data = np.array(self.volume_history)
            self.volume_curve.setData(volume_data)
        
        # 更新VAD状态
        if len(self.vad_state_history) > 0:
            vad_data = np.array(self.vad_state_history)
            self.vad_curve.setData(vad_data)
        
        # 更新统计信息
        status = self.recorder.get_status()
        vad_status = f"VAD: {'开启' if self.enable_vad else '关闭'}"
        stats_text = (
            f"设备: {status.device_name} | "
            f"已捕获: {status.frames_captured} 帧 | "
            f"丢帧: {status.dropped_frames} | "
            f"缓冲区: {status.buffer_usage:.1%} | "
            f"平均音量: {status.average_level:.4f} | "
            f"{vad_status}"
        )
        self.stats_label.setText(stats_text)
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.is_recording:
            self.stop_recording()
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用 Fusion 风格
    
    window = AudioVisualizerWidget()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
