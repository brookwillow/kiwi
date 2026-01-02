"""
执行模块管理器 - 统一对外接口
提供执行模块的所有核心功能
"""
from typing import Dict, List, Any, Optional
from .tool_registry import Tool, ToolCategory, ToolRegistry, get_tool_registry
from .vehicle_state import VehicleState, VehicleStateManager, get_vehicle_state
from .mcp_server import MCPServer, MCPRequest, MCPResponse, get_mcp_server


class ExecutionManager:
    """
    执行模块管理器 - 统一对外接口
    
    这是执行模块的唯一对外接口类，封装了所有核心功能：
    - 工具注册和管理
    - 工具执行
    - 车辆状态管理
    - MCP服务器
    
    Examples:
        >>> manager = ExecutionManager()
        >>> 
        >>> # 执行工具
        >>> result = await manager.execute_tool("start_engine")
        >>> 
        >>> # 查询状态
        >>> is_running = manager.is_engine_running()
        >>> 
        >>> # 获取工具列表
        >>> tools = manager.list_tools()
    """

    @property
    def name(self):
        return "execution"

    @property
    def is_running(self):
        return True
    
    def __init__(self):
        """初始化执行管理器"""
        self._registry: ToolRegistry = get_tool_registry()
        self._vehicle: VehicleStateManager = get_vehicle_state()
        self._mcp_server: MCPServer = get_mcp_server()
    
    def initialize(self) -> bool:
        """初始化模块"""
        return True

    def start(self) -> bool:
        """启动模块"""
        return True

    def stop(self):
        """停止模块"""
        pass

    def cleanup(self):
        """清理资源"""
        pass

    def handle_event(self, event):
        """处理事件"""
        pass
    
    # ==================== 工具执行相关 ====================
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            执行结果字典，包含 success, message 等字段
            
        Example:
            >>> result = await manager.execute_tool("turn_on_ac")
            >>> result = await manager.execute_tool("set_temperature", zone="driver", temperature=22)
        """
        tool = self._registry.get_tool(tool_name)
        if not tool:
            return {
                "success": False,
                "message": f"工具不存在: {tool_name}"
            }
        
        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            return {
                "success": False,
                "message": f"工具执行失败: {str(e)}"
            }
    
    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """
        获取工具对象
        
        Args:
            tool_name: 工具名称
            
        Returns:
            Tool对象，如果不存在返回None
        """
        return self._registry.get_tool(tool_name)
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[Tool]:
        """
        列出所有工具
        
        Args:
            category: 可选的工具分类过滤
            
        Returns:
            工具列表
            
        Example:
            >>> all_tools = manager.list_tools()
            >>> climate_tools = manager.list_tools(ToolCategory.CLIMATE)
        """
        return self._registry.list_tools(category)
    
    def get_tool_count(self) -> int:
        """
        获取工具总数
        
        Returns:
            工具数量
        """
        return len(self._registry.tools)
    
    def get_tool_categories(self) -> List[str]:
        """
        获取所有工具分类
        
        Returns:
            分类列表
        """
        return [cat.value for cat in ToolCategory]
    
    def get_tools_by_category(self) -> Dict[str, List[str]]:
        """
        按分类获取工具名称
        
        Returns:
            分类 -> 工具名称列表的字典
            
        Example:
            >>> tools_by_cat = manager.get_tools_by_category()
            >>> climate_tools = tools_by_cat['climate']
        """
        result = {}
        for category in ToolCategory:
            tools = self.list_tools(category)
            result[category.value] = [tool.name for tool in tools]
        return result
    
    # ==================== 车辆状态相关 ====================
    
    def get_vehicle_state(self) -> VehicleState:
        """
        获取车辆状态对象
        
        Returns:
            VehicleState对象
        """
        return self._vehicle.state
    
    def get_state_value(self, key: str) -> Any:
        """
        获取指定状态值
        
        Args:
            key: 状态键名
            
        Returns:
            状态值
            
        Example:
            >>> speed = manager.get_state_value("speed")
            >>> ac_on = manager.get_state_value("ac_on")
        """
        return self._vehicle.get_value(key)
    
    def set_state_value(self, key: str, value: Any) -> bool:
        """
        设置状态值
        
        Args:
            key: 状态键名
            value: 状态值
            
        Returns:
            是否设置成功
        """
        return self._vehicle.set_value(key, value)
    
    def update_state_values(self, updates: Dict[str, Any]) -> bool:
        """
        批量更新状态值
        
        Args:
            updates: 状态更新字典
            
        Returns:
            是否更新成功
            
        Example:
            >>> manager.update_state_values({
            ...     "speed": 80.0,
            ...     "cruise_control_enabled": True
            ... })
        """
        return self._vehicle.update_values(updates)
    
    def get_all_states(self) -> Dict[str, Any]:
        """
        获取所有状态（字典格式）
        
        Returns:
            状态字典
        """
        return self._vehicle.to_dict()
    
    # ==================== 便捷状态查询 ====================
    
    def is_engine_running(self) -> bool:
        """发动机是否运行"""
        return self._vehicle.is_engine_running()
    
    def get_speed(self) -> float:
        """获取当前车速 (km/h)"""
        return self._vehicle.get_speed()
    
    def get_fuel_level(self) -> float:
        """获取油量百分比"""
        return self._vehicle.get_fuel_level()
    
    def get_battery_level(self) -> float:
        """获取电量百分比"""
        return self._vehicle.get_battery_level()
    
    def get_temperature(self, zone: str = "driver") -> float:
        """获取指定区域温度 (℃)"""
        return self._vehicle.get_temperature(zone)
    
    def get_volume(self) -> int:
        """获取音量 (0-100)"""
        return self._vehicle.get_volume()
    
    def is_ac_on(self) -> bool:
        """空调是否开启"""
        return self._vehicle.state.ac_on
    
    def is_music_playing(self) -> bool:
        """音乐是否播放中"""
        return self._vehicle.state.music_playing
    
    def is_navigation_active(self) -> bool:
        """导航是否激活"""
        return self._vehicle.state.navigation_active
    
    def get_navigation_destination(self) -> str:
        """获取导航目的地"""
        return self._vehicle.state.navigation_destination
    
    # ==================== MCP服务器相关 ====================
    
    async def handle_mcp_request(self, request: MCPRequest) -> MCPResponse:
        """
        处理MCP请求
        
        Args:
            request: MCP请求对象
            
        Returns:
            MCP响应对象
        """
        return await self._mcp_server.handle_request(request)
    
    def get_mcp_tools_schema(self) -> List[Dict]:
        """
        获取所有工具的MCP schema
        
        Returns:
            MCP工具schema列表
        """
        return self._registry.get_mcp_tools()
    
    # ==================== 统计信息 ====================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取执行模块统计信息
        
        Returns:
            统计信息字典
        """
        tools_by_cat = self.get_tools_by_category()
        return {
            "total_tools": self.get_tool_count(),
            "total_categories": len(ToolCategory),
            "tools_by_category": {
                cat: len(tools) for cat, tools in tools_by_cat.items()
            },
            "vehicle_state_fields": len(self.get_all_states()),
            "engine_running": self.is_engine_running(),
            "current_speed": self.get_speed(),
        }
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取执行模块信息
        
        Returns:
            模块信息字典
        """
        return {
            "name": "KIWI Execution Module",
            "version": "1.0.0",
            "description": "车载控制执行模块，提供170个工具和完整状态管理",
            "capabilities": {
                "tools": True,
                "state_management": True,
                "mcp_protocol": True,
            },
            "statistics": self.get_statistics(),
        }
    
    # ==================== 便捷方法 ====================
    
    async def start_vehicle(self) -> Dict[str, Any]:
        """
        启动车辆（解锁+启动发动机）
        
        Returns:
            执行结果
        """
        await self.execute_tool("unlock_vehicle")
        return await self.execute_tool("start_engine")
    
    async def stop_vehicle(self) -> Dict[str, Any]:
        """
        停车（熄火+锁车）
        
        Returns:
            执行结果
        """
        await self.execute_tool("stop_engine")
        return await self.execute_tool("lock_vehicle")
    
    async def set_comfort_mode(self, temperature: float = 24) -> Dict[str, Any]:
        """
        开启舒适模式（空调+音乐）
        
        Args:
            temperature: 温度设置 (℃)
            
        Returns:
            执行结果
        """
        await self.execute_tool("turn_on_ac")
        await self.execute_tool("set_temperature", zone="all", temperature=temperature)
        await self.execute_tool("play_music")
        return {"success": True, "message": f"舒适模式已开启，温度 {temperature}℃"}
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"<ExecutionManager: {self.get_tool_count()} tools, engine={'ON' if self.is_engine_running() else 'OFF'}>"


# 全局单例
_manager = None


def get_execution_manager() -> ExecutionManager:
    """
    获取执行管理器单例
    
    Returns:
        ExecutionManager实例
        
    Example:
        >>> from execution import get_execution_manager
        >>> manager = get_execution_manager()
        >>> result = await manager.execute_tool("start_engine")
    """
    global _manager
    if _manager is None:
        _manager = ExecutionManager()
    return _manager
