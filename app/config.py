"""配置管理

集中管理应用配置，支持 .env 与环境变量覆盖，并提供校验与打印功能。
"""

import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # 应用配置
    app_name: str = "LangGraph旅行助手"
    app_version: str = "1.0.0"
    debug: bool = False

    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS 配置
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # 高德地图 API Key
    amap_api_key: str = ""

    # LLM 配置
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = ""

    # 日志配置
    log_level: str = "INFO"

    class Config:
        # .env 文件仅作为默认值来源，环境变量优先级更高
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    def get_cors_origins_list(self) -> List[str]:
        # 将逗号分隔的 CORS 配置转为列表
        return [origin.strip() for origin in self.cors_origins.split(",")]

settings = Settings()

def get_settings() -> Settings:
    # 返回全局唯一的 Settings 实例
    return settings

def validate_config():
    # 校验关键配置是否缺失，并给出告警信息
    errors = []
    warnings = []
    if not settings.amap_api_key:
        warnings.append("AMAP_API_KEY未配置,地图功能可能不可用")
    llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not llm_api_key:
        warnings.append("LLM_API_KEY或OPENAI_API_KEY未配置,LLM功能可能不可用")
    if errors:
        error_msg = "配置错误:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(error_msg)
    if warnings:
        print("\n⚠️  配置警告:")
        for w in warnings:
            print(f"  - {w}")
    return True

def print_config():
    # 打印关键配置，便于启动时排查环境问题
    print(f"应用名称: {settings.app_name}")
    print(f"版本: {settings.app_version}")
    print(f"服务器: {settings.host}:{settings.port}")
    print(f"高德地图API Key: {'已配置' if settings.amap_api_key else '未配置'}")
    llm_api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    llm_base_url = os.getenv("LLM_BASE_URL") or settings.openai_base_url
    llm_model = os.getenv("LLM_MODEL_ID") or settings.openai_model
    print(f"LLM API Key: {'已配置' if llm_api_key else '未配置'}")
    print(f"LLM Base URL: {llm_base_url}")
    print(f"LLM Model: {llm_model}")
    print(f"日志级别: {settings.log_level}")
