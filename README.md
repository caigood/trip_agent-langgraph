# 🗺️ Trip Planner - LangGraph 智能旅行规划助手

基于 LangGraph 和 MCP 的智能旅行规划系统，支持多 Agent 并行协作，自动生成个性化旅行行程。

## ✨ 功能特性

- 🤖 **多 Agent 协作**：景点搜索、天气查询、酒店推荐三个 Agent 并行执行
- 🔧 **MCP 工具集成**：通过 MCP 协议集成高德地图 API
- 📊 **结构化输出**：生成包含景点、餐饮、预算的完整 JSON 行程
- 🚀 **异步架构**：全异步设计，支持高并发请求
- 🎨 **现代前端**：Vue 3 + TypeScript + Vite

## 🛠️ 技术栈

| 层级 | 技术 |
|-----|------|
| **后端框架** | FastAPI |
| **工作流引擎** | LangGraph |
| **工具协议** | MCP (Model Context Protocol) |
| **地图服务** | 高德地图 API |
| **大模型** | OpenAI / 兼容 API |
| **前端框架** | Vue 3 + TypeScript |
| **构建工具** | Vite |

## 📐 项目架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户请求                                   │
│                  "帮我规划北京3日游"                              │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI 路由层                                │
│                     (app/api/routes/trip.py)                     │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   TripPlannerAgent                               │
│              (app/agents/trip_planner_agent.py)                  │
│                                                                 │
│  职责：初始化 LLM、获取 MCP 工具、构建 LangGraph 工作流           │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LangGraph 工作流                               │
│                      (app/graph.py)                              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                      START                               │   │
│  │                         │                                │   │
│  │         ┌───────────────┼───────────────┐               │   │
│  │         │               │               │               │   │
│  │         ▼               ▼               ▼               │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐    │   │
│  │  │ Attraction   │ │   Weather    │ │    Hotel     │    │   │
│  │  │    Agent     │ │    Agent     │ │    Agent     │    │   │
│  │  │              │ │              │ │              │    │   │
│  │  │ Agent↔Tools  │ │ Agent↔Tools  │ │ Agent↔Tools  │    │   │
│  │  │  (ReAct)     │ │  (ReAct)     │ │  (ReAct)     │    │   │
│  │  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘    │   │
│  │         │               │               │               │   │
│  │         └───────────────┼───────────────┘               │   │
│  │                         │                                │   │
│  │                         ▼                                │   │
│  │                  ┌──────────────┐                       │   │
│  │                  │   Planner    │                       │   │
│  │                  │    Agent     │                       │   │
│  │                  └──────┬───────┘                       │   │
│  │                         │                                │   │
│  │                         ▼                                │   │
│  │                        END                               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  每个 Agent 是独立的子图，支持 ReAct 循环                         │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      服务层                                      │
│                                                                 │
│  ┌─────────────────────┐    ┌─────────────────────┐            │
│  │    llm_service      │    │    amap_service     │            │
│  │                     │    │                     │            │
│  │  - LLM 初始化       │    │  - MCP 连接         │            │
│  │  - API 配置         │    │  - 高德地图工具      │            │
│  └─────────────────────┘    └─────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 目录结构

```
trip-langgraph-V3/
├── app/                          # 后端应用
│   ├── __init__.py
│   ├── config.py                 # 配置管理（环境变量）
│   ├── graph.py                  # LangGraph 工作流定义
│   │
│   ├── agents/                   # Agent 封装层
│   │   ├── __init__.py
│   │   └── trip_planner_agent.py # 旅行规划 Agent 入口
│   │
│   ├── api/                      # API 层
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI 应用入口
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── trip.py           # 旅行规划 API 路由
│   │
│   ├── models/                   # 数据模型
│   │   ├── __init__.py
│   │   └── schemas.py            # Pydantic 模型定义
│   │
│   └── services/                 # 服务层
│       ├── __init__.py
│       ├── llm_service.py        # LLM 服务（初始化、配置）
│       └── amap_service.py       # 高德地图 MCP 服务
│
├── frontend/                     # 前端应用
│   ├── src/
│   │   ├── main.ts               # 入口文件
│   │   ├── App.vue               # 根组件
│   │   ├── services/
│   │   │   └── api.ts            # API 调用封装
│   │   ├── types/
│   │   │   └── index.ts          # TypeScript 类型定义
│   │   └── views/
│   │       ├── Home.vue          # 首页（输入表单）
│   │       └── Result.vue        # 结果页（行程展示）
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── .env.example                  # 环境变量示例
├── .gitignore                    # Git 忽略规则
├── requirements.txt              # Python 依赖
├── run_dev.py                    # 开发服务器启动脚本
└── README.md                     # 项目文档
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-username/trip-langgraph.git
cd trip-langgraph
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的 API Key：

```env
# 高德地图 API Key
AMAP_API_KEY=your_amap_api_key_here

# 大模型 API 配置
LLM_API_KEY=your_llm_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_ID=gpt-4o-mini
```

### 3. 安装依赖

```bash
# Python 依赖
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
cd ..
```

### 4. 启动服务

```bash
# 方式一：同时启动前后端
python run_dev.py

# 方式二：分别启动
# 后端（端口 8001）
uvicorn app.api.main:app --host 0.0.0.0 --port 8001 --reload

# 前端（端口 5173）
cd frontend
npm run dev
```

### 5. 访问应用

打开浏览器访问：http://localhost:5173

## 📡 API 文档

### POST /api/trip/plan

生成旅行计划

**请求体：**

```json
{
  "city": "北京",
  "start_date": "2024-01-01",
  "end_date": "2024-01-03",
  "preferences": "历史文化",
  "budget": "中等",
  "transportation": "地铁",
  "accommodation": "酒店"
}
```

**响应：**

```json
{
  "city": "北京",
  "start_date": "2024-01-01",
  "end_date": "2024-01-03",
  "days": [
    {
      "date": "2024-01-01",
      "day_index": 0,
      "description": "故宫-天安门广场一日游",
      "attractions": [...],
      "meals": [...]
    }
  ],
  "weather_info": [...],
  "budget": {
    "total": 2500,
    "breakdown": "..."
  }
}
```

### GET /api/health

健康检查

## ⚙️ 配置说明

| 环境变量 | 说明 | 必填 |
|---------|------|------|
| `AMAP_API_KEY` | 高德地图 API Key | ✅ |
| `LLM_API_KEY` | 大模型 API Key | ✅ |
| `LLM_BASE_URL` | 大模型 API 地址 | ✅ |
| `LLM_MODEL_ID` | 模型 ID | ✅ |
| `DEBUG` | 调试模式 | ❌ |

## 🔧 开发说明

### LangGraph 工作流

本项目使用 LangGraph 构建多 Agent 工作流：

1. **并行执行**：景点、天气、酒店三个 Agent 同时运行
2. **ReAct 模式**：每个 Agent 内部支持多轮工具调用
3. **条件边**：根据 LLM 输出动态决定是否继续调用工具
4. **子图封装**：每个 Agent 是独立的子图，消息流互不干扰

### MCP 工具集成

通过 `langchain-mcp-adapters` 集成高德地图 MCP 服务：

- 支持 SSE 传输方式
- 支持并行工具调用
- 自动处理工具生命周期

## 📄 许可证

MIT License

## 🙏 致谢

- [LangGraph](https://github.com/langchain-ai/langgraph)
- [LangChain](https://github.com/langchain-ai/langchain)
- [FastAPI](https://fastapi.tiangolo.com/)
- [高德地图](https://lbs.amap.com/)
  -helloagent datewhale 项目组
