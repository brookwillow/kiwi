"""
车辆状态管理系统
维护车辆的所有状态信息，工具执行会实际修改这些状态
"""
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
import json


class DrivingMode(Enum):
    """驾驶模式"""
    COMFORT = "comfort"
    SPORT = "sport"
    ECO = "eco"
    SNOW = "snow"
    OFFROAD = "offroad"


class SeatPosition(Enum):
    """座椅位置"""
    DRIVER = "driver"
    PASSENGER = "passenger"
    REAR_LEFT = "rear_left"
    REAR_RIGHT = "rear_right"


@dataclass
class VehicleState:
    """车辆状态"""
    # 车辆基本状态
    engine_running: bool = False
    locked: bool = True
    speed: float = 0.0  # km/h
    fuel_level: float = 50.0  # %
    battery_level: float = 80.0  # %
    range_km: float = 400.0  # km
    mileage: float = 50000.0  # km
    outside_temperature: float = 25.0  # ℃
    
    # 驾驶控制
    driving_mode: str = "comfort"
    parking_brake: bool = True
    cruise_control_enabled: bool = False
    cruise_control_speed: float = 0.0
    speed_limit: float = 0.0
    
    # 空调系统
    ac_on: bool = False
    ac_max_mode: bool = False
    auto_climate: bool = False
    recirculation: bool = False
    defrost_front: bool = False
    defrost_rear: bool = False
    temperature: Dict[str, float] = field(default_factory=lambda: {
        "driver": 22.0,
        "passenger": 22.0,
        "rear_left": 22.0,
        "rear_right": 22.0
    })
    fan_speed: int = 3  # 1-7
    air_direction: str = "auto"
    
    # 座椅状态
    seat_heating: Dict[str, int] = field(default_factory=lambda: {
        "driver": 0,
        "passenger": 0,
        "rear_left": 0,
        "rear_right": 0
    })
    seat_ventilation: Dict[str, int] = field(default_factory=lambda: {
        "driver": 0,
        "passenger": 0,
        "rear_left": 0,
        "rear_right": 0
    })
    seat_massage: Dict[str, bool] = field(default_factory=lambda: {
        "driver": False,
        "passenger": False
    })
    seat_memory: Dict[int, Dict] = field(default_factory=dict)
    
    # 娱乐系统
    music_playing: bool = False
    music_paused: bool = False
    volume: int = 50  # 0-100
    muted: bool = False
    audio_source: str = "bluetooth"
    bluetooth_enabled: bool = True
    
    # 灯光系统
    headlights_on: bool = False
    headlight_mode: str = "auto"
    high_beam: bool = False
    fog_lights_front: bool = False
    fog_lights_rear: bool = False
    interior_lights_on: bool = False
    interior_brightness: int = 50  # 0-100
    daytime_running_lights: bool = True
    
    # 车窗/天窗
    windows: Dict[str, int] = field(default_factory=lambda: {
        "driver": 0,
        "passenger": 0,
        "rear_left": 0,
        "rear_right": 0
    })  # 0=关闭, 100=全开
    sunroof_position: int = 0  # 0=关闭, 100=全开
    sunroof_tilted: bool = False
    
    # 车门/后备箱
    doors_locked: bool = True
    doors_open: Dict[str, bool] = field(default_factory=lambda: {
        "driver": False,
        "passenger": False,
        "rear_left": False,
        "rear_right": False
    })
    trunk_open: bool = False
    hood_open: bool = False
    
    # 安全系统
    lane_assist: bool = False
    blind_spot_monitor: bool = True
    collision_warning: bool = True
    emergency_brake: bool = True
    rear_cross_traffic_alert: bool = True
    
    # ADAS
    autopilot: bool = False
    auto_parking: bool = False
    traffic_sign_recognition: bool = True
    following_distance: int = 3  # 1-5
    
    # 雨刷
    wipers_on: bool = False
    wiper_speed: str = "auto"
    auto_wipers: bool = True
    
    # 氛围
    fragrance_on: bool = False
    fragrance_intensity: int = 3  # 1-5
    ambient_lights_on: bool = True
    ambient_light_color: str = "white"
    ambient_light_brightness: int = 50  # 0-100
    
    # 导航
    navigation_active: bool = False
    navigation_destination: str = ""
    voice_guidance: bool = True
    
    # 充电
    charging: bool = False
    charge_limit: int = 80  # %
    
    # 胎压 (bar)
    tire_pressure: Dict[str, float] = field(default_factory=lambda: {
        "front_left": 2.4,
        "front_right": 2.4,
        "rear_left": 2.4,
        "rear_right": 2.4
    })


class VehicleStateManager:
    """车辆状态管理器（单例）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.state = VehicleState()
        self._lock = threading.Lock()
        self._initialized = True
    
    def get_state(self) -> VehicleState:
        """获取完整状态"""
        with self._lock:
            return self.state
    
    def get_value(self, key: str) -> Any:
        """获取单个状态值"""
        with self._lock:
            return getattr(self.state, key, None)
    
    def set_value(self, key: str, value: Any) -> bool:
        """设置单个状态值"""
        with self._lock:
            if hasattr(self.state, key):
                setattr(self.state, key, value)
                return True
            return False
    
    def update_values(self, updates: Dict[str, Any]) -> bool:
        """批量更新状态值"""
        with self._lock:
            for key, value in updates.items():
                if hasattr(self.state, key):
                    setattr(self.state, key, value)
            return True
    
    def reset(self):
        """重置为默认状态"""
        with self._lock:
            self.state = VehicleState()
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        with self._lock:
            return asdict(self.state)
    
    def to_json(self) -> str:
        """转换为JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    # 便捷查询方法
    def is_engine_running(self) -> bool:
        return self.state.engine_running
    
    def is_ac_on(self) -> bool:
        return self.state.ac_on
    
    def is_music_playing(self) -> bool:
        return self.state.music_playing
    
    def get_temperature(self, zone: str = "driver") -> float:
        return self.state.temperature.get(zone, 22.0)
    
    def get_window_position(self, window: str = "driver") -> int:
        return self.state.windows.get(window, 0)
    
    def get_volume(self) -> int:
        return self.state.volume
    
    def get_speed(self) -> float:
        return self.state.speed
    
    def get_fuel_level(self) -> float:
        return self.state.fuel_level
    
    def get_battery_level(self) -> float:
        return self.state.battery_level


# 全局单例
def get_vehicle_state() -> VehicleStateManager:
    """获取车辆状态管理器"""
    return VehicleStateManager()
