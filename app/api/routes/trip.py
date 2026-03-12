"""
旅行规划 API 路由层

【本模块的作用】
这是系统的"入口层"，负责处理 HTTP 请求和响应。
遵循 FastAPI 的最佳实践，职责单一：
1. 接收并校验请求参数
2. 调用业务层（TripPlannerAgent）处理请求
3. 统一包装响应格式
4. 处理异常并返回标准错误

【API 设计】
- POST /trip/plan: 生成旅行计划（主要功能）
- GET /trip/health: 健康检查

【请求流程】
前端请求 → FastAPI 路由 → TripPlannerAgent → LangGraph → 返回结果
"""

from fastapi import APIRouter, HTTPException
from ...models.schemas import TripRequest, TripPlanResponse
from ...agents.trip_planner_agent import get_trip_planner_agent

# =============================================================================
# 路由器定义
# =============================================================================

router = APIRouter(prefix="/trip", tags=["旅行规划"])


# =============================================================================
# 生成旅行计划接口
# =============================================================================

@router.post(
    "/plan",
    response_model=TripPlanResponse,
    summary="生成旅行计划",
    description="根据用户输入的旅行需求，生成详细的旅行计划"
)
async def plan_trip(request: TripRequest):
    """
    【处理流程】
    1. 接收并自动校验请求参数（FastAPI + Pydantic）
    2. 获取 TripPlannerAgent 实例（单例）
    3. 调用 plan_trip_async() 生成计划
    4. 包装为统一响应格式返回
    
    Args:
        request: TripRequest 对象，包含用户的旅行需求
    Returns:
        TripPlanResponse: 统一响应格式，包含生成的旅行计划
    """
    print(f"\n{'='*60}")
    print(f"[DEBUG] 收到前端请求")
    print(f"[DEBUG] 城市: {request.city}")
    print(f"[DEBUG] 日期: {request.start_date} 至 {request.end_date}")
    print(f"[DEBUG] 天数: {request.travel_days}")
    print(f"[DEBUG] 偏好: {request.preferences}")
    print(f"{'='*60}\n")
    
    try:
        print("[DEBUG] 正在获取规划器实例...")
        agent = await get_trip_planner_agent()
        print("[DEBUG] 规划器实例获取成功，开始规划...")
        
        trip_plan = await agent.plan_trip_async(request)
        print(f"[DEBUG] 规划完成，返回结果")
        
        return TripPlanResponse(
            success=True,
            message="旅行计划生成成功",
            data=trip_plan
        )
        
    except Exception as e:
        print(f"[ERROR] 规划失败: {e}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"生成旅行计划失败: {str(e)}"
        )
