# KIWI 执行模块 - 快速开始指南

## 🎯 5分钟快速上手

### 1. 基本使用

```python
from src.execution import get_tool_registry, get_vehicle_state
import asyncio

async def main():
    # 获取工具注册中心和状态管理器
    registry = get_tool_registry()
    vehicle = get_vehicle_state()
    
    # 执行工具
    tool = registry.get_tool("start_engine")
    result = await tool.execute()
    print(result)  # {'success': True, 'message': '发动机启动成功'}
    
    # 查询状态
    print(f"发动机: {vehicle.is_engine_running()}")  # True

asyncio.run(main())
```

### 2. 查看所有工具

```python
from src.execution import get_tool_registry

registry = get_tool_registry()
print(f"总工具数: {len(registry.tools)}")

# 按分类查看
for tool in registry.tools.values():
    print(f"{tool.name} - {tool.description}")
```

### 3. 使用交互式控制台

```bash
python -m src.execution.console
```

控制台功能：
- 📋 列出所有170个工具
- 🔍 按15个分类查看
- ⚡ 交互式执行工具
- 📊 实时查看车辆状态
- 🚀 5个快捷场景

### 4. 运行测试

```bash
# 测试执行模块（8个测试组）
python tests/test_execution_module.py
```

### 5. 查看示例

```bash
# 7个详细使用场景
python examples/state_management_examples.py
```

## 📚 常用工具示例

### 车辆控制
```python
# 启动/熄火
await registry.get_tool("start_engine").execute()
await registry.get_tool("stop_engine").execute()

# 锁车/解锁
await registry.get_tool("lock_vehicle").execute()
await registry.get_tool("unlock_vehicle").execute()

# 驾驶模式
await registry.get_tool("set_driving_mode").execute(mode="sport")
```

### 空调系统
```python
# 开启空调
await registry.get_tool("turn_on_ac").execute()

# 设置温度（分区控制）
await registry.get_tool("set_temperature").execute(
    zone="driver", 
    temperature=22
)

# 调整风速
await registry.get_tool("set_fan_speed").execute(speed=5)
```

### 娱乐系统
```python
# 播放音乐
await registry.get_tool("play_music").execute()

# 调整音量
await registry.get_tool("set_volume").execute(volume=60)

# 静音
await registry.get_tool("mute_audio").execute()
```

### 导航系统
```python
# 导航到目的地
await registry.get_tool("navigate_to").execute(
    destination="北京市朝阳区"
)

# 快捷导航
await registry.get_tool("navigate_home").execute()
await registry.get_tool("navigate_to_work").execute()

# 开启语音导航
await registry.get_tool("enable_voice_guidance").execute()
```

### 车窗控制
```python
# 打开车窗（百分比控制）
await registry.get_tool("open_window").execute(
    window="driver", 
    percentage=50
)

# 关闭所有车窗
await registry.get_tool("close_window").execute(window="all")

# 打开天窗
await registry.get_tool("open_sunroof").execute(mode="slide")
```

## 🔍 状态查询

### 便捷方法
```python
from src.execution import get_vehicle_state

vehicle = get_vehicle_state()

# 基本状态
vehicle.is_engine_running()      # bool
vehicle.get_speed()              # float
vehicle.get_fuel_level()         # float
vehicle.get_battery_level()      # float

# 空调状态
vehicle.state.ac_on              # bool
vehicle.get_temperature('driver') # float

# 娱乐系统
vehicle.state.music_playing      # bool
vehicle.get_volume()             # int
```

### 完整状态
```python
# 获取所有状态（70个字段）
state_dict = vehicle.to_dict()

# 或使用查询工具
status_tool = registry.get_tool("get_vehicle_status")
result = await status_tool.execute()
print(result['state'])
```

## 🎬 快速场景

### 场景1: 启动车辆
```python
async def start_vehicle():
    await registry.get_tool("unlock_vehicle").execute()
    await registry.get_tool("start_engine").execute()
    print("✅ 车辆已启动")
```

### 场景2: 舒适驾驶
```python
async def comfort_mode():
    # 空调
    await registry.get_tool("turn_on_ac").execute()
    await registry.get_tool("set_temperature").execute(
        zone="all", temperature=24
    )
    
    # 音乐
    await registry.get_tool("play_music").execute()
    await registry.get_tool("set_volume").execute(volume=50)
    
    # 座椅
    await registry.get_tool("enable_seat_heating").execute(
        seat="driver", level=2
    )
    
    print("✅ 舒适模式已开启")
```

### 场景3: 完整驾车流程
```python
async def complete_driving():
    # 1. 解锁上车
    await registry.get_tool("unlock_vehicle").execute()
    
    # 2. 启动发动机
    await registry.get_tool("start_engine").execute()
    
    # 3. 调整环境
    await registry.get_tool("turn_on_ac").execute()
    await registry.get_tool("set_temperature").execute(
        zone="all", temperature=23
    )
    
    # 4. 娱乐系统
    await registry.get_tool("play_music").execute()
    
    # 5. 导航
    await registry.get_tool("navigate_to_work").execute()
    await registry.get_tool("enable_voice_guidance").execute()
    
    # 6. 驾驶辅助
    await registry.get_tool("enable_lane_assist").execute()
    await registry.get_tool("enable_blind_spot_monitor").execute()
    
    print("✅ 准备出发！")
```

## 📖 深入学习

### 文档
- [执行模块完整文档](../docs/EXECUTION_MODULE.md)
- [状态管理详解](../docs/STATE_MANAGEMENT.md)
- [最新更新说明](../docs/STATE_MANAGEMENT_UPDATE.md)

### 示例代码
- [执行场景示例](../examples/execution_scenarios.py)
- [状态管理示例](../examples/state_management_examples.py)

### 测试代码
- [执行模块测试](../tests/test_execution_module.py) - 8个测试组，覆盖所有功能

## 💡 提示

1. **并发执行**: 使用 `asyncio.gather()` 并发执行多个工具
   ```python
   await asyncio.gather(
       registry.get_tool("turn_on_ac").execute(),
       registry.get_tool("play_music").execute(),
       registry.get_tool("open_window").execute(window="driver", percentage=30)
   )
   ```

2. **状态监控**: 执行工具后立即查询状态验证
   ```python
   await tool.execute()
   assert vehicle.is_engine_running() == True
   ```

3. **错误处理**: 工具执行返回结果包含 success 字段
   ```python
   result = await tool.execute()
   if result['success']:
       print(f"✅ {result['message']}")
   else:
       print(f"❌ {result['message']}")
   ```

4. **参数校验**: 工具定义包含参数类型和枚举值
   ```python
   tool = registry.get_tool("set_driving_mode")
   # mode 必须是: comfort, sport, eco, snow, offroad 之一
   ```

## 🚀 下一步

- 探索170个工具的完整列表
- 尝试编写自己的场景脚本
- 查看状态管理系统的高级用法
- 了解MCP服务器的使用

## ❓ 常见问题

**Q: 如何查看所有可用工具？**
A: 使用 `python -m src.execution.console` 或查看文档

**Q: 工具执行会真实改变状态吗？**
A: 是的！每个工具执行都会修改 VehicleStateManager 中的对应状态

**Q: 状态是持久化的吗？**
A: 状态在程序运行期间持久化，重启会重置

**Q: 如何添加新工具？**
A: 在 tool_registry.py 中定义工具，在 tool_handlers.py 中实现handler

**Q: 支持并发调用吗？**
A: 支持！VehicleStateManager 是线程安全的

---

**开始探索吧！** 🎉
