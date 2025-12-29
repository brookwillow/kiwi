"""
Kiwi 语音助手 - 新架构GUI主程序

使用 SystemController 和事件驱动架构的完整GUI实现
"""
import sys
import numpy as np
from collections import deque
from typing import Optional
import pyqtgraph as pg
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QLabel, QComboBox, QTextEdit,
    QGroupBox, QCheckBox
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont

from src.core.controller import SystemController
from src.adapters import (
    AudioModuleAdapter,
    WakewordModuleAdapter,
    VADModuleAdapter,
    ASRModuleAdapter,
    GUIModuleAdapter
)
from src.audio import AudioConfig, AudioRecorder
from src.wakeword import WakeWordConfig
from src.vad import VADConfig
from src.asr import ASRConfig
from src.config_manager import get_config


class KiwiVoiceAssistantGUI(QWidget):
    """Kiwi 智能语音助手GUI - 新架构版本"""
    
    def __init__(self):
        super().__init__()
        
        # SystemController
        self.controller: Optional[SystemController] = None
        self.gui_adapter: Optional[GUIModuleAdapter] = None
        
        # 各模块适配器
        self.audio_adapter: Optional[AudioModuleAdapter] = None
        self.wakeword_adapter: Optional[WakewordModuleAdapter] = None
        self.vad_adapter: Optional[VADModuleAdapter] = None
        self.asr_adapter: Optional[ASRModuleAdapter] = None
        
        # UI状态
        self.is_running = False
        self.current_vad_state = 0.0  # 当前VAD状态：0=静音，1=语音
        
        # 显示数据缓冲区
        self.waveform_buffer = deque(maxlen=16000)  # 1秒 @ 16kHz
        self.vad_state_history = deque(maxlen=100)
        self.spectrum_data = None  # 频谱数据
        
        # 初始化UI
        self.init_ui()
        
        # 显示更新定时器
        self.display_timer = QTimer()
        self.display_timer.timeout.connect(self.update_display)
        self.display_timer.setInterval(50)  # 20 FPS
        
        # 统计信息更新定时器
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.setInterval(500)  # 2 Hz
    
    def init_ui(self):
        """初始化UI组件"""
        self.setWindowTitle("🥝 Kiwi 智能语音助手")
        self.resize(1200, 900)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 标题
        title = QLabel("🥝 Kiwi 智能语音助手")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # 控制面板
        control_layout = self.create_control_panel()
        main_layout.addLayout(control_layout)
        
        # 状态显示
        self.status_label = QLabel("Status: ready")
        self.status_label.setFont(QFont("Arial", 14))
        self.status_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        main_layout.addWidget(self.status_label)
        
        # 波形显示（增大显示区域）
        self.waveform_plot = self.create_waveform_plot()
        main_layout.addWidget(self.waveform_plot)
        
        # 频谱显示（新增）
        self.spectrum_plot = self.create_spectrum_plot()
        main_layout.addWidget(self.spectrum_plot)
        
        # VAD状态
        self.vad_plot = self.create_vad_plot()
        main_layout.addWidget(self.vad_plot)
        
        # ASR结果
        asr_group = self.create_asr_panel()
        main_layout.addWidget(asr_group)
        
        # 统计信息
        self.stats_label = QLabel("统计信息: --")
        self.stats_label.setFont(QFont("Courier", 10))
        self.stats_label.setStyleSheet("padding: 5px; background-color: #f9f9f9;")
        main_layout.addWidget(self.stats_label)
        
        self.setLayout(main_layout)
    
    def create_control_panel(self) -> QHBoxLayout:
        """创建控制面板"""
        layout = QHBoxLayout()
        
        layout.addStretch()
        
        # 启动/停止按钮
        self.start_btn = QPushButton("▶️ 启动系统")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 24px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.start_btn.clicked.connect(self.toggle_system)
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
        plot.setMinimumHeight(250)  # 调整高度以适应频谱图
        # 增加线条宽度，使波形更明显
        self.waveform_curve = plot.plot(pen=pg.mkPen(color='b', width=2))
        return plot
    
    def create_spectrum_plot(self) -> pg.PlotWidget:
        """创建频谱显示"""
        plot = pg.PlotWidget()
        plot.setTitle("音频频谱 (FFT)", size="14pt")
        plot.setLabel('left', '幅度 (dB)')
        plot.setLabel('bottom', '频率 (Hz)')
        plot.setBackground('w')
        plot.showGrid(x=True, y=True, alpha=0.3)
        plot.setMinimumHeight(200)
        plot.setXRange(0, 4000)  # 显示0-4kHz范围（语音主要频段）
        plot.setYRange(-60, 0)   # dB范围调整为-60到0以匹配压缩后的数据
        # 使用渐变填充
        self.spectrum_curve = plot.plot(
            pen=pg.mkPen(color='g', width=2),
            fillLevel=-60,
            brush=(0, 255, 0, 100)
        )
        return plot
    
    def create_vad_plot(self) -> pg.PlotWidget:
        """创建VAD状态显示"""
        plot = pg.PlotWidget()
        plot.setTitle("VAD 语音活动检测", size="12pt")
        plot.setLabel('left', '状态')
        plot.setLabel('bottom', '时间')
        plot.setYRange(-0.1, 1.1)
        plot.setBackground('w')
        plot.showGrid(x=True, y=True, alpha=0.3)
        self.vad_curve = plot.plot(
            pen=pg.mkPen(color='r', width=2),
            fillLevel=0,
            brush=(255, 0, 0, 100)
        )
        return plot
    
    def create_asr_panel(self) -> QGroupBox:
        """创建ASR结果面板"""
        group = QGroupBox("ASR 识别结果")
        group.setFont(QFont("Arial", 12, QFont.Bold))
        
        layout = QVBoxLayout()
        
        self.asr_result_text = QTextEdit()
        self.asr_result_text.setReadOnly(True)
        self.asr_result_text.setFont(QFont("Arial", 12))
        self.asr_result_text.setPlaceholderText("识别结果将显示在这里...")
        self.asr_result_text.setMaximumHeight(150)
        layout.addWidget(self.asr_result_text)
        
        self.asr_detail_label = QLabel("")
        self.asr_detail_label.setFont(QFont("Courier", 9))
        layout.addWidget(self.asr_detail_label)
        
        group.setLayout(layout)
        return group
    
    def toggle_system(self):
        """切换系统运行状态"""
        if not self.is_running:
            self.start_system()
        else:
            self.stop_system()
    
    def start_system(self):
        """启动系统"""
        try:
            print("\n" + "="*60)
            print("🚀 启动 Kiwi 语音助手系统")
            print("="*60)
            
            # 1. 创建控制器
            self.controller = SystemController(debug=False)
            
            # 2. 创建配置
            config = get_config()
            
            # 使用系统默认麦克风（device_index=None）
            audio_config = AudioConfig(
                sample_rate=16000,
                channels=1,
                chunk_size=1024,
                device_index=None
            )
            
            # 唤醒词配置
            wakeword_settings = config.wakeword.settings
            wakeword_config = WakeWordConfig(
                sample_rate=16000,
                models=wakeword_settings.get('models', []),
                threshold=wakeword_settings.get('threshold', 0.5)
            )
            
            # VAD配置
            vad_settings = config.vad.settings
            vad_config = VADConfig(
                sample_rate=16000,
                frame_duration_ms=vad_settings.get('frame_duration_ms', 30),
                aggressiveness=vad_settings.get('aggressiveness', 2),
                wakeword_delay_ms=vad_settings.get('wakeword_delay_ms', 500),
                vad_end_silence_ms=vad_settings.get('vad_end_silence_ms', 1000)
            )
            
            # ASR配置
            asr_config = ASRConfig(
                model=config.asr.settings['model'],
                language=config.asr.settings['language'],
                model_size='base',
                device='auto'
            )
            
            # 3. 创建并注册模块
            self.audio_adapter = AudioModuleAdapter(self.controller, audio_config)
            self.controller.register_module(self.audio_adapter)
            
            self.wakeword_adapter = WakewordModuleAdapter(self.controller, wakeword_config)
            self.controller.register_module(self.wakeword_adapter)
            
            self.vad_adapter = VADModuleAdapter(self.controller, vad_config)
            self.controller.register_module(self.vad_adapter)
            
            self.asr_adapter = ASRModuleAdapter(self.controller, asr_config)
            self.controller.register_module(self.asr_adapter)
            
            # 4. 创建并注册GUI适配器
            self.gui_adapter = GUIModuleAdapter(self.controller)
            self.controller.register_module(self.gui_adapter)
            
            # 5. 连接GUI信号处理器
            self.connect_gui_signals()
            
            # 6. 创建状态机配置
            from src.state_machine import StateConfig
            state_config = StateConfig(
                enable_wakeword=True,
                wakeword_timeout=10.0,
                max_vad_end_count=1,  # 一次VAD END就重置
                enable_vad=True,
                enable_asr=True,
                debug=False
            )
            
            # 7. 初始化所有模块
            if not self.controller.initialize_all(state_config):
                raise Exception("模块初始化失败")
            
            # 8. 启动所有模块
            if not self.controller.start_all():
                raise Exception("模块启动失败")
            
            # 9. 更新UI状态
            self.is_running = True
            self.start_btn.setText("⏸️ 停止系统")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 12px 24px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """)
            self.status_label.setText("Status: ready")
            
            # 9. 启动显示更新定时器
            self.display_timer.start()
            self.stats_timer.start()
            
            print("✅ 系统启动成功")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"❌ 系统启动失败: {e}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"错误: {e}")
            self.cleanup_system()
    
    def stop_system(self):
        """停止系统"""
        print("\n" + "="*60)
        print("🛑 停止 Kiwi 语音助手系统")
        print("="*60)
        
        try:
            # 停止定时器
            self.display_timer.stop()
            self.stats_timer.stop()
            
            # 停止控制器
            if self.controller:
                self.controller.stop_all()
                self.controller.cleanup_all()
            
            self.cleanup_system()
            
            # 更新UI
            self.start_btn.setText("▶️ 启动系统")
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 12px 24px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            self.status_label.setText("Status: ready")
            
            print("✅ 系统已停止")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"❌ 停止系统时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def cleanup_system(self):
        """清理系统资源"""
        self.is_running = False
        self.controller = None
        self.gui_adapter = None
        self.audio_adapter = None
        self.wakeword_adapter = None
        self.vad_adapter = None
        self.asr_adapter = None
        
        # 清空缓冲区
        self.waveform_buffer.clear()
        self.vad_state_history.clear()
        self.spectrum_data = None
    
    def connect_gui_signals(self):
        """连接GUI信号处理器"""
        if not self.gui_adapter:
            return
        
        self.gui_adapter.connect_wakeword_handler(self.on_wakeword_detected)
        self.gui_adapter.connect_vad_start_handler(self.on_vad_speech_start)
        self.gui_adapter.connect_vad_end_handler(self.on_vad_speech_end)
        self.gui_adapter.connect_asr_result_handler(self.on_asr_result)
        self.gui_adapter.connect_asr_error_handler(self.on_asr_error)
        self.gui_adapter.connect_state_changed_handler(self.on_state_changed)
        self.gui_adapter.connect_audio_frame_handler(self.on_audio_frame)
    
    # ==================== 事件处理器 ====================
    
    def on_wakeword_detected(self, data: dict):
        """唤醒词检测处理"""
        keyword = data.get('keyword', 'unknown')
        confidence = data.get('confidence', 0.0)
        self.status_label.setText("Status: wake up")
        print(f"🎯 唤醒词: {keyword} ({confidence:.2f})")
    
    def on_vad_speech_start(self, data: dict):
        """语音开始处理"""
        self.status_label.setText("Status: vad begin")
        print("🎤 语音开始")
        # 更新当前VAD状态为1（语音活动）
        self.current_vad_state = 1.0
    
    def on_vad_speech_end(self, data: dict):
        """语音结束处理"""
        duration = data.get('duration_ms', 0)
        self.status_label.setText("Status: vad end")
        print(f"🔇 语音结束 (时长: {duration:.0f}ms)")
        # 更新当前VAD状态为0（静音）
        self.current_vad_state = 0.0
        
        # VAD END后延迟切换回ready状态
        QTimer.singleShot(100, lambda: self.status_label.setText("Status: ready"))
    
    def on_asr_result(self, data: dict):
        """ASR识别结果处理"""
        text = data.get('text', '')
        confidence = data.get('confidence', 0.0)
        latency = data.get('latency_ms', 0.0)
        
        # 显示结果 - 使用append而不是setText避免重复
        if text and text.strip():  # 只添加非空文本
            self.asr_result_text.append(text)
        
        # 滚动到底部
        self.asr_result_text.verticalScrollBar().setValue(
            self.asr_result_text.verticalScrollBar().maximum()
        )
        
        # 显示详情
        detail = f"置信度: {confidence:.2f} | 延迟: {latency:.0f}ms"
        self.asr_detail_label.setText(detail)
        
        # ASR结果不改变状态（已经是ready）
        print(f"✅ 识别结果: {text} ({confidence:.2f}, {latency:.0f}ms)")
    
    def on_asr_error(self, error: str):
        """ASR识别错误处理"""
        # ASR错误不改变状态（已经是ready）
        print(f"❌ ASR错误: {error}")
    
    def on_state_changed(self, data: dict):
        """状态变化处理"""
        new_state = data.get('new_state', '')
        print(f"📊 状态变化: {new_state}")
    
    def on_audio_frame(self, data: dict):
        """音频帧处理（用于波形显示和频谱分析）"""
        audio_data = data.get('audio_data')
        if audio_data is None:
            return
        
        # 归一化
        if audio_data.dtype == np.int16:
            normalized = audio_data.astype(np.float32) / 32768.0
        else:
            normalized = audio_data
        
        # 添加到缓冲区
        self.waveform_buffer.extend(normalized)
        
        # 更新VAD状态历史（每个音频帧都添加当前状态）
        self.vad_state_history.append(self.current_vad_state)
        
        # 计算频谱（FFT）
        if len(normalized) >= 512:  # 至少需要512个样本
            self._compute_spectrum(normalized)
    
    def _compute_spectrum(self, audio_data: np.ndarray):
        """计算音频频谱"""
        # 使用最近的1024个样本以获得更好的频率分辨率
        samples = audio_data[-1024:] if len(audio_data) > 1024 else audio_data
        
        # 应用汉宁窗减少频谱泄漏
        window = np.hanning(len(samples))
        windowed_samples = samples * window
        
        # 执行FFT
        fft_result = np.fft.rfft(windowed_samples)
        
        # 计算幅度（dB）
        magnitude = np.abs(fft_result)
        magnitude = np.maximum(magnitude, 1e-10)  # 避免log(0)
        magnitude_db = 20 * np.log10(magnitude)
        
        # 归一化到[-60, 0]范围，增强对比度
        magnitude_db = np.clip(magnitude_db, -60, 0)
        
        # 应用动态范围压缩，拉开频段差距
        # 使用平方根压缩增强低幅度信号的可见度
        magnitude_normalized = (magnitude_db + 60) / 60  # 归一化到[0, 1]
        magnitude_compressed = np.sqrt(magnitude_normalized)  # 平方根压缩
        magnitude_db_enhanced = magnitude_compressed * 60 - 60  # 映射回dB范围
        
        # 计算频率轴（假设采样率16kHz）
        sample_rate = 16000
        freqs = np.fft.rfftfreq(len(samples), 1.0 / sample_rate)
        
        # 存储频谱数据
        self.spectrum_data = (freqs, magnitude_db_enhanced)
    
    # ==================== 显示更新 ====================
    
    def update_display(self):
        """更新显示"""
        if not self.is_running:
            return
        
        # 更新波形
        if len(self.waveform_buffer) > 0:
            waveform_data = np.array(self.waveform_buffer)
            self.waveform_curve.setData(waveform_data)
        
        # 更新频谱
        if self.spectrum_data is not None:
            freqs, magnitude_db = self.spectrum_data
            self.spectrum_curve.setData(freqs, magnitude_db)
        
        # 更新VAD状态
        if len(self.vad_state_history) > 0:
            vad_data = np.array(self.vad_state_history)
            self.vad_curve.setData(vad_data)
    
    def update_stats(self):
        """更新统计信息"""
        if not self.controller:
            return
        
        try:
            stats = self.controller.get_statistics()
            
            stats_text = (
                f"运行时间: {stats['uptime_seconds']:.1f}s | "
                f"模块: {stats['modules_count']} | "
                f"事件处理: {stats['events_processed']} | "
                f"队列: {stats['event_queue_size']} | "
                f"状态: {stats['current_state']}"
            )
            
            # 添加模块统计
            if self.audio_adapter:
                audio_stats = self.audio_adapter.get_statistics()
                stats_text += f" | 音频帧: {audio_stats['frames_processed']}"
            
            self.stats_label.setText(stats_text)
            
        except Exception as e:
            print(f"⚠️ 更新统计信息失败: {e}")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.is_running:
            self.stop_system()
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = KiwiVoiceAssistantGUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
