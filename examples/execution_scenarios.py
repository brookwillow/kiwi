"""
执行模块使用示例
展示常见的车载控制场景
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.execution import call_tool


async def scenario_morning_drive():
    """场景：早晨开车去上班"""
    print("\n" + "="*60)
    print("🌅 场景：早晨开车去上班")
    print("="*60)
    
    steps = [
        ("解锁车辆", "unlock_vehicle", {}),
        ("启动发动机", "start_engine", {}),
        ("开启空调", "turn_on_ac", {}),
        ("设置温度24℃", "set_temperature", {"zone": "all", "temperature": 24}),
        ("载入座椅记忆", "load_seat_memory", {"profile": 1}),
        ("播放音乐", "play_music", {}),
        ("设置音量", "set_volume", {"volume": 50}),
        ("导航到公司", "navigate_to_work", {}),
        ("开启语音导航", "enable_voice_guidance", {}),
        ("设置节能模式", "set_driving_mode", {"mode": "eco"}),
    ]
    
    for i, (desc, tool, params) in enumerate(steps, 1):
        try:
            result = await call_tool(tool, **params)
            print(f"{i:2d}. ✅ {desc}")
        except Exception as e:
            print(f"{i:2d}. ❌ {desc} - 失败: {e}")


async def scenario_hot_summer():
    """场景：夏天高温快速降温"""
    print("\n" + "="*60)
    print("🔥 场景：夏天高温快速降温")
    print("="*60)
    
    steps = [
        ("开启最大制冷", "enable_ac_max", {}),
        ("打开所有车窗通风", "open_window", {"window": "all", "percentage": 100}),
        ("开启座椅通风", "enable_seat_ventilation", {"seat": "driver", "level": 3}),
        ("开启外循环", "disable_recirculation", {}),
        ("设置风速最大", "set_fan_speed", {"speed": 7}),
    ]
    
    for i, (desc, tool, params) in enumerate(steps, 1):
        try:
            result = await call_tool(tool, **params)
            print(f"{i}. ✅ {desc}")
        except Exception as e:
            print(f"{i}. ❌ {desc} - 失败: {e}")
    
    print("\n⏳ 等待5秒...")
    await asyncio.sleep(1)  # 模拟等待
    
    print("\n关闭车窗:")
    try:
        await call_tool("close_window", window="all")
        print("✅ 所有车窗已关闭")
    except Exception as e:
        print(f"❌ 关闭车窗失败: {e}")


async def scenario_night_drive():
    """场景：夜间驾驶"""
    print("\n" + "="*60)
    print("🌙 场景：夜间驾驶")
    print("="*60)
    
    steps = [
        ("打开大灯", "turn_on_headlights", {}),
        ("开启自动大灯", "set_headlight_mode", {"mode": "auto"}),
        ("设置氛围灯", "set_ambient_light_color", {"color": "blue"}),
        ("调低内饰亮度", "set_interior_brightness", {"brightness": 30}),
        ("播放轻音乐", "play_music", {}),
        ("降低音量", "set_volume", {"volume": 30}),
    ]
    
    for i, (desc, tool, params) in enumerate(steps, 1):
        try:
            result = await call_tool(tool, **params)
            print(f"{i}. ✅ {desc}")
        except Exception as e:
            print(f"{i}. ❌ {desc} - 失败: {e}")


async def scenario_long_highway():
    """场景：高速长途驾驶"""
    print("\n" + "="*60)
    print("🛣️  场景：高速长途驾驶")
    print("="*60)
    
    steps = [
        ("设置运动模式", "set_driving_mode", {"mode": "sport"}),
        ("开启定速巡航", "enable_cruise_control", {"speed": 110}),
        ("开启车道保持", "enable_lane_assist", {}),
        ("开启盲区监测", "enable_blind_spot_monitor", {}),
        ("开启碰撞预警", "enable_collision_warning", {}),
        ("调节座椅靠背", "adjust_seat_backrest", {"seat": "driver", "angle": 110}),
        ("开启座椅按摩", "enable_seat_massage", {"seat": "driver", "mode": "relax"}),
        ("设置腰部支撑", "adjust_lumbar_support", {"seat": "driver", "level": 3}),
    ]
    
    for i, (desc, tool, params) in enumerate(steps, 1):
        try:
            result = await call_tool(tool, **params)
            print(f"{i}. ✅ {desc}")
        except Exception as e:
            print(f"{i}. ❌ {desc} - 失败: {e}")


async def scenario_rainy_day():
    """场景：雨天驾驶"""
    print("\n" + "="*60)
    print("🌧️  场景：雨天驾驶")
    print("="*60)
    
    steps = [
        ("开启自动雨刷", "enable_auto_wipers", {}),
        ("打开雾灯", "turn_on_fog_lights", {"position": "front"}),
        ("开启除雾", "enable_defrost", {"position": "front"}),
        ("关闭天窗", "close_sunroof", {}),
        ("开启雨量感应", "enable_rain_sensing", {}),
        ("降低车速", "set_speed_limit", {"speed": 80}),
    ]
    
    for i, (desc, tool, params) in enumerate(steps, 1):
        try:
            result = await call_tool(tool, **params)
            print(f"{i}. ✅ {desc}")
        except Exception as e:
            print(f"{i}. ❌ {desc} - 失败: {e}")


async def scenario_parking():
    """场景：停车"""
    print("\n" + "="*60)
    print("🅿️  场景：停车")
    print("="*60)
    
    steps = [
        ("开启自动泊车", "enable_auto_parking", {}),
        ("关闭音乐", "pause_music", {}),
        ("关闭空调", "turn_off_ac", {}),
        ("拉起手刹", "enable_parking_brake", {}),
        ("熄火", "stop_engine", {}),
        ("锁车", "lock_vehicle", {}),
    ]
    
    for i, (desc, tool, params) in enumerate(steps, 1):
        try:
            result = await call_tool(tool, **params)
            print(f"{i}. ✅ {desc}")
        except Exception as e:
            print(f"{i}. ❌ {desc} - 失败: {e}")


async def scenario_romantic_night():
    """场景：浪漫约会"""
    print("\n" + "="*60)
    print("💕 场景：浪漫约会")
    print("="*60)
    
    steps = [
        ("设置氛围主题", "set_ambient_theme", {"theme": "romantic"}),
        ("开启香氛", "enable_fragrance", {"intensity": 3}),
        ("设置氛围灯", "set_ambient_light_color", {"color": "purple"}),
        ("调低亮度", "set_ambient_light_brightness", {"brightness": 40}),
        ("播放音乐", "play_music", {}),
        ("开启环绕音效", "enable_surround_sound", {}),
        ("调节座椅", "set_seat_position_preset", {"preset": "relax"}),
        ("打开天窗", "open_sunroof", {"mode": "tilt"}),
    ]
    
    for i, (desc, tool, params) in enumerate(steps, 1):
        try:
            result = await call_tool(tool, **params)
            print(f"{i}. ✅ {desc}")
        except Exception as e:
            print(f"{i}. ❌ {desc} - 失败: {e}")


async def main():
    """运行所有场景"""
    print("\n" + "="*60)
    print("🚗 KIWI 车载执行模块 - 使用示例")
    print("="*60)
    
    scenarios = [
        scenario_morning_drive,
        scenario_hot_summer,
        scenario_night_drive,
        scenario_long_highway,
        scenario_rainy_day,
        scenario_parking,
        scenario_romantic_night,
    ]
    
    for scenario in scenarios:
        try:
            await scenario()
            await asyncio.sleep(0.5)  # 场景间短暂停顿
        except Exception as e:
            print(f"\n❌ 场景执行失败: {e}")
    
    print("\n" + "="*60)
    print("✅ 所有场景执行完成！")
    print("="*60)
    print()


if __name__ == "__main__":
    asyncio.run(main())
