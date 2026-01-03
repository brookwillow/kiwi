"""
性能评估界面

用于运行和显示系统评估结果
"""
import sys
import time
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QGroupBox, QTextEdit, QSplitter, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont

from src.evaluation import SystemEvaluator, QwenEvaluator, TestCase, EvaluationResult


class EvaluationThread(QThread):
    """评估线程"""
    case_completed = pyqtSignal(int, TestCase)  # (索引, 测试用例)
    all_completed = pyqtSignal(EvaluationResult)  # 评估结果
    
    def __init__(self, evaluator: SystemEvaluator):
        super().__init__()
        self.evaluator = evaluator
    
    def run(self):
        """运行评估"""
        # 设置回调
        self.evaluator.on_case_complete = self._on_case_complete
        self.evaluator.on_all_complete = self._on_all_complete
        
        # 运行评估
        self.evaluator.run_evaluation()
    
    def _on_case_complete(self, test_case: TestCase):
        """单个用例完成"""
        index = self.evaluator.current_case_index
        self.case_completed.emit(index, test_case)
    
    def _on_all_complete(self, result: EvaluationResult):
        """所有用例完成"""
        self.all_completed.emit(result)


class EvaluationWindow(QWidget):
    """评估窗口"""
    
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.evaluator = None
        self.evaluation_thread = None
        
        self.init_ui()
        self.load_default_cases()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("🔍 Kiwi 性能评估系统")
        self.resize(1200, 800)
        
        # 主布局
        main_layout = QVBoxLayout()
        
        # 标题
        title = QLabel("🔍 性能评估系统")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # 控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        main_layout.addWidget(self.progress_bar)
        
        # 分割器
        splitter = QSplitter(Qt.Vertical)
        
        # 测试用例表格
        self.test_table = self.create_test_table()
        splitter.addWidget(self.test_table)
        
        # 详情面板
        details_panel = self.create_details_panel()
        splitter.addWidget(details_panel)
        
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        
        self.setLayout(main_layout)
    
    def create_control_panel(self) -> QGroupBox:
        """创建控制面板"""
        group = QGroupBox("控制面板")
        layout = QHBoxLayout()
        
        # 加载按钮
        self.load_btn = QPushButton("📁 加载测试用例")
        self.load_btn.clicked.connect(self.load_test_cases)
        layout.addWidget(self.load_btn)
        
        # 运行按钮
        self.run_btn = QPushButton("▶️  运行评估")
        self.run_btn.clicked.connect(self.run_evaluation)
        self.run_btn.setEnabled(False)
        layout.addWidget(self.run_btn)
        
        # 停止按钮
        self.stop_btn = QPushButton("⏹️  停止")
        self.stop_btn.clicked.connect(self.stop_evaluation)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)
        
        # 导出按钮
        self.export_btn = QPushButton("💾 导出结果")
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)
        layout.addWidget(self.export_btn)
        
        layout.addStretch()
        
        # 统计信息
        self.stats_label = QLabel("就绪")
        self.stats_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.stats_label)
        
        group.setLayout(layout)
        return group
    
    def create_test_table(self) -> QTableWidget:
        """创建测试用例表格"""
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            "序号", "查询", "预期Agent", "实际Agent", "状态", "耗时(ms)", "详情"
        ])
        
        # 设置列宽
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        
        # 启用选择
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.itemSelectionChanged.connect(self.on_row_selected)
        
        return table
    
    def create_details_panel(self) -> QGroupBox:
        """创建详情面板"""
        group = QGroupBox("详情")
        layout = QVBoxLayout()
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        layout.addWidget(self.details_text)
        
        group.setLayout(layout)
        return group
    
    def load_default_cases(self):
        """加载默认测试用例"""
        default_file = Path(__file__).parent.parent.parent / "data" / "test_cases.jsonl"
        if default_file.exists():
            self.load_cases_from_file(str(default_file))
    
    def load_test_cases(self):
        """加载测试用例"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择测试用例文件",
            str(Path.home()),
            "JSONL Files (*.jsonl);;All Files (*)"
        )
        
        if file_path:
            self.load_cases_from_file(file_path)
    
    def load_cases_from_file(self, file_path: str):
        """从文件加载测试用例"""
        # 创建评估器
        qwen_evaluator = QwenEvaluator()
        self.evaluator = SystemEvaluator(self.controller, qwen_evaluator)
        
        # 加载用例
        count = self.evaluator.load_test_cases(file_path)
        
        if count > 0:
            # 更新表格
            self.update_table()
            
            # 更新状态
            self.stats_label.setText(f"已加载 {count} 个测试用例")
            self.run_btn.setEnabled(True)
            
            QMessageBox.information(self, "成功", f"成功加载 {count} 个测试用例")
        else:
            QMessageBox.warning(self, "失败", "加载测试用例失败")
    
    def update_table(self):
        """更新表格"""
        if not self.evaluator:
            return
        
        test_cases = self.evaluator.test_cases
        self.test_table.setRowCount(len(test_cases))
        
        for i, tc in enumerate(test_cases):
            # 序号
            self.test_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            
            # 查询
            self.test_table.setItem(i, 1, QTableWidgetItem(tc.query))
            
            # 预期Agent
            self.test_table.setItem(i, 2, QTableWidgetItem(tc.expected_agent))
            
            # 实际Agent
            actual_agent = tc.actual_agent if tc.actual_agent else "-"
            self.test_table.setItem(i, 3, QTableWidgetItem(actual_agent))
            
            # 状态
            status_item = self._create_status_item(tc)
            self.test_table.setItem(i, 4, status_item)
            
            # 耗时
            duration = f"{tc.duration_ms:.2f}" if tc.duration_ms else "-"
            self.test_table.setItem(i, 5, QTableWidgetItem(duration))
            
            # 详情
            details = self._create_details_text(tc)
            self.test_table.setItem(i, 6, QTableWidgetItem(details))
    
    def _create_status_item(self, tc: TestCase) -> QTableWidgetItem:
        """创建状态单元格"""
        if tc.error:
            item = QTableWidgetItem("❌ 错误")
            item.setBackground(QColor(255, 200, 200))
        elif tc.passed:
            item = QTableWidgetItem("✅ 通过")
            item.setBackground(QColor(200, 255, 200))
        elif tc.agent_match is not None or tc.response_pass is not None:
            item = QTableWidgetItem("❌ 失败")
            item.setBackground(QColor(255, 200, 200))
        else:
            item = QTableWidgetItem("⏳ 等待")
            item.setBackground(QColor(240, 240, 240))
        
        item.setTextAlignment(Qt.AlignCenter)
        return item
    
    def _create_details_text(self, tc: TestCase) -> str:
        """创建详情文本"""
        if tc.error:
            return f"错误: {tc.error}"
        elif tc.evaluation_reason:
            return tc.evaluation_reason
        else:
            return ""
    
    def run_evaluation(self):
        """运行评估"""
        if not self.evaluator or not self.evaluator.test_cases:
            QMessageBox.warning(self, "警告", "请先加载测试用例")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认",
            f"确定要运行 {len(self.evaluator.test_cases)} 个测试用例吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 禁用按钮
        self.run_btn.setEnabled(False)
        self.load_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # 重置进度
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(self.evaluator.test_cases))
        
        # 创建并启动评估线程
        self.evaluation_thread = EvaluationThread(self.evaluator)
        self.evaluation_thread.case_completed.connect(self.on_case_completed)
        self.evaluation_thread.all_completed.connect(self.on_all_completed)
        self.evaluation_thread.start()
    
    def stop_evaluation(self):
        """停止评估"""
        if self.evaluation_thread and self.evaluation_thread.isRunning():
            # TODO: 实现优雅停止
            self.evaluation_thread.terminate()
            self.evaluation_thread.wait()
            
            self.run_btn.setEnabled(True)
            self.load_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            
            QMessageBox.information(self, "已停止", "评估已停止")
    
    def on_case_completed(self, index: int, test_case: TestCase):
        """单个用例完成"""
        # 更新进度条
        self.progress_bar.setValue(index + 1)
        
        # 更新表格行
        if index < self.test_table.rowCount():
            # 实际Agent
            self.test_table.setItem(index, 3, QTableWidgetItem(test_case.actual_agent or "-"))
            
            # 状态
            status_item = self._create_status_item(test_case)
            self.test_table.setItem(index, 4, status_item)
            
            # 耗时
            duration = f"{test_case.duration_ms:.2f}" if test_case.duration_ms else "-"
            self.test_table.setItem(index, 5, QTableWidgetItem(duration))
            
            # 详情
            details = self._create_details_text(test_case)
            self.test_table.setItem(index, 6, QTableWidgetItem(details))
    
    def on_all_completed(self, result: EvaluationResult):
        """所有用例完成"""
        # 更新统计信息
        stats_text = (
            f"完成 | "
            f"通过: {result.passed_cases}/{result.total_cases} ({result.pass_rate*100:.1f}%) | "
            f"Agent准确率: {result.agent_accuracy*100:.1f}% | "
            f"平均耗时: {result.avg_duration_ms:.2f}ms"
        )
        self.stats_label.setText(stats_text)
        
        # 恢复按钮
        self.run_btn.setEnabled(True)
        self.load_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.export_btn.setEnabled(True)
        
        # 显示总结
        QMessageBox.information(
            self,
            "评估完成",
            f"评估已完成！\n\n"
            f"总用例: {result.total_cases}\n"
            f"通过: {result.passed_cases} ({result.pass_rate*100:.1f}%)\n"
            f"失败: {result.failed_cases}\n"
            f"Agent准确率: {result.agent_accuracy*100:.1f}%\n"
            f"响应通过率: {result.response_pass_rate*100:.1f}%\n"
            f"总耗时: {result.duration_seconds:.2f}秒"
        )
    
    def on_row_selected(self):
        """行选中事件"""
        selected_rows = self.test_table.selectedIndexes()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        if row >= len(self.evaluator.test_cases):
            return
        
        test_case = self.evaluator.test_cases[row]
        
        # 显示详细信息
        details = f"""测试用例详情:

查询: {test_case.query}
类别: {test_case.category}

预期Agent: {test_case.expected_agent}
实际Agent: {test_case.actual_agent or "未运行"}
Agent匹配: {"✅" if test_case.agent_match else "❌" if test_case.agent_match is not None else "⏳"}

预期响应类型: {test_case.expected_response}
实际响应: {test_case.actual_response or "未运行"}
响应评估: {"✅ 通过" if test_case.response_pass else "❌ 失败" if test_case.response_pass is not None else "⏳ 等待"}
评估理由: {test_case.evaluation_reason or "无"}

耗时: {f"{test_case.duration_ms:.2f}ms" if test_case.duration_ms else "未运行"}
消息ID: {test_case.msg_id or "无"}

{"错误: " + test_case.error if test_case.error else ""}
"""
        
        self.details_text.setPlainText(details)
    
    def export_results(self):
        """导出结果"""
        if not self.evaluator or not self.evaluator.test_cases:
            QMessageBox.warning(self, "警告", "没有结果可导出")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出结果",
            str(Path.home() / "evaluation_results.json"),
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                import json
                from datetime import datetime
                
                # 计算结果
                result = self.evaluator._calculate_results(time.time(), time.time())
                
                # 保存
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
                
                QMessageBox.information(self, "成功", f"结果已导出到:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败:\n{e}")
