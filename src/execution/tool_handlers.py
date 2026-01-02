"""
工具执行处理器
实现每个工具的实际执行逻辑，修改车辆状态
"""
from typing import Dict, Any
from .vehicle_state import get_vehicle_state


class ToolHandlers:
    """工具处理器集合"""
    
    def __init__(self):
        self.vehicle = get_vehicle_state()
    
    # ==================== 车辆控制 ====================
    
    async def start_engine(self, **kwargs) -> Dict[str, Any]:
        """启动发动机"""
        if self.vehicle.state.engine_running:
            return {"success": False, "message": "发动机已经启动"}
        
        self.vehicle.set_value("engine_running", True)
        self.vehicle.set_value("parking_brake", False)
        return {"success": True, "message": "发动机启动成功"}
    
    async def stop_engine(self, **kwargs) -> Dict[str, Any]:
        """熄火"""
        if not self.vehicle.state.engine_running:
            return {"success": False, "message": "发动机已经关闭"}
        
        self.vehicle.update_values({
            "engine_running": False,
            "speed": 0.0,
            "cruise_control_enabled": False,
            "autopilot": False
        })
        return {"success": True, "message": "发动机已熄火"}
    
    async def lock_vehicle(self, **kwargs) -> Dict[str, Any]:
        """锁车"""
        self.vehicle.set_value("doors_locked", True)
        return {"success": True, "message": "车辆已锁定"}
    
    async def unlock_vehicle(self, **kwargs) -> Dict[str, Any]:
        """解锁车辆"""
        self.vehicle.set_value("doors_locked", False)
        return {"success": True, "message": "车辆已解锁"}
    
    async def honk_horn(self, duration: float = 1, **kwargs) -> Dict[str, Any]:
        """鸣笛"""
        return {"success": True, "message": f"鸣笛 {duration} 秒"}
    
    async def flash_lights(self, times: int = 3, **kwargs) -> Dict[str, Any]:
        """闪烁车灯"""
        return {"success": True, "message": f"车灯闪烁 {times} 次"}
    
    async def set_driving_mode(self, mode: str, **kwargs) -> Dict[str, Any]:
        """设置驾驶模式"""
        self.vehicle.set_value("driving_mode", mode)
        return {"success": True, "message": f"驾驶模式已切换为: {mode}"}
    
    async def enable_parking_brake(self, **kwargs) -> Dict[str, Any]:
        """拉起手刹"""
        self.vehicle.set_value("parking_brake", True)
        return {"success": True, "message": "手刹已拉起"}
    
    async def disable_parking_brake(self, **kwargs) -> Dict[str, Any]:
        """放下手刹"""
        self.vehicle.set_value("parking_brake", False)
        return {"success": True, "message": "手刹已放下"}
    
    async def enable_cruise_control(self, speed: float, **kwargs) -> Dict[str, Any]:
        """开启定速巡航"""
        self.vehicle.update_values({
            "cruise_control_enabled": True,
            "cruise_control_speed": speed
        })
        return {"success": True, "message": f"定速巡航已开启，速度: {speed} km/h"}
    
    async def disable_cruise_control(self, **kwargs) -> Dict[str, Any]:
        """关闭定速巡航"""
        self.vehicle.set_value("cruise_control_enabled", False)
        return {"success": True, "message": "定速巡航已关闭"}
    
    # ==================== 空调系统 ====================
    
    async def turn_on_ac(self, **kwargs) -> Dict[str, Any]:
        """打开空调"""
        self.vehicle.set_value("ac_on", True)
        return {"success": True, "message": "空调已开启"}
    
    async def turn_off_ac(self, **kwargs) -> Dict[str, Any]:
        """关闭空调"""
        self.vehicle.set_value("ac_on", False)
        return {"success": True, "message": "空调已关闭"}
    
    async def set_temperature(self, zone: str, temperature: float, **kwargs) -> Dict[str, Any]:
        """设置温度"""
        if zone == "all":
            for z in ["driver", "passenger", "rear_left", "rear_right"]:
                self.vehicle.state.temperature[z] = temperature
        else:
            self.vehicle.state.temperature[zone] = temperature
        return {"success": True, "message": f"{zone} 温度已设置为 {temperature}℃"}
    
    async def set_fan_speed(self, speed: int, **kwargs) -> Dict[str, Any]:
        """设置风速"""
        self.vehicle.set_value("fan_speed", speed)
        return {"success": True, "message": f"风速已设置为: {speed}"}
    
    async def enable_auto_climate(self, **kwargs) -> Dict[str, Any]:
        """开启自动空调"""
        self.vehicle.set_value("auto_climate", True)
        return {"success": True, "message": "自动空调已开启"}
    
    async def enable_recirculation(self, **kwargs) -> Dict[str, Any]:
        """开启内循环"""
        self.vehicle.set_value("recirculation", True)
        return {"success": True, "message": "内循环已开启"}
    
    async def disable_recirculation(self, **kwargs) -> Dict[str, Any]:
        """开启外循环"""
        self.vehicle.set_value("recirculation", False)
        return {"success": True, "message": "外循环已开启"}
    
    async def enable_ac_max(self, **kwargs) -> Dict[str, Any]:
        """开启最大制冷"""
        self.vehicle.update_values({
            "ac_on": True,
            "ac_max_mode": True,
            "fan_speed": 7,
            "recirculation": True
        })
        return {"success": True, "message": "最大制冷模式已开启"}
    
    async def enable_seat_heating(self, seat: str, level: int = 2, **kwargs) -> Dict[str, Any]:
        """开启座椅加热"""
        self.vehicle.state.seat_heating[seat] = level
        return {"success": True, "message": f"{seat} 座椅加热已开启，级别: {level}"}
    
    # ==================== 娱乐系统 ====================
    
    async def play_music(self, **kwargs) -> Dict[str, Any]:
        """播放音乐"""
        self.vehicle.set_value("music_playing", True)
        return {"success": True, "message": "音乐播放中"}
    
    async def pause_music(self, **kwargs) -> Dict[str, Any]:
        """暂停音乐"""
        self.vehicle.set_value("music_playing", False)
        return {"success": True, "message": "音乐已暂停"}
    
    async def set_volume(self, volume: int, **kwargs) -> Dict[str, Any]:
        """设置音量"""
        self.vehicle.set_value("volume", volume)
        return {"success": True, "message": f"音量已设置为: {volume}"}
    
    async def mute_audio(self, **kwargs) -> Dict[str, Any]:
        """静音"""
        self.vehicle.set_value("muted", True)
        return {"success": True, "message": "已静音"}
    
    async def unmute_audio(self, **kwargs) -> Dict[str, Any]:
        """取消静音"""
        self.vehicle.set_value("muted", False)
        return {"success": True, "message": "已取消静音"}
    
    async def enable_bluetooth(self, **kwargs) -> Dict[str, Any]:
        """开启蓝牙"""
        self.vehicle.set_value("bluetooth_enabled", True)
        return {"success": True, "message": "蓝牙已开启"}
    
    # ==================== 导航系统 ====================
    
    async def navigate_to(self, destination: str, **kwargs) -> Dict[str, Any]:
        """导航到目的地"""
        self.vehicle.update_values({
            "navigation_active": True,
            "navigation_destination": destination
        })
        return {"success": True, "message": f"导航已启动，目的地: {destination}"}
    
    async def navigate_home(self, **kwargs) -> Dict[str, Any]:
        """导航回家"""
        return await self.navigate_to("家")
    
    async def navigate_to_work(self, **kwargs) -> Dict[str, Any]:
        """导航到公司"""
        return await self.navigate_to("公司")
    
    async def cancel_navigation(self, **kwargs) -> Dict[str, Any]:
        """取消导航"""
        self.vehicle.update_values({
            "navigation_active": False,
            "navigation_destination": ""
        })
        return {"success": True, "message": "导航已取消"}
    
    async def enable_voice_guidance(self, **kwargs) -> Dict[str, Any]:
        """开启语音导航"""
        self.vehicle.set_value("voice_guidance", True)
        return {"success": True, "message": "语音导航已开启"}
    
    # ==================== 车窗/天窗 ====================
    
    async def open_window(self, window: str, percentage: int = 100, **kwargs) -> Dict[str, Any]:
        """打开车窗"""
        if window == "all":
            for w in ["driver", "passenger", "rear_left", "rear_right"]:
                self.vehicle.state.windows[w] = percentage
        else:
            self.vehicle.state.windows[window] = percentage
        return {"success": True, "message": f"{window} 车窗已打开 {percentage}%"}
    
    async def close_window(self, window: str, **kwargs) -> Dict[str, Any]:
        """关闭车窗"""
        if window == "all":
            for w in ["driver", "passenger", "rear_left", "rear_right"]:
                self.vehicle.state.windows[w] = 0
        else:
            self.vehicle.state.windows[window] = 0
        return {"success": True, "message": f"{window} 车窗已关闭"}
    
    async def open_sunroof(self, mode: str = "slide", **kwargs) -> Dict[str, Any]:
        """打开天窗"""
        if mode == "tilt":
            self.vehicle.update_values({
                "sunroof_tilted": True,
                "sunroof_position": 0
            })
        else:
            self.vehicle.update_values({
                "sunroof_tilted": False,
                "sunroof_position": 100
            })
        return {"success": True, "message": f"天窗已打开 (模式: {mode})"}
    
    async def close_sunroof(self, **kwargs) -> Dict[str, Any]:
        """关闭天窗"""
        self.vehicle.update_values({
            "sunroof_tilted": False,
            "sunroof_position": 0
        })
        return {"success": True, "message": "天窗已关闭"}
    
    # ==================== 座椅调节 ====================
    
    async def load_seat_memory(self, profile: int, **kwargs) -> Dict[str, Any]:
        """载入座椅记忆"""
        if profile in self.vehicle.state.seat_memory:
            return {"success": True, "message": f"已载入座椅记忆位置 {profile}"}
        return {"success": True, "message": f"座椅记忆位置 {profile} 已载入（默认）"}
    
    async def enable_seat_massage(self, seat: str, mode: str = "wave", **kwargs) -> Dict[str, Any]:
        """开启座椅按摩"""
        self.vehicle.state.seat_massage[seat] = True
        return {"success": True, "message": f"{seat} 座椅按摩已开启 (模式: {mode})"}
    
    async def enable_seat_ventilation(self, seat: str, level: int = 2, **kwargs) -> Dict[str, Any]:
        """开启座椅通风"""
        self.vehicle.state.seat_ventilation[seat] = level
        return {"success": True, "message": f"{seat} 座椅通风已开启，级别: {level}"}
    
    # ==================== 灯光控制 ====================
    
    async def turn_on_headlights(self, **kwargs) -> Dict[str, Any]:
        """打开大灯"""
        self.vehicle.set_value("headlights_on", True)
        return {"success": True, "message": "大灯已打开"}
    
    async def turn_off_headlights(self, **kwargs) -> Dict[str, Any]:
        """关闭大灯"""
        self.vehicle.set_value("headlights_on", False)
        return {"success": True, "message": "大灯已关闭"}
    
    async def set_headlight_mode(self, mode: str, **kwargs) -> Dict[str, Any]:
        """设置大灯模式"""
        self.vehicle.set_value("headlight_mode", mode)
        if mode in ["low_beam", "high_beam", "auto"]:
            self.vehicle.set_value("headlights_on", True)
        return {"success": True, "message": f"大灯模式已设置为: {mode}"}
    
    async def set_ambient_light_color(self, color: str, **kwargs) -> Dict[str, Any]:
        """设置氛围灯颜色"""
        self.vehicle.update_values({
            "ambient_lights_on": True,
            "ambient_light_color": color
        })
        return {"success": True, "message": f"氛围灯颜色已设置为: {color}"}
    
    async def set_interior_brightness(self, brightness: int, **kwargs) -> Dict[str, Any]:
        """设置内饰亮度"""
        self.vehicle.set_value("interior_brightness", brightness)
        return {"success": True, "message": f"内饰亮度已设置为: {brightness}"}
    
    # ==================== 安全系统 ====================
    
    async def enable_lane_assist(self, **kwargs) -> Dict[str, Any]:
        """开启车道保持"""
        self.vehicle.set_value("lane_assist", True)
        return {"success": True, "message": "车道保持已开启"}
    
    async def enable_blind_spot_monitor(self, **kwargs) -> Dict[str, Any]:
        """开启盲区监测"""
        self.vehicle.set_value("blind_spot_monitor", True)
        return {"success": True, "message": "盲区监测已开启"}
    
    async def enable_collision_warning(self, **kwargs) -> Dict[str, Any]:
        """开启碰撞预警"""
        self.vehicle.set_value("collision_warning", True)
        return {"success": True, "message": "碰撞预警已开启"}
    
    # ==================== ADAS ====================
    
    async def enable_autopilot(self, **kwargs) -> Dict[str, Any]:
        """开启自动驾驶"""
        self.vehicle.set_value("autopilot", True)
        return {"success": True, "message": "自动驾驶已开启"}
    
    async def enable_auto_parking(self, **kwargs) -> Dict[str, Any]:
        """开启自动泊车"""
        self.vehicle.set_value("auto_parking", True)
        return {"success": True, "message": "自动泊车已开启"}
    
    # ==================== 雨刷 ====================
    
    async def enable_wipers(self, speed: str = "auto", **kwargs) -> Dict[str, Any]:
        """开启雨刷"""
        self.vehicle.update_values({
            "wipers_on": True,
            "wiper_speed": speed
        })
        return {"success": True, "message": f"雨刷已开启 (速度: {speed})"}
    
    async def disable_wipers(self, **kwargs) -> Dict[str, Any]:
        """关闭雨刷"""
        self.vehicle.set_value("wipers_on", False)
        return {"success": True, "message": "雨刷已关闭"}
    
    async def enable_auto_wipers(self, **kwargs) -> Dict[str, Any]:
        """开启自动雨刷"""
        self.vehicle.set_value("auto_wipers", True)
        return {"success": True, "message": "自动雨刷已开启"}
    
    # ==================== 氛围 ====================
    
    async def enable_fragrance(self, intensity: int = 3, **kwargs) -> Dict[str, Any]:
        """开启香氛"""
        self.vehicle.update_values({
            "fragrance_on": True,
            "fragrance_intensity": intensity
        })
        return {"success": True, "message": f"香氛已开启 (强度: {intensity})"}
    
    async def set_ambient_theme(self, theme: str, **kwargs) -> Dict[str, Any]:
        """设置氛围主题"""
        theme_colors = {
            "romantic": "purple",
            "energetic": "red",
            "calm": "blue",
            "party": "auto"
        }
        color = theme_colors.get(theme, "white")
        self.vehicle.set_value("ambient_light_color", color)
        return {"success": True, "message": f"氛围主题已设置为: {theme}"}
    
    # ==================== 通信系统 ====================
    
    async def make_call(self, contact: str, **kwargs) -> Dict[str, Any]:
        """拨打电话"""
        self.vehicle.update_values({
            "call_active": True,
            "call_contact": contact
        })
        return {"success": True, "message": f"正在呼叫 {contact}...", "contact": contact}
    
    async def answer_call(self, **kwargs) -> Dict[str, Any]:
        """接听电话"""
        self.vehicle.set_value("call_active", True)
        return {"success": True, "message": "已接听来电"}
    
    async def end_call(self, **kwargs) -> Dict[str, Any]:
        """挂断电话"""
        self.vehicle.update_values({
            "call_active": False,
            "call_contact": ""
        })
        return {"success": True, "message": "已挂断电话"}
    
    async def send_message(self, recipient: str, message: str, **kwargs) -> Dict[str, Any]:
        """发送消息"""
        return {
            "success": True, 
            "message": f"已发送消息给 {recipient}: {message}",
            "recipient": recipient,
            "content": message
        }
    
    async def read_messages(self, **kwargs) -> Dict[str, Any]:
        """读取消息"""
        return {"success": True, "message": "没有新消息"}
    
    async def enable_do_not_disturb(self, **kwargs) -> Dict[str, Any]:
        """开启勿扰模式"""
        self.vehicle.set_value("do_not_disturb", True)
        return {"success": True, "message": "勿扰模式已开启"}
    
    async def disable_do_not_disturb(self, **kwargs) -> Dict[str, Any]:
        """关闭勿扰模式"""
        self.vehicle.set_value("do_not_disturb", False)
        return {"success": True, "message": "勿扰模式已关闭"}
    
    async def switch_call_audio(self, device: str, **kwargs) -> Dict[str, Any]:
        """切换通话音频"""
        self.vehicle.set_value("call_audio_device", device)
        return {"success": True, "message": f"已切换到 {device} 设备", "device": device}
    
    # ==================== 信息查询 ====================
    
    async def get_fuel_level(self, **kwargs) -> Dict[str, Any]:
        """查询油量"""
        level = self.vehicle.get_fuel_level()
        return {"success": True, "message": f"当前油量: {level}%", "value": level}
    
    async def get_battery_level(self, **kwargs) -> Dict[str, Any]:
        """查询电量"""
        level = self.vehicle.get_battery_level()
        return {"success": True, "message": f"当前电量: {level}%", "value": level}
    
    async def get_speed(self, **kwargs) -> Dict[str, Any]:
        """查询当前车速"""
        speed = self.vehicle.get_speed()
        return {"success": True, "message": f"当前车速: {speed} km/h", "value": speed}
    
    # ==================== 单个状态查询 ====================
    
    async def get_engine_status(self, **kwargs) -> Dict[str, Any]:
        """查询发动机状态"""
        running = self.vehicle.state.engine_running
        return {"success": True, "message": f"发动机: {'运行中' if running else '熄火'}", "value": running}
    
    async def get_lock_status(self, **kwargs) -> Dict[str, Any]:
        """查询车辆锁定状态"""
        locked = self.vehicle.state.doors_locked
        return {"success": True, "message": f"车辆: {'已锁定' if locked else '已解锁'}", "value": locked}
    
    async def get_driving_mode(self, **kwargs) -> Dict[str, Any]:
        """查询驾驶模式"""
        mode = self.vehicle.state.driving_mode
        return {"success": True, "message": f"当前驾驶模式: {mode}", "value": mode}
    
    async def get_parking_brake_status(self, **kwargs) -> Dict[str, Any]:
        """查询手刹状态"""
        engaged = self.vehicle.state.parking_brake
        return {"success": True, "message": f"手刹: {'拉起' if engaged else '放下'}", "value": engaged}
    
    async def get_cruise_control_status(self, **kwargs) -> Dict[str, Any]:
        """查询定速巡航状态"""
        enabled = self.vehicle.state.cruise_control_enabled
        speed = self.vehicle.state.cruise_control_speed
        return {
            "success": True, 
            "message": f"定速巡航: {'开启' if enabled else '关闭'}{f' {speed}km/h' if enabled else ''}",
            "enabled": enabled,
            "speed": speed
        }
    
    async def get_ac_status(self, **kwargs) -> Dict[str, Any]:
        """查询空调状态"""
        ac_on = self.vehicle.state.ac_on
        return {"success": True, "message": f"空调: {'开启' if ac_on else '关闭'}", "value": ac_on}
    
    async def get_temperature(self, zone: str = "driver", **kwargs) -> Dict[str, Any]:
        """查询温度设置"""
        temp = self.vehicle.state.temperature.get(zone, 22.0)
        return {"success": True, "message": f"{zone} 温度: {temp}℃", "value": temp}
    
    async def get_fan_speed(self, **kwargs) -> Dict[str, Any]:
        """查询风速"""
        speed = self.vehicle.state.fan_speed
        return {"success": True, "message": f"风速: {speed}级", "value": speed}
    
    async def get_auto_climate_status(self, **kwargs) -> Dict[str, Any]:
        """查询自动空调状态"""
        auto = self.vehicle.state.auto_climate
        return {"success": True, "message": f"自动空调: {'开启' if auto else '关闭'}", "value": auto}
    
    async def get_music_status(self, **kwargs) -> Dict[str, Any]:
        """查询音乐状态"""
        playing = self.vehicle.state.music_playing
        return {
            "success": True, 
            "message": f"音乐: {'播放中' if playing else '已暂停'}",
            "playing": playing
        }
    
    async def get_volume(self, **kwargs) -> Dict[str, Any]:
        """查询音量"""
        volume = self.vehicle.get_volume()
        return {"success": True, "message": f"当前音量: {volume}", "value": volume}
    
    async def get_mute_status(self, **kwargs) -> Dict[str, Any]:
        """查询静音状态"""
        muted = self.vehicle.state.muted
        return {"success": True, "message": f"静音: {'是' if muted else '否'}", "value": muted}
    
    async def get_bluetooth_status(self, **kwargs) -> Dict[str, Any]:
        """查询蓝牙状态"""
        enabled = self.vehicle.state.bluetooth_enabled
        return {"success": True, "message": f"蓝牙: {'已连接' if enabled else '未连接'}", "value": enabled}
    
    async def get_navigation_status(self, **kwargs) -> Dict[str, Any]:
        """查询导航状态"""
        active = self.vehicle.state.navigation_active
        destination = self.vehicle.state.navigation_destination
        return {
            "success": True,
            "message": f"导航: {'活跃' if active else '未激活'}{f' - {destination}' if active else ''}",
            "active": active,
            "destination": destination
        }
    
    async def get_window_status(self, window: str = "driver", **kwargs) -> Dict[str, Any]:
        """查询车窗状态"""
        position = self.vehicle.state.windows.get(window, 0)
        return {"success": True, "message": f"{window} 车窗: {position}%", "value": position}
    
    async def get_sunroof_status(self, **kwargs) -> Dict[str, Any]:
        """查询天窗状态"""
        position = self.vehicle.state.sunroof_position
        tilted = self.vehicle.state.sunroof_tilted
        return {
            "success": True,
            "message": f"天窗: {position}%{' (翻起)' if tilted else ''}",
            "position": position,
            "tilted": tilted
        }
    
    async def get_headlight_status(self, **kwargs) -> Dict[str, Any]:
        """查询大灯状态"""
        on = self.vehicle.state.headlights_on
        mode = self.vehicle.state.headlight_mode
        return {
            "success": True,
            "message": f"大灯: {'开启' if on else '关闭'} - 模式: {mode}",
            "on": on,
            "mode": mode
        }
    
    async def get_ambient_light_status(self, **kwargs) -> Dict[str, Any]:
        """查询氛围灯状态"""
        on = self.vehicle.state.ambient_lights_on
        color = self.vehicle.state.ambient_light_color
        brightness = self.vehicle.state.ambient_light_brightness
        return {
            "success": True,
            "message": f"氛围灯: {'开启' if on else '关闭'} - 颜色: {color} - 亮度: {brightness}",
            "on": on,
            "color": color,
            "brightness": brightness
        }
    
    async def get_lane_assist_status(self, **kwargs) -> Dict[str, Any]:
        """查询车道保持状态"""
        enabled = self.vehicle.state.lane_assist
        return {"success": True, "message": f"车道保持: {'开启' if enabled else '关闭'}", "value": enabled}
    
    async def get_autopilot_status(self, **kwargs) -> Dict[str, Any]:
        """查询自动驾驶状态"""
        enabled = self.vehicle.state.autopilot
        return {"success": True, "message": f"自动驾驶: {'开启' if enabled else '关闭'}", "value": enabled}
    
    async def get_door_status(self, door: str = "driver", **kwargs) -> Dict[str, Any]:
        """查询车门状态"""
        open_status = self.vehicle.state.doors_open.get(door, False)
        return {"success": True, "message": f"{door} 车门: {'打开' if open_status else '关闭'}", "value": open_status}
    
    async def get_trunk_status(self, **kwargs) -> Dict[str, Any]:
        """查询后备箱状态"""
        open_status = self.vehicle.state.trunk_open
        return {"success": True, "message": f"后备箱: {'打开' if open_status else '关闭'}", "value": open_status}
    
    async def get_wiper_status(self, **kwargs) -> Dict[str, Any]:
        """查询雨刷状态"""
        on = self.vehicle.state.wipers_on
        speed = self.vehicle.state.wiper_speed
        auto = self.vehicle.state.auto_wipers
        return {
            "success": True,
            "message": f"雨刷: {'开启' if on else '关闭'} - 速度: {speed} - 自动: {'是' if auto else '否'}",
            "on": on,
            "speed": speed,
            "auto": auto
        }
    
    async def get_call_status(self, **kwargs) -> Dict[str, Any]:
        """查询通话状态"""
        active = self.vehicle.state.call_active
        contact = self.vehicle.state.call_contact
        return {
            "success": True,
            "message": f"通话: {'进行中' if active else '无通话'}{f' - {contact}' if active and contact else ''}",
            "active": active,
            "contact": contact
        }
    
    async def get_do_not_disturb_status(self, **kwargs) -> Dict[str, Any]:
        """查询勿扰模式状态"""
        enabled = self.vehicle.state.do_not_disturb
        return {"success": True, "message": f"勿扰模式: {'开启' if enabled else '关闭'}", "value": enabled}
    
    async def get_call_audio_device(self, **kwargs) -> Dict[str, Any]:
        """查询通话音频设备"""
        device = self.vehicle.state.call_audio_device
        return {"success": True, "message": f"通话音频设备: {device}", "value": device}


# 全局单例
_handlers = None


def get_tool_handlers() -> ToolHandlers:
    """获取工具处理器单例"""
    global _handlers
    if _handlers is None:
        _handlers = ToolHandlers()
    return _handlers
