"""
高德地图 MCP 工具封装（使用 langchain-mcp-adapters）

【本模块的作用】
使用 LangChain 官方的 MCP 适配器 (langchain-mcp-adapters)，
连接高德地图的 MCP 服务器，
将高德地图的工具转换为 LangChain 可以使用的工具格式。

【传输方式：SSE vs stdio】
- SSE (Server-Sent Events): HTTP 通信，支持并行调用
- stdio: 本地进程通信，不支持并行调用

本模块使用 SSE 方式，实现真正的并行工具调用。

【使用方式】
本模块只提供异步函数 get_amap_tools_async()。
调用方需要在自己的异步函数中 await 调用。

示例：
    tools = await get_amap_tools_async()
"""

from typing import List
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import BaseTool
from ..config import get_settings

# =============================================================================
# 全局变量：用于缓存工具实例，避免重复创建
# =============================================================================

_amap_tools: List[BaseTool] | None = None
_mcp_client: MultiServerMCPClient | None = None


# =============================================================================
# 异步获取工具函数
# =============================================================================

async def get_amap_tools_async() -> List[BaseTool]:
    """
    【异步】获取高德地图 MCP 工具列表

    使用 SSE (Server-Sent Events) 方式连接高德地图 MCP 服务器。
    【SSE 的优势】
    - 支持 HTTP 并发请求，可以真正并行调用多个工具
    - 不需要本地安装 amap-mcp-server
    - 连接更稳定
    
    Returns:
        List[BaseTool]:  工具列表
    """
    global _amap_tools, _mcp_client
    
    if _amap_tools is not None:
        print("[DEBUG] 使用缓存的高德地图工具")
        return _amap_tools
    
    settings = get_settings()
    if not settings.amap_api_key:
        raise ValueError("高德地图API Key未配置，请在 .env 文件中设置 AMAP_API_KEY")
    
    print("[DEBUG] 正在连接高德地图 MCP 服务器 (SSE)...")
    
    # 【SSE 方式连接】
    # 使用高德官方提供的 MCP SSE 端点
    _mcp_client = MultiServerMCPClient({
        "amap": {
            "url": f"https://mcp.amap.com/sse?key={settings.amap_api_key}",
            "transport": "sse",
        }
    })
    
    _amap_tools = await _mcp_client.get_tools()
    
    print(f"[DEBUG] 成功获取 {len(_amap_tools)} 个高德地图工具")
    for tool in _amap_tools:
        print(f"  - {tool.name}: {tool.description[:50]}...")
    
    return _amap_tools
