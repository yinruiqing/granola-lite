"""
Redis缓存系统 - 提供统一的缓存接口和策略
"""

import json
import pickle
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import redis.asyncio as aioredis
from contextlib import asynccontextmanager

from app.config import settings
from loguru import logger


class CacheStrategy(Enum):
    """缓存策略枚举"""
    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最少使用频次
    TTL = "ttl"  # 基于时间过期
    WRITE_THROUGH = "write_through"  # 写穿透
    WRITE_BACK = "write_back"  # 写回
    READ_THROUGH = "read_through"  # 读穿透


@dataclass
class CacheConfig:
    """缓存配置"""
    default_ttl: int = 3600  # 默认过期时间（秒）
    max_connections: int = 10  # 最大连接数
    encoding: str = "utf-8"  # 编码格式
    decode_responses: bool = True  # 自动解码响应
    health_check_interval: int = 30  # 健康检查间隔（秒）
    retry_on_timeout: bool = True  # 超时重试
    socket_keepalive: bool = True  # Socket保活
    socket_keepalive_options: Dict = None  # Socket保活选项


@dataclass
class CacheStats:
    """缓存统计信息"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    total_requests: int = 0
    hit_rate: float = 0.0
    last_reset: datetime = None

    def update_stats(self, operation: str, success: bool = True):
        """更新统计信息"""
        self.total_requests += 1
        
        if success:
            if operation == "get":
                self.hits += 1
            elif operation == "get_miss":
                self.misses += 1
            elif operation == "set":
                self.sets += 1
            elif operation == "delete":
                self.deletes += 1
        else:
            self.errors += 1
        
        # 计算命中率
        total_gets = self.hits + self.misses
        if total_gets > 0:
            self.hit_rate = self.hits / total_gets
    
    def reset(self):
        """重置统计信息"""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
        self.total_requests = 0
        self.hit_rate = 0.0
        self.last_reset = datetime.now()


class CacheSerializer:
    """缓存序列化器"""
    
    @staticmethod
    def serialize(data: Any) -> bytes:
        """序列化数据"""
        try:
            if isinstance(data, (str, int, float, bool)):
                return json.dumps(data).encode('utf-8')
            else:
                return pickle.dumps(data)
        except Exception as e:
            logger.error(f"序列化失败: {e}")
            raise
    
    @staticmethod
    def deserialize(data: bytes) -> Any:
        """反序列化数据"""
        try:
            # 先尝试JSON反序列化
            try:
                return json.loads(data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # 如果JSON失败，使用pickle
                return pickle.loads(data)
        except Exception as e:
            logger.error(f"反序列化失败: {e}")
            raise


class CacheManager:
    """Redis缓存管理器"""
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.redis_client: Optional[aioredis.Redis] = None
        self.connection_pool: Optional[aioredis.ConnectionPool] = None
        self.stats = CacheStats()
        self.stats.last_reset = datetime.now()
        
        # 序列化器
        self.serializer = CacheSerializer()
        
        # 健康检查任务
        self.health_check_task: Optional[asyncio.Task] = None
        self.is_healthy = False
        
        # 缓存策略处理器
        self.strategy_handlers = {
            CacheStrategy.TTL: self._handle_ttl_strategy,
            CacheStrategy.LRU: self._handle_lru_strategy,
            CacheStrategy.LFU: self._handle_lfu_strategy,
        }
    
    async def initialize(self, redis_url: str = None):
        """初始化缓存管理器"""
        try:
            redis_url = redis_url or settings.redis_url
            
            # 创建连接池
            self.connection_pool = aioredis.ConnectionPool.from_url(
                redis_url,
                max_connections=self.config.max_connections,
                encoding=self.config.encoding,
                decode_responses=False,  # 我们手动处理序列化
                socket_keepalive=self.config.socket_keepalive,
                socket_keepalive_options=self.config.socket_keepalive_options or {},
                retry_on_timeout=self.config.retry_on_timeout
            )
            
            # 创建Redis客户端
            self.redis_client = aioredis.Redis(connection_pool=self.connection_pool)
            
            # 测试连接
            await self.redis_client.ping()
            self.is_healthy = True
            
            # 启动健康检查
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            
            logger.info("缓存管理器初始化成功")
            
        except Exception as e:
            logger.error(f"缓存管理器初始化失败: {e}")
            self.is_healthy = False
            raise
    
    async def shutdown(self):
        """关闭缓存管理器"""
        try:
            # 停止健康检查
            if self.health_check_task:
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass
            
            # 关闭Redis连接
            if self.redis_client:
                await self.redis_client.close()
            
            # 关闭连接池
            if self.connection_pool:
                await self.connection_pool.disconnect()
            
            logger.info("缓存管理器已关闭")
            
        except Exception as e:
            logger.error(f"关闭缓存管理器失败: {e}")
    
    def _generate_key(self, namespace: str, key: str) -> str:
        """生成缓存键"""
        return f"{namespace}:{key}"
    
    def _generate_hash_key(self, data: Dict[str, Any]) -> str:
        """根据数据生成哈希键"""
        key_string = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                # 执行简单的ping检查
                await self.redis_client.ping()
                
                if not self.is_healthy:
                    self.is_healthy = True
                    logger.info("缓存服务恢复健康")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.is_healthy:
                    self.is_healthy = False
                    logger.error(f"缓存健康检查失败: {e}")
    
    async def _handle_ttl_strategy(self, key: str, ttl: int):
        """处理TTL策略"""
        if ttl > 0:
            await self.redis_client.expire(key, ttl)
    
    async def _handle_lru_strategy(self, key: str, ttl: int):
        """处理LRU策略"""
        # Redis的默认淘汰策略，这里可以添加额外的逻辑
        await self._handle_ttl_strategy(key, ttl)
    
    async def _handle_lfu_strategy(self, key: str, ttl: int):
        """处理LFU策略"""
        # 可以通过Redis的CONFIG SET maxmemory-policy allkeys-lfu配置
        await self._handle_ttl_strategy(key, ttl)
    
    @asynccontextmanager
    async def _handle_operation(self, operation: str):
        """操作处理上下文管理器"""
        success = False
        try:
            if not self.is_healthy:
                raise Exception("缓存服务不健康")
            
            yield
            success = True
            
        except Exception as e:
            logger.error(f"缓存操作失败 {operation}: {e}")
            self.stats.update_stats(operation, False)
            raise
        finally:
            if success:
                self.stats.update_stats(operation, True)
    
    async def get(
        self, 
        namespace: str, 
        key: str, 
        default: Any = None,
        deserialize: bool = True
    ) -> Any:
        """获取缓存值"""
        cache_key = self._generate_key(namespace, key)
        
        async with self._handle_operation("get"):
            try:
                data = await self.redis_client.get(cache_key)
                
                if data is None:
                    self.stats.update_stats("get_miss", True)
                    return default
                
                if deserialize:
                    return self.serializer.deserialize(data)
                return data
                
            except Exception as e:
                logger.error(f"获取缓存失败 {cache_key}: {e}")
                self.stats.update_stats("get", False)
                return default
    
    async def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: int = None,
        strategy: CacheStrategy = CacheStrategy.TTL,
        serialize: bool = True
    ) -> bool:
        """设置缓存值"""
        cache_key = self._generate_key(namespace, key)
        ttl = ttl or self.config.default_ttl
        
        async with self._handle_operation("set"):
            try:
                # 序列化数据
                if serialize:
                    data = self.serializer.serialize(value)
                else:
                    data = value
                
                # 设置缓存
                if ttl > 0:
                    await self.redis_client.setex(cache_key, ttl, data)
                else:
                    await self.redis_client.set(cache_key, data)
                
                # 应用缓存策略
                if strategy in self.strategy_handlers:
                    await self.strategy_handlers[strategy](cache_key, ttl)
                
                return True
                
            except Exception as e:
                logger.error(f"设置缓存失败 {cache_key}: {e}")
                self.stats.update_stats("set", False)
                return False
    
    async def delete(self, namespace: str, key: str) -> bool:
        """删除缓存"""
        cache_key = self._generate_key(namespace, key)
        
        async with self._handle_operation("delete"):
            try:
                result = await self.redis_client.delete(cache_key)
                return result > 0
                
            except Exception as e:
                logger.error(f"删除缓存失败 {cache_key}: {e}")
                self.stats.update_stats("delete", False)
                return False
    
    async def exists(self, namespace: str, key: str) -> bool:
        """检查缓存是否存在"""
        cache_key = self._generate_key(namespace, key)
        
        try:
            result = await self.redis_client.exists(cache_key)
            return result > 0
        except Exception as e:
            logger.error(f"检查缓存存在失败 {cache_key}: {e}")
            return False
    
    async def mget(self, namespace: str, keys: List[str]) -> Dict[str, Any]:
        """批量获取缓存"""
        cache_keys = [self._generate_key(namespace, key) for key in keys]
        
        try:
            values = await self.redis_client.mget(cache_keys)
            result = {}
            
            for i, (key, value) in enumerate(zip(keys, values)):
                if value is not None:
                    try:
                        result[key] = self.serializer.deserialize(value)
                        self.stats.update_stats("get", True)
                    except Exception as e:
                        logger.error(f"反序列化失败 {key}: {e}")
                        self.stats.update_stats("get", False)
                else:
                    self.stats.update_stats("get_miss", True)
            
            return result
            
        except Exception as e:
            logger.error(f"批量获取缓存失败: {e}")
            return {}
    
    async def mset(
        self, 
        namespace: str, 
        data: Dict[str, Any], 
        ttl: int = None
    ) -> bool:
        """批量设置缓存"""
        try:
            ttl = ttl or self.config.default_ttl
            
            # 序列化所有数据
            cache_data = {}
            for key, value in data.items():
                cache_key = self._generate_key(namespace, key)
                cache_data[cache_key] = self.serializer.serialize(value)
            
            # 批量设置
            await self.redis_client.mset(cache_data)
            
            # 如果设置了TTL，需要逐个设置过期时间
            if ttl > 0:
                for cache_key in cache_data.keys():
                    await self.redis_client.expire(cache_key, ttl)
            
            self.stats.sets += len(data)
            return True
            
        except Exception as e:
            logger.error(f"批量设置缓存失败: {e}")
            self.stats.errors += len(data)
            return False
    
    async def clear_namespace(self, namespace: str) -> int:
        """清空命名空间下的所有缓存"""
        try:
            pattern = f"{namespace}:*"
            keys = []
            
            # 使用scan迭代查找所有匹配的键
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                deleted = await self.redis_client.delete(*keys)
                self.stats.deletes += deleted
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"清空命名空间失败 {namespace}: {e}")
            self.stats.errors += 1
            return 0
    
    async def get_ttl(self, namespace: str, key: str) -> int:
        """获取缓存剩余过期时间"""
        cache_key = self._generate_key(namespace, key)
        
        try:
            ttl = await self.redis_client.ttl(cache_key)
            return ttl if ttl >= 0 else 0
        except Exception as e:
            logger.error(f"获取TTL失败 {cache_key}: {e}")
            return 0
    
    async def extend_ttl(self, namespace: str, key: str, ttl: int) -> bool:
        """延长缓存过期时间"""
        cache_key = self._generate_key(namespace, key)
        
        try:
            result = await self.redis_client.expire(cache_key, ttl)
            return result
        except Exception as e:
            logger.error(f"延长TTL失败 {cache_key}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "hits": self.stats.hits,
            "misses": self.stats.misses,
            "sets": self.stats.sets,
            "deletes": self.stats.deletes,
            "errors": self.stats.errors,
            "total_requests": self.stats.total_requests,
            "hit_rate": round(self.stats.hit_rate * 100, 2),  # 百分比
            "is_healthy": self.is_healthy,
            "last_reset": self.stats.last_reset.isoformat() if self.stats.last_reset else None
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats.reset()
        logger.info("缓存统计信息已重置")


# 全局缓存管理器实例
cache_manager = CacheManager()


# 缓存装饰器
def cached(
    namespace: str,
    ttl: int = None,
    key_func: Callable = None,
    strategy: CacheStrategy = CacheStrategy.TTL
):
    """缓存装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 使用函数名和参数生成键
                import inspect
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                
                key_data = {
                    'func': func.__name__,
                    'args': bound_args.arguments
                }
                cache_key = cache_manager._generate_hash_key(key_data)
            
            # 尝试从缓存获取
            cached_result = await cache_manager.get(namespace, cache_key)
            if cached_result is not None:
                return cached_result
            
            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            await cache_manager.set(
                namespace, 
                cache_key, 
                result, 
                ttl=ttl,
                strategy=strategy
            )
            
            return result
            
        return wrapper
    return decorator