# 状态管理系统

## 概述

执行模块现在支持真实的状态管理。每个工具执行后，会实际修改车辆的状态值，并且这些状态可以被查询。

## 核心组件

### 1. VehicleState (数据类)
定义所有车辆状态字段（70+字段），包括：
- 基本状态：发动机、车速、油量、电量等
- 空调系统：温度（分区）、风速、模式等
- 娱乐系统：音乐播放、音量、音源等
- 导航系统：目的地、导航状态等
- 车窗/车门：开关度、锁定状态等
- 座椅：加热、通风、按摩等级等
- 灯光：大灯、氛围灯、雾灯等
- 安全/ADAS：车道保持、盲区监测、自动驾驶等

### 2. VehicleStateManager (状态管理器)
- **单例模式**：全局唯一实例
- **线程安全**：使用锁保护并发访问
- **状态操作**：get_value(), set_value(), update_values()
- **便捷查询**：is_engine_running(), get_temperature(), get_volume()等
- **序列化**：to_dict(), to_json()

### 3. ToolHandlers (工具处理器)
为每个工具实现真实的handler函数，修改对应的状态值。

## 使用示例

### 基本使用

```python
from src.execution import get_tool_registry, get_vehicle_state

# 获取工具和状态管理器
registry = get_tool_registry()
vehicle = get_vehicle_state()

# 执行前查询
print(f"发动机: {vehicle.is_engine_running()}")  # False

# 执行工具
tool = registry.get_tool("start_engine")
result = await tool.execute()

# 执行后查询
print(f"发动机: {vehicle.is_engine_running()}")  # True
```

### 状态查询

```python
vehicle = get_vehicle_state()

# 基本查询
vehicle.is_engine_running()      # 发动机状态
vehicle.get_speed()              # 车速
vehicle.get_fuel_level()         # 油量
vehicle.get_battery_level()      # 电量

# 空调查询
vehicle.state.ac_on              # 空调开关
vehicle.get_temperature('driver') # 驾驶侧温度

# 娱乐系统查询
vehicle.state.music_playing      # 音乐播放
vehicle.get_volume()             # 音量

# 完整状态
state_dict = vehicle.to_dict()   # 所有状态字典
```

### 状态修改

```python
vehicle = get_vehicle_state()

# 单个值修改
vehicle.set_value("ac_on", True)

# 批量修改
vehicle.update_values({
    "ac_on": True,
    "fan_speed": 5,
    "recirculation": True
})
```

## 工作流程

```
┌─────────────┐      ┌──────────────┐      ┌─────────────────────┐
│   用户请求   │ ───> │ Tool.execute │ ───> │  Handler函数         │
└─────────────┘      └──────────────┘      └─────────────────────┘
                                                       │
                                                       ▼
┌─────────────┐      ┌──────────────┐      ┌─────────────────────┐
│  状态更新   │ <─── │  set_value   │ <─── │ VehicleStateManager │
└─────────────┘      └──────────────┘      └─────────────────────┘
```

## 特性

1. **真实状态反馈**：工具执行会立即反映到状态中
2. **线程安全**：支持并发工具调用
3. **状态持久化**：状态在程序生命周期内保持
4. **查询接口**：提供丰富的查询方法
5. **类型安全**：使用dataclass确保类型正确

## 测试

运行状态管理测试：

```bash
# 完整测试
python tests/test_state_management.py

# 查看使用示例
python examples/state_management_examples.py
```

测试包含：
- 基本工具执行与状态变化
- 并发操作测试
- 状态查询测试
- 复杂场景模拟（完整驾车流程）

## 实现的工具Handler

目前已实现的handler（部分列表）：

### 车辆控制
- start_engine, stop_engine
- lock_vehicle, unlock_vehicle
- set_driving_mode
- enable/disable_cruise_control

### 空调系统
- turn_on/off_ac
- set_temperature (支持分区)
- set_fan_speed
- enable_seat_heating

### 娱乐系统
- play_music, pause_music
- set_volume
- mute/unmute_audio
- enable_bluetooth

### 导航系统
- navigate_to, navigate_home
- cancel_navigation
- enable_voice_guidance

### 车窗控制
- open/close_window (支持分窗和百分比)
- open/close_sunroof

### 座椅控制
- load_seat_memory
- enable_seat_massage
- enable_seat_ventilation

### 灯光控制
- turn_on/off_headlights
- set_headlight_mode
- set_ambient_light_color

### 安全系统
- enable_lane_assist
- enable_blind_spot_monitor
- enable_collision_warning
- enable_autopilot

### 信息查询
- get_fuel_level
- get_battery_level
- get_speed
- get_vehicle_status

## 未来扩展

- [ ] 状态变化监听器（Observer模式）
- [ ] 状态历史记录
- [ ] 状态保存/恢复（持久化到文件）
- [ ] 状态校验（值范围检查）
- [ ] 状态变化通知
- [ ] 与感知模块集成
