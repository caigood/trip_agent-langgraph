"""
LLM 服务模块

【本模块的作用】
负责创建和管理大语言模型（LLM）的客户端实例。
使用 LangChain 的 ChatOpenAI 类，兼容 OpenAI API 格式的各种模型（如 GPT、Claude、国产大模型等）。

【为什么用 ChatOpenAI？】
1. 兼容性好：支持所有 OpenAI API 格式的服务
2. 功能强大：支持 bind_tools() 方法绑定工具，让模型可以调用外部工具
3. 生态丰富：与 LangChain/LangGraph 完美集成

"""

import os
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from ..config import get_settings

# =============================================================================
# 全局变量：缓存 LLM 实例（单例模式）
# =============================================================================

# _llm_instance 缓存 LLM 客户端，避免重复创建
_llm_instance: BaseChatModel | None = None


# =============================================================================
# 配置解析函数
# =============================================================================

def _resolve_openai_base_url(settings) -> str:
    """
    解析并规范化 OpenAI Base URL
    
    【优先级】（从高到低）
    1. 环境变量 LLM_BASE_URL
    2. 环境变量 OPENAI_BASE_URL
    3. 配置文件中的 openai_base_url
    
    【为什么要加 /v1？】
    OpenAI API 的标准路径格式是 https://xxx.com/v1/chat/completions
    如果用户配置的 URL 没有 /v1 后缀，我们自动补上
    
    Args:
        settings: 配置对象，包含各种设置项
        
    Returns:
        str: 规范化后的 base_url（以 /v1 结尾）
    """
    # 按优先级获取 Base URL
    base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or settings.openai_base_url
    
    if base_url:
        # 去掉末尾的斜杠，避免重复
        normalized = base_url.rstrip("/")
        
        # 检查是否已经包含 /v1
        # 如果没有，自动添加 /v1
        if not normalized.endswith("/v1") and "/v1/" not in normalized:
            normalized = f"{normalized}/v1"
        
        # 同步设置到环境变量（确保其他库也能读取到）
        os.environ["LLM_BASE_URL"] = normalized
        os.environ["OPENAI_BASE_URL"] = normalized
        
        return normalized
    
    return ""


def _resolve_openai_api_key(settings) -> str:
    """
    获取 API Key
    """
    return os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or settings.openai_api_key


def _resolve_openai_model(settings) -> str:
    """
    获取模型名称    
    """
    return os.getenv("LLM_MODEL_ID") or os.getenv("OPENAI_MODEL") or settings.openai_model


# =============================================================================
# LLM 实例获取函数
# =============================================================================

def get_llm() -> BaseChatModel:
    """
    获取 LLM 客户端实例（单例模式）
   
    返回的 ChatOpenAI 实例支持：
    1. 直接调用: llm.invoke([messages]) 获取回复
    2. 绑定工具: llm.bind_tools(tools) 让模型可以调用工具
    3. 流式输出: llm.stream([messages]) 逐字返回

    Returns:
        BaseChatModel: LangChain 聊天模型实例
    """
    global _llm_instance
    
    # 【单例模式】如果已经创建过，直接返回缓存的实例
    if _llm_instance is None:
        print("[DEBUG] 正在创建 LLM 实例...")
        
        # 读取配置
        settings = get_settings()
        base_url = _resolve_openai_base_url(settings)
        api_key = _resolve_openai_api_key(settings) or ""
        model = _resolve_openai_model(settings)
        
        print(f"[DEBUG] 模型: {model}")
        print(f"[DEBUG] Base URL: {base_url}")
        print(f"[DEBUG] API Key: {'已配置' if api_key else '未配置'}")
        
        # 创建 ChatOpenAI 实例
        # 这是 LangChain 提供的 OpenAI 兼容客户端
        _llm_instance = ChatOpenAI(
            model=model,           # 模型名称
            api_key=api_key,       # API 密钥
            base_url=base_url if base_url else None,  # API 基础地址
        )
        
        print("[DEBUG] LLM 实例创建成功")
    
    return _llm_instance
