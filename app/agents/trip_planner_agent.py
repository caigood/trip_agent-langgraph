"""
旅行规划智能体封装

【本模块的作用】
这是整个旅行规划系统的"入口层"，负责：
1. 初始化所有依赖组件（LLM、工具、图）
2. 对外提供简洁的调用接口
3. 解析和验证 LLM 的输出

【架构位置】
┌─────────────────────────────────────┐
│         API 路由层 (trip.py)         │  ← 接收 HTTP 请求
└─────────────────┬───────────────────┘
                  │ 调用
┌─────────────────▼───────────────────┐
│   TripPlannerAgent (本模块)          │  ← 封装业务逻辑
│   - 初始化 LLM、工具、图              │
│   - 结果解析和降级处理                │
└─────────────────┬───────────────────┘
                  │ 调用
┌─────────────────▼───────────────────┐
│   LangGraph 工作流 (graph.py)        │  ← 执行多 Agent 协作
└─────────────────┬───────────────────┘
                  │ 调用
┌─────────────────▼───────────────────┐
│   服务层 (llm_service, amap_service) │  ← 底层工具封装
└─────────────────────────────────────┘

【为什么需要这一层？】
1. 解耦：API 层不需要关心 LangGraph 的细节
2. 复用：单例模式确保 LLM 和工具只初始化一次
3. 容错：解析失败时提供降级方案

【异步设计】
本模块全部采用异步设计，与 FastAPI 原生异步架构完美配合：
- __init__()：同步构造函数，只做简单初始化
- initialize()：异步初始化，获取工具、构建图
- plan_trip_async()：异步规划方法
"""

import json
from typing import Dict, Any
from ..services.llm_service import get_llm
from ..services.amap_service import get_amap_tools_async
from ..models.schemas import TripRequest, TripPlan, Budget
from ..graph import build_trip_graph


# =============================================================================
# 旅行规划器类
# =============================================================================

class LangGraphTripPlanner:
    """
    【LangGraph 旅行规划器】
    
    这是系统的核心类，负责协调各个组件完成旅行规划任务。
    
    【初始化流程】
    1. __init__(): 同步构造函数，初始化空属性
    2. initialize(): 异步初始化，获取工具、构建图
    
    【使用示例】
        planner = LangGraphTripPlanner()
        await planner.initialize()  # 异步初始化
        
        request = TripRequest(
            city="北京",
            start_date="2024-01-01",
            end_date="2024-01-03",
            ...
        )
        plan = await planner.plan_trip_async(request)
        print(plan.city, plan.days)
    """
    
    def __init__(self):
        """
        【同步构造函数】
        
        只做简单的属性初始化，真正的初始化在 initialize() 中异步进行。
        
        【为什么要分开？】
        - __init__ 必须是同步的（Python 语法限制）
        - 获取 MCP 工具需要异步（网络 IO）
        - 分开后代码更清晰，避免复杂的同步/异步转换
        """
        self.llm = None
        self.tools = None
        self.llm_with_tools = None
        self.graph = None
        self._initialized = False
        
    async def initialize(self):
        """
        【异步初始化】获取工具并构建 LangGraph 工作流
    
        这是真正的初始化逻辑，负责：
        1. 获取 LLM 实例
        2. 【异步】获取高德地图工具（MCP 需要异步）
        3. 绑定工具到 LLM
        4. 构建 LangGraph 工作流图
        
        【调用时机】
        在第一次调用 plan_trip_async() 之前调用一次即可。
        使用 _initialized 标记避免重复初始化。
        """
        if self._initialized:
            return
            
        print("[DEBUG] 正在初始化 LangGraphTripPlanner...")
        
        self.llm = get_llm()
        print("[DEBUG] LLM 实例获取成功")
        
        self.tools = await get_amap_tools_async()
        print(f"[DEBUG] 获取到 {len(self.tools)} 个工具")
        
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        print("[DEBUG] 工具绑定成功")
        
        self.graph = build_trip_graph(self.llm_with_tools, self.llm, self.tools)
        print("[DEBUG] LangGraph 工作流构建成功")
        
        self._initialized = True
        print("[DEBUG] LangGraphTripPlanner 初始化完成")
        
    async def plan_trip_async(self, request: TripRequest) -> TripPlan:
        """
        【异步】生成旅行计划
        
        这是核心方法，使用 LangGraph 的异步执行能力。
        
        【工作流程】
        1. 确保已初始化（自动调用 initialize()）
        2. 构造初始状态（包含用户请求）
        3. 调用 graph.ainvoke() 异步执行工作流
        4. 等待所有节点完成（并行执行 Attraction/Weather/Hotel）
        5. 获取最终状态中的 plan_raw
        6. 解析 JSON 并返回 TripPlan 对象
        
        Args:
            request: 用户的旅行请求（城市、日期、偏好等）
            
        Returns:
            TripPlan: 结构化的旅行计划对象
        """
        if not self._initialized:
            await self.initialize()
        
        initial_state = {
            #request.model_dump() 将Pydantic 模型实例转换为普通 Python 字典，LangGraph 的状态需要普通字典，不能是 Pydantic 对象
            "request": request.model_dump(),
            "attraction_response": None,
            "weather_response": None,
            "hotel_response": None,
            "plan_raw": ""
        }
        
        print("\n" + "="*60)
        print("[DEBUG] 开始执行旅行规划工作流...")
        print("="*60)
        
        final_state = await self.graph.ainvoke(initial_state)
        
        print("="*60)
        print("[DEBUG] 工作流执行完成")
        print("="*60 + "\n")
        
        plan_raw = final_state.get("plan_raw", "") or ""
        
        return self._parse_response(plan_raw, request)

    def _parse_response(self, raw_response: str, request: TripRequest) -> TripPlan:
        """
        【解析 LLM 返回的 JSON 字符串】
        
        LLM 返回的是 JSON 格式的字符串，但可能有以下问题：
        1. 包含 Markdown 代码块标记（```json ... ```）
        2. 包含额外的说明文字
        3. JSON 格式不完整
        
        这个方法负责：
        1. 提取 JSON 部分（找到第一个 { 和最后一个 }）
        2. 解析为 Python 字典
        3. 转换为 TripPlan 对象
        
        【降级策略】
        如果解析失败，调用 _create_fallback_plan() 返回一个最小可用计划，
        避免前端显示空白或报错。
        
        Args:
            raw_response: LLM 返回的原始字符串
            request: 原始请求（用于降级时填充基本信息）
            
        Returns:
            TripPlan: 解析后的旅行计划对象
        """
        try:
            start_idx = raw_response.find('{')
            end_idx = raw_response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = raw_response[start_idx:end_idx]
                data = json.loads(json_str)
                return TripPlan(**data)
            else:
                print(f"[WARNING] 无法在响应中找到 JSON: {raw_response[:100]}...")
                return self._create_fallback_plan(request, raw_response)
                
        except Exception as e:
            print(f"[ERROR] 解析响应失败: {e}")
            return self._create_fallback_plan(request, raw_response)

    def _create_fallback_plan(self, request: TripRequest, raw_text: str) -> TripPlan:
        """
        【创建降级计划】
        
        当 LLM 输出解析失败时，返回一个最小可用的计划，
        确保前端不会崩溃或显示空白。
        
        Args:
            request: 原始请求
            raw_text: LLM 的原始输出
            
        Returns:
            TripPlan: 降级后的旅行计划
        """
        return TripPlan(
            city=request.city,
            start_date=str(request.start_date),
            end_date=str(request.end_date),
            days=[],
            weather_info=[],
            overall_suggestions=raw_text[:500] + "...",
            budget=Budget(total=0, breakdown="解析失败，请参考建议")
        )
    

# =============================================================================
# 单例模式实现
# =============================================================================

_planner_agent: LangGraphTripPlanner | None = None


async def get_trip_planner_agent() -> LangGraphTripPlanner:
    """
    【异步】获取规划器实例（单例模式）
    【使用方式】
        planner = await get_trip_planner_agent()
        plan = await planner.plan_trip_async(request)
    
    【初始化流程】
    1. 首次调用：创建实例 → 调用 initialize() → 返回
    2. 后续调用：直接返回缓存的实例

    Returns:
        LangGraphTripPlanner: 规划器实例（已初始化完成）
    """
    global _planner_agent
    
    if _planner_agent is None:
        print("[DEBUG] 创建新的 TripPlannerAgent 实例...")
        _planner_agent = LangGraphTripPlanner()
        await _planner_agent.initialize()
        print("[DEBUG] TripPlannerAgent 实例创建完成")
    else:
        print("[DEBUG] 复用已有的 TripPlannerAgent 实例")
    
    return _planner_agent
