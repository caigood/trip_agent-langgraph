"""
旅行规划 LangGraph 工作流（标准 ToolNode 方式）

【什么是 LangGraph？】
LangGraph 是 LangChain 的扩展库，用于构建复杂的多智能体工作流。
它使用"状态机"的概念，让多个 AI Agent 按照定义好的流程协作完成任务。

【本模块的核心概念】
1. State（状态）: 工作流的共享数据容器，所有节点都可以读写
2. Node（节点）: 执行特定任务的函数（如搜索景点、查询天气）
3. Edge（边）: 定义节点之间的流转关系

【并行执行设计 - 标准 ToolNode 方式】
每个 Agent 是一个独立的子图，包含自己的 ToolNode，实现真正的并行执行。

┌─────────────────────────────────────────────────────────────────┐
│  START                                                          │
│     │                                                           │
│     ├─────→ Attraction Agent (子图)                             │
│     │           │                                               │
│     │           Agent ←──→ ToolNode                             │
│     │           │                                               │
│     │           └──→ attraction_response                        │
│     │                                                           │
│     ├─────→ Weather Agent (子图)                                │
│     │           │                                               │
│     │           Agent ←──→ ToolNode                             │
│     │           │                                               │
│     │           └──→ weather_response                           │
│     │                                                           │
│     └─────→ Hotel Agent (子图)                                  │
│                 │                                               │
│                 Agent ←──→ ToolNode                             │
│                 │                                               │
│                 └──→ hotel_response                             │
│                                                                 │
│     ────────────────────────────────────────────────────────── │
│                                                                 │
│     Planner ←── 汇聚所有 response                               │
│         │                                                       │
│         └──→ END                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

【关于工具调用的说明】
本版本使用 LangGraph 标准的 ToolNode 和条件边。
每个 Agent 子图内部使用 ReAct 模式：Agent ↔ ToolNode 循环。
"""

from typing import Dict, Any, List, TypedDict, Optional, Annotated
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from langchain_core.tools import BaseTool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, BaseMessage, SystemMessage


# =============================================================================
# 状态定义 (State)
# =============================================================================

class AgentState(TypedDict):
    """
    【单个 Agent 的状态】
    
    使用标准的 messages 列表，支持 LangGraph 的消息累积。
    add_messages 会自动合并消息列表。
    """
    #带元数据的类型注解 ，LangGraph 用它来定义 状态更新行为
    # 语法结构 Annotated[类型, 元数据1, 元数据2, ...]
    # List[BaseMessage]类型：消息列表  add_messages元数据：更新函数（reducer） 
    # add_messages 的行为
    # 新消息不是替换，而是追加到现有列表
    messages: Annotated[List[BaseMessage], add_messages]


class TripState(TypedDict):
    """
    【工作流状态定义】
    
    主图的状态，存储各个 Agent 的最终结果。
    """
    request: Dict[str, Any]
    attraction_response: Optional[str]
    weather_response: Optional[str]
    hotel_response: Optional[str]
    plan_raw: str


# =============================================================================
# 提示词模板 (Prompts)
# =============================================================================

ATTRACTION_SYSTEM_PROMPT = """你是景点搜索专家。

你的任务是搜索指定城市的景点信息。

**重要:**
- 请使用可用的工具搜索真实信息，不要编造
- 如果没有找到合适的工具，可以基于你的知识回答
- 优先搜索符合用户偏好的景点
- 获得结果后，总结景点信息并返回

请搜索{city}的景点信息，用户偏好：{preferences}。
"""

WEATHER_SYSTEM_PROMPT = """你是天气查询专家。

你的任务是查询指定城市的天气信息。

**重要:**
- 请使用可用的工具查询真实天气数据
- 如果没有天气工具，可以基于常识描述该城市 typical 的天气情况
- 获得结果后，总结天气信息并返回

请查询{city}的天气信息。
"""

HOTEL_SYSTEM_PROMPT = """你是酒店推荐专家。

你的任务是搜索指定城市的住宿信息。

**重要:**
- 请使用可用的工具搜索真实酒店/住宿信息
- 如果没有找到合适的工具，可以基于你的知识推荐住宿区域
- 考虑用户的预算和偏好
- 获得结果后，总结酒店信息并返回

请搜索{city}的住宿信息，类型：{accommodation}。
"""

PLANNER_AGENT_PROMPT = """你是行程规划专家。

**输出格式:**
严格按照以下JSON格式返回 (不要返回Markdown代码块, 直接返回JSON字符串):
{
 "city": "城市名称",
 "start_date": "YYYY-MM-DD",
 "end_date": "YYYY-MM-DD",
 "days": [
  {
   "date": "YYYY-MM-DD",
   "day_index": 0,
   "description": "当日行程概述",
   "transportation": "交通方式",
   "accommodation": "住宿地点",
   "morning": "上午行程详情",
   "afternoon": "下午行程详情",
   "evening": "晚上行程详情",
   "attractions": [
    {
     "name": "景点名称",
     "description": "景点描述",
     "visit_duration": 120,
     "ticket_price": 60,
     "location": {
      "latitude": 39.9,
      "longitude": 116.4
     },
     "address": "景点地址"
    }
   ],
   "meals": [
    {
     "name": "餐厅名称",
     "type": "lunch",
     "description": "餐饮描述",
     "estimated_cost": 100,
     "location": {
      "latitude": 39.9,
      "longitude": 116.4
     },
     "address": "餐厅地址"
    }
   ]
  }
 ],
 "weather_info": [
  {
   "date": "YYYY-MM-DD",
   "day_weather": "白天天气",
   "night_weather": "夜间天气",
   "day_temp": 25,
   "night_temp": 15,
   "wind_direction": "风向",
   "wind_power": "风力"
  }
 ],
 "overall_suggestions": "总体建议",
 "budget": {
  "total_attractions": 500,
  "total_hotels": 1000,
  "total_meals": 800,
  "total_transportation": 200,
  "total": 2500,
  "breakdown": "预算明细说明"
 }
}

**注意:**
1. days数组长度必须等于旅行天数
2. day_index从0开始递增
3. weather_info数组长度最好覆盖每天
4. 所有金额字段为整数(int)
5. 请基于提供的天气、景点和酒店信息进行规划
6. **重要**: 景点信息中的 `location` 字段可能为 "经度,纬度" 格式的字符串(例如 "116.397,39.918")。请务必将其解析为 `{"latitude": 39.918, "longitude": 116.397}` 的JSON对象格式填入 `attractions` 列表中。如果不包含位置信息，请勿填入该景点。
7. **重要**: 务必为每天安排 `attractions` (景点) 和 `meals` (餐饮)。请从提供的景点信息中选择合适的POI填入。如果没有具体的餐饮POI，请根据当地特色推荐餐厅名称和类型。
8. 确保 `attractions` 列表不为空，除非确实没有搜索到任何景点。
"""


# =============================================================================
# Agent 子图构建函数
# =============================================================================

def _should_continue(state: AgentState) -> str:
    """
    【条件边：判断是否继续调用工具】
    
    检查最后一条消息是否有工具调用。
    - 如果有 tool_calls，返回 "tools" 继续执行工具
    - 如果没有，返回 END 结束
    """
    messages = state["messages"]
    last_message = messages[-1]
    # 双重条件判断：前面检查对象是否有 tool_calls 属性（不是所有消息类型都有这个属性），后面检查tool_calls是否为空列表
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


def _create_agent_node(
    llm_with_tools: BaseChatModel,
    tools: List[BaseTool],
    prompt: str,
    output_field: str
):
    """
    【通用 Agent 节点工厂】
    
    创建一个独立的 Agent 子图，处理特定任务。
    
    【设计模式】
    使用闭包封装 Agent 子图，每个 Agent 有独立的消息流。
    
    Args:
        llm_with_tools: 绑定了工具的 LLM
        tools: 工具列表
        prompt: 提示词（支持 {city}, {preferences}, {accommodation} 占位符）
        output_field: 输出字段名（如 "attraction_response"）
        
    Returns:
        异步节点函数
    """
    async def node_func(state: TripState):
        # - ToolNode 是 LangGraph 提供的工具执行器
        # - 它会自动处理：
        # - 从 AIMessage.tool_calls 中提取工具调用
        # - 执行对应的工具
        # - 返回 ToolMessage 结果
        tool_node = ToolNode(tools)
        # 定义 Agent 内部节点函数
        # 作用 ：定义 LLM 调用节点
        # - 输入： AgentState （包含消息列表）
        # - 处理：调用绑定了工具的 LLM
        # - 输出：返回 LLM 的响应（可能是文本或工具调用）
        #- 下面函数只是在这里定义，没有执行，后面compiled.ainvoke才执行子图
        async def agent_node_inner(agent_state: AgentState):
            response = await llm_with_tools.ainvoke(agent_state["messages"])
            return {"messages": [response]}
        
        subgraph = StateGraph(AgentState)
        subgraph.add_node("agent", agent_node_inner)
        subgraph.add_node("tools", tool_node)
        subgraph.add_edge(START, "agent")
        subgraph.add_conditional_edges("agent", _should_continue, {"tools": "tools", END: END})
        subgraph.add_edge("tools", "agent")
        
        compiled = subgraph.compile()
        
        request = state["request"]
        #将请求里面的关键词替换到提示词里面
        formatted_prompt = prompt.format(
            #get里面第二个参数是默认值，第一个key取不到时，返回第二个参数的字符串
            city=request.get("city", ""),
            preferences=request.get("preferences", "著名景点"),
            accommodation=request.get("accommodation", "酒店")
        )
        
        initial_messages = [HumanMessage(content=formatted_prompt)]
        
        result = await compiled.ainvoke({"messages": initial_messages})
        final_content = result["messages"][-1].content
        
        return {output_field: final_content}
    
    return node_func


def _create_planner_node(llm: BaseChatModel):
    """
    【行程规划节点工厂】
    
    整合所有信息生成最终行程。
    """
    async def node_func(state: TripState):
        request = state["request"]
        
        attraction = state.get("attraction_response", "")
        weather = state.get("weather_response", "")
        hotel = state.get("hotel_response", "")
        
        planner_query = f"""
        请根据以下信息生成{request.get('city')}的{request.get('travel_days')}日旅行计划:

        **用户需求:**
        - 目的地: {request.get('city')}
        - 日期: {request.get('start_date')} 至 {request.get('end_date')}
        - 天数: {request.get('travel_days')}天
        - 偏好: {request.get('preferences')}
        - 预算: {request.get('budget')}
        - 交通方式: {request.get('transportation')}
        - 住宿类型: {request.get('accommodation')}

        **景点信息:**
        {attraction}

        **天气信息:**
        {weather}

        **酒店信息:**
        {hotel}

        请生成详细的旅行计划,包括每天的景点安排、餐饮推荐、住宿信息和预算明细。
        """
        
        messages = [
            SystemMessage(content=PLANNER_AGENT_PROMPT),
            HumanMessage(content=planner_query)
        ]
        
        response = await llm.ainvoke(messages)
        
        return {"plan_raw": response.content or ""}
    
    return node_func


# =============================================================================
# 图构建函数
# =============================================================================

def build_trip_graph(llm_with_tools: BaseChatModel, llm: BaseChatModel, tools: List[BaseTool]):
    """
    【构建旅行规划工作流图 - 标准 ToolNode 方式】
    
    这是 LangGraph 的标准做法：
    1. 每个 Agent 是一个独立的子图
    2. 子图内部使用 ReAct 模式：Agent ↔ ToolNode 循环
    3. 主图并行执行三个 Agent 子图
    4. 最后汇聚到 Planner 节点
    
    【为什么这样设计？】
    - 每个 Agent 子图有独立的消息流，互不干扰
    - 使用标准的 ToolNode 和条件边
    - 支持真正的并行执行
    - 符合 LangGraph 的最佳实践
    
    Args:
        llm_with_tools: 绑定了工具的 LLM 实例
        llm: 未绑定工具的 LLM 实例
        tools: LangChain 工具列表
        
    Returns:
        CompiledGraph: 编译后的 LangGraph 图实例
    """
    graph = StateGraph(TripState)
    
    graph.add_node("attraction_agent", _create_agent_node(
        llm_with_tools, tools,
        ATTRACTION_SYSTEM_PROMPT,
        "attraction_response"
    ))
    
    graph.add_node("weather_agent", _create_agent_node(
        llm_with_tools, tools,
        WEATHER_SYSTEM_PROMPT,
        "weather_response"
    ))
    
    graph.add_node("hotel_agent", _create_agent_node(
        llm_with_tools, tools,
        HOTEL_SYSTEM_PROMPT,
        "hotel_response"
    ))
    
    graph.add_node("planner", _create_planner_node(llm))
    
    graph.add_edge(START, "attraction_agent")
    graph.add_edge(START, "weather_agent")
    graph.add_edge(START, "hotel_agent")
    
    graph.add_edge("attraction_agent", "planner")
    graph.add_edge("weather_agent", "planner")
    graph.add_edge("hotel_agent", "planner")
    
    graph.add_edge("planner", END)
    
    return graph.compile()
