# 执行模块 - 统一接口使用指南

## 概述

执行模块现在提供统一的 `ExecutionManager` 接口类，作为唯一对外入口，简化使用方式。

## 快速开始

### 基本使用

```python
from execution import get_execution_manager
import asyncio

async def main():
    # 获取管理器（单例）
    manager = get_execution_manager()
    
    # 执行工具
    result = await manager.execute_tool("start_engine")
    print(result['message'])  # "发动机启动成功"
    
    # 查询状态
    print(manager.is_engine_running())  # True

asyncio.run(main())
```

## 核心功能

### 1. 工具执行

```python
manager = get_execution_manager()

# 执行工具
await manager.execute_tool("turn_on_ac")
await manager.execute_tool("set_temperature", zone="driver", temperature=22)

# 获取工具对象
tool = manager.get_tool("start_engine")
```

### 2. 工具管理

```python
# 获取工具数量
count = manager.get_tool_count()  # 170

# 列出所有工具
all_tools = manager.list_tools()

# 按分类列出
from execution import ToolCategory
climate_tools = manager.list_tools(ToolCategory.CLIMATE)

# 按分类获取工具名
tools_by_cat = manager.get_tools_by_category()
# {'climate': ['turn_on_ac', ...], 'entertainment': [...]}
```

### 3. 状态管理

```python
# 获取状态值
speed = manager.get_state_value("speed")
ac_on = manager.get_state_value("ac_on")

# 设置状态值
manager.set_state_value("speed", 80.0)

# 批量更新
manager.update_state_values({
    "speed": 100.0,
    "cruise_control_enabled": True
})

# 获取所有状态
all_states = manager.get_all_states()  # 字典格式
```

### 4. 便捷状态查询

```python
# 车辆基本状态
manager.is_engine_running()     # bool
manager.get_speed()             # float (km/h)
manager.get_fuel_level()        # float (%)
manager.get_battery_level()     # float (%)

# 空调系统
manager.is_ac_on()              # bool
manager.get_temperature('driver')  # float (℃)

# 娱乐系统
manager.is_music_playing()      # bool
manager.get_volume()            # int (0-100)

# 导航系统
manager.is_navigation_active()  # bool
manager.get_navigation_destination()  # str
```

### 5. 便捷场景方法

```python
# 启动车辆（解锁+启动）
await manager.start_vehicle()

# 停车（熄火+锁车）
await manager.stop_vehicle()

# 舒适模式（空调+音乐）
await manager.set_comfort_mode(temperature=24)
```

### 6. 统计和信息

```python
# 获取统计信息
stats = manager.get_statistics()
# {
#     "total_tools": 170,
#     "total_categories": 15,
#     "tools_by_category": {...},
#     "vehicle_state_fields": 70,
#     "engine_running": True,
#     "current_speed": 0.0
# }

# 获取模块信息
info = manager.get_info()
# {
#     "name": "KIWI Execution Module",
#     "version": "1.0.0",
#     "description": "...",
#     "capabilities": {...}
# }
```

### 7. MCP协议支持

```python
from execution import MCPRequest

# 处理MCP请求
request = MCPRequest(method="tools/list", id="1")
response = await manager.handle_mcp_request(request)

# 获取MCP工具schema
mcp_tools = manager.get_mcp_tools_schema()
```

## 完整示例

### 示例1：启动并驾驶

```python
from execution import get_execution_manager
import asyncio

async def start_driving():
    manager = get_execution_manager()
    
    # 1. 启动车辆
    await manager.start_vehicle()
    print(f"发动机: {manager.is_engine_running()}")
    
    # 2. 设置舒适模式
    await manager.set_comfort_mode(temperature=23)
    print(f"空调: {manager.is_ac_on()}")
    print(f"音乐: {manager.is_music_playing()}")
    
    # 3. 开始导航
    await manager.execute_tool("navigate_to", destination="公司")
    print(f"导航: {manager.get_navigation_destination()}")
    
    # 4. 查看状态
    print(f"\n当前状态:")
    print(f"  车速: {manager.get_speed()} km/h")
    print(f"  温度: {manager.get_temperature('driver')}℃")
    print(f"  音量: {manager.get_volume()}")

asyncio.run(start_driving())
```

### 示例2：状态监控

```python
from execution import get_execution_manager

def monitor_vehicle():
    manager = get_execution_manager()
    
    print("车辆状态监控:")
    print(f"  发动机: {'✅' if manager.is_engine_running() else '❌'}")
    print(f"  空调: {'✅' if manager.is_ac_on() else '❌'}")
    print(f"  音乐: {'▶️' if manager.is_music_playing() else '⏸️'}")
    print(f"  导航: {'✅' if manager.is_navigation_active() else '❌'}")
    print(f"  车速: {manager.get_speed()} km/h")
    print(f"  油量: {manager.get_fuel_level()}%")
    
monitor_vehicle()
```

### 示例3：工具探索

```python
from execution import get_execution_manager

def explore_tools():
    manager = get_execution_manager()
    
    print(f"工具总数: {manager.get_tool_count()}")
    print(f"分类数: {len(manager.get_tool_categories())}")
    
    # 查看各分类工具数量
    tools_by_cat = manager.get_tools_by_category()
    for category, tools in sorted(tools_by_cat.items()):
        print(f"  {category}: {len(tools)}个工具")
    
    # 查看空调工具
    print("\n空调工具:")
    for tool_name in tools_by_cat['climate'][:5]:
        tool = manager.get_tool(tool_name)
        print(f"  - {tool.name}: {tool.description}")

explore_tools()
```

## API参考

### ExecutionManager 方法列表

#### 工具执行
- `execute_tool(tool_name, **kwargs)` - 执行工具
- `get_tool(tool_name)` - 获取工具对象
- `list_tools(category=None)` - 列出工具
- `get_tool_count()` - 获取工具总数
- `get_tool_categories()` - 获取分类列表
- `get_tools_by_category()` - 按分类获取工具

#### 状态管理
- `get_vehicle_state()` - 获取状态对象
- `get_state_value(key)` - 获取状态值
- `set_state_value(key, value)` - 设置状态值
- `update_state_values(updates)` - 批量更新
- `get_all_states()` - 获取所有状态

#### 便捷查询
- `is_engine_running()` - 发动机状态
- `get_speed()` - 车速
- `get_fuel_level()` - 油量
- `get_battery_level()` - 电量
- `get_temperature(zone)` - 温度
- `get_volume()` - 音量
- `is_ac_on()` - 空调状态
- `is_music_playing()` - 音乐状态
- `is_navigation_active()` - 导航状态
- `get_navigation_destination()` - 导航目的地

#### 便捷场景
- `start_vehicle()` - 启动车辆
- `stop_vehicle()` - 停车
- `set_comfort_mode(temperature)` - 舒适模式

#### MCP协议
- `handle_mcp_request(request)` - 处理MCP请求
- `get_mcp_tools_schema()` - 获取MCP schema

#### 统计信息
- `get_statistics()` - 获取统计信息
- `get_info()` - 获取模块信息

## 与旧接口对比

### 旧方式（分散）
```python
from execution import get_tool_registry, get_vehicle_state, call_tool

registry = get_tool_registry()
vehicle = get_vehicle_state()

tool = registry.get_tool("start_engine")
await tool.execute()
print(vehicle.is_engine_running())
```

### 新方式（统一）✅
```python
from execution import get_execution_manager

manager = get_execution_manager()

await manager.execute_tool("start_engine")
print(manager.is_engine_running())
```

## 优势

1. **统一入口** - 一个类管理所有功能
2. **简化使用** - 更少的导入和对象
3. **清晰接口** - 功能分类明确
4. **便捷方法** - 常用操作一行完成
5. **向后兼容** - 旧接口仍然可用

## 最佳实践

```python
# ✅ 推荐：使用统一管理器
from execution import get_execution_manager
manager = get_execution_manager()
await manager.execute_tool("start_engine")

# ⚠️ 不推荐：直接使用内部模块
from execution.tool_registry import get_tool_registry
registry = get_tool_registry()  # 内部实现细节
```

## 总结

使用 `ExecutionManager` 作为执行模块的唯一对外接口，提供：
- ✅ 170个工具的执行能力
- ✅ 完整的状态管理
- ✅ MCP协议支持
- ✅ 便捷的查询和场景方法
- ✅ 统计和信息获取

**一个类，搞定所有！** 🎉
