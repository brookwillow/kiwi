"""
工具注册中心 - 管理所有可执行工具
"""
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
from .tool_handlers import get_tool_handlers


class ToolCategory(Enum):
    """工具分类"""
    # 车辆控制
    VEHICLE_CONTROL = "vehicle_control"
    # 空调系统
    CLIMATE = "climate"
    # 娱乐系统
    ENTERTAINMENT = "entertainment"
    # 导航系统
    NAVIGATION = "navigation"
    # 车窗/天窗
    WINDOW = "window"
    # 座椅调节
    SEAT = "seat"
    # 灯光控制
    LIGHTING = "lighting"
    # 安全系统
    SAFETY = "safety"
    # 通信系统
    COMMUNICATION = "communication"
    # 信息查询
    INFORMATION = "information"
    # 充电/加油
    ENERGY = "energy"
    # 驾驶辅助
    ADAS = "adas"
    # 车门/后备箱
    DOOR = "door"
    # 雨刷/洗涤
    WIPER = "wiper"
    # 香氛/氛围灯
    AMBIENT = "ambient"


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str  # string, number, boolean, array, object
    description: str
    required: bool = True
    enum: Optional[List[Any]] = None
    default: Optional[Any] = None


@dataclass
class Tool:
    """工具定义"""
    name: str
    description: str
    category: ToolCategory
    parameters: List[ToolParameter] = field(default_factory=list)
    handler: Optional[Callable] = None
    
    def to_mcp_schema(self) -> Dict:
        """转换为MCP工具schema"""
        schema = {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
            
            schema["inputSchema"]["properties"][param.name] = prop
            if param.required:
                schema["inputSchema"]["required"].append(param.name)
        
        return schema
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        if self.handler:
            return await self.handler(**kwargs)
        else:
            # 模拟执行
            return {
                "success": True,
                "message": f"工具 {self.name} 执行成功",
                "parameters": kwargs
            }


class ToolRegistry:
    """工具注册中心"""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._initialize_tools()
    
    def _initialize_tools(self):
        """初始化所有工具"""
        tools = self._create_all_tools()
        for tool in tools:
            self.register_tool(tool)
    
    def register_tool(self, tool: Tool):
        """注册工具"""
        self.tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self.tools.get(name)
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[Tool]:
        """列出工具"""
        if category:
            return [t for t in self.tools.values() if t.category == category]
        return list(self.tools.values())
    
    def get_mcp_tools(self) -> List[Dict]:
        """获取所有工具的MCP schema"""
        return [tool.to_mcp_schema() for tool in self.tools.values()]
    
    def _create_all_tools(self) -> List[Tool]:
        """创建所有工具定义"""
        tools = []
        
        # 1. 车辆控制类 (15个)
        tools.extend([
            Tool("start_engine", "启动发动机", ToolCategory.VEHICLE_CONTROL),
            Tool("stop_engine", "熄火", ToolCategory.VEHICLE_CONTROL),
            Tool("lock_vehicle", "锁车", ToolCategory.VEHICLE_CONTROL),
            Tool("unlock_vehicle", "解锁车辆", ToolCategory.VEHICLE_CONTROL),
            Tool("honk_horn", "鸣笛", ToolCategory.VEHICLE_CONTROL, [
                ToolParameter("duration", "number", "鸣笛时长(秒)", True, default=1)
            ]),
            Tool("flash_lights", "闪烁车灯", ToolCategory.VEHICLE_CONTROL, [
                ToolParameter("times", "number", "闪烁次数", True, default=3)
            ]),
            Tool("set_driving_mode", "设置驾驶模式", ToolCategory.VEHICLE_CONTROL, [
                ToolParameter("mode", "string", "驾驶模式", True, 
                            enum=["comfort", "sport", "eco", "snow", "offroad"])
            ]),
            Tool("enable_parking_brake", "拉起手刹", ToolCategory.VEHICLE_CONTROL),
            Tool("disable_parking_brake", "放下手刹", ToolCategory.VEHICLE_CONTROL),
            Tool("set_speed_limit", "设置限速", ToolCategory.VEHICLE_CONTROL, [
                ToolParameter("speed", "number", "限速值(km/h)", True)
            ]),
            Tool("enable_cruise_control", "开启定速巡航", ToolCategory.VEHICLE_CONTROL, [
                ToolParameter("speed", "number", "巡航速度(km/h)", True)
            ]),
            Tool("disable_cruise_control", "关闭定速巡航", ToolCategory.VEHICLE_CONTROL),
            Tool("set_suspension_height", "调节悬挂高度", ToolCategory.VEHICLE_CONTROL, [
                ToolParameter("height", "string", "高度级别", True, 
                            enum=["low", "normal", "high", "auto"])
            ]),
            Tool("enable_eco_mode", "开启节能模式", ToolCategory.VEHICLE_CONTROL),
            Tool("disable_eco_mode", "关闭节能模式", ToolCategory.VEHICLE_CONTROL),
        ])
        
        # 2. 空调系统 (18个)
        tools.extend([
            Tool("turn_on_ac", "打开空调", ToolCategory.CLIMATE),
            Tool("turn_off_ac", "关闭空调", ToolCategory.CLIMATE),
            Tool("set_temperature", "设置温度", ToolCategory.CLIMATE, [
                ToolParameter("zone", "string", "区域", True, 
                            enum=["driver", "passenger", "rear_left", "rear_right", "all"]),
                ToolParameter("temperature", "number", "温度(℃)", True)
            ]),
            Tool("increase_temperature", "升高温度", ToolCategory.CLIMATE, [
                ToolParameter("zone", "string", "区域", False, default="all"),
                ToolParameter("delta", "number", "变化值(℃)", False, default=1)
            ]),
            Tool("decrease_temperature", "降低温度", ToolCategory.CLIMATE, [
                ToolParameter("zone", "string", "区域", False, default="all"),
                ToolParameter("delta", "number", "变化值(℃)", False, default=1)
            ]),
            Tool("set_fan_speed", "设置风速", ToolCategory.CLIMATE, [
                ToolParameter("speed", "number", "风速(1-7)", True)
            ]),
            Tool("increase_fan_speed", "增加风速", ToolCategory.CLIMATE),
            Tool("decrease_fan_speed", "减小风速", ToolCategory.CLIMATE),
            Tool("set_air_direction", "设置出风方向", ToolCategory.CLIMATE, [
                ToolParameter("direction", "string", "方向", True,
                            enum=["face", "feet", "face_feet", "windshield", "auto"])
            ]),
            Tool("enable_auto_climate", "开启自动空调", ToolCategory.CLIMATE),
            Tool("disable_auto_climate", "关闭自动空调", ToolCategory.CLIMATE),
            Tool("enable_recirculation", "开启内循环", ToolCategory.CLIMATE),
            Tool("disable_recirculation", "开启外循环", ToolCategory.CLIMATE),
            Tool("enable_ac_max", "开启最大制冷", ToolCategory.CLIMATE),
            Tool("disable_ac_max", "关闭最大制冷", ToolCategory.CLIMATE),
            Tool("enable_defrost", "开启除雾", ToolCategory.CLIMATE, [
                ToolParameter("position", "string", "位置", True, 
                            enum=["front", "rear", "all"])
            ]),
            Tool("disable_defrost", "关闭除雾", ToolCategory.CLIMATE, [
                ToolParameter("position", "string", "位置", True, 
                            enum=["front", "rear", "all"])
            ]),
            Tool("enable_seat_heating", "开启座椅加热", ToolCategory.CLIMATE, [
                ToolParameter("seat", "string", "座椅", True,
                            enum=["driver", "passenger", "rear_left", "rear_right"]),
                ToolParameter("level", "number", "加热级别(1-3)", False, default=2)
            ]),
        ])
        
        # 3. 娱乐系统 (20个)
        tools.extend([
            Tool("play_music", "播放音乐", ToolCategory.ENTERTAINMENT),
            Tool("pause_music", "暂停音乐", ToolCategory.ENTERTAINMENT),
            Tool("next_track", "下一曲", ToolCategory.ENTERTAINMENT),
            Tool("previous_track", "上一曲", ToolCategory.ENTERTAINMENT),
            Tool("set_volume", "设置音量", ToolCategory.ENTERTAINMENT, [
                ToolParameter("volume", "number", "音量(0-100)", True)
            ]),
            Tool("increase_volume", "增加音量", ToolCategory.ENTERTAINMENT, [
                ToolParameter("delta", "number", "变化值", False, default=5)
            ]),
            Tool("decrease_volume", "减小音量", ToolCategory.ENTERTAINMENT, [
                ToolParameter("delta", "number", "变化值", False, default=5)
            ]),
            Tool("mute_audio", "静音", ToolCategory.ENTERTAINMENT),
            Tool("unmute_audio", "取消静音", ToolCategory.ENTERTAINMENT),
            Tool("play_radio", "播放收音机", ToolCategory.ENTERTAINMENT, [
                ToolParameter("frequency", "number", "频率(MHz)", False)
            ]),
            Tool("switch_audio_source", "切换音源", ToolCategory.ENTERTAINMENT, [
                ToolParameter("source", "string", "音源", True,
                            enum=["bluetooth", "usb", "radio", "aux", "online"])
            ]),
            Tool("search_song", "搜索歌曲", ToolCategory.ENTERTAINMENT, [
                ToolParameter("query", "string", "搜索关键词", True)
            ]),
            Tool("play_playlist", "播放歌单", ToolCategory.ENTERTAINMENT, [
                ToolParameter("playlist_name", "string", "歌单名称", True)
            ]),
            Tool("enable_bluetooth", "开启蓝牙", ToolCategory.ENTERTAINMENT),
            Tool("disable_bluetooth", "关闭蓝牙", ToolCategory.ENTERTAINMENT),
            Tool("pair_bluetooth_device", "配对蓝牙设备", ToolCategory.ENTERTAINMENT, [
                ToolParameter("device_name", "string", "设备名称", True)
            ]),
            Tool("set_equalizer", "设置均衡器", ToolCategory.ENTERTAINMENT, [
                ToolParameter("preset", "string", "预设", True,
                            enum=["rock", "jazz", "classical", "pop", "custom"])
            ]),
            Tool("enable_surround_sound", "开启环绕音效", ToolCategory.ENTERTAINMENT),
            Tool("disable_surround_sound", "关闭环绕音效", ToolCategory.ENTERTAINMENT),
            Tool("play_podcast", "播放播客", ToolCategory.ENTERTAINMENT, [
                ToolParameter("title", "string", "播客标题", True)
            ]),
        ])
        
        # 4. 导航系统 (15个)
        tools.extend([
            Tool("navigate_to", "导航到目的地", ToolCategory.NAVIGATION, [
                ToolParameter("destination", "string", "目的地", True),
                ToolParameter("avoid_highway", "boolean", "避开高速", False, default=False),
                ToolParameter("avoid_toll", "boolean", "避开收费站", False, default=False)
            ]),
            Tool("navigate_home", "导航回家", ToolCategory.NAVIGATION),
            Tool("navigate_to_work", "导航到公司", ToolCategory.NAVIGATION),
            Tool("search_nearby", "搜索附近", ToolCategory.NAVIGATION, [
                ToolParameter("category", "string", "类别", True,
                            enum=["gas_station", "parking", "restaurant", "hotel", 
                                  "hospital", "atm", "charging_station"])
            ]),
            Tool("cancel_navigation", "取消导航", ToolCategory.NAVIGATION),
            Tool("show_traffic", "显示路况", ToolCategory.NAVIGATION),
            Tool("enable_voice_guidance", "开启语音导航", ToolCategory.NAVIGATION),
            Tool("disable_voice_guidance", "关闭语音导航", ToolCategory.NAVIGATION),
            Tool("set_map_view", "设置地图视图", ToolCategory.NAVIGATION, [
                ToolParameter("view", "string", "视图模式", True,
                            enum=["2d", "3d", "north_up", "heading_up"])
            ]),
            Tool("zoom_in_map", "放大地图", ToolCategory.NAVIGATION),
            Tool("zoom_out_map", "缩小地图", ToolCategory.NAVIGATION),
            Tool("add_waypoint", "添加途经点", ToolCategory.NAVIGATION, [
                ToolParameter("location", "string", "地点", True)
            ]),
            Tool("show_speed_limit", "显示限速信息", ToolCategory.NAVIGATION),
            Tool("enable_traffic_alerts", "开启路况提醒", ToolCategory.NAVIGATION),
            Tool("save_location", "保存当前位置", ToolCategory.NAVIGATION, [
                ToolParameter("name", "string", "位置名称", True)
            ]),
        ])
        
        # 5. 车窗/天窗控制 (12个)
        tools.extend([
            Tool("open_window", "打开车窗", ToolCategory.WINDOW, [
                ToolParameter("window", "string", "窗户", True,
                            enum=["driver", "passenger", "rear_left", "rear_right", "all"]),
                ToolParameter("percentage", "number", "开启百分比(0-100)", False, default=100)
            ]),
            Tool("close_window", "关闭车窗", ToolCategory.WINDOW, [
                ToolParameter("window", "string", "窗户", True,
                            enum=["driver", "passenger", "rear_left", "rear_right", "all"])
            ]),
            Tool("open_sunroof", "打开天窗", ToolCategory.WINDOW, [
                ToolParameter("mode", "string", "模式", False, 
                            enum=["tilt", "slide", "full"], default="slide")
            ]),
            Tool("close_sunroof", "关闭天窗", ToolCategory.WINDOW),
            Tool("vent_windows", "车窗通风", ToolCategory.WINDOW),
            Tool("enable_rain_sensing", "开启雨量感应", ToolCategory.WINDOW),
            Tool("disable_rain_sensing", "关闭雨量感应", ToolCategory.WINDOW),
            Tool("enable_auto_window_up", "开启自动升窗", ToolCategory.WINDOW),
            Tool("disable_auto_window_up", "关闭自动升窗", ToolCategory.WINDOW),
            Tool("enable_pinch_protection", "开启防夹保护", ToolCategory.WINDOW),
            Tool("disable_pinch_protection", "关闭防夹保护", ToolCategory.WINDOW),
            Tool("calibrate_windows", "校准车窗", ToolCategory.WINDOW),
        ])
        
        # 6. 座椅调节 (15个)
        tools.extend([
            Tool("adjust_seat_position", "调节座椅位置", ToolCategory.SEAT, [
                ToolParameter("seat", "string", "座椅", True,
                            enum=["driver", "passenger"]),
                ToolParameter("direction", "string", "方向", True,
                            enum=["forward", "backward", "up", "down"])
            ]),
            Tool("adjust_seat_backrest", "调节座椅靠背", ToolCategory.SEAT, [
                ToolParameter("seat", "string", "座椅", True,
                            enum=["driver", "passenger"]),
                ToolParameter("angle", "number", "角度", True)
            ]),
            Tool("adjust_lumbar_support", "调节腰部支撑", ToolCategory.SEAT, [
                ToolParameter("seat", "string", "座椅", True,
                            enum=["driver", "passenger"]),
                ToolParameter("level", "number", "支撑级别(1-5)", True)
            ]),
            Tool("save_seat_memory", "保存座椅记忆", ToolCategory.SEAT, [
                ToolParameter("profile", "number", "记忆位置(1-3)", True)
            ]),
            Tool("load_seat_memory", "载入座椅记忆", ToolCategory.SEAT, [
                ToolParameter("profile", "number", "记忆位置(1-3)", True)
            ]),
            Tool("enable_seat_massage", "开启座椅按摩", ToolCategory.SEAT, [
                ToolParameter("seat", "string", "座椅", True,
                            enum=["driver", "passenger"]),
                ToolParameter("mode", "string", "按摩模式", False,
                            enum=["wave", "pulse", "relax"], default="wave")
            ]),
            Tool("disable_seat_massage", "关闭座椅按摩", ToolCategory.SEAT, [
                ToolParameter("seat", "string", "座椅", True,
                            enum=["driver", "passenger"])
            ]),
            Tool("enable_seat_ventilation", "开启座椅通风", ToolCategory.SEAT, [
                ToolParameter("seat", "string", "座椅", True,
                            enum=["driver", "passenger", "rear_left", "rear_right"]),
                ToolParameter("level", "number", "通风级别(1-3)", False, default=2)
            ]),
            Tool("disable_seat_ventilation", "关闭座椅通风", ToolCategory.SEAT, [
                ToolParameter("seat", "string", "座椅", True,
                            enum=["driver", "passenger", "rear_left", "rear_right"])
            ]),
            Tool("fold_rear_seat", "放倒后排座椅", ToolCategory.SEAT, [
                ToolParameter("position", "string", "位置", True,
                            enum=["left", "right", "all"])
            ]),
            Tool("restore_rear_seat", "恢复后排座椅", ToolCategory.SEAT, [
                ToolParameter("position", "string", "位置", True,
                            enum=["left", "right", "all"])
            ]),
            Tool("adjust_headrest", "调节头枕高度", ToolCategory.SEAT, [
                ToolParameter("seat", "string", "座椅", True,
                            enum=["driver", "passenger", "rear_left", "rear_right"]),
                ToolParameter("height", "number", "高度级别(1-5)", True)
            ]),
            Tool("enable_easy_entry", "开启上下车便利", ToolCategory.SEAT),
            Tool("disable_easy_entry", "关闭上下车便利", ToolCategory.SEAT),
            Tool("set_seat_position_preset", "设置座椅快捷位置", ToolCategory.SEAT, [
                ToolParameter("preset", "string", "预设", True,
                            enum=["comfort", "sport", "relax"])
            ]),
        ])
        
        # 7. 灯光控制 (12个)
        tools.extend([
            Tool("turn_on_headlights", "打开大灯", ToolCategory.LIGHTING),
            Tool("turn_off_headlights", "关闭大灯", ToolCategory.LIGHTING),
            Tool("set_headlight_mode", "设置大灯模式", ToolCategory.LIGHTING, [
                ToolParameter("mode", "string", "模式", True,
                            enum=["auto", "low_beam", "high_beam", "off"])
            ]),
            Tool("enable_high_beam", "开启远光灯", ToolCategory.LIGHTING),
            Tool("disable_high_beam", "关闭远光灯", ToolCategory.LIGHTING),
            Tool("turn_on_fog_lights", "打开雾灯", ToolCategory.LIGHTING, [
                ToolParameter("position", "string", "位置", True,
                            enum=["front", "rear", "all"])
            ]),
            Tool("turn_off_fog_lights", "关闭雾灯", ToolCategory.LIGHTING),
            Tool("set_interior_brightness", "设置内饰亮度", ToolCategory.LIGHTING, [
                ToolParameter("brightness", "number", "亮度(0-100)", True)
            ]),
            Tool("turn_on_interior_lights", "打开车内灯", ToolCategory.LIGHTING),
            Tool("turn_off_interior_lights", "关闭车内灯", ToolCategory.LIGHTING),
            Tool("enable_daytime_running_lights", "开启日间行车灯", ToolCategory.LIGHTING),
            Tool("disable_daytime_running_lights", "关闭日间行车灯", ToolCategory.LIGHTING),
        ])
        
        # 8. 安全系统 (10个)
        tools.extend([
            Tool("enable_lane_assist", "开启车道保持", ToolCategory.SAFETY),
            Tool("disable_lane_assist", "关闭车道保持", ToolCategory.SAFETY),
            Tool("enable_blind_spot_monitor", "开启盲区监测", ToolCategory.SAFETY),
            Tool("disable_blind_spot_monitor", "关闭盲区监测", ToolCategory.SAFETY),
            Tool("enable_collision_warning", "开启碰撞预警", ToolCategory.SAFETY),
            Tool("disable_collision_warning", "关闭碰撞预警", ToolCategory.SAFETY),
            Tool("enable_emergency_brake", "开启自动紧急制动", ToolCategory.SAFETY),
            Tool("disable_emergency_brake", "关闭自动紧急制动", ToolCategory.SAFETY),
            Tool("enable_rear_cross_traffic_alert", "开启后方交叉警示", ToolCategory.SAFETY),
            Tool("disable_rear_cross_traffic_alert", "关闭后方交叉警示", ToolCategory.SAFETY),
        ])
        
        # 9. 通信系统 (8个)
        tools.extend([
            Tool("make_call", "拨打电话", ToolCategory.COMMUNICATION, [
                ToolParameter("contact", "string", "联系人或号码", True)
            ]),
            Tool("answer_call", "接听电话", ToolCategory.COMMUNICATION),
            Tool("end_call", "挂断电话", ToolCategory.COMMUNICATION),
            Tool("send_message", "发送消息", ToolCategory.COMMUNICATION, [
                ToolParameter("recipient", "string", "接收人", True),
                ToolParameter("message", "string", "消息内容", True)
            ]),
            Tool("read_messages", "读取消息", ToolCategory.COMMUNICATION),
            Tool("enable_do_not_disturb", "开启勿扰模式", ToolCategory.COMMUNICATION),
            Tool("disable_do_not_disturb", "关闭勿扰模式", ToolCategory.COMMUNICATION),
            Tool("switch_call_audio", "切换通话音频", ToolCategory.COMMUNICATION, [
                ToolParameter("device", "string", "设备", True,
                            enum=["car", "phone"])
            ]),
        ])
        
        # 10. 信息查询 (30+个 - 单个状态查询)
        tools.extend([
            # 基础信息
            Tool("get_fuel_level", "查询油量", ToolCategory.INFORMATION),
            Tool("get_battery_level", "查询电量", ToolCategory.INFORMATION),
            Tool("get_speed", "查询当前车速", ToolCategory.INFORMATION),
            Tool("get_engine_status", "查询发动机状态", ToolCategory.INFORMATION),
            Tool("get_lock_status", "查询车辆锁定状态", ToolCategory.INFORMATION),
            Tool("get_driving_mode", "查询驾驶模式", ToolCategory.INFORMATION),
            Tool("get_parking_brake_status", "查询手刹状态", ToolCategory.INFORMATION),
            Tool("get_cruise_control_status", "查询定速巡航状态", ToolCategory.INFORMATION),
            
            # 空调系统
            Tool("get_ac_status", "查询空调状态", ToolCategory.INFORMATION),
            Tool("get_temperature", "查询温度设置", ToolCategory.INFORMATION, [
                ToolParameter("zone", "string", "区域", False,
                            enum=["driver", "passenger", "rear_left", "rear_right"],
                            default="driver")
            ]),
            Tool("get_fan_speed", "查询风速", ToolCategory.INFORMATION),
            Tool("get_auto_climate_status", "查询自动空调状态", ToolCategory.INFORMATION),
            
            # 娱乐系统
            Tool("get_music_status", "查询音乐状态", ToolCategory.INFORMATION),
            Tool("get_volume", "查询音量", ToolCategory.INFORMATION),
            Tool("get_mute_status", "查询静音状态", ToolCategory.INFORMATION),
            Tool("get_bluetooth_status", "查询蓝牙状态", ToolCategory.INFORMATION),
            
            # 导航系统
            Tool("get_navigation_status", "查询导航状态", ToolCategory.INFORMATION),
            
            # 车窗/天窗
            Tool("get_window_status", "查询车窗状态", ToolCategory.INFORMATION, [
                ToolParameter("window", "string", "车窗", False,
                            enum=["driver", "passenger", "rear_left", "rear_right"],
                            default="driver")
            ]),
            Tool("get_sunroof_status", "查询天窗状态", ToolCategory.INFORMATION),
            
            # 灯光
            Tool("get_headlight_status", "查询大灯状态", ToolCategory.INFORMATION),
            Tool("get_ambient_light_status", "查询氛围灯状态", ToolCategory.INFORMATION),
            
            # 安全辅助
            Tool("get_lane_assist_status", "查询车道保持状态", ToolCategory.INFORMATION),
            Tool("get_autopilot_status", "查询自动驾驶状态", ToolCategory.INFORMATION),
            
            # 车门/后备箱
            Tool("get_door_status", "查询车门状态", ToolCategory.INFORMATION, [
                ToolParameter("door", "string", "车门", False,
                            enum=["driver", "passenger", "rear_left", "rear_right"],
                            default="driver")
            ]),
            Tool("get_trunk_status", "查询后备箱状态", ToolCategory.INFORMATION),
            
            # 雨刷
            Tool("get_wiper_status", "查询雨刷状态", ToolCategory.INFORMATION),
            
            # 通信状态
            Tool("get_call_status", "查询通话状态", ToolCategory.INFORMATION),
            Tool("get_do_not_disturb_status", "查询勿扰模式状态", ToolCategory.INFORMATION),
            Tool("get_call_audio_device", "查询通话音频设备", ToolCategory.INFORMATION),
            
            # 其他查询（保留原有的）
            Tool("get_range", "查询续航里程", ToolCategory.INFORMATION),
            Tool("get_tire_pressure", "查询胎压", ToolCategory.INFORMATION),
            Tool("get_outside_temperature", "查询外部温度", ToolCategory.INFORMATION),
            Tool("get_mileage", "查询里程数", ToolCategory.INFORMATION),
            Tool("get_maintenance_info", "查询保养信息", ToolCategory.INFORMATION),
            Tool("get_trip_statistics", "查询行程统计", ToolCategory.INFORMATION),
        ])
        
        # 11. 充电/加油 (5个)
        tools.extend([
            Tool("start_charging", "开始充电", ToolCategory.ENERGY),
            Tool("stop_charging", "停止充电", ToolCategory.ENERGY),
            Tool("schedule_charging", "预约充电", ToolCategory.ENERGY, [
                ToolParameter("start_time", "string", "开始时间(HH:MM)", True),
                ToolParameter("target_soc", "number", "目标电量(%)", False, default=80)
            ]),
            Tool("set_charge_limit", "设置充电限制", ToolCategory.ENERGY, [
                ToolParameter("limit", "number", "限制电量(%)", True)
            ]),
            Tool("find_charging_station", "查找充电站", ToolCategory.ENERGY),
        ])
        
        # 12. 驾驶辅助(ADAS) (8个)
        tools.extend([
            Tool("enable_autopilot", "开启自动驾驶", ToolCategory.ADAS),
            Tool("disable_autopilot", "关闭自动驾驶", ToolCategory.ADAS),
            Tool("enable_auto_parking", "开启自动泊车", ToolCategory.ADAS),
            Tool("cancel_auto_parking", "取消自动泊车", ToolCategory.ADAS),
            Tool("enable_traffic_sign_recognition", "开启交通标识识别", ToolCategory.ADAS),
            Tool("disable_traffic_sign_recognition", "关闭交通标识识别", ToolCategory.ADAS),
            Tool("set_following_distance", "设置跟车距离", ToolCategory.ADAS, [
                ToolParameter("level", "number", "距离级别(1-5)", True)
            ]),
            Tool("enable_summon", "开启召唤功能", ToolCategory.ADAS),
        ])
        
        # 13. 车门/后备箱 (8个)
        tools.extend([
            Tool("open_door", "打开车门", ToolCategory.DOOR, [
                ToolParameter("door", "string", "车门", True,
                            enum=["driver", "passenger", "rear_left", "rear_right"])
            ]),
            Tool("close_door", "关闭车门", ToolCategory.DOOR, [
                ToolParameter("door", "string", "车门", True,
                            enum=["driver", "passenger", "rear_left", "rear_right"])
            ]),
            Tool("open_trunk", "打开后备箱", ToolCategory.DOOR),
            Tool("close_trunk", "关闭后备箱", ToolCategory.DOOR),
            Tool("open_hood", "打开引擎盖", ToolCategory.DOOR),
            Tool("enable_keyless_entry", "开启无钥匙进入", ToolCategory.DOOR),
            Tool("disable_keyless_entry", "关闭无钥匙进入", ToolCategory.DOOR),
            Tool("set_trunk_height", "设置后备箱高度", ToolCategory.DOOR, [
                ToolParameter("height", "number", "高度级别(1-5)", True)
            ]),
        ])
        
        # 14. 雨刷/洗涤 (6个)
        tools.extend([
            Tool("enable_wipers", "开启雨刷", ToolCategory.WIPER, [
                ToolParameter("speed", "string", "速度", False,
                            enum=["low", "medium", "high", "auto"], default="auto")
            ]),
            Tool("disable_wipers", "关闭雨刷", ToolCategory.WIPER),
            Tool("adjust_wiper_speed", "调节雨刷速度", ToolCategory.WIPER, [
                ToolParameter("speed", "string", "速度", True,
                            enum=["low", "medium", "high"])
            ]),
            Tool("spray_washer_fluid", "喷洒玻璃水", ToolCategory.WIPER, [
                ToolParameter("position", "string", "位置", False,
                            enum=["front", "rear"], default="front")
            ]),
            Tool("enable_auto_wipers", "开启自动雨刷", ToolCategory.WIPER),
            Tool("disable_auto_wipers", "关闭自动雨刷", ToolCategory.WIPER),
        ])
        
        # 15. 香氛/氛围灯 (8个)
        tools.extend([
            Tool("enable_fragrance", "开启香氛", ToolCategory.AMBIENT, [
                ToolParameter("intensity", "number", "强度级别(1-5)", False, default=3)
            ]),
            Tool("disable_fragrance", "关闭香氛", ToolCategory.AMBIENT),
            Tool("set_ambient_light_color", "设置氛围灯颜色", ToolCategory.AMBIENT, [
                ToolParameter("color", "string", "颜色", True,
                            enum=["red", "blue", "green", "purple", "orange", "white", "auto"])
            ]),
            Tool("set_ambient_light_brightness", "设置氛围灯亮度", ToolCategory.AMBIENT, [
                ToolParameter("brightness", "number", "亮度(0-100)", True)
            ]),
            Tool("turn_on_ambient_lights", "打开氛围灯", ToolCategory.AMBIENT),
            Tool("turn_off_ambient_lights", "关闭氛围灯", ToolCategory.AMBIENT),
            Tool("set_ambient_theme", "设置氛围主题", ToolCategory.AMBIENT, [
                ToolParameter("theme", "string", "主题", True,
                            enum=["romantic", "energetic", "calm", "party"])
            ]),
            Tool("enable_ambient_sync_music", "开启氛围灯音乐同步", ToolCategory.AMBIENT),
        ])
        
        return tools
    
    def _bind_handlers(self):
        """绑定工具处理器"""
        handlers = get_tool_handlers()
        
        # 获取handlers中所有的异步方法
        handler_methods = {
            name: getattr(handlers, name)
            for name in dir(handlers)
            if not name.startswith('_') and callable(getattr(handlers, name))
        }
        
        # 将handler绑定到对应的工具
        for tool_name, tool in self.tools.items():
            if tool_name in handler_methods:
                tool.handler = handler_methods[tool_name]


# 全局单例
_registry = None


def get_tool_registry() -> ToolRegistry:
    """获取工具注册中心单例"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
        _registry._bind_handlers()  # 绑定handlers
    return _registry
