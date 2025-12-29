"""
状态管理使用示例
展示如何使用车辆状态管理系统
"""
import asyncio
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from execution import get_tool_registry, get_vehicle_state


async def example_1_basic_control():
    """示例1: 基本车辆控制"""
    print("=" * 60)
    print("示例1: 基本车辆控制")
    print("=" * 60)
    
    registry = get_tool_registry()
    vehicle = get_vehicle_state()
    
    # 解锁车辆
    print("\n1. 解锁车辆")
    unlock = registry.get_tool("unlock_vehicle")
    result = await unlock.execute()
    print(f"   {result['message']}")
    print(f"   车门状态: {'已锁定' if vehicle.state.doors_locked else '已解锁'}")
    
    # 启动发动机
    print("\n2. 启动发动机")
    start = registry.get_tool("start_engine")
    result = await start.execute()
    print(f"   {result['message']}")
    print(f"   发动机状态: {'运行中' if vehicle.is_engine_running() else '熄火'}")
    
    # 设置驾驶模式
    print("\n3. 切换到运动模式")
    mode = registry.get_tool("set_driving_mode")
    result = await mode.execute(mode="sport")
    print(f"   {result['message']}")
    print(f"   当前驾驶模式: {vehicle.state.driving_mode}")


async def example_2_climate_control():
    """示例2: 空调控制"""
    print("\n" + "=" * 60)
    print("示例2: 智能空调控制")
    print("=" * 60)
    
    registry = get_tool_registry()
    vehicle = get_vehicle_state()
    
    # 打开空调
    print("\n1. 打开空调系统")
    ac = registry.get_tool("turn_on_ac")
    await ac.execute()
    print(f"   空调状态: {'开启' if vehicle.state.ac_on else '关闭'}")
    
    # 设置分区温度
    print("\n2. 设置分区温度")
    temp = registry.get_tool("set_temperature")
    await temp.execute(zone="driver", temperature=22)
    await temp.execute(zone="passenger", temperature=24)
    print(f"   驾驶侧温度: {vehicle.get_temperature('driver')}℃")
    print(f"   乘客侧温度: {vehicle.get_temperature('passenger')}℃")
    
    # 调整风速
    print("\n3. 调整风速")
    fan = registry.get_tool("set_fan_speed")
    await fan.execute(speed=5)
    print(f"   风速: {vehicle.state.fan_speed}级")
    
    # 开启座椅加热
    print("\n4. 开启座椅加热")
    heating = registry.get_tool("enable_seat_heating")
    await heating.execute(seat="driver", level=3)
    print(f"   驾驶座加热: {vehicle.state.seat_heating['driver']}级")


async def example_3_entertainment():
    """示例3: 娱乐系统"""
    print("\n" + "=" * 60)
    print("示例3: 娱乐系统控制")
    print("=" * 60)
    
    registry = get_tool_registry()
    vehicle = get_vehicle_state()
    
    # 播放音乐
    print("\n1. 播放音乐")
    play = registry.get_tool("play_music")
    await play.execute()
    print(f"   音乐状态: {'播放中' if vehicle.state.music_playing else '暂停'}")
    
    # 调整音量
    print("\n2. 调整音量")
    volume = registry.get_tool("set_volume")
    await volume.execute(volume=60)
    print(f"   当前音量: {vehicle.get_volume()}")
    
    # 开启蓝牙
    print("\n3. 开启蓝牙")
    bluetooth = registry.get_tool("enable_bluetooth")
    await bluetooth.execute()
    print(f"   蓝牙状态: {'已开启' if vehicle.state.bluetooth_enabled else '已关闭'}")


async def example_4_navigation():
    """示例4: 导航系统"""
    print("\n" + "=" * 60)
    print("示例4: 智能导航")
    print("=" * 60)
    
    registry = get_tool_registry()
    vehicle = get_vehicle_state()
    
    # 导航到目的地
    print("\n1. 导航到目的地")
    nav = registry.get_tool("navigate_to")
    result = await nav.execute(destination="北京市海淀区中关村")
    print(f"   {result['message']}")
    print(f"   目的地: {vehicle.state.navigation_destination}")
    print(f"   导航状态: {'活跃' if vehicle.state.navigation_active else '未激活'}")
    
    # 开启语音导航
    print("\n2. 开启语音导航")
    voice = registry.get_tool("enable_voice_guidance")
    await voice.execute()
    print(f"   语音导航: {'已开启' if vehicle.state.voice_guidance else '已关闭'}")


async def example_5_window_control():
    """示例5: 车窗控制"""
    print("\n" + "=" * 60)
    print("示例5: 车窗和天窗控制")
    print("=" * 60)
    
    registry = get_tool_registry()
    vehicle = get_vehicle_state()
    
    # 打开驾驶侧车窗
    print("\n1. 打开驾驶侧车窗")
    window = registry.get_tool("open_window")
    await window.execute(window="driver", percentage=50)
    print(f"   驾驶侧车窗: {vehicle.state.windows['driver']}%")
    
    # 打开天窗
    print("\n2. 打开天窗（滑动模式）")
    sunroof = registry.get_tool("open_sunroof")
    await sunroof.execute(mode="slide")
    print(f"   天窗位置: {vehicle.state.sunroof_position}%")
    print(f"   天窗模式: {'倾斜' if vehicle.state.sunroof_tilted else '滑动'}")


async def example_6_query_status():
    """示例6: 查询车辆状态"""
    print("\n" + "=" * 60)
    print("示例6: 查询车辆状态")
    print("=" * 60)
    
    registry = get_tool_registry()
    vehicle = get_vehicle_state()
    
    # 设置一些状态用于查询
    vehicle.set_value("fuel_level", 75.5)
    vehicle.set_value("battery_level", 92.0)
    vehicle.set_value("speed", 65.0)
    
    # 查询油量
    print("\n1. 查询油量")
    fuel = registry.get_tool("get_fuel_level")
    result = await fuel.execute()
    print(f"   {result['message']}")
    
    # 查询电量
    print("\n2. 查询电量")
    battery = registry.get_tool("get_battery_level")
    result = await battery.execute()
    print(f"   {result['message']}")
    
    # 查询车速
    print("\n3. 查询车速")
    speed = registry.get_tool("get_speed")
    result = await speed.execute()
    print(f"   {result['message']}")
    
    # 查询完整状态
    print("\n4. 查询完整车辆状态")
    status = registry.get_tool("get_vehicle_status")
    result = await status.execute()
    print(f"   {result['message']}")
    print(f"   状态包含: {len(result['state'])} 个字段")


async def example_7_complex_scenario():
    """示例7: 复杂场景 - 完整的驾车流程"""
    print("\n" + "=" * 60)
    print("示例7: 完整驾车场景")
    print("=" * 60)
    
    registry = get_tool_registry()
    vehicle = get_vehicle_state()
    
    print("\n场景: 早上上班 - 从家到公司")
    print("-" * 60)
    
    # 1. 解锁并上车
    print("\n步骤1: 解锁车辆")
    await registry.get_tool("unlock_vehicle").execute()
    print("   ✓ 车门已解锁")
    
    # 2. 启动发动机
    print("\n步骤2: 启动发动机")
    await registry.get_tool("start_engine").execute()
    print("   ✓ 发动机启动成功")
    
    # 3. 调整座椅（加载记忆位置）
    print("\n步骤3: 调整座椅")
    await registry.get_tool("load_seat_memory").execute(profile=1)
    print("   ✓ 已载入座椅记忆位置1")
    
    # 4. 设置舒适的空调
    print("\n步骤4: 调整空调")
    await registry.get_tool("turn_on_ac").execute()
    await registry.get_tool("set_temperature").execute(zone="all", temperature=23)
    await registry.get_tool("enable_auto_climate").execute()
    print("   ✓ 空调已开启，温度23℃，自动模式")
    
    # 5. 播放音乐
    print("\n步骤5: 播放音乐")
    await registry.get_tool("play_music").execute()
    await registry.get_tool("set_volume").execute(volume=40)
    print("   ✓ 音乐播放中，音量40")
    
    # 6. 开始导航
    print("\n步骤6: 启动导航")
    await registry.get_tool("navigate_to_work").execute()
    await registry.get_tool("enable_voice_guidance").execute()
    print("   ✓ 导航至公司，语音播报已开启")
    
    # 7. 开启驾驶辅助
    print("\n步骤7: 开启驾驶辅助")
    await registry.get_tool("enable_lane_assist").execute()
    await registry.get_tool("enable_blind_spot_monitor").execute()
    await registry.get_tool("enable_collision_warning").execute()
    print("   ✓ 车道保持、盲区监测、碰撞预警已开启")
    
    # 8. 开启定速巡航
    print("\n步骤8: 开启定速巡航（高速路段）")
    await registry.get_tool("enable_cruise_control").execute(speed=100)
    print("   ✓ 定速巡航已开启，速度100 km/h")
    
    # 9. 到达公司
    print("\n步骤9: 到达公司 - 停车")
    await registry.get_tool("disable_cruise_control").execute()
    await registry.get_tool("stop_engine").execute()
    await registry.get_tool("lock_vehicle").execute()
    print("   ✓ 车辆已熄火并锁定")
    
    # 查看最终状态
    print("\n最终状态总结:")
    print(f"   发动机: {'运行中' if vehicle.is_engine_running() else '熄火'}")
    print(f"   车门: {'已锁定' if vehicle.state.doors_locked else '已解锁'}")
    print(f"   定速巡航: {'开启' if vehicle.state.cruise_control_enabled else '关闭'}")
    print(f"   导航目的地: {vehicle.state.navigation_destination if vehicle.state.navigation_active else '无'}")


async def main():
    """运行所有示例"""
    print("\n" + "🚗" * 30)
    print("车辆状态管理系统 - 使用示例")
    print("🚗" * 30)
    
    await example_1_basic_control()
    await example_2_climate_control()
    await example_3_entertainment()
    await example_4_navigation()
    await example_5_window_control()
    await example_6_query_status()
    await example_7_complex_scenario()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例运行完成!")
    print("=" * 60)
    
    # 展示工具注册统计
    registry = get_tool_registry()
    print(f"\n📊 工具统计:")
    print(f"   总工具数: {len(registry.tools)}")
    
    categories = {}
    for tool in registry.tools.values():
        cat = tool.category.value
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"   分类数: {len(categories)}")
    for cat, count in sorted(categories.items()):
        print(f"   - {cat}: {count}个工具")


if __name__ == "__main__":
    asyncio.run(main())
