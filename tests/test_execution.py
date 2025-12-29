"""
执行模块测试
测试 ExecutionManager 的输入输出
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.execution import get_execution_manager, ToolCategory


def print_section(title: str):
    """打印测试节标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


async def test_basic_interface():
    """测试基本接口"""
    print_section("1. 基本接口测试")
    
    manager = get_execution_manager()
    print(f"✅ 管理器实例: {manager}")
    
    # 测试模块信息
    info = manager.get_info()
    print(f"\n模块信息:")
    print(f"  名称: {info['name']}")
    print(f"  版本: {info['version']}")
    print(f"  工具数: {info['statistics']['total_tools']}")
    print(f"  分类数: {info['statistics']['total_categories']}")
    
    assert info['statistics']['total_tools'] == 170, "工具数量错误"
    assert info['statistics']['total_categories'] == 15, "分类数量错误"
    print("\n✅ 基本接口测试通过")


async def test_tool_execution():
    """测试工具执行"""
    print_section("2. 工具执行测试")
    
    manager = get_execution_manager()
    
    # 测试1: 启动发动机
    print("\n【测试】启动发动机")
    result = await manager.execute_tool("start_engine")
    assert result['success'] == True, "启动发动机失败"
    assert manager.is_engine_running() == True, "发动机状态错误"
    print(f"  ✅ {result['message']}")
    print(f"  ✅ 发动机状态: {manager.is_engine_running()}")
    
    # 测试2: 空调控制
    print("\n【测试】空调控制")
    result = await manager.execute_tool("turn_on_ac")
    assert result['success'] == True, "开启空调失败"
    assert manager.is_ac_on() == True, "空调状态错误"
    print(f"  ✅ {result['message']}")
    
    result = await manager.execute_tool("set_temperature", zone="driver", temperature=23.5)
    assert result['success'] == True, "设置温度失败"
    assert manager.get_temperature('driver') == 23.5, "温度设置错误"
    print(f"  ✅ 温度设置为: {manager.get_temperature('driver')}℃")
    
    # 测试3: 娱乐系统
    print("\n【测试】娱乐系统")
    result = await manager.execute_tool("play_music")
    assert result['success'] == True, "播放音乐失败"
    assert manager.is_music_playing() == True, "音乐状态错误"
    print(f"  ✅ {result['message']}")
    
    result = await manager.execute_tool("set_volume", volume=75)
    assert result['success'] == True, "设置音量失败"
    assert manager.get_volume() == 75, "音量设置错误"
    print(f"  ✅ 音量设置为: {manager.get_volume()}")
    
    # 测试4: 导航系统
    print("\n【测试】导航系统")
    result = await manager.execute_tool("navigate_to", destination="北京市朝阳区")
    assert result['success'] == True, "导航设置失败"
    assert manager.is_navigation_active() == True, "导航状态错误"
    assert manager.get_navigation_destination() == "北京市朝阳区", "导航目的地错误"
    print(f"  ✅ 导航至: {manager.get_navigation_destination()}")
    
    # 测试5: 车窗控制
    print("\n【测试】车窗控制")
    result = await manager.execute_tool("open_window", window="driver", percentage=50)
    assert result['success'] == True, "打开车窗失败"
    assert manager.get_state_value("windows")["driver"] == 50, "车窗位置错误"
    print(f"  ✅ 驾驶侧车窗: {manager.get_state_value('windows')['driver']}%")
    
    print("\n✅ 工具执行测试通过 (5/5)")


async def test_state_management():
    """测试状态管理"""
    print_section("3. 状态管理测试")
    
    manager = get_execution_manager()
    
    # 测试单个状态设置
    print("\n【测试】单个状态设置")
    manager.set_state_value("speed", 80.0)
    assert manager.get_speed() == 80.0, "速度设置错误"
    print(f"  ✅ 速度设置: {manager.get_speed()} km/h")
    
    manager.set_state_value("fuel_level", 65.5)
    assert manager.get_fuel_level() == 65.5, "油量设置错误"
    print(f"  ✅ 油量设置: {manager.get_fuel_level()}%")
    
    # 测试批量更新
    print("\n【测试】批量状态更新")
    updates = {
        "battery_level": 88.0,
        "cruise_control_enabled": True,
        "cruise_control_speed": 100
    }
    success = manager.update_state_values(updates)
    assert success == True, "批量更新失败"
    assert manager.get_battery_level() == 88.0, "电量更新错误"
    assert manager.get_state_value("cruise_control_enabled") == True, "巡航状态错误"
    print(f"  ✅ 电量: {manager.get_battery_level()}%")
    print(f"  ✅ 定速巡航: {manager.get_state_value('cruise_control_enabled')}")
    
    # 测试获取所有状态
    print("\n【测试】获取所有状态")
    all_states = manager.get_all_states()
    assert isinstance(all_states, dict), "状态格式错误"
    assert len(all_states) == 70, "状态字段数量错误"
    print(f"  ✅ 状态字段数: {len(all_states)}")
    
    print("\n✅ 状态管理测试通过")


async def test_convenience_methods():
    """测试便捷方法"""
    print_section("4. 便捷方法测试")
    
    manager = get_execution_manager()
    
    # 先确保发动机关闭
    await manager.execute_tool("stop_engine")
    
    # 测试场景方法
    print("\n【测试】场景方法")
    
    # 启动车辆
    result = await manager.start_vehicle()
    assert result['success'] == True, "启动车辆失败"
    assert manager.is_engine_running() == True, "发动机未启动"
    print(f"  ✅ 启动车辆成功")
    
    # 舒适模式
    result = await manager.set_comfort_mode(temperature=24)
    assert result['success'] == True, "舒适模式失败"
    assert manager.is_ac_on() == True, "空调未开启"
    assert manager.is_music_playing() == True, "音乐未播放"
    print(f"  ✅ 舒适模式开启")
    
    # 停车
    result = await manager.stop_vehicle()
    assert result['success'] == True, "停车失败"
    assert manager.is_engine_running() == False, "发动机未熄火"
    print(f"  ✅ 停车成功")
    
    print("\n✅ 便捷方法测试通过")


async def test_tool_management():
    """测试工具管理"""
    print_section("5. 工具管理测试")
    
    manager = get_execution_manager()
    
    # 测试工具数量
    print("\n【测试】工具统计")
    count = manager.get_tool_count()
    assert count == 170, "工具数量错误"
    print(f"  ✅ 工具总数: {count}")
    
    # 测试分类列表
    categories = manager.get_tool_categories()
    assert len(categories) == 15, "分类数量错误"
    print(f"  ✅ 分类总数: {len(categories)}")
    
    # 测试按分类获取
    print("\n【测试】按分类获取工具")
    tools_by_cat = manager.get_tools_by_category()
    assert 'climate' in tools_by_cat, "缺少climate分类"
    assert 'entertainment' in tools_by_cat, "缺少entertainment分类"
    assert len(tools_by_cat['climate']) == 18, "climate工具数量错误"
    assert len(tools_by_cat['entertainment']) == 20, "entertainment工具数量错误"
    
    print(f"  ✅ 空调工具: {len(tools_by_cat['climate'])}个")
    print(f"  ✅ 娱乐工具: {len(tools_by_cat['entertainment'])}个")
    
    # 测试获取工具对象
    print("\n【测试】获取工具对象")
    tool = manager.get_tool("start_engine")
    assert tool is not None, "获取工具失败"
    assert tool.name == "start_engine", "工具名称错误"
    print(f"  ✅ 工具名称: {tool.name}")
    print(f"  ✅ 工具描述: {tool.description}")
    
    # 测试按分类列出
    print("\n【测试】按分类列出工具")
    climate_tools = manager.list_tools(ToolCategory.CLIMATE)
    assert len(climate_tools) == 18, "按分类列出失败"
    print(f"  ✅ 空调分类工具: {len(climate_tools)}个")
    
    print("\n✅ 工具管理测试通过")


async def test_complex_scenarios():
    """测试复杂场景"""
    print_section("6. 复杂场景测试")
    
    manager = get_execution_manager()
    
    # 先重置状态：停车
    await manager.execute_tool("stop_engine")
    
    print("\n【场景】完整驾车流程")
    
    steps = [
        ("unlock_vehicle", {}, "解锁车辆"),
        ("start_engine", {}, "启动发动机"),
        ("turn_on_ac", {}, "开启空调"),
        ("set_temperature", {"zone": "all", "temperature": 24}, "设置温度24℃"),
        ("play_music", {}, "播放音乐"),
        ("set_volume", {"volume": 50}, "设置音量50"),
        ("navigate_to", {"destination": "公司"}, "导航到公司"),
        ("enable_lane_assist", {}, "开启车道保持"),
    ]
    
    success_count = 0
    for tool_name, params, description in steps:
        result = await manager.execute_tool(tool_name, **params)
        if result['success']:
            success_count += 1
            print(f"  ✅ {description}")
        else:
            print(f"  ❌ {description}: {result['message']}")
    
    assert success_count == len(steps), f"场景执行失败: {success_count}/{len(steps)}"
    
    # 验证最终状态
    print(f"\n【验证】最终状态")
    assert manager.is_engine_running() == True, "发动机应该运行"
    assert manager.is_ac_on() == True, "空调应该开启"
    assert manager.is_music_playing() == True, "音乐应该播放"
    assert manager.is_navigation_active() == True, "导航应该激活"
    print(f"  ✅ 发动机: 运行中")
    print(f"  ✅ 空调: 开启")
    print(f"  ✅ 音乐: 播放中")
    print(f"  ✅ 导航: 活跃")
    
    print(f"\n✅ 复杂场景测试通过: {success_count}/{len(steps)} 步骤成功")


async def test_concurrent_execution():
    """测试并发执行"""
    print_section("7. 并发执行测试")
    
    manager = get_execution_manager()
    
    print("\n【测试】并发执行多个工具")
    
    # 并发执行
    results = await asyncio.gather(
        manager.execute_tool("turn_on_ac"),
        manager.execute_tool("play_music"),
        manager.execute_tool("set_volume", volume=60),
        manager.execute_tool("open_window", window="driver", percentage=30),
        manager.execute_tool("enable_seat_heating", seat="driver", level=2),
    )
    
    # 验证结果
    for i, result in enumerate(results, 1):
        assert result['success'] == True, f"并发任务{i}失败"
        print(f"  ✅ 任务{i}: {result['message']}")
    
    # 验证状态
    assert manager.is_ac_on() == True, "空调状态错误"
    assert manager.is_music_playing() == True, "音乐状态错误"
    assert manager.get_volume() == 60, "音量错误"
    
    print("\n✅ 并发执行测试通过 (5个任务)")


async def test_statistics_and_info():
    """测试统计和信息"""
    print_section("8. 统计和信息测试")
    
    manager = get_execution_manager()
    
    # 测试统计信息
    print("\n【测试】统计信息")
    stats = manager.get_statistics()
    assert stats['total_tools'] == 170, "工具数量错误"
    assert stats['total_categories'] == 15, "分类数量错误"
    assert stats['vehicle_state_fields'] == 70, "状态字段数量错误"
    print(f"  ✅ 工具总数: {stats['total_tools']}")
    print(f"  ✅ 分类总数: {stats['total_categories']}")
    print(f"  ✅ 状态字段: {stats['vehicle_state_fields']}")
    
    # 测试模块信息
    print("\n【测试】模块信息")
    info = manager.get_info()
    assert info['name'] == "KIWI Execution Module", "模块名称错误"
    assert info['version'] == "1.0.0", "版本号错误"
    assert 'tools' in info['capabilities'], "缺少工具能力"
    assert 'state_management' in info['capabilities'], "缺少状态管理能力"
    print(f"  ✅ 模块名称: {info['name']}")
    print(f"  ✅ 版本: {info['version']}")
    print(f"  ✅ 能力: {', '.join(info['capabilities'].keys())}")
    
    print("\n✅ 统计和信息测试通过")


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "🚗" * 40)
    print("执行模块测试")
    print("🚗" * 40)
    
    tests = [
        ("基本接口", test_basic_interface),
        ("工具执行", test_tool_execution),
        ("状态管理", test_state_management),
        ("便捷方法", test_convenience_methods),
        ("工具管理", test_tool_management),
        ("复杂场景", test_complex_scenarios),
        ("并发执行", test_concurrent_execution),
        ("统计信息", test_statistics_and_info),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"\n❌ 测试失败: {name}")
            print(f"   错误: {e}")
        except Exception as e:
            failed += 1
            print(f"\n❌ 测试异常: {name}")
            print(f"   错误: {e}")
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"  ✅ 通过: {passed}/{len(tests)}")
    print(f"  ❌ 失败: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 所有测试通过！执行模块工作正常。")
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查。")
    
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
