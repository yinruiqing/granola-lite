"""
OpenAI API集成实现
包含Whisper STT和GPT LLM服务
"""

import io
import json
import asyncio
import httpx
from typing import Dict, Any, List, Optional, AsyncGenerator
from openai import AsyncOpenAI
import openai

from .base import (
    STTProvider, LLMProvider, AIProvider, 
    TranscriptionResult, LLMResponse
)


class OpenAISTTProvider(STTProvider):
    """OpenAI Whisper语音转录服务"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # 构建代理配置
        http_client = None
        if config.get("http_proxy") or config.get("https_proxy"):
            proxies = {}
            if config.get("http_proxy"):
                proxies["http://"] = config.get("http_proxy")
            if config.get("https_proxy"):
                proxies["https://"] = config.get("https_proxy")
            
            # 添加代理认证
            auth = None
            if config.get("proxy_auth"):
                username, password = config.get("proxy_auth").split(":")
                auth = (username, password)
            
            http_client = httpx.AsyncClient(
                proxies=proxies,
                auth=auth,
                timeout=config.get("timeout", 60)
            )
        
        self.client = AsyncOpenAI(
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),  # 支持自定义endpoint
            timeout=config.get("timeout", 60),
            http_client=http_client
        )
        self.default_model = config.get("model", "whisper-1")
    
    def _get_provider_name(self) -> AIProvider:
        return AIProvider.OPENAI
    
    async def transcribe_audio(
        self, 
        audio_file: io.BytesIO,
        language: str = "auto",
        **kwargs
    ) -> TranscriptionResult:
        """使用Whisper API转录音频"""
        try:
            # 准备参数
            transcription_params = {
                "model": kwargs.get("model", self.default_model),
                "response_format": "verbose_json",  # 获取详细信息
                "timestamp_granularities": ["segment"]
            }
            
            # 设置语言
            if language != "auto":
                transcription_params["language"] = language
            
            # 其他可选参数
            if "temperature" in kwargs:
                transcription_params["temperature"] = kwargs["temperature"]
            if "prompt" in kwargs:
                transcription_params["prompt"] = kwargs["prompt"]
            
            # 调用API
            response = await self.client.audio.transcriptions.create(
                file=audio_file,
                **transcription_params
            )
            
            # 解析结果
            segments = []
            if hasattr(response, 'segments') and response.segments:
                segments = [
                    {
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text,
                        "confidence": getattr(seg, 'confidence', 1.0)
                    }
                    for seg in response.segments
                ]
            
            return TranscriptionResult(
                text=response.text,
                confidence=1.0,  # OpenAI不提供整体置信度
                language=getattr(response, 'language', language),
                segments=segments
            )
            
        except Exception as e:
            raise Exception(f"OpenAI STT error: {str(e)}")
    
    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: str = "auto",
        **kwargs
    ) -> AsyncGenerator[TranscriptionResult, None]:
        """
        实时转录音频流
        注意：OpenAI目前不支持真正的流式转录，这里使用分块处理
        """
        buffer = io.BytesIO()
        chunk_size = kwargs.get("chunk_duration", 5)  # 5秒分块
        
        async for audio_chunk in audio_stream:
            buffer.write(audio_chunk)
            
            # 当缓冲区足够大时，进行转录
            if buffer.tell() > chunk_size * 16000 * 2:  # 假设16kHz, 16bit
                buffer.seek(0)
                
                try:
                    result = await self.transcribe_audio(
                        buffer, language=language, **kwargs
                    )
                    yield result
                except Exception as e:
                    # 记录错误但继续处理
                    print(f"Stream transcription error: {e}")
                
                # 重置缓冲区
                buffer = io.BytesIO()


class OpenAILLMProvider(LLMProvider):
    """OpenAI GPT大语言模型服务"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # 构建代理配置
        http_client = None
        if config.get("http_proxy") or config.get("https_proxy"):
            proxies = {}
            if config.get("http_proxy"):
                proxies["http://"] = config.get("http_proxy")
            if config.get("https_proxy"):
                proxies["https://"] = config.get("https_proxy")
            
            # 添加代理认证
            auth = None
            if config.get("proxy_auth"):
                username, password = config.get("proxy_auth").split(":")
                auth = (username, password)
            
            http_client = httpx.AsyncClient(
                proxies=proxies,
                auth=auth,
                timeout=config.get("timeout", 60)
            )
        
        self.client = AsyncOpenAI(
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            timeout=config.get("timeout", 60),
            http_client=http_client
        )
        self.default_model = config.get("model", "gpt-4o-mini")
    
    def _get_provider_name(self) -> AIProvider:
        return AIProvider.OPENAI
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        **kwargs
    ) -> LLMResponse:
        """GPT聊天完成"""
        try:
            response = await self.client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                finish_reason=response.choices[0].finish_reason,
                metadata={"id": response.id}
            )
            
        except Exception as e:
            raise Exception(f"OpenAI LLM error: {str(e)}")
    
    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        **kwargs
    ) -> AsyncGenerator[LLMResponse, None]:
        """流式GPT聊天完成"""
        try:
            stream = await self.client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield LLMResponse(
                        content=chunk.choices[0].delta.content,
                        model=chunk.model,
                        usage={},  # 流式响应中usage信息在最后
                        finish_reason=chunk.choices[0].finish_reason,
                        metadata={"id": chunk.id, "is_stream": True}
                    )
                    
        except Exception as e:
            raise Exception(f"OpenAI stream LLM error: {str(e)}")
    
    async def enhance_notes(
        self,
        original_notes: str,
        transcription: str,
        template_prompt: str = None,
        **kwargs
    ) -> str:
        """使用GPT增强笔记内容"""
        
        # 构建提示
        system_prompt = template_prompt or """
你是一个专业的会议记录助手。请基于用户的简要笔记和完整的会议转录内容，
生成一份结构化、清晰的会议纪要。

要求：
1. 保留用户笔记的核心要点
2. 从转录中补充重要细节
3. 使用清晰的结构组织内容
4. 提取行动项和关键决策
5. 使用用户笔记的语言风格

请直接输出增强后的笔记，不要添加解释。
"""
        
        user_prompt = f"""
原始笔记：
{original_notes}

会议转录：
{transcription}
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.chat_completion(
            messages=messages,
            temperature=kwargs.get("temperature", 0.3),
            **kwargs
        )
        
        return response.content
    
    async def answer_question(
        self,
        question: str,
        context: str,
        **kwargs
    ) -> str:
        """基于会议内容回答问题"""
        
        system_prompt = """
你是一个会议内容分析助手。请基于提供的会议内容回答用户的问题。

要求：
1. 只基于提供的会议内容回答
2. 如果会议内容中没有相关信息，请明确说明
3. 引用具体的会议内容支持你的答案
4. 保持客观和准确

请直接回答问题，简洁明了。
"""
        
        user_prompt = f"""
会议内容：
{context}

问题：
{question}
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.chat_completion(
            messages=messages,
            temperature=kwargs.get("temperature", 0.1),
            **kwargs
        )
        
        return response.content


# 注册OpenAI提供商到工厂
def register_openai_providers():
    """注册OpenAI服务提供商"""
    from .base import AIServiceFactory
    
    AIServiceFactory.register_stt_provider(
        AIProvider.OPENAI, 
        OpenAISTTProvider
    )
    AIServiceFactory.register_llm_provider(
        AIProvider.OPENAI, 
        OpenAILLMProvider
    )