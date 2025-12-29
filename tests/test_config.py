"""
配置管理器测试示例
"""
from src.config_manager import ConfigManager, get_config_manager, get_config


def test_load_config():
    """测试加载配置"""
    print("=== 测试加载配置 ===\n")
    
    manager = get_config_manager()
    manager.print_config()
    print()


def test_working_modes():
    """测试不同工作模式"""
    print("=== 测试工作模式切换 ===\n")
    
    manager = get_config_manager()
    
    for mode in [1, 2, 3]:
        manager.set_working_mode(mode)
        config = manager.config
        print(f"模式 {mode}: {config.pipeline_description}")
        print(f"  唤醒词: {'✅' if config.is_wakeword_enabled else '❌'}")
        print(f"  VAD:   {'✅' if config.is_vad_enabled else '❌'}")
        print(f"  ASR:   {'✅' if config.is_asr_enabled else '❌'}")
        print()


def test_module_toggle():
    """测试模块开关"""
    print("=== 测试模块开关 ===\n")
    
    manager = get_config_manager()
    
    # 禁用唤醒词
    manager.enable_module('wakeword', False)
    print("已禁用唤醒词模块")
    
    # 启用VAD
    manager.enable_module('vad', True)
    print("已启用VAD模块")
    
    manager.print_config()
    print()


def test_get_config():
    """测试获取配置"""
    print("=== 测试获取配置 ===\n")
    
    config = get_config()
    
    print(f"系统名称: {config.system.name}")
    print(f"系统版本: {config.system.version}")
    print(f"工作模式: {config.working_mode}")
    print(f"当前流水线: {config.pipeline_description}")
    
    # 获取模块配置
    asr_config = get_config_manager().get_module_config('asr')
    print(f"\nASR配置:")
    print(f"  启用: {asr_config.enabled}")
    print(f"  模型: {asr_config.settings['model']}")
    print(f"  语言: {asr_config.settings['language']}")
    print()


if __name__ == "__main__":
    try:
        test_load_config()
        test_working_modes()
        test_module_toggle()
        test_get_config()
        
        print("✅ 所有测试完成!")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
