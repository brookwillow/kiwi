"""
执行模块 - 车载能力工具集
提供170个车载控制工具，并通过MCP标准对外暴露

主要对外接口：
    ExecutionManager - 统一管理器（推荐使用）
    get_execution_manager() - 获取管理器单例

Example:
    >>> from execution import get_execution_manager
    >>> manager = get_execution_manager()
    >>> result = await manager.execute_tool("start_engine")
    >>> print(manager.is_engine_running())
"""

# ==================== 主要对外接口 ====================
from .manager import (
    ExecutionManager,
    get_execution_manager
)

# ==================== 内部模块（高级用户可选） ====================
from .tool_registry import (
    Tool,
    ToolCategory,
)

from .mcp_server import (
    MCPRequest,
    MCPResponse,
)

from .vehicle_state import (
    VehicleState,
)

# 控制台作为可选导入
try:
    from . import console
except ImportError:
    console = None

__all__ = [
    # ==================== 主要对外接口 ====================
    'ExecutionManager',      # 统一管理器类
    'get_execution_manager', # 获取管理器单例（推荐使用）
    
    # ==================== 数据类型（可选） ====================
    'Tool',                  # 工具定义类
    'ToolCategory',          # 工具分类枚举
    'VehicleState',          # 车辆状态类
    'MCPRequest',            # MCP请求类
    'MCPResponse',           # MCP响应类
    
    # ==================== 控制台（可选） ====================
    'console',               # 交互式控制台模块
]
