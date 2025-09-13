"""
Anthropic Claude API集成实现
提供Claude LLM服务支持
"""

import io
import json
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
import httpx

from .base import (
    STTProvider, LLMProvider, AIProvider, 
    TranscriptionResult, LLMResponse
)


class AnthropicSTTProvider(STTProvider):
    """
    Anthropic STT服务（占位符实现）
    注意：Anthropic目前不提供STT服务，这里仅作为架构示例
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
    
    def _get_provider_name(self) -> AIProvider:
        return AIProvider.ANTHROPIC
    
    async def transcribe_audio(
        self, 
        audio_file: io.BytesIO,
        language: str = "auto",
        **kwargs
    ) -> TranscriptionResult:
        """
        Anthropic STT转录（占位符实现）
        实际使用时需要集成其他STT服务或抛出不支持错误
        """
        raise NotImplementedError("Anthropic does not provide STT service")
    
    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: str = "auto",
        **kwargs
    ) -> AsyncGenerator[TranscriptionResult, None]:
        """流式STT转录占位符"""
        raise NotImplementedError("Anthropic does not provide STT service")
        yield  # 为了满足AsyncGenerator类型要求


class AnthropicLLMProvider(LLMProvider):
    """Anthropic Claude大语言模型服务"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", "https://api.anthropic.com")
        self.default_model = config.get("model", "claude-3-haiku-20240307")
        self.timeout = config.get("timeout", 60)
        
        # 创建HTTP客户端
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
        )
    
    def _get_provider_name(self) -> AIProvider:
        return AIProvider.ANTHROPIC
    
    def _convert_messages(self, messages: List[Dict[str, str]]) -> tuple:
        """
        转换消息格式为Claude API格式
        Claude使用system和messages的分离结构
        """
        system_message = ""
        claude_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            elif msg["role"] in ["user", "assistant"]:
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        return system_message, claude_messages
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        **kwargs
    ) -> LLMResponse:
        """Claude聊天完成"""
        try:
            system_message, claude_messages = self._convert_messages(messages)
            
            # 构建请求数据
            request_data = {
                "model": model or self.default_model,
                "messages": claude_messages,
                "max_tokens": max_tokens or 4096,
                "temperature": temperature
            }
            
            if system_message:
                request_data["system"] = system_message
            
            # 添加其他参数
            if "top_p" in kwargs:
                request_data["top_p"] = kwargs["top_p"]
            if "stop_sequences" in kwargs:
                request_data["stop_sequences"] = kwargs["stop_sequences"]
            
            # 发送请求
            response = await self.client.post(
                "/v1/messages",
                json=request_data
            )
            
            if response.status_code != 200:
                raise Exception(f"API request failed: {response.status_code} - {response.text}")
            
            data = response.json()
            
            return LLMResponse(
                content=data["content"][0]["text"] if data["content"] else "",
                model=data.get("model", model or self.default_model),
                usage={
                    "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                    "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
                    "total_tokens": (
                        data.get("usage", {}).get("input_tokens", 0) + 
                        data.get("usage", {}).get("output_tokens", 0)
                    )
                },
                finish_reason=data.get("stop_reason", "stop"),
                metadata={"id": data.get("id"), "type": data.get("type")}
            )
            
        except Exception as e:
            raise Exception(f"Anthropic LLM error: {str(e)}")
    
    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        **kwargs
    ) -> AsyncGenerator[LLMResponse, None]:
        """流式Claude聊天完成"""
        try:
            system_message, claude_messages = self._convert_messages(messages)
            
            # 构建请求数据
            request_data = {
                "model": model or self.default_model,
                "messages": claude_messages,
                "max_tokens": max_tokens or 4096,
                "temperature": temperature,
                "stream": True
            }
            
            if system_message:
                request_data["system"] = system_message
            
            # 流式请求
            async with self.client.stream(
                "POST",
                "/v1/messages",
                json=request_data
            ) as response:
                
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"Stream API request failed: {response.status_code} - {error_text}")
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # 移除"data: "前缀
                        
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            data = json.loads(data_str)
                            
                            # 处理不同类型的事件
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield LLMResponse(
                                        content=delta.get("text", ""),
                                        model=model or self.default_model,
                                        usage={},  # 流式响应中usage在最后
                                        finish_reason="",
                                        metadata={
                                            "is_stream": True,
                                            "event_type": data.get("type")
                                        }
                                    )
                                    
                        except json.JSONDecodeError:
                            continue  # 跳过无效的JSON行
                            
        except Exception as e:
            raise Exception(f"Anthropic stream LLM error: {str(e)}")
    
    async def enhance_notes(
        self,
        original_notes: str,
        transcription: str,
        template_prompt: str = None,
        **kwargs
    ) -> str:
        """使用Claude增强笔记内容"""
        
        system_prompt = template_prompt or """
你是一个专业的会议记录助手。请基于用户的简要笔记和完整的会议转录内容，
生成一份结构化、清晰的会议纪要。

要求：
1. 保留用户笔记的核心要点
2. 从转录中补充重要细节
3. 使用清晰的结构组织内容（标题、要点、行动项等）
4. 提取关键决策和行动项
5. 保持专业且易读的语言风格

请直接输出增强后的会议纪要，使用Markdown格式。
"""
        
        user_prompt = f"""
请基于以下内容生成增强的会议纪要：

## 用户原始笔记：
{original_notes}

## 完整会议转录：
{transcription}
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.chat_completion(
            messages=messages,
            temperature=kwargs.get("temperature", 0.3),
            max_tokens=kwargs.get("max_tokens", 4096),
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
你是一个会议内容分析助手。请基于提供的会议内容准确回答用户的问题。

要求：
1. 只基于提供的会议内容回答，不要添加会议外的信息
2. 如果会议内容中没有相关信息，请明确说明"会议内容中未涉及此问题"
3. 引用具体的会议片段来支持你的答案
4. 保持客观、准确和简洁
5. 如果问题模糊，请先澄清理解，再提供答案

请用友好专业的语气回答。
"""
        
        user_prompt = f"""
## 会议内容：
{context}

## 问题：
{question}
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.chat_completion(
            messages=messages,
            temperature=kwargs.get("temperature", 0.1),
            max_tokens=kwargs.get("max_tokens", 2048),
            **kwargs
        )
        
        return response.content
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.client.aclose()


# 注册Anthropic提供商到工厂
def register_anthropic_providers():
    """注册Anthropic服务提供商"""
    from .base import AIServiceFactory
    
    # 注意：Anthropic不提供STT服务，这里仅注册LLM
    AIServiceFactory.register_llm_provider(
        AIProvider.ANTHROPIC, 
        AnthropicLLMProvider
    )
    
    # 如果需要STT支持，可以考虑：
    # 1. 使用其他STT服务 + Anthropic LLM的组合
    # 2. 在应用层面处理STT fallback到其他提供商
    # AIServiceFactory.register_stt_provider(
    #     AIProvider.ANTHROPIC, 
    #     AnthropicSTTProvider  # 这会抛出NotImplementedError
    # )