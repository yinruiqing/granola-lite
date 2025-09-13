"""
数据缓存策略 - 为常用数据库查询提供缓存支持
"""

from typing import Any, Optional, Dict, List, Callable, TypeVar, Generic
from functools import wraps
import hashlib
import json
import inspect
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import select, func

from app.core.cache import cache_manager, cached, CacheStrategy
from app.models.user import User
from app.models.meeting import Meeting
from app.models.note import Note
from loguru import logger


T = TypeVar('T')


class DataCacheManager:
    """数据缓存管理器"""
    
    def __init__(self):
        self.cache_configs = {
            # 用户数据缓存配置
            "users": {
                "ttl": 3600,  # 1小时
                "strategy": CacheStrategy.LRU
            },
            # 会议数据缓存配置
            "meetings": {
                "ttl": 1800,  # 30分钟
                "strategy": CacheStrategy.TTL
            },
            # 笔记数据缓存配置
            "notes": {
                "ttl": 900,  # 15分钟
                "strategy": CacheStrategy.LRU
            },
            # 搜索结果缓存
            "search": {
                "ttl": 600,  # 10分钟
                "strategy": CacheStrategy.TTL
            },
            # 统计数据缓存
            "stats": {
                "ttl": 300,  # 5分钟
                "strategy": CacheStrategy.TTL
            },
            # AI处理结果缓存
            "ai_results": {
                "ttl": 7200,  # 2小时
                "strategy": CacheStrategy.LFU
            }
        }
    
    def get_cache_key(self, namespace: str, **kwargs) -> str:
        """生成缓存键"""
        # 排序参数确保一致性
        sorted_params = dict(sorted(kwargs.items()))
        key_data = json.dumps(sorted_params, sort_keys=True, ensure_ascii=False)
        key_hash = hashlib.md5(key_data.encode('utf-8')).hexdigest()
        return f"{namespace}:{key_hash}"
    
    def cache_query(
        self,
        namespace: str,
        ttl: Optional[int] = None,
        strategy: Optional[CacheStrategy] = None,
        key_func: Optional[Callable] = None,
        invalidate_on: Optional[List[str]] = None
    ):
        """
        数据库查询缓存装饰器
        
        Args:
            namespace: 缓存命名空间
            ttl: 过期时间（秒）
            strategy: 缓存策略
            key_func: 自定义键生成函数
            invalidate_on: 需要失效此缓存的操作类型列表
        """
        config = self.cache_configs.get(namespace, {})
        ttl = ttl or config.get("ttl", 3600)
        strategy = strategy or config.get("strategy", CacheStrategy.TTL)
        
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 生成缓存键
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    # 从参数中提取可序列化的部分
                    cache_params = {}
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()
                    
                    for param_name, param_value in bound_args.arguments.items():
                        if isinstance(param_value, (str, int, float, bool, type(None))):
                            cache_params[param_name] = param_value
                        elif hasattr(param_value, 'id'):  # 模型对象
                            cache_params[f"{param_name}_id"] = param_value.id
                        elif isinstance(param_value, (list, tuple)):
                            # 列表中的ID
                            if all(hasattr(item, 'id') for item in param_value):
                                cache_params[param_name] = [item.id for item in param_value]
                            elif all(isinstance(item, (str, int, float, bool)) for item in param_value):
                                cache_params[param_name] = list(param_value)
                    
                    cache_key = self.get_cache_key(namespace, **cache_params)
                
                # 尝试从缓存获取
                cached_result = await cache_manager.get(namespace, cache_key)
                if cached_result is not None:
                    logger.debug(f"缓存命中: {namespace}:{cache_key}")
                    return cached_result
                
                # 执行原函数
                result = await func(*args, **kwargs)
                
                # 缓存结果（如果不为None）
                if result is not None:
                    await cache_manager.set(
                        namespace,
                        cache_key,
                        result,
                        ttl=ttl,
                        strategy=strategy
                    )
                    logger.debug(f"缓存设置: {namespace}:{cache_key}")
                
                return result
                
            # 添加缓存失效方法
            wrapper.invalidate_cache = lambda **kwargs: self.invalidate_query_cache(
                namespace, key_func, **kwargs
            )
            
            return wrapper
        return decorator
    
    async def invalidate_query_cache(
        self,
        namespace: str,
        key_func: Optional[Callable] = None,
        **kwargs
    ):
        """失效查询缓存"""
        try:
            if key_func:
                cache_key = key_func(**kwargs)
                await cache_manager.delete(namespace, cache_key)
            else:
                cache_key = self.get_cache_key(namespace, **kwargs)
                await cache_manager.delete(namespace, cache_key)
            
            logger.debug(f"缓存失效: {namespace}:{cache_key}")
            
        except Exception as e:
            logger.error(f"缓存失效失败: {e}")
    
    async def invalidate_namespace(self, namespace: str):
        """失效整个命名空间的缓存"""
        try:
            deleted_count = await cache_manager.clear_namespace(namespace)
            logger.info(f"命名空间缓存失效: {namespace}, 删除 {deleted_count} 项")
            return deleted_count
        except Exception as e:
            logger.error(f"命名空间缓存失效失败: {e}")
            return 0


# 全局数据缓存管理器
data_cache = DataCacheManager()


# 用户相关缓存查询
class UserCache:
    """用户数据缓存"""
    
    @staticmethod
    @data_cache.cache_query("users", ttl=3600)
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """根据ID获取用户（缓存）"""
        result = await db.execute(select(User).filter(User.id == user_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    @data_cache.cache_query("users", ttl=3600)
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """根据邮箱获取用户（缓存）"""
        result = await db.execute(select(User).filter(User.email == email))
        return result.scalar_one_or_none()
    
    @staticmethod
    @data_cache.cache_query("users", ttl=1800)
    async def get_active_users_count(db: AsyncSession) -> int:
        """获取活跃用户数量（缓存）"""
        result = await db.execute(select(func.count(User.id)).filter(User.is_active == True))
        return result.scalar()
    
    @staticmethod
    async def invalidate_user_cache(user_id: int):
        """失效用户缓存"""
        await data_cache.invalidate_query_cache("users", user_id=user_id)


# 会议相关缓存查询
class MeetingCache:
    """会议数据缓存"""
    
    @staticmethod
    @data_cache.cache_query("meetings", ttl=1800)
    async def get_meeting_by_id(db: AsyncSession, meeting_id: int) -> Optional[Meeting]:
        """根据ID获取会议（缓存）"""
        result = await db.execute(
            select(Meeting)
            .options(selectinload(Meeting.notes))
            .filter(Meeting.id == meeting_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    @data_cache.cache_query("meetings", ttl=900)
    async def get_user_meetings(
        db: AsyncSession,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Meeting]:
        """获取用户会议列表（缓存）"""
        result = await db.execute(
            select(Meeting)
            .filter(Meeting.user_id == user_id)
            .order_by(Meeting.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    @staticmethod
    @data_cache.cache_query("meetings", ttl=600)
    async def get_recent_meetings(
        db: AsyncSession,
        user_id: int,
        days: int = 7
    ) -> List[Meeting]:
        """获取最近会议（缓存）"""
        from datetime import datetime, timedelta
        
        since_date = datetime.now() - timedelta(days=days)
        result = await db.execute(
            select(Meeting)
            .filter(Meeting.user_id == user_id)
            .filter(Meeting.created_at >= since_date)
            .order_by(Meeting.created_at.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def invalidate_meeting_cache(meeting_id: int, user_id: int):
        """失效会议缓存"""
        await data_cache.invalidate_query_cache("meetings", meeting_id=meeting_id)
        await data_cache.invalidate_query_cache("meetings", user_id=user_id)


# 笔记相关缓存查询
class NoteCache:
    """笔记数据缓存"""
    
    @staticmethod
    @data_cache.cache_query("notes", ttl=900)
    async def get_note_by_id(db: AsyncSession, note_id: int) -> Optional[Note]:
        """根据ID获取笔记（缓存）"""
        result = await db.execute(
            select(Note)
            .options(joinedload(Note.meeting))
            .filter(Note.id == note_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    @data_cache.cache_query("notes", ttl=600)
    async def get_meeting_notes(db: AsyncSession, meeting_id: int) -> List[Note]:
        """获取会议笔记列表（缓存）"""
        result = await db.execute(
            select(Note)
            .filter(Note.meeting_id == meeting_id)
            .order_by(Note.created_at.asc())
        )
        return result.scalars().all()
    
    @staticmethod
    @data_cache.cache_query("notes", ttl=1200)
    async def search_notes(
        db: AsyncSession,
        user_id: int,
        query: str,
        limit: int = 50
    ) -> List[Note]:
        """搜索笔记（缓存）"""
        # 简单的全文搜索，生产环境建议使用专门的搜索引擎
        result = await db.execute(
            select(Note)
            .join(Meeting)
            .filter(Meeting.user_id == user_id)
            .filter(Note.content.contains(query))
            .order_by(Note.updated_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def invalidate_note_cache(note_id: int, meeting_id: int):
        """失效笔记缓存"""
        await data_cache.invalidate_query_cache("notes", note_id=note_id)
        await data_cache.invalidate_query_cache("notes", meeting_id=meeting_id)


# 统计数据缓存
class StatsCache:
    """统计数据缓存"""
    
    @staticmethod
    @data_cache.cache_query("stats", ttl=300)
    async def get_user_stats(db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """获取用户统计数据（缓存）"""
        # 会议数量
        meetings_count = await db.execute(
            select(func.count(Meeting.id)).filter(Meeting.user_id == user_id)
        )
        
        # 笔记数量
        notes_count = await db.execute(
            select(func.count(Note.id))
            .join(Meeting)
            .filter(Meeting.user_id == user_id)
        )
        
        # 最近30天的会议数量
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_meetings = await db.execute(
            select(func.count(Meeting.id))
            .filter(Meeting.user_id == user_id)
            .filter(Meeting.created_at >= thirty_days_ago)
        )
        
        return {
            "total_meetings": meetings_count.scalar(),
            "total_notes": notes_count.scalar(),
            "recent_meetings": recent_meetings.scalar(),
            "updated_at": datetime.now().isoformat()
        }
    
    @staticmethod
    @data_cache.cache_query("stats", ttl=600)
    async def get_system_stats(db: AsyncSession) -> Dict[str, Any]:
        """获取系统统计数据（缓存）"""
        total_users = await db.execute(select(func.count(User.id)))
        active_users = await db.execute(
            select(func.count(User.id)).filter(User.is_active == True)
        )
        total_meetings = await db.execute(select(func.count(Meeting.id)))
        total_notes = await db.execute(select(func.count(Note.id)))
        
        return {
            "total_users": total_users.scalar(),
            "active_users": active_users.scalar(),
            "total_meetings": total_meetings.scalar(),
            "total_notes": total_notes.scalar(),
            "updated_at": datetime.now().isoformat()
        }


# AI结果缓存
class AIResultCache:
    """AI处理结果缓存"""
    
    @staticmethod
    async def cache_transcription_result(
        audio_hash: str,
        provider: str,
        language: str,
        result: Any,
        ttl: int = 7200
    ):
        """缓存转录结果"""
        cache_key = f"transcription:{provider}:{language}:{audio_hash}"
        await cache_manager.set("ai_results", cache_key, result, ttl=ttl)
    
    @staticmethod
    async def get_cached_transcription_result(
        audio_hash: str,
        provider: str,
        language: str
    ) -> Optional[Any]:
        """获取缓存的转录结果"""
        cache_key = f"transcription:{provider}:{language}:{audio_hash}"
        return await cache_manager.get("ai_results", cache_key)
    
    @staticmethod
    async def cache_enhancement_result(
        content_hash: str,
        provider: str,
        template: str,
        result: str,
        ttl: int = 7200
    ):
        """缓存增强结果"""
        cache_key = f"enhancement:{provider}:{template}:{content_hash}"
        await cache_manager.set("ai_results", cache_key, result, ttl=ttl)
    
    @staticmethod
    async def get_cached_enhancement_result(
        content_hash: str,
        provider: str,
        template: str
    ) -> Optional[str]:
        """获取缓存的增强结果"""
        cache_key = f"enhancement:{provider}:{template}:{content_hash}"
        return await cache_manager.get("ai_results", cache_key)


# 缓存失效触发器
class CacheInvalidationTrigger:
    """缓存失效触发器"""
    
    @staticmethod
    async def on_user_updated(user_id: int):
        """用户更新时的缓存失效"""
        await UserCache.invalidate_user_cache(user_id)
        await data_cache.invalidate_namespace("stats")
    
    @staticmethod
    async def on_meeting_created_or_updated(meeting_id: int, user_id: int):
        """会议创建或更新时的缓存失效"""
        await MeetingCache.invalidate_meeting_cache(meeting_id, user_id)
        await data_cache.invalidate_namespace("stats")
    
    @staticmethod
    async def on_note_created_or_updated(note_id: int, meeting_id: int, user_id: int):
        """笔记创建或更新时的缓存失效"""
        await NoteCache.invalidate_note_cache(note_id, meeting_id)
        await data_cache.invalidate_namespace("stats")
        
        # 失效搜索缓存
        await data_cache.invalidate_namespace("search")


# 导出常用的缓存类
__all__ = [
    'DataCacheManager',
    'data_cache',
    'UserCache',
    'MeetingCache', 
    'NoteCache',
    'StatsCache',
    'AIResultCache',
    'CacheInvalidationTrigger'
]