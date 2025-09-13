"""
AI服务抽象基类
支持语音转录(STT)和大语言模型(LLM)的通用接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import io


class AIProvider(Enum):
    """AI服务提供商枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    GOOGLE = "google"
    BAIDU = "baidu"
    ALIBABA = "alibaba"


@dataclass
class TranscriptionResult:
    """语音转录结果"""
    text: str
    confidence: float
    language: str
    segments: List[Dict[str, Any]] = None  # 分段信息
    speaker: Optional[str] = None


@dataclass
class LLMResponse:
    """大语言模型响应结果"""
    content: str
    model: str
    usage: Dict[str, int]  # tokens使用情况
    finish_reason: str
    metadata: Dict[str, Any] = None


class STTProvider(ABC):
    """语音转录服务抽象基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider = self._get_provider_name()
    
    @abstractmethod
    def _get_provider_name(self) -> AIProvider:
        """获取提供商名称"""
        pass
    
    @abstractmethod
    async def transcribe_audio(
        self, 
        audio_file: io.BytesIO,
        language: str = "auto",
        **kwargs
    ) -> TranscriptionResult:
        """
        转录音频文件
        
        Args:
            audio_file: 音频文件流
            language: 语言代码，如 'zh', 'en', 'auto'
            **kwargs: 其他参数
            
        Returns:
            TranscriptionResult: 转录结果
        """
        pass
    
    @abstractmethod
    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: str = "auto",
        **kwargs
    ) -> AsyncGenerator[TranscriptionResult, None]:
        """
        实时转录音频流
        
        Args:
            audio_stream: 音频数据流
            language: 语言代码
            **kwargs: 其他参数
            
        Yields:
            TranscriptionResult: 实时转录结果
        """
        pass


class LLMProvider(ABC):
    """大语言模型服务抽象基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.provider = self._get_provider_name()
    
    @abstractmethod
    def _get_provider_name(self) -> AIProvider:
        """获取提供商名称"""
        pass
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        **kwargs
    ) -> LLMResponse:
        """
        聊天完成接口
        
        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
            
        Returns:
            LLMResponse: 模型响应
        """
        pass
    
    @abstractmethod
    async def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        **kwargs
    ) -> AsyncGenerator[LLMResponse, None]:
        """
        流式聊天完成
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
            
        Yields:
            LLMResponse: 流式响应
        """
        pass
    
    @abstractmethod
    async def enhance_notes(
        self,
        original_notes: str,
        transcription: str,
        template_prompt: str = None,
        **kwargs
    ) -> str:
        """
        增强笔记内容
        
        Args:
            original_notes: 原始笔记
            transcription: 转录内容
            template_prompt: 模板提示
            **kwargs: 其他参数
            
        Returns:
            str: 增强后的笔记
        """
        pass
    
    @abstractmethod
    async def answer_question(
        self,
        question: str,
        context: str,
        **kwargs
    ) -> str:
        """
        基于上下文回答问题
        
        Args:
            question: 问题
            context: 上下文内容
            **kwargs: 其他参数
            
        Returns:
            str: 答案
        """
        pass


@dataclass
class AIConfig:
    """AI服务配置"""
    stt_provider: AIProvider
    llm_provider: AIProvider
    stt_config: Dict[str, Any]
    llm_config: Dict[str, Any]
    default_stt_model: str = None
    default_llm_model: str = None


class AIServiceFactory:
    """AI服务工厂类"""
    
    _stt_providers = {}
    _llm_providers = {}
    
    @classmethod
    def register_stt_provider(cls, provider: AIProvider, provider_class):
        """注册STT提供商"""
        cls._stt_providers[provider] = provider_class
    
    @classmethod
    def register_llm_provider(cls, provider: AIProvider, provider_class):
        """注册LLM提供商"""
        cls._llm_providers[provider] = provider_class
    
    @classmethod
    def create_stt_provider(cls, provider: AIProvider, config: Dict[str, Any]) -> STTProvider:
        """创建STT服务实例"""
        if provider not in cls._stt_providers:
            raise ValueError(f"Unknown STT provider: {provider}")
        return cls._stt_providers[provider](config)
    
    @classmethod
    def create_llm_provider(cls, provider: AIProvider, config: Dict[str, Any]) -> LLMProvider:
        """创建LLM服务实例"""
        if provider not in cls._llm_providers:
            raise ValueError(f"Unknown LLM provider: {provider}")
        return cls._llm_providers[provider](config)