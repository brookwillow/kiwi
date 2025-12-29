"""
MCP (Model Context Protocol) 服务器实现
提供标准化的工具接口供AI模型调用
"""
import asyncio
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from .tool_registry import get_tool_registry, ToolRegistry


@dataclass
class MCPRequest:
    """MCP请求"""
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


@dataclass
class MCPResponse:
    """MCP响应"""
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        data = {}
        if self.result is not None:
            data["result"] = self.result
        if self.error is not None:
            data["error"] = self.error
        if self.id is not None:
            data["id"] = self.id
        return data


class MCPServer:
    """MCP服务器"""
    
    def __init__(self):
        self.registry: ToolRegistry = get_tool_registry()
        self.version = "1.0.0"
        self.capabilities = {
            "tools": True,
            "resources": False,
            "prompts": False
        }
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """处理MCP请求"""
        try:
            if request.method == "initialize":
                return await self._handle_initialize(request)
            elif request.method == "tools/list":
                return await self._handle_tools_list(request)
            elif request.method == "tools/call":
                return await self._handle_tools_call(request)
            else:
                return MCPResponse(
                    error={
                        "code": -32601,
                        "message": f"Method not found: {request.method}"
                    },
                    id=request.id
                )
        except Exception as e:
            return MCPResponse(
                error={
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                },
                id=request.id
            )
    
    async def _handle_initialize(self, request: MCPRequest) -> MCPResponse:
        """处理初始化请求"""
        return MCPResponse(
            result={
                "protocolVersion": self.version,
                "capabilities": self.capabilities,
                "serverInfo": {
                    "name": "Kiwi Vehicle Control Server",
                    "version": "1.0.0"
                }
            },
            id=request.id
        )
    
    async def _handle_tools_list(self, request: MCPRequest) -> MCPResponse:
        """处理工具列表请求"""
        tools = self.registry.get_mcp_tools()
        return MCPResponse(
            result={
                "tools": tools
            },
            id=request.id
        )
    
    async def _handle_tools_call(self, request: MCPRequest) -> MCPResponse:
        """处理工具调用请求"""
        if not request.params:
            return MCPResponse(
                error={
                    "code": -32602,
                    "message": "Invalid params: missing params"
                },
                id=request.id
            )
        
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})
        
        if not tool_name:
            return MCPResponse(
                error={
                    "code": -32602,
                    "message": "Invalid params: missing tool name"
                },
                id=request.id
            )
        
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return MCPResponse(
                error={
                    "code": -32602,
                    "message": f"Tool not found: {tool_name}"
                },
                id=request.id
            )
        
        try:
            result = await tool.execute(**arguments)
            return MCPResponse(
                result=result,  # 直接返回工具执行结果
                id=request.id
            )
        except Exception as e:
            return MCPResponse(
                error={
                    "code": -32603,
                    "message": f"Tool execution failed: {str(e)}"
                },
                id=request.id
            )
    
    def list_tools_by_category(self) -> Dict[str, List[str]]:
        """按分类列出所有工具"""
        from .tool_registry import ToolCategory
        result = {}
        for category in ToolCategory:
            tools = self.registry.list_tools(category)
            result[category.value] = [tool.name for tool in tools]
        return result
    
    def get_tool_count(self) -> int:
        """获取工具总数"""
        return len(self.registry.tools)
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict]:
        """获取工具详细信息"""
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return None
        
        return {
            "name": tool.name,
            "description": tool.description,
            "category": tool.category.value,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "enum": p.enum,
                    "default": p.default
                }
                for p in tool.parameters
            ]
        }


# 全局单例
_server = None


def get_mcp_server() -> MCPServer:
    """获取MCP服务器单例"""
    global _server
    if _server is None:
        _server = MCPServer()
    return _server


# 便捷函数
async def call_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """调用工具的便捷函数"""
    server = get_mcp_server()
    request = MCPRequest(
        method="tools/call",
        params={
            "name": tool_name,
            "arguments": kwargs
        },
        id="1"
    )
    response = await server.handle_request(request)
    
    if response.error:
        raise Exception(response.error["message"])
    
    return response.result


async def list_all_tools() -> List[Dict]:
    """列出所有工具的便捷函数"""
    server = get_mcp_server()
    request = MCPRequest(
        method="tools/list",
        id="1"
    )
    response = await server.handle_request(request)
    
    if response.error:
        raise Exception(response.error["message"])
    
    return response.result["tools"]
