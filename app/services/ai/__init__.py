"""
AI服务模块初始化
"""

from .base import AIProvider, AIConfig, AIServiceFactory, TranscriptionResult, LLMResponse
from .manager import ai_service_manager, AIServiceConfig
from .openai_provider import register_openai_providers
from .anthropic_provider import register_anthropic_providers


async def initialize_ai_services(config: AIConfig):
    """初始化AI服务"""
    # 注册提供商
    register_openai_providers()
    register_anthropic_providers()
    
    # 启动服务
    await ai_service_manager.initialize(config)


async def shutdown_ai_services():
    """关闭AI服务"""
    await ai_service_manager.shutdown()


__all__ = [
    'AIProvider',
    'AIConfig', 
    'AIServiceFactory',
    'TranscriptionResult',
    'LLMResponse',
    'ai_service_manager',
    'AIServiceConfig',
    'initialize_ai_services',
    'shutdown_ai_services'
]