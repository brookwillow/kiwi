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
    QGroupBox, QCheckBox, QLineEdit
)
from PyQt5.QtCore import QTimer, Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QFont, QColor

from src.core.controller import SystemController
from src.core.events import Event, EventType
from src.adapters import (
    AudioModuleAdapter,
    WakewordModuleAdapter,
    VADModuleAdapter,
    ASRModuleAdapter,
    GUIModuleAdapter,
    TTSModuleAdapter,
    MemoryModuleAdapter
)
from src.adapters.orchestrator_adapter import OrchestratorModuleAdapter
from src.agents import AgentsModule
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
        self.tts_adapter: Optional[TTSModuleAdapter] = None
        
        # UI状态
        self.is_running = False
        self.current_vad_state = 0.0  # 当前VAD状态：0=静音，1=语音
        
        # 查询历史追踪（用于将query、agent、response关联起来）
        self._current_query_info = {}  # 存储当前查询的信息
        
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
        self.resize(1400, 900)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 标题
        title = QLabel("🥝 Kiwi 智能语音助手")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # 系统状态和工作状态的容器
        status_container = QHBoxLayout()
        
        # 系统运行状态指示器（左侧）
        self.system_status_label = QLabel("⚫ 系统未启动")
        self.system_status_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.system_status_label.setAlignment(Qt.AlignCenter)
        self.system_status_label.setStyleSheet("""
            QLabel {
                padding: 10px 20px;
                background-color: #757575;
                color: white;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        status_container.addWidget(self.system_status_label, stretch=1)
        
        # 工作状态显示（右侧，美化版）
        self.status_label = QLabel("💤 系统就绪")
        self.status_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 20px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e8f5e9, stop:1 #c8e6c9);
                color: #2e7d32;
                border-radius: 10px;
                border: 2px solid #81c784;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        status_container.addWidget(self.status_label, stretch=3)
        
        main_layout.addLayout(status_container)
        
        # 创建左右分栏布局
        content_layout = QHBoxLayout()
        
        # 左侧：音频可视化面板
        left_panel = self.create_left_panel()
        content_layout.addWidget(left_panel, stretch=1)
        
        # 右侧：Orchestrator决策结果面板
        right_panel = self.create_right_panel()
        content_layout.addWidget(right_panel, stretch=1)
        
        main_layout.addLayout(content_layout)
        
        # 统计信息
        self.stats_label = QLabel("统计信息: --")
        self.stats_label.setFont(QFont("Courier", 10))
        self.stats_label.setStyleSheet("padding: 5px; background-color: #f9f9f9;")
        main_layout.addWidget(self.stats_label)
        
        # 控制面板（移到最下方）
        control_layout = self.create_control_panel()
        main_layout.addLayout(control_layout)
        
        self.setLayout(main_layout)
    
    def create_left_panel(self) -> QGroupBox:
        """创建左侧音频可视化面板"""
        group = QGroupBox("音频可视化")
        group.setFont(QFont("Arial", 12, QFont.Bold))
        
        layout = QVBoxLayout()
        
        # 波形显示
        self.waveform_plot = self.create_waveform_plot()
        layout.addWidget(self.waveform_plot)
        
        # 频谱显示
        self.spectrum_plot = self.create_spectrum_plot()
        layout.addWidget(self.spectrum_plot)
        
        # VAD状态
        self.vad_plot = self.create_vad_plot()
        layout.addWidget(self.vad_plot)
        
        # ASR结果（简化版）
        asr_group = self.create_asr_panel()
        layout.addWidget(asr_group)
        
        group.setLayout(layout)
        return group
    
    def create_right_panel(self) -> QGroupBox:
        """创建右侧Orchestrator决策结果面板"""
        group = QGroupBox("🤖 AI决策中心")
        group.setFont(QFont("Arial", 12, QFont.Bold))
        
        layout = QVBoxLayout()
        
        # 当前选中的Agent
        agent_label = QLabel("当前选中Agent:")
        agent_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(agent_label)
        
        self.selected_agent_label = QLabel("--")
        self.selected_agent_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.selected_agent_label.setStyleSheet("""
            padding: 15px;
            background-color: #e3f2fd;
            border: 2px solid #2196F3;
            border-radius: 8px;
            color: #1976D2;
        """)
        self.selected_agent_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.selected_agent_label)
        
        # 置信度显示
        confidence_label = QLabel("置信度:")
        confidence_label.setFont(QFont("Arial", 11))
        layout.addWidget(confidence_label)
        
        self.confidence_label = QLabel("--")
        self.confidence_label.setFont(QFont("Arial", 14))
        self.confidence_label.setStyleSheet("padding: 10px; background-color: #f5f5f5; border-radius: 5px;")
        layout.addWidget(self.confidence_label)
        
        # 决策理由
        reasoning_label = QLabel("决策理由:")
        reasoning_label.setFont(QFont("Arial", 11))
        layout.addWidget(reasoning_label)
        
        self.reasoning_text = QTextEdit()
        self.reasoning_text.setReadOnly(True)
        self.reasoning_text.setFont(QFont("Arial", 11))
        self.reasoning_text.setPlaceholderText("决策理由将显示在这里...")
        self.reasoning_text.setMaximumHeight(150)
        layout.addWidget(self.reasoning_text)
        
        # 创建短期记忆和长期记忆的水平布局
        memory_layout = QHBoxLayout()
        
        # 左侧：短期记忆（原查询历史）
        short_term_widget = QWidget()
        short_term_layout = QVBoxLayout()
        short_term_layout.setContentsMargins(0, 0, 0, 0)
        
        short_term_label = QLabel("📝 短期记忆:")
        short_term_label.setFont(QFont("Arial", 11, QFont.Bold))
        short_term_layout.addWidget(short_term_label)
        
        self.query_history_text = QTextEdit()
        self.query_history_text.setReadOnly(True)
        self.query_history_text.setFont(QFont("Courier", 10))
        self.query_history_text.setPlaceholderText("短期记忆将显示在这里...")
        short_term_layout.addWidget(self.query_history_text)
        
        short_term_widget.setLayout(short_term_layout)
        memory_layout.addWidget(short_term_widget, stretch=1)
        
        # 右侧：长期记忆
        long_term_widget = QWidget()
        long_term_layout = QVBoxLayout()
        long_term_layout.setContentsMargins(0, 0, 0, 0)
        
        long_term_label = QLabel("🧠 长期记忆:")
        long_term_label.setFont(QFont("Arial", 11, QFont.Bold))
        long_term_layout.addWidget(long_term_label)
        
        self.long_term_memory_text = QTextEdit()
        self.long_term_memory_text.setReadOnly(True)
        self.long_term_memory_text.setFont(QFont("Courier", 10))
        self.long_term_memory_text.setPlaceholderText("长期记忆将显示在这里...")
        self.long_term_memory_text.setStyleSheet("""
            QTextEdit {
                background-color: #fff8e1;
                border: 1px solid #ffc107;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        long_term_layout.addWidget(self.long_term_memory_text)
        
        long_term_widget.setLayout(long_term_layout)
        memory_layout.addWidget(long_term_widget, stretch=1)
        
        layout.addLayout(memory_layout)
        
        # Orchestrator统计
        self.orchestrator_stats_label = QLabel("Orchestrator统计: --")
        self.orchestrator_stats_label.setFont(QFont("Courier", 9))
        self.orchestrator_stats_label.setStyleSheet("padding: 5px; background-color: #fafafa;")
        layout.addWidget(self.orchestrator_stats_label)
        
        group.setLayout(layout)
        return group
    
    def create_control_panel(self) -> QHBoxLayout:
        """创建控制面板"""
        layout = QHBoxLayout()
        
        # 文本输入测试区域
        test_label = QLabel("测试输入:")
        test_label.setFont(QFont("Arial", 11))
        layout.addWidget(test_label)
        
        self.test_input = QLineEdit()
        self.test_input.setPlaceholderText("输入文本测试（不需要语音）...")
        self.test_input.setFont(QFont("Arial", 12))
        self.test_input.setMinimumWidth(300)
        self.test_input.returnPressed.connect(self.send_test_query)
        layout.addWidget(self.test_input)
        
        self.send_btn = QPushButton("📤 发送")
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.send_btn.clicked.connect(self.send_test_query)
        layout.addWidget(self.send_btn)
        
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
    
    def send_test_query(self):
        """发送测试查询（不通过语音）"""
        # 检查系统是否运行
        if not self.is_running:
            print("⚠️ [测试] 系统未启动，无法发送查询")
            return
        
        # 获取输入文本
        text = self.test_input.text().strip()
        if not text:
            return
        
        # 清空输入框
        self.test_input.clear()
        
        # 在单独的线程中发布事件，避免阻塞GUI主线程
        import threading
        def publish_event_async():
            print("publish_event_async ")
            try:
                # 创建合成ASR事件
                event = Event.create(
                    event_type=EventType.ASR_RECOGNITION_SUCCESS,
                    source="gui_test",
                    data={
                        'text': text,
                        'confidence': 1.0,
                        'latency_ms': 0
                    }
                )
                
                # 发布事件到系统（这会触发orchestrator → agent → TTS的处理链）
                self.controller.publish_event(event)
                print(f"🧪 [测试] 发送查询: {text}")
                
            except Exception as e:
                print(f"❌ [测试] 发送查询失败: {e}")
                import traceback
                traceback.print_exc()
        
        # 启动异步线程
        # thread = threading.Thread(target=publish_event_async, daemon=True)
        # thread.start()
        publish_event_async()
    
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
            
            # 4. 创建并注册Agents模块
            self.agents_module = AgentsModule(self.controller,config_path="config/agents_config.yaml")
            self.controller.register_module(self.agents_module)
            
            # 5. 创建并注册Orchestrator模块
            # 从环境变量或配置读取API Key
            import os
            api_key = os.getenv("DASHSCOPE_API_KEY")
            use_mock = config.orchestrator.settings.get('use_mock_llm', True)
            
            self.orchestrator_adapter = OrchestratorModuleAdapter(
                self.controller,
                llm_api_key=api_key,
                use_mock_llm=use_mock
            )
            self.controller.register_module(self.orchestrator_adapter)
            
            # 6. 创建并注册TTS模块
            self.tts_adapter = TTSModuleAdapter(self.controller)
            self.controller.register_module(self.tts_adapter)
            
            # 7. 创建并注册GUI适配器
            self.gui_adapter = GUIModuleAdapter(self.controller)
            self.controller.register_module(self.gui_adapter)

            # 8. 创建并注册记忆适配器（使用相同的API key）
            self.memory_adapter = MemoryModuleAdapter(self.controller, api_key=api_key)
            self.controller.register_module(self.memory_adapter)
            
            # 9. 连接GUI信号处理器
            self.connect_gui_signals()
            
            # 10. 创建状态机配置
            from src.state_machine import StateConfig
            state_config = StateConfig(
                enable_wakeword=True,
                wakeword_timeout=10.0,
                max_vad_end_count=1,  # 一次VAD END就重置
                enable_vad=True,
                enable_asr=True,
                debug=False
            )
            
            # 11. 初始化所有模块
            if not self.controller.initialize_all(state_config):
                raise Exception("模块初始化失败")
            
            # 12. 启动所有模块
            if not self.controller.start_all():
                raise Exception("模块启动失败")
            
            # 13. 更新UI状态
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
            
            # 更新系统状态指示器为运行中
            self.system_status_label.setText("🟢 系统运行中")
            self.system_status_label.setStyleSheet("""
                QLabel {
                    padding: 10px 20px;
                    background-color: #4CAF50;
                    color: white;
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: bold;
                }
            """)
            
            # 更新工作状态
            self.update_status_display(
                'ready', '💤', '系统就绪',
                '#e8f5e9', '#c8e6c9', '#81c784'
            )
            
            # 启动显示更新定时器
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
            
            # 更新系统状态指示器为未启动
            self.system_status_label.setText("⚫ 系统未启动")
            self.system_status_label.setStyleSheet("""
                QLabel {
                    padding: 10px 20px;
                    background-color: #757575;
                    color: white;
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: bold;
                }
            """)
            
            # 更新工作状态
            self.status_label.setText("💤 系统就绪")
            self.status_label.setStyleSheet("""
                QLabel {
                    padding: 20px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #e8f5e9, stop:1 #c8e6c9);
                    color: #2e7d32;
                    border-radius: 10px;
                    border: 2px solid #81c784;
                    font-size: 18px;
                    font-weight: bold;
                }
            """)
            
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
        self.gui_adapter.connect_asr_start_handler(self.on_asr_start)
        self.gui_adapter.connect_asr_result_handler(self.on_asr_result)
        self.gui_adapter.connect_asr_error_handler(self.on_asr_error)
        self.gui_adapter.connect_state_changed_handler(self.on_state_changed)
        self.gui_adapter.connect_audio_frame_handler(self.on_audio_frame)
        self.gui_adapter.connect_orchestrator_decision_handler(self.on_orchestrator_decision)
        self.gui_adapter.connect_agent_response_handler(self._on_agent_response)
    
    def update_status_display(self, status: str, icon: str, text: str, color_start: str, color_end: str, border_color: str):
        """
        更新状态显示的样式
        
        Args:
            status: 状态标识
            icon: 状态图标
            text: 显示文本
            color_start: 渐变起始颜色
            color_end: 渐变结束颜色
            border_color: 边框颜色
        """
        self.status_label.setText(f"{icon} {text}")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                padding: 20px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color_start}, stop:1 {color_end});
                color: #1a1a1a;
                border-radius: 10px;
                border: 3px solid {border_color};
                font-size: 18px;
                font-weight: bold;
            }}
        """)
    
    # ==================== 事件处理器 ====================
    
    def on_wakeword_detected(self, data: dict):
        """唤醒词检测处理"""
        keyword = data.get('keyword', 'unknown')
        confidence = data.get('confidence', 0.0)
        self.update_status_display(
            'wake_up', '🎯', f'唤醒',
            '#fff3e0', '#ffe0b2', '#ffb74d'
        )
        print(f"🎯 唤醒词: {keyword} ({confidence:.2f})")
    
    def on_vad_speech_start(self, data: dict):
        """语音开始处理"""
        self.update_status_display(
            'vad_begin', '🎤', '正在说话...',
            '#e3f2fd', '#bbdefb', '#42a5f5'
        )
        print("🎤 语音开始")
        # 更新当前VAD状态为1（语音活动）
        self.current_vad_state = 1.0
    
    def on_vad_speech_end(self, data: dict):
        """语音结束处理"""
        duration = data.get('duration_ms', 0)
        # VAD结束后直接进入ASR识别状态
        self.update_status_display(
            'asr_recognizing', '🔄', '识别中...',
            '#f3e5f5', '#e1bee7', '#ab47bc'
        )
        print(f"🔇 语音结束 (时长: {duration:.0f}ms) → 开始ASR识别")
        # 更新当前VAD状态为0（静音）
        self.current_vad_state = 0.0
    
    def on_asr_start(self, data: dict):
        """ASR开始识别处理"""
        # 状态已在 on_vad_speech_end 中设置为 "asr recognizing"
        # 这里只记录日志
        print("🎙️ ASR: 开始处理音频数据...")
    
    def on_asr_result(self, data: dict):
        """ASR识别结果处理"""
        text = data.get('text', '')
        confidence = data.get('confidence', 0.0)
        latency = data.get('latency_ms', 0.0)
        
        # ASR识别完成，进入Orchestrator决策状态
        self.update_status_display(
            'orchestrator_deciding', '🤔', 'AI决策中...',
            '#e8eaf6', '#c5cae9', '#5c6bc0'
        )
        print(f"✅ 识别结果: {text} (置信度: {confidence:.2f}, 耗时: {latency:.0f}ms)")
        print("🤔 Orchestrator决策中...")
        print("="*60)
        
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
        
        print(f"✅ 识别结果: {text} ({confidence:.2f}, {latency:.0f}ms)")
        print("🤔 Orchestrator决策中...")
    
    def on_asr_error(self, error: str):
        """ASR识别错误处理"""
        print(f"❌ ASR错误: {error}")
        # ASR错误，回到ready状态
        self.update_status_display(
            'ready', '💤', '系统就绪',
            '#e8f5e9', '#c8e6c9', '#81c784'
        )
    
    def on_state_changed(self, data: dict):
        """状态变化处理"""
        new_state = data.get('new_state', '')
        print(f"📊 状态变化: {new_state}")
    
    def on_audio_frame(self, data: dict):
        """音频帧处理（用于波形显示和频谱分析）"""
        audio_data = data.get('audio_data')
        if audio_data is None or len(audio_data) == 0:
            return
        
        try:
            # 归一化
            if audio_data.dtype == np.int16:
                normalized = audio_data.astype(np.float32) / 32768.0
            else:
                normalized = audio_data
            
            # 检查数据有效性
            if not np.isfinite(normalized).all():
                return
            
            # 添加到缓冲区
            self.waveform_buffer.extend(normalized)
            
            # 更新VAD状态历史（每个音频帧都添加当前状态）
            self.vad_state_history.append(self.current_vad_state)
            
            # 计算频谱（FFT）
            if len(normalized) >= 512:  # 至少需要512个样本
                self._compute_spectrum(normalized)
        except Exception as e:
            # 避免音频处理错误影响系统运行
            pass
    
    def on_orchestrator_decision(self, data: dict):
        """Orchestrator决策结果处理"""
        print("="*60)
        print("🤖 GUI: 收到Orchestrator决策结果")
        print("="*60)
        
        query = data.get('query', '')
        agent = data.get('agent', '')
        confidence = data.get('confidence', 0.0)
        reasoning = data.get('reasoning', '')
        
        # 更新状态为Agent运行中
        self.update_status_display(
            'agent_running', '🚀', f'执行 {agent}...',
            '#e8f5e9', '#c8e6c9', '#66bb6a'
        )
        print(f"✅ GUI: 状态已更新为 'agent running' (选中: {agent})")
        print("="*60)
        
        # 更新选中的Agent
        self.selected_agent_label.setText(f"🎯 {agent}")
        
        # 根据Agent类型设置不同颜色
        agent_colors = {
            'music_agent': '#e1f5fe',  # 浅蓝
            'navigation_agent': '#f3e5f5',  # 浅紫
            'vehicle_control_agent': '#fff3e0',  # 浅橙
            'weather_agent': '#e0f2f1',  # 浅青
            'chat_agent': '#fce4ec',  # 浅粉
        }
        bg_color = agent_colors.get(agent, '#e3f2fd')
        self.selected_agent_label.setStyleSheet(f"""
            padding: 15px;
            background-color: {bg_color};
            border: 2px solid #2196F3;
            border-radius: 8px;
            color: #1976D2;
        """)
        
        # 更新置信度
        confidence_percent = confidence * 100
        self.confidence_label.setText(f"{confidence_percent:.1f}%")
        
        # 根据置信度设置颜色
        if confidence >= 0.8:
            conf_color = "#c8e6c9"  # 绿色
        elif confidence >= 0.5:
            conf_color = "#fff9c4"  # 黄色
        else:
            conf_color = "#ffcdd2"  # 红色
        
        self.confidence_label.setStyleSheet(f"""
            padding: 10px;
            background-color: {conf_color};
            border-radius: 5px;
            font-weight: bold;
        """)
        
        # 更新决策理由
        self.reasoning_text.setText(reasoning)
        
        # 保存当前查询信息，等待Agent响应后再添加到历史
        import time
        timestamp = time.strftime("%H:%M:%S")
        self._current_query_info = {
            'timestamp': timestamp,
            'query': query,
            'agent': agent,
            'confidence': confidence_percent
        }
        
        print(f"🤖 Orchestrator决策: {agent} (置信度: {confidence:.2f})")
    
    
    def _on_agent_response(self, response_data: dict):
        """处理Agent响应结果"""
        agent = response_data.get('agent', '')
        message = response_data.get('message', '')
        success = response_data.get('success', False)
        
        # 添加完整的历史记录（包含query、agent、response）
        if self._current_query_info:
            timestamp = self._current_query_info.get('timestamp', '')
            query = self._current_query_info.get('query', '')
            agent_name = self._current_query_info.get('agent', '')
            confidence = self._current_query_info.get('confidence', 0)
            
            # 构建历史记录行
            status_icon = "✅" if success else "❌"
            history_line = f"{status_icon} [{timestamp}] {query}\n   → Agent: {agent_name} ({confidence:.0f}%)\n   → 回复: {message}\n"
            
            self.query_history_text.append(history_line)
            
            # 滚动到底部
            self.query_history_text.verticalScrollBar().setValue(
                self.query_history_text.verticalScrollBar().maximum()
            )
            
            # 清空当前查询信息
            self._current_query_info = {}

        """Agent执行完成处理"""
        self.update_status_display(
            'ready', '💤', '系统就绪',
            '#e8f5e9', '#c8e6c9', '#81c784'
        )
        print("✅ Agent执行完成，回到ready状态")

        print(f"📝 [GUI] Agent响应已记录: {message}")
    
    def _compute_spectrum(self, audio_data: np.ndarray):
        """计算音频频谱"""
        try:
            # 检查输入数据
            if audio_data is None or len(audio_data) == 0:
                return
            
            # 使用最近的1024个样本以获得更好的频率分辨率
            samples = audio_data[-1024:] if len(audio_data) > 1024 else audio_data
            
            if len(samples) < 64:  # 至少需要64个样本
                return
            
            # 应用汉宁窗减少频谱泄漏
            window = np.hanning(len(samples))
            windowed_samples = samples * window
            
            # 执行FFT
            fft_result = np.fft.rfft(windowed_samples)
            
            # 计算幅度（dB）
            magnitude = np.abs(fft_result)
            magnitude = np.maximum(magnitude, 1e-10)  # 避免log(0)
            magnitude_db = 20 * np.log10(magnitude)
            
            # 检查计算结果有效性
            if not np.isfinite(magnitude_db).all():
                return
            
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
        except Exception as e:
            # 避免频谱计算错误影响系统
            pass
    
    # ==================== 显示更新 ====================
    
    def update_display(self):
        """更新显示"""
        if not self.is_running:
            return
        
        try:
            # 更新波形
            if len(self.waveform_buffer) > 0:
                waveform_data = np.array(self.waveform_buffer)
                if len(waveform_data) > 0 and np.isfinite(waveform_data).all():
                    self.waveform_curve.setData(waveform_data)
            
            # 更新频谱
            if self.spectrum_data is not None:
                freqs, magnitude_db = self.spectrum_data
                if len(freqs) > 0 and len(magnitude_db) > 0 and np.isfinite(magnitude_db).all():
                    self.spectrum_curve.setData(freqs, magnitude_db)
            
            # 更新VAD状态
            if len(self.vad_state_history) > 0:
                vad_data = np.array(self.vad_state_history)
                if len(vad_data) > 0 and np.isfinite(vad_data).all():
                    self.vad_curve.setData(vad_data)
        except Exception as e:
            # 避免显示更新错误导致整个GUI卡死
            pass  # 静默处理，不打印日志以避免终端刷屏
    
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
                f"队列: {stats['event_queue_size']}"
            )
            # 添加模块统计
            if self.audio_adapter:
                audio_stats = self.audio_adapter.get_statistics()
                stats_text += f" | 音频帧: {audio_stats['frames_processed']}"
            self.stats_label.setText(stats_text)
            
            # 更新长期记忆显示
            self.update_long_term_memory_display()
        except Exception as e:
            print(f"⚠️ 更新统计信息失败: {e}")
    
    def update_long_term_memory_display(self):
        """更新长期记忆显示"""
        try:
            if not self.memory_adapter:
                return
            
            # 从memory模块获取长期记忆（返回LongTermMemory对象）
            long_term = self.memory_adapter.get_related_long_term_memory()
            if not long_term:
                return
            
            # 格式化显示
            display_text = ""
            
            # 摘要
            if long_term.summary:
                display_text += f"📝 摘要:\n{long_term.summary}\n\n"
            
            # 用户画像
            if long_term.user_profile:
                display_text += "👤 用户画像:\n"
                for key, value in long_term.user_profile.items():
                    if value:
                        display_text += f"  • {key}: {value}\n"
                display_text += "\n"
            
            # 偏好信息
            if long_term.preferences:
                display_text += "❤️ 偏好信息:\n"
                for key, value in long_term.preferences.items():
                    if value:
                        if isinstance(value, list) and value:
                            display_text += f"  • {key}: {', '.join(str(v) for v in value)}\n"
                        elif not isinstance(value, list):
                            display_text += f"  • {key}: {value}\n"
            
            # 只在内容有变化时更新（避免闪烁）
            if display_text and display_text != self.long_term_memory_text.toPlainText():
                self.long_term_memory_text.setPlainText(display_text)
                
        except Exception as e:
            print(f"⚠️ 更新长期记忆显示失败: {e}")
    
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
