"""FastAPI 主应用

该文件负责完成以下职责：
- 初始化 FastAPI 应用与生命周期钩子
- 挂载 CORS 中间件与业务路由
- 提供基础信息与健康检查端点
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..config import get_settings, validate_config, print_config
from .routes import trip

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 生命周期钩子会在应用启动与关闭时触发
    # 启动阶段：打印配置并校验关键环境变量
    print("\n" + "=" * 60)
    print(f"🚀 {settings.app_name} v{settings.app_version}")
    print("=" * 60)
    print_config()
    validate_config()
    print("=" * 60 + "\n")
    yield
    # 关闭阶段：输出友好日志，便于排查服务停止原因
    print("\n" + "=" * 60)
    print("👋 应用正在关闭...")
    print("=" * 60 + "\n")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于 LangGraph 的智能旅行规划助手 API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    # 允许前端跨域访问后端 API
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 统一挂载旅行规划相关路由，路由统一加上 /api 前缀
app.include_router(trip.router, prefix="/api")

@app.get("/")
async def root():
    # 首页：提供基础信息与文档入口，便于调试与展示
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health():
    # 健康检查：用于监控与存活探针
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }
