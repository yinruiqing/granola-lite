"""
AI服务管理器 - 统一管理多个AI提供商，提供错误处理、重试和缓存
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, AsyncGenerator, Union
from dataclasses import dataclass, asdict
from enum import Enum
import redis.asyncio as aioredis

from app.services.ai.base import (
    AIProvider, STTProvider, LLMProvider, TranscriptionResult, 
    LLMResponse, AIConfig, AIServiceFactory
)
from app.core.events import event_emitter, Events
from app.config import settings
from loguru import logger


class ServiceStatus(Enum):
    """服务状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    MAINTENANCE = "maintenance"


@dataclass
class ProviderHealth:
    """提供商健康状态"""
    provider: AIProvider
    status: ServiceStatus
    last_check: datetime
    response_time: float  # 毫秒
    error_count: int
    success_count: int
    last_error: Optional[str] = None


@dataclass
class AIServiceConfig:
    """AI服务扩展配置"""
    retry_attempts: int = 3
    retry_delay: float = 1.0  # 秒
    timeout: float = 30.0  # 秒
    cache_ttl: int = 3600  # 缓存TTL，秒
    health_check_interval: int = 300  # 健康检查间隔，秒
    enable_cache: bool = True
    enable_fallback: bool = True
    max_concurrent_requests: int = 100


class AIServiceManager:
    """AI服务统一管理器"""
    
    def __init__(self, config: AIServiceConfig = None):
        self.config = config or AIServiceConfig()
        self.redis_client: Optional[aioredis.Redis] = None
        
        # 提供商实例缓存
        self.stt_providers: Dict[AIProvider, STTProvider] = {}
        self.llm_providers: Dict[AIProvider, LLMProvider] = {}
        
        # 健康状态监控
        self.provider_health: Dict[AIProvider, ProviderHealth] = {}
        self.health_check_task: Optional[asyncio.Task] = None
        
        # 速率限制
        self.request_semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        
        # 指标统计
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'fallback_requests': 0,
            'retry_attempts': 0
        }
    
    async def initialize(self, ai_config: AIConfig):
        """初始化AI服务管理器"""
        try:
            # 初始化Redis缓存（如果启用）
            if self.config.enable_cache:
                try:
                    self.redis_client = await aioredis.from_url(settings.redis_url)
                    await self.redis_client.ping()
                    logger.info("Redis缓存连接成功")
                except Exception as e:
                    logger.warning(f"Redis连接失败，禁用缓存: {e}")
                    self.config.enable_cache = False
            
            # 初始化STT提供商
            try:
                stt_provider_instance = AIServiceFactory.create_stt_provider(
                    ai_config.stt_provider, ai_config.stt_config
                )
                self.stt_providers[ai_config.stt_provider] = stt_provider_instance
                
                # 初始化健康状态
                self.provider_health[ai_config.stt_provider] = ProviderHealth(
                    provider=ai_config.stt_provider,
                    status=ServiceStatus.HEALTHY,
                    last_check=datetime.now(),
                    response_time=0.0,
                    error_count=0,
                    success_count=0
                )
                
                logger.info(f"STT提供商初始化成功: {ai_config.stt_provider.value}")
                
            except Exception as e:
                logger.error(f"STT提供商初始化失败: {e}")
                raise
            
            # 初始化LLM提供商
            try:
                llm_provider_instance = AIServiceFactory.create_llm_provider(
                    ai_config.llm_provider, ai_config.llm_config
                )
                self.llm_providers[ai_config.llm_provider] = llm_provider_instance
                
                # 初始化健康状态
                self.provider_health[ai_config.llm_provider] = ProviderHealth(
                    provider=ai_config.llm_provider,
                    status=ServiceStatus.HEALTHY,
                    last_check=datetime.now(),
                    response_time=0.0,
                    error_count=0,
                    success_count=0
                )
                
                logger.info(f"LLM提供商初始化成功: {ai_config.llm_provider.value}")
                
            except Exception as e:
                logger.error(f"LLM提供商初始化失败: {e}")
                raise
            
            # 启动健康检查任务
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            logger.info("AI服务管理器初始化完成")
            
        except Exception as e:
            logger.error(f"AI服务管理器初始化失败: {e}")
            raise
    
    async def shutdown(self):
        """关闭AI服务管理器"""
        try:
            # 停止健康检查任务
            if self.health_check_task:
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass
            
            # 关闭Redis连接
            if self.redis_client:
                await self.redis_client.close()
            
            logger.info("AI服务管理器已关闭")
            
        except Exception as e:
            logger.error(f"关闭AI服务管理器失败: {e}")
    
    def _get_cache_key(self, operation: str, **kwargs) -> str:
        """生成缓存键"""
        # 创建一个包含所有关键参数的字符串
        key_data = {
            'operation': operation,
            **{k: v for k, v in kwargs.items() if v is not None}
        }
        
        # 生成哈希作为缓存键
        key_string = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        key_hash = hashlib.md5(key_string.encode('utf-8')).hexdigest()
        
        return f"ai_cache:{operation}:{key_hash}"
    
    async def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """从缓存获取结果"""
        if not self.config.enable_cache or not self.redis_client:
            return None
        
        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                self.metrics['cache_hits'] += 1
                return json.loads(cached_data)
            else:
                self.metrics['cache_misses'] += 1
                return None
                
        except Exception as e:
            logger.warning(f"缓存读取失败: {e}")
            self.metrics['cache_misses'] += 1
            return None
    
    async def _set_cache(self, cache_key: str, data: Dict[str, Any], ttl: int = None):
        """设置缓存"""
        if not self.config.enable_cache or not self.redis_client:
            return
        
        try:
            ttl = ttl or self.config.cache_ttl
            await self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(data, ensure_ascii=False, default=str)
            )
        except Exception as e:
            logger.warning(f"缓存写入失败: {e}")
    
    async def _execute_with_retry(
        self, 
        operation_name: str,
        provider: AIProvider,
        operation_func,
        *args,
        **kwargs
    ) -> Any:
        """带重试和错误处理的操作执行"""
        last_error = None
        
        for attempt in range(self.config.retry_attempts):
            try:
                # 检查提供商健康状态
                health = self.provider_health.get(provider)
                if health and health.status == ServiceStatus.DOWN:
                    raise Exception(f"Provider {provider.value} is down")
                
                # 限制并发请求数
                async with self.request_semaphore:
                    # 记录开始时间
                    start_time = datetime.now()
                    
                    # 执行操作
                    result = await asyncio.wait_for(
                        operation_func(*args, **kwargs),
                        timeout=self.config.timeout
                    )
                    
                    # 记录响应时间
                    response_time = (datetime.now() - start_time).total_seconds() * 1000
                    
                    # 更新健康状态
                    await self._update_provider_health(provider, True, response_time)
                    
                    # 更新指标
                    self.metrics['total_requests'] += 1
                    self.metrics['successful_requests'] += 1
                    
                    # 发射成功事件
                    await event_emitter.emit(Events.AI_REQUEST_SUCCESS, {
                        'operation': operation_name,
                        'provider': provider.value,
                        'response_time': response_time,
                        'attempt': attempt + 1
                    })
                    
                    return result
                    
            except Exception as e:
                last_error = e
                
                # 更新健康状态
                await self._update_provider_health(provider, False, error=str(e))
                
                # 更新指标
                self.metrics['total_requests'] += 1
                self.metrics['failed_requests'] += 1
                
                if attempt < self.config.retry_attempts - 1:
                    self.metrics['retry_attempts'] += 1
                    
                    # 等待重试
                    delay = self.config.retry_delay * (2 ** attempt)  # 指数退避
                    logger.warning(
                        f"{operation_name} 请求失败 (尝试 {attempt + 1}/{self.config.retry_attempts}): {e}, "
                        f"{delay}秒后重试"
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"{operation_name} 请求最终失败: {e}")
        
        # 发射失败事件
        await event_emitter.emit(Events.AI_REQUEST_FAILED, {
            'operation': operation_name,
            'provider': provider.value,
            'error': str(last_error),
            'attempts': self.config.retry_attempts
        })
        
        raise last_error
    
    async def _update_provider_health(
        self, 
        provider: AIProvider, 
        success: bool, 
        response_time: float = 0.0, 
        error: str = None
    ):
        """更新提供商健康状态"""
        if provider not in self.provider_health:
            self.provider_health[provider] = ProviderHealth(
                provider=provider,
                status=ServiceStatus.HEALTHY,
                last_check=datetime.now(),
                response_time=0.0,
                error_count=0,
                success_count=0
            )
        
        health = self.provider_health[provider]
        health.last_check = datetime.now()
        health.response_time = response_time
        
        if success:
            health.success_count += 1
            # 如果连续成功，恢复健康状态
            if health.status == ServiceStatus.DOWN and health.success_count >= 3:
                health.status = ServiceStatus.HEALTHY
                logger.info(f"Provider {provider.value} 恢复健康")
        else:
            health.error_count += 1
            health.last_error = error
            
            # 根据错误率调整状态
            total_requests = health.success_count + health.error_count
            error_rate = health.error_count / total_requests if total_requests > 0 else 0
            
            if error_rate > 0.8 and total_requests >= 10:
                health.status = ServiceStatus.DOWN
                logger.warning(f"Provider {provider.value} 标记为不可用")
            elif error_rate > 0.5:
                health.status = ServiceStatus.DEGRADED
                logger.warning(f"Provider {provider.value} 服务降级")
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查失败: {e}")
    
    async def _perform_health_checks(self):
        """执行健康检查"""
        # 这里可以实现具体的健康检查逻辑
        # 例如发送简单的测试请求
        logger.debug("执行AI服务健康检查")
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        provider: AIProvider = None,
        language: str = "auto",
        use_cache: bool = True,
        **kwargs
    ) -> TranscriptionResult:
        """语音转录"""
        # 选择提供商
        if not provider:
            provider = list(self.stt_providers.keys())[0]
        
        if provider not in self.stt_providers:
            raise ValueError(f"STT provider {provider.value} not available")
        
        # 检查缓存
        cache_key = None
        if use_cache:
            audio_hash = hashlib.md5(audio_data).hexdigest()
            cache_key = self._get_cache_key(
                'transcribe',
                provider=provider.value,
                audio_hash=audio_hash,
                language=language,
                **kwargs
            )
            
            cached_result = await self._get_from_cache(cache_key)
            if cached_result:
                return TranscriptionResult(**cached_result)
        
        # 执行转录
        stt_provider = self.stt_providers[provider]
        import io
        audio_file = io.BytesIO(audio_data)
        
        result = await self._execute_with_retry(
            'transcribe_audio',
            provider,
            stt_provider.transcribe_audio,
            audio_file,
            language,
            **kwargs
        )
        
        # 缓存结果
        if use_cache and cache_key:
            await self._set_cache(cache_key, asdict(result))
        
        return result
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        provider: AIProvider = None,
        model: str = None,
        use_cache: bool = True,
        **kwargs
    ) -> LLMResponse:
        """聊天完成"""
        # 选择提供商
        if not provider:
            provider = list(self.llm_providers.keys())[0]
        
        if provider not in self.llm_providers:
            raise ValueError(f"LLM provider {provider.value} not available")
        
        # 检查缓存
        cache_key = None
        if use_cache:
            cache_key = self._get_cache_key(
                'chat_completion',
                provider=provider.value,
                messages=messages,
                model=model,
                **kwargs
            )
            
            cached_result = await self._get_from_cache(cache_key)
            if cached_result:
                return LLMResponse(**cached_result)
        
        # 执行聊天完成
        llm_provider = self.llm_providers[provider]
        
        result = await self._execute_with_retry(
            'chat_completion',
            provider,
            llm_provider.chat_completion,
            messages,
            model,
            **kwargs
        )
        
        # 缓存结果
        if use_cache and cache_key:
            await self._set_cache(cache_key, asdict(result))
        
        return result
    
    def get_provider_health(self, provider: AIProvider = None) -> Union[ProviderHealth, Dict[AIProvider, ProviderHealth]]:
        """获取提供商健康状态"""
        if provider:
            return self.provider_health.get(provider)
        return self.provider_health.copy()
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取服务指标"""
        return {
            **self.metrics,
            'provider_health': {
                provider.value: {
                    'status': health.status.value,
                    'response_time': health.response_time,
                    'error_count': health.error_count,
                    'success_count': health.success_count,
                    'last_check': health.last_check.isoformat(),
                    'last_error': health.last_error
                }
                for provider, health in self.provider_health.items()
            }
        }


# 全局AI服务管理器实例
ai_service_manager = AIServiceManager()