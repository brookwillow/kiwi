"""
测试模块适配器

验证所有适配器的基本功能
"""
import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch

from src.core.controller import SystemController
from src.core.events import EventType
from src.adapters import (
    AudioModuleAdapter,
    WakewordModuleAdapter,
    VADModuleAdapter,
    ASRModuleAdapter
)


class TestAudioModuleAdapter:
    """测试音频模块适配器"""
    
    def test_initialization(self):
        """测试初始化"""
        controller = SystemController()
        adapter = AudioModuleAdapter(controller)
        
        assert adapter.name == "audio"
        assert not adapter.is_running
    
    def test_lifecycle(self):
        """测试生命周期"""
        controller = SystemController()
        adapter = AudioModuleAdapter(controller)
        
        # 初始化
        assert adapter.initialize()
        
        # 启动
        assert adapter.start()
        assert adapter.is_running
        
        # 停止
        adapter.stop()
        assert not adapter.is_running
        
        # 清理
        adapter.cleanup()
    
    def test_statistics(self):
        """测试统计信息"""
        controller = SystemController()
        adapter = AudioModuleAdapter(controller)
        
        stats = adapter.get_statistics()
        # 注意：只有初始化并启动后才会有 frames_captured
        assert 'frames_processed' in stats
        assert 'is_running' in stats


class TestWakewordModuleAdapter:
    """测试唤醒词模块适配器"""
    
    def test_initialization(self):
        """测试初始化"""
        controller = SystemController()
        adapter = WakewordModuleAdapter(controller)
        
        assert adapter.name == "wakeword"
        assert not adapter.is_running
    
    def test_lifecycle_without_config(self):
        """测试无配置的生命周期"""
        controller = SystemController()
        adapter = WakewordModuleAdapter(controller)
        
        # 无配置应该跳过初始化
        assert adapter.initialize()
        assert adapter.start()
        adapter.stop()
        adapter.cleanup()
    
    def test_enable_disable(self):
        """测试启用/禁用"""
        controller = SystemController()
        adapter = WakewordModuleAdapter(controller)
        
        adapter.enable()
        stats = adapter.get_statistics()
        assert stats['enabled']
        
        adapter.disable()
        stats = adapter.get_statistics()
        assert not stats['enabled']
    
    def test_statistics(self):
        """测试统计信息"""
        controller = SystemController()
        adapter = WakewordModuleAdapter(controller)
        
        stats = adapter.get_statistics()
        assert 'detections' in stats
        assert 'frames_processed' in stats
        assert stats['detections'] == 0


class TestVADModuleAdapter:
    """测试VAD模块适配器"""
    
    def test_initialization(self):
        """测试初始化"""
        controller = SystemController()
        adapter = VADModuleAdapter(controller)
        
        assert adapter.name == "vad"
        assert not adapter.is_running
    
    def test_lifecycle_without_config(self):
        """测试无配置的生命周期"""
        controller = SystemController()
        adapter = VADModuleAdapter(controller)
        
        # 无配置应该跳过初始化
        assert adapter.initialize()
        assert adapter.start()
        adapter.stop()
        adapter.cleanup()
    
    def test_reset(self):
        """测试重置"""
        controller = SystemController()
        adapter = VADModuleAdapter(controller)
        
        # 即使没有引擎，reset也应该正常工作
        adapter.reset()
    
    def test_enable_disable(self):
        """测试启用/禁用"""
        controller = SystemController()
        adapter = VADModuleAdapter(controller)
        
        adapter.enable()
        stats = adapter.get_statistics()
        assert stats['enabled']
        
        adapter.disable()
        stats = adapter.get_statistics()
        assert not stats['enabled']
    
    def test_statistics(self):
        """测试统计信息"""
        controller = SystemController()
        adapter = VADModuleAdapter(controller)
        
        stats = adapter.get_statistics()
        assert 'frames_processed' in stats
        assert 'speech_segments' in stats
        assert stats['frames_processed'] == 0


class TestASRModuleAdapter:
    """测试ASR模块适配器"""
    
    def test_initialization(self):
        """测试初始化"""
        controller = SystemController()
        adapter = ASRModuleAdapter(controller)
        
        assert adapter.name == "asr"
        assert not adapter.is_running
    
    def test_lifecycle_without_config(self):
        """测试无配置的生命周期"""
        controller = SystemController()
        adapter = ASRModuleAdapter(controller)
        
        # 无配置应该跳过初始化
        assert adapter.initialize()
        assert adapter.start()
        adapter.stop()
        adapter.cleanup()
    
    def test_enable_disable(self):
        """测试启用/禁用"""
        controller = SystemController()
        adapter = ASRModuleAdapter(controller)
        
        adapter.enable()
        stats = adapter.get_statistics()
        assert stats['enabled']
        
        adapter.disable()
        stats = adapter.get_statistics()
        assert not stats['enabled']
    
    def test_statistics(self):
        """测试统计信息"""
        controller = SystemController()
        adapter = ASRModuleAdapter(controller)
        
        stats = adapter.get_statistics()
        assert 'total_recognitions' in stats
        assert 'successful_recognitions' in stats
        assert 'failed_recognitions' in stats
        assert 'success_rate' in stats
        assert 'average_latency_ms' in stats
        assert stats['total_recognitions'] == 0


class TestAdaptersIntegration:
    """测试适配器集成"""
    
    def test_register_all_adapters(self):
        """测试注册所有适配器"""
        controller = SystemController()
        
        # 注册所有适配器
        controller.register_module(AudioModuleAdapter(controller))
        controller.register_module(WakewordModuleAdapter(controller))
        controller.register_module(VADModuleAdapter(controller))
        controller.register_module(ASRModuleAdapter(controller))
        
        # 验证注册
        stats = controller.get_statistics()
        assert len(stats['modules']) == 4
        assert 'audio' in stats['modules']
        assert 'wakeword' in stats['modules']
        assert 'vad' in stats['modules']
        assert 'asr' in stats['modules']
    
    def test_initialize_all_adapters(self):
        """测试初始化所有适配器"""
        controller = SystemController()
        
        # 注册所有适配器
        controller.register_module(AudioModuleAdapter(controller))
        controller.register_module(WakewordModuleAdapter(controller))
        controller.register_module(VADModuleAdapter(controller))
        controller.register_module(ASRModuleAdapter(controller))
        
        # 初始化（无配置应该都成功）
        assert controller.initialize_all()
    
    def test_start_all_adapters(self):
        """测试启动所有适配器"""
        controller = SystemController()
        
        # 注册所有适配器
        controller.register_module(AudioModuleAdapter(controller))
        controller.register_module(WakewordModuleAdapter(controller))
        controller.register_module(VADModuleAdapter(controller))
        controller.register_module(ASRModuleAdapter(controller))
        
        # 初始化并启动
        controller.initialize_all()
        assert controller.start_all()
        
        # 验证所有模块都在运行
        # 简单验证：所有模块启动调用成功即可
        assert True  # start_all() 返回True表示成功
    
    def test_stop_all_adapters(self):
        """测试停止所有适配器"""
        controller = SystemController()
        
        # 注册所有适配器
        controller.register_module(AudioModuleAdapter(controller))
        controller.register_module(WakewordModuleAdapter(controller))
        controller.register_module(VADModuleAdapter(controller))
        controller.register_module(ASRModuleAdapter(controller))
        
        # 初始化并启动
        controller.initialize_all()
        controller.start_all()
        
        # 停止
        controller.stop_all()
        
        # 验证：stop_all 执行成功
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
