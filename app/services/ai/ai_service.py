"""
AI服务管理器
统一管理STT和LLM服务
"""

from typing import Dict, Any, Optional
import asyncio
import io

from .base import (
    AIServiceFactory, AIProvider, STTProvider, LLMProvider,
    TranscriptionResult, LLMResponse, AIConfig
)
from .openai_provider import register_openai_providers


class AIService:
    """AI服务管理器"""
    
    def __init__(self, config: AIConfig):
        self.config = config
        
        # 注册所有提供商
        register_openai_providers()
        
        # 初始化服务提供商
        self.stt_provider: STTProvider = AIServiceFactory.create_stt_provider(
            config.stt_provider, 
            config.stt_config
        )
        self.llm_provider: LLMProvider = AIServiceFactory.create_llm_provider(
            config.llm_provider,
            config.llm_config
        )
    
    # STT相关方法
    async def transcribe_audio(
        self, 
        audio_file: io.BytesIO,
        language: str = "auto",
        **kwargs
    ) -> TranscriptionResult:
        """转录音频文件"""
        return await self.stt_provider.transcribe_audio(
            audio_file, language, **kwargs
        )
    
    async def transcribe_stream(
        self,
        audio_stream,
        language: str = "auto",
        **kwargs
    ):
        """实时转录音频流"""
        async for result in self.stt_provider.transcribe_stream(
            audio_stream, language, **kwargs
        ):
            yield result
    
    # LLM相关方法
    async def chat_completion(
        self,
        messages,
        model: str = None,
        **kwargs
    ) -> LLMResponse:
        """聊天完成"""
        return await self.llm_provider.chat_completion(
            messages, 
            model or self.config.default_llm_model,
            **kwargs
        )
    
    async def stream_chat_completion(
        self,
        messages,
        model: str = None,
        **kwargs
    ):
        """流式聊天完成"""
        async for response in self.llm_provider.stream_chat_completion(
            messages, 
            model or self.config.default_llm_model,
            **kwargs
        ):
            yield response
    
    async def enhance_notes(
        self,
        original_notes: str,
        transcription: str,
        template_prompt: str = None,
        **kwargs
    ) -> str:
        """增强笔记内容"""
        return await self.llm_provider.enhance_notes(
            original_notes,
            transcription,
            template_prompt,
            **kwargs
        )
    
    async def answer_question(
        self,
        question: str,
        context: str,
        **kwargs
    ) -> str:
        """基于上下文回答问题"""
        return await self.llm_provider.answer_question(
            question,
            context,
            **kwargs
        )
    
    def get_provider_info(self) -> Dict[str, str]:
        """获取当前使用的提供商信息"""
        return {
            "stt_provider": self.stt_provider.provider.value,
            "llm_provider": self.llm_provider.provider.value
        }


# 全局AI服务实例
ai_service: Optional[AIService] = None


def init_ai_service(config: AIConfig):
    """初始化AI服务"""
    global ai_service
    ai_service = AIService(config)


def get_ai_service() -> AIService:
    """获取AI服务实例"""
    if ai_service is None:
        raise RuntimeError("AI service not initialized. Call init_ai_service() first.")
    return ai_service