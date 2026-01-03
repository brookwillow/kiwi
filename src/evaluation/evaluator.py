"""
性能评估系统

用于评估系统的Agent选择和响应质量
"""
import json
import time
import os
from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
import requests


@dataclass
class TestCase:
    """测试用例"""
    query: str                          # 用户查询
    expected_agent: str                 # 预期的Agent
    expected_response: str              # 预期的响应类型
    category: str                       # 类别
    
    # 运行结果
    actual_agent: Optional[str] = None          # 实际选择的Agent
    actual_response: Optional[str] = None       # 实际响应
    agent_match: Optional[bool] = None          # Agent是否匹配
    response_pass: Optional[bool] = None        # 响应是否通过
    evaluation_reason: Optional[str] = None     # 评估理由
    duration_ms: Optional[float] = None         # 执行耗时
    error: Optional[str] = None                 # 错误信息
    msg_id: Optional[str] = None                # 消息追踪ID
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    @property
    def passed(self) -> bool:
        """测试是否通过"""
        if self.error:
            return False
        if self.agent_match is None or self.response_pass is None:
            return False
        return self.agent_match and self.response_pass


@dataclass
class EvaluationResult:
    """评估结果"""
    total_cases: int                    # 总测试数
    passed_cases: int                   # 通过数
    failed_cases: int                   # 失败数
    agent_accuracy: float               # Agent准确率
    response_pass_rate: float           # 响应通过率
    avg_duration_ms: float              # 平均耗时
    test_cases: List[TestCase]          # 所有测试用例
    start_time: float                   # 开始时间
    end_time: float                     # 结束时间
    
    @property
    def pass_rate(self) -> float:
        """总体通过率"""
        return self.passed_cases / self.total_cases if self.total_cases > 0 else 0.0
    
    @property
    def duration_seconds(self) -> float:
        """总耗时（秒）"""
        return self.end_time - self.start_time
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'total_cases': self.total_cases,
            'passed_cases': self.passed_cases,
            'failed_cases': self.failed_cases,
            'pass_rate': self.pass_rate,
            'agent_accuracy': self.agent_accuracy,
            'response_pass_rate': self.response_pass_rate,
            'avg_duration_ms': self.avg_duration_ms,
            'duration_seconds': self.duration_seconds,
            'start_time': datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': datetime.fromtimestamp(self.end_time).strftime('%Y-%m-%d %H:%M:%S'),
            'test_cases': [tc.to_dict() for tc in self.test_cases]
        }


class QwenEvaluator:
    """使用Qwen Plus模型进行评估"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化评估器
        
        Args:
            api_key: 阿里云API密钥
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            print("⚠️  未配置DASHSCOPE_API_KEY，将使用规则评估")
        
        self.api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    
    def evaluate_response(self, test_case: TestCase) -> tuple[bool, str]:
        """
        评估响应是否符合预期
        
        Args:
            test_case: 测试用例
            
        Returns:
            (是否通过, 评估理由)
        """
        # 如果没有API Key，使用简单的规则评估
        if not self.api_key:
            return self._rule_based_evaluate(test_case)
        
        try:
            # 构建评估提示
            prompt = f"""作为一个AI助手评估专家，请评估以下对话的质量：

用户查询：{test_case.query}
预期响应类型：{test_case.expected_response}
实际系统响应：{test_case.actual_response}

请判断实际响应是否符合预期响应类型的要求。评估标准：
1. 响应是否理解了用户意图
2. 响应是否提供了相关的功能或信息
3. 响应是否符合预期的响应类型

请以JSON格式回复：
{{
    "pass": true/false,
    "reason": "评估理由"
}}
"""
            
            # 调用Qwen API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "qwen-plus",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 500
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # 解析JSON响应
                try:
                    eval_result = json.loads(content)
                    return eval_result.get('pass', False), eval_result.get('reason', '未提供理由')
                except json.JSONDecodeError:
                    # 如果不是JSON，尝试从文本中提取
                    if 'pass' in content.lower() and 'true' in content.lower():
                        return True, content
                    else:
                        return False, content
            else:
                print(f"⚠️  API调用失败: {response.status_code}, 使用规则评估")
                return self._rule_based_evaluate(test_case)
                
        except Exception as e:
            print(f"⚠️  评估异常: {e}, 使用规则评估")
            return self._rule_based_evaluate(test_case)
    
    def _rule_based_evaluate(self, test_case: TestCase) -> tuple[bool, str]:
        """基于规则的简单评估"""
        if not test_case.actual_response:
            return False, "无响应"
        
        # 检查是否包含错误信息
        if any(word in test_case.actual_response.lower() for word in ['错误', 'error', '失败', 'failed']):
            return False, "响应包含错误信息"
        
        # 检查响应长度
        if len(test_case.actual_response) < 2:
            return False, "响应过短"
        
        # 简单通过
        return True, "基于规则的简单评估通过"


class SystemEvaluator:
    """系统评估器"""
    
    def __init__(self, controller, qwen_evaluator: Optional[QwenEvaluator] = None):
        """
        初始化评估器
        
        Args:
            controller: SystemController实例
            qwen_evaluator: Qwen评估器
        """
        self.controller = controller
        self.qwen_evaluator = qwen_evaluator or QwenEvaluator()
        self.test_cases: List[TestCase] = []
        self.current_case_index = 0
        self.is_running = False
        
        # 回调函数
        self.on_case_complete: Optional[Callable[[TestCase], None]] = None
        self.on_all_complete: Optional[Callable[[EvaluationResult], None]] = None
    
    def load_test_cases(self, file_path: str) -> int:
        """
        加载测试用例
        
        Args:
            file_path: JSONL文件路径
            
        Returns:
            加载的用例数量
        """
        self.test_cases.clear()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        test_case = TestCase(
                            query=data['query'],
                            expected_agent=data['expected_agent'],
                            expected_response=data['expected_response'],
                            category=data.get('category', 'unknown')
                        )
                        self.test_cases.append(test_case)
            
            print(f"✅ 加载了 {len(self.test_cases)} 个测试用例")
            return len(self.test_cases)
            
        except Exception as e:
            print(f"❌ 加载测试用例失败: {e}")
            return 0
    
    def run_evaluation(self):
        """运行评估"""
        if not self.test_cases:
            print("❌ 没有测试用例")
            return
        
        if self.is_running:
            print("⚠️  评估正在运行中")
            return
        
        self.is_running = True
        self.current_case_index = 0
        start_time = time.time()
        
        print(f"\n{'='*80}")
        print(f"开始评估 - 共 {len(self.test_cases)} 个测试用例")
        print(f"{'='*80}\n")
        
        # 运行所有测试用例
        for i, test_case in enumerate(self.test_cases):
            self.current_case_index = i
            print(f"\n[{i+1}/{len(self.test_cases)}] 测试: {test_case.query}")
            
            # 运行单个用例
            self._run_single_case(test_case)
            
            # 回调通知
            if self.on_case_complete:
                self.on_case_complete(test_case)
            
            # 短暂延迟，避免过快
            time.sleep(0.1)
        
        # 计算统计结果
        end_time = time.time()
        result = self._calculate_results(start_time, end_time)
        
        # 打印总结
        self._print_summary(result)
        
        # 保存结果
        self._save_results(result)
        
        # 完成回调
        if self.on_all_complete:
            self.on_all_complete(result)
        
        self.is_running = False
    
    def _run_single_case(self, test_case: TestCase):
        """运行单个测试用例"""
        case_start = time.time()
        
        try:
            # 导入消息追踪器
            from src.core.message_tracker import get_message_tracker
            from src.core.events import Event, EventType
            
            tracker = get_message_tracker()
            
            # 创建消息ID
            msg_id = tracker.create_message_id(session_type="evaluation")
            test_case.msg_id = msg_id
            tracker.update_query(msg_id, test_case.query)
            
            # 启用评估模式（禁用TTS）
            self.controller.evaluation_mode = True
            
            # 模拟文本输入 - 发布ASR识别成功事件
            event = Event.create(
                event_type=EventType.ASR_RECOGNITION_SUCCESS,
                source="evaluator",
                msg_id=msg_id,
                data={
                    'text': test_case.query,
                    'confidence': 1.0,
                    'latency_ms': 0
                }
            )
            
            # 发布事件
            self.controller.publish_event(event)
            
            # 等待agent处理完成 - 轮询检查trace是否有响应（最多等待5秒）
            max_wait = 5.0  # 最多等待5秒
            check_interval = 0.1  # 每100ms检查一次
            elapsed = 0
            
            while elapsed < max_wait:
                time.sleep(check_interval)
                elapsed += check_interval
                
                # 检查是否有响应
                trace = tracker.get_trace(msg_id)
                if trace and trace.response:
                    # 有响应了，等待一点让所有trace记录完成
                    time.sleep(0.2)
                    break
            
            # 获取最终追踪结果
            trace = tracker.get_trace(msg_id)
            
            if trace:
                # 提取Agent选择
                for module_trace in trace.traces:
                    if module_trace.event_type == "orchestrator_decision":
                        output_data = module_trace.output_data or {}
                        test_case.actual_agent = output_data.get('selected_agent', 'unknown')
                        break
                
                # 提取响应
                test_case.actual_response = trace.response
                
                # 评估Agent匹配
                test_case.agent_match = (test_case.actual_agent == test_case.expected_agent)
                
                # 使用Qwen评估响应
                test_case.response_pass, test_case.evaluation_reason = \
                    self.qwen_evaluator.evaluate_response(test_case)
                
                # 记录耗时
                test_case.duration_ms = trace.duration_ms
                
                # 打印结果
                status = "✅ 通过" if test_case.passed else "❌ 失败"
                print(f"   {status}")
                print(f"   预期Agent: {test_case.expected_agent}, 实际: {test_case.actual_agent}")
                if not test_case.response_pass:
                    print(f"   评估理由: {test_case.evaluation_reason}")
            else:
                test_case.error = "未找到追踪记录"
                print(f"   ❌ 失败: {test_case.error}")
                
        except Exception as e:
            test_case.error = str(e)
            print(f"   ❌ 异常: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # 关闭评估模式
            self.controller.evaluation_mode = False
            
            if test_case.duration_ms is None:
                test_case.duration_ms = (time.time() - case_start) * 1000
    
    def _calculate_results(self, start_time: float, end_time: float) -> EvaluationResult:
        """计算评估结果"""
        total = len(self.test_cases)
        passed = sum(1 for tc in self.test_cases if tc.passed)
        failed = total - passed
        
        # Agent准确率
        agent_correct = sum(1 for tc in self.test_cases if tc.agent_match)
        agent_accuracy = agent_correct / total if total > 0 else 0.0
        
        # 响应通过率
        response_passed = sum(1 for tc in self.test_cases if tc.response_pass)
        response_pass_rate = response_passed / total if total > 0 else 0.0
        
        # 平均耗时
        durations = [tc.duration_ms for tc in self.test_cases if tc.duration_ms is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        return EvaluationResult(
            total_cases=total,
            passed_cases=passed,
            failed_cases=failed,
            agent_accuracy=agent_accuracy,
            response_pass_rate=response_pass_rate,
            avg_duration_ms=avg_duration,
            test_cases=self.test_cases,
            start_time=start_time,
            end_time=end_time
        )
    
    def _print_summary(self, result: EvaluationResult):
        """打印评估总结"""
        print(f"\n{'='*80}")
        print(f"评估完成")
        print(f"{'='*80}")
        print(f"总用例数: {result.total_cases}")
        print(f"通过: {result.passed_cases} ({result.pass_rate*100:.1f}%)")
        print(f"失败: {result.failed_cases}")
        print(f"Agent准确率: {result.agent_accuracy*100:.1f}%")
        print(f"响应通过率: {result.response_pass_rate*100:.1f}%")
        print(f"平均耗时: {result.avg_duration_ms:.2f}ms")
        print(f"总耗时: {result.duration_seconds:.2f}s")
        print(f"{'='*80}\n")
    
    def _save_results(self, result: EvaluationResult):
        """保存评估结果"""
        try:
            # 创建结果目录
            results_dir = Path(__file__).parent.parent.parent / "logs" / "evaluation_results"
            results_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            result_file = results_dir / f"evaluation_{timestamp}.json"
            
            # 保存为JSON
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            
            print(f"📝 评估结果已保存: {result_file}")
            
        except Exception as e:
            print(f"⚠️  保存结果失败: {e}")
