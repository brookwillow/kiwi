# KIWI 执行模块

车载智能系统的执行能力模块，提供170个车载控制工具，并通过MCP（Model Context Protocol）标准对外暴露。

## 📋 概述

执行模块模拟了完整的车载控制能力，涵盖车辆的各个方面：
- ✅ **170个工具** 覆盖15个功能分类
- ✅ **真实状态管理** 工具执行会实际修改车辆状态
- ✅ **状态查询** 支持查询所有车辆状态值
- ✅ **MCP标准接口** 符合Model Context Protocol规范
- ✅ **完整参数定义** 每个工具都有详细的参数说明
- ✅ **类型安全** 使用dataclass和类型注解
- ✅ **异步执行** 支持async/await模式
- ✅ **线程安全** 状态管理支持并发访问

## 🎯 核心特性

### 状态管理系统
执行模块包含完整的车辆状态管理系统：
- **VehicleState**: 定义所有车辆状态字段（70+字段）
- **VehicleStateManager**: 单例模式的状态管理器
- **线程安全**: 使用锁保护并发访问
- **实时更新**: 工具执行立即反映到状态中
- **状态查询**: 提供便捷的查询接口

### 工具执行流程
```
用户请求 → Tool.execute() → Handler函数 → VehicleStateManager.set_value() → 状态更新
```

### 状态查询
```python
from execution import get_vehicle_state

vehicle = get_vehicle_state()
print(vehicle.is_engine_running())  # 查询发动机状态
print(vehicle.get_temperature('driver'))  # 查询驾驶侧温度
print(vehicle.get_volume())  # 查询音量
```

## 🔧 工具分类

### 1. 车辆控制 (Vehicle Control) - 15个工具
- 启动/熄火、锁车/解锁
- 鸣笛、闪灯
- 驾驶模式切换（舒适/运动/节能/雪地/越野）
- 手刹控制、限速设置
- 定速巡航、悬挂高度调节

### 2. 空调系统 (Climate) - 18个工具
- 空调开关、温度控制（分区控制）
- 风速调节、出风方向设置
- 自动空调、内外循环
- 最大制冷、除雾功能
- 座椅加热

### 3. 娱乐系统 (Entertainment) - 20个工具
- 音乐播放控制（播放/暂停/上一曲/下一曲）
- 音量调节、静音
- 收音机、音源切换
- 歌曲搜索、歌单播放
- 蓝牙连接、均衡器设置
- 环绕音效、播客播放

### 4. 导航系统 (Navigation) - 15个工具
- 目的地导航（支持避开高速/收费站）
- 回家/去公司快捷导航
- 搜索附近（加油站/停车场/餐厅/酒店等）
- 取消导航、显示路况
- 语音导航开关
- 地图视图设置、放大缩小
- 添加途经点、保存位置

### 5. 车窗/天窗 (Window) - 12个工具
- 车窗开关（分窗控制、百分比控制）
- 天窗开关（倾斜/滑动/全开）
- 车窗通风
- 雨量感应、自动升窗
- 防夹保护、车窗校准

### 6. 座椅调节 (Seat) - 15个工具
- 座椅位置调节（前后/上下）
- 靠背角度调节
- 腰部支撑调节
- 座椅记忆（保存/载入）
- 座椅按摩（多种模式）
- 座椅通风
- 后排座椅放倒/恢复
- 头枕高度调节
- 上下车便利功能

### 7. 灯光控制 (Lighting) - 12个工具
- 大灯开关、模式设置
- 远光灯控制
- 雾灯开关（前/后）
- 车内灯控制
- 内饰亮度调节
- 日间行车灯

### 8. 安全系统 (Safety) - 10个工具
- 车道保持辅助
- 盲区监测
- 碰撞预警
- 自动紧急制动
- 后方交叉警示

### 9. 通信系统 (Communication) - 8个工具
- 拨打/接听/挂断电话
- 发送/读取消息
- 勿扰模式
- 通话音频切换

### 10. 信息查询 (Information) - 10个工具
- 油量/电量查询
- 续航里程查询
- 胎压查询
- 车速查询
- 外部温度查询
- 里程数查询
- 保养信息、行程统计
- 车辆状态

### 11. 充电/加油 (Energy) - 5个工具
- 开始/停止充电
- 预约充电
- 充电限制设置
- 查找充电站

### 12. 驾驶辅助 (ADAS) - 8个工具
- 自动驾驶开关
- 自动泊车
- 交通标识识别
- 跟车距离设置
- 召唤功能

### 13. 车门/后备箱 (Door) - 8个工具
- 车门开关（分门控制）
- 后备箱开关
- 引擎盖开启
- 无钥匙进入
- 后备箱高度设置

### 14. 雨刷/洗涤 (Wiper) - 6个工具
- 雨刷开关、速度调节
- 玻璃水喷洒
- 自动雨刷

### 15. 香氛/氛围灯 (Ambient) - 8个工具
- 香氛开关、强度调节
- 氛围灯颜色设置
- 氛围灯亮度调节
- 氛围主题设置
- 氛围灯音乐同步

## 🚀 快速开始

### 安装依赖

```bash
# 执行模块没有额外依赖，只需要Python 3.7+
python --version  # 确保Python版本 >= 3.7
```

### 基本使用

```python
import asyncio
from src.execution import get_tool_registry, get_vehicle_state

async def main():
    # 1. 获取工具注册中心和状态管理器
    registry = get_tool_registry()
    vehicle = get_vehicle_state()
    
    print(f"总工具数: {len(registry.tools)}")
    print(f"发动机状态: {vehicle.is_engine_running()}")
    
    # 2. 执行工具 - 启动发动机
    tool = registry.get_tool("start_engine")
    result = await tool.execute()
    print(result)  # {'success': True, 'message': '发动机启动成功'}
    
    # 3. 查询状态变化
    print(f"发动机状态: {vehicle.is_engine_running()}")  # True
    
    # 4. 带参数调用 - 设置温度
    temp_tool = registry.get_tool("set_temperature")
    result = await temp_tool.execute(zone="driver", temperature=22)
    print(result)
    print(f"驾驶侧温度: {vehicle.get_temperature('driver')}℃")  # 22.0

asyncio.run(main())
```

### 状态查询

```python
from src.execution import get_vehicle_state

# 获取车辆状态管理器
vehicle = get_vehicle_state()

# 查询基本状态
print(vehicle.is_engine_running())  # 发动机状态
print(vehicle.get_speed())  # 当前车速
print(vehicle.get_fuel_level())  # 油量百分比

# 查询空调状态
print(vehicle.state.ac_on)  # 空调开关
print(vehicle.get_temperature('driver'))  # 驾驶侧温度

# 查询娱乐系统
print(vehicle.state.music_playing)  # 音乐播放状态
print(vehicle.get_volume())  # 音量

# 获取完整状态（字典格式）
state_dict = vehicle.to_dict()
print(f"包含 {len(state_dict)} 个状态字段")
```

### MCP服务器使用

```python
import asyncio
from src.execution import get_mcp_server, MCPRequest

async def main():
    server = get_mcp_server()
    
    # 初始化请求
    request = MCPRequest(method="initialize", id="1")
    response = await server.handle_request(request)
    print(response.result)
    
    # 列出所有工具
    request = MCPRequest(method="tools/list", id="2")
    response = await server.handle_request(request)
    print(f"工具数: {len(response.result['tools'])}")
    
    # 调用工具
    request = MCPRequest(
        method="tools/call",
        params={
            "name": "navigate_to",
            "arguments": {
                "destination": "北京天安门",
                "avoid_highway": False,
                "avoid_toll": True
            }
        },
        id="3"
    )
    response = await server.handle_request(request)
    print(response.result)

asyncio.run(main())
```

## 🧪 运行测试

```bash
# 运行完整测试套件
python test_execution.py
```

测试包括：
1. ✅ 工具注册中心测试
2. ✅ MCP服务器测试
3. ✅ 工具执行测试（5个场景）
4. ✅ 工具分类详情
5. ✅ 复杂场景测试（12步骤）

## 📊 工具统计

```
总工具数: 170

分类统计:
- vehicle_control     :  15 个工具
- climate             :  18 个工具
- entertainment       :  20 个工具
- navigation          :  15 个工具
- window              :  12 个工具
- seat                :  15 个工具
- lighting            :  12 个工具
- safety              :  10 个工具
- communication       :   8 个工具
- information         :  10 个工具
- energy              :   5 个工具
- adas                :   8 个工具
- door                :   8 个工具
- wiper               :   6 个工具
- ambient             :   8 个工具
```

## 🔌 MCP协议支持

### 支持的方法

1. **initialize** - 初始化服务器
   ```json
   {
     "method": "initialize",
     "id": "1"
   }
   ```

2. **tools/list** - 列出所有工具
   ```json
   {
     "method": "tools/list",
     "id": "2"
   }
   ```

3. **tools/call** - 调用工具
   ```json
   {
     "method": "tools/call",
     "params": {
       "name": "set_temperature",
       "arguments": {
         "zone": "driver",
         "temperature": 22
       }
     },
     "id": "3"
   }
   ```

### 响应格式

成功响应：
```json
{
  "result": {
    "success": true,
    "message": "工具执行成功",
    "parameters": {...}
  },
  "id": "3"
}
```

错误响应：
```json
{
  "error": {
    "code": -32602,
    "message": "Invalid params"
  },
  "id": "3"
}
```

## 💡 使用示例

### 场景1：开车前准备

```python
import asyncio
from src.execution import call_tool

async def prepare_to_drive():
    # 解锁车辆
    await call_tool("unlock_vehicle")
    
    # 启动发动机
    await call_tool("start_engine")
    
    # 开启空调并设置温度
    await call_tool("turn_on_ac")
    await call_tool("set_temperature", zone="driver", temperature=24)
    
    # 调节座椅
    await call_tool("load_seat_memory", profile=1)
    
    # 播放音乐
    await call_tool("play_music")
    await call_tool("set_volume", volume=50)
    
    # 导航到目的地
    await call_tool("navigate_to", destination="公司")

asyncio.run(prepare_to_drive())
```

### 场景2：夏天降温

```python
async def cool_down_car():
    # 开启最大制冷
    await call_tool("enable_ac_max")
    
    # 打开所有车窗通风
    await call_tool("vent_windows")
    
    # 开启座椅通风
    await call_tool("enable_seat_ventilation", seat="driver", level=3)
    await call_tool("enable_seat_ventilation", seat="passenger", level=3)
    
    # 5秒后关闭车窗
    await asyncio.sleep(5)
    await call_tool("close_window", window="all")

asyncio.run(cool_down_car())
```

### 场景3：长途驾驶

```python
async def long_drive_setup():
    # 设置驾驶模式为节能
    await call_tool("set_driving_mode", mode="eco")
    
    # 开启定速巡航
    await call_tool("enable_cruise_control", speed=100)
    
    # 开启驾驶辅助
    await call_tool("enable_lane_assist")
    await call_tool("enable_blind_spot_monitor")
    
    # 开启座椅按摩
    await call_tool("enable_seat_massage", seat="driver", mode="relax")
    
    # 播放播客
    await call_tool("play_podcast", title="技术播客")

asyncio.run(long_drive_setup())
```

## 🏗️ 架构设计

```
src/execution/
├── __init__.py           # 模块入口
├── tool_registry.py      # 工具注册中心
└── mcp_server.py         # MCP服务器实现

核心类:
- ToolParameter         # 工具参数定义
- Tool                  # 工具定义
- ToolRegistry          # 工具注册中心
- MCPServer            # MCP服务器
- MCPRequest/Response  # MCP消息格式
```

## 🔄 扩展工具

添加新工具非常简单：

```python
from src.execution import Tool, ToolParameter, ToolCategory

# 1. 定义工具
new_tool = Tool(
    name="my_custom_tool",
    description="我的自定义工具",
    category=ToolCategory.VEHICLE_CONTROL,
    parameters=[
        ToolParameter("param1", "string", "参数1说明", True),
        ToolParameter("param2", "number", "参数2说明", False, default=10)
    ]
)

# 2. 注册工具
from src.execution import get_tool_registry
registry = get_tool_registry()
registry.register_tool(new_tool)
```

## 📝 API文档

### Tool类

```python
@dataclass
class Tool:
    name: str                      # 工具名称
    description: str               # 工具描述
    category: ToolCategory         # 工具分类
    parameters: List[ToolParameter] # 参数列表
    handler: Optional[Callable]    # 执行函数
    
    def to_mcp_schema(self) -> Dict  # 转换为MCP schema
    async def execute(self, **kwargs) -> Dict  # 执行工具
```

### ToolRegistry类

```python
class ToolRegistry:
    def register_tool(self, tool: Tool)  # 注册工具
    def get_tool(self, name: str) -> Optional[Tool]  # 获取工具
    def list_tools(self, category: Optional[ToolCategory]) -> List[Tool]  # 列出工具
    def get_mcp_tools(self) -> List[Dict]  # 获取MCP格式工具列表
```

### MCPServer类

```python
class MCPServer:
    async def handle_request(self, request: MCPRequest) -> MCPResponse  # 处理请求
    def list_tools_by_category(self) -> Dict[str, List[str]]  # 按分类列表
    def get_tool_count(self) -> int  # 获取工具总数
    def get_tool_info(self, tool_name: str) -> Optional[Dict]  # 获取工具信息
```

## 🤝 贡献

欢迎提交PR添加更多工具！请遵循以下规范：
1. 工具命名使用snake_case
2. 提供清晰的描述和参数说明
3. 选择合适的工具分类
4. 添加相应的测试用例

## 📄 许可证

MIT License

## 📧 联系方式

如有问题或建议，请提交Issue。
