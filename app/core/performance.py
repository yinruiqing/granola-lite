"""
性能优化系统
"""

from typing import Dict, Any, List, Optional, Callable, AsyncGenerator
import asyncio
import time
import functools
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from sqlalchemy.orm import selectinload
from loguru import logger

from app.db.database import get_db_session
from app.core.cache import cache_manager
from app.core.monitoring import metrics_collector


class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self):
        self.query_cache_ttl = 300  # 5分钟
        self.slow_query_threshold = 1.0  # 1秒
        self.batch_size = 1000
        
    async def analyze_slow_queries(
        self, 
        threshold_seconds: float = None
    ) -> Dict[str, Any]:
        """分析慢查询"""
        try:
            threshold = threshold_seconds or self.slow_query_threshold
            
            # 这里需要根据实际数据库实现慢查询分析
            # 以PostgreSQL为例
            async with get_db_session() as db:
                # 获取最近的慢查询统计
                slow_queries_result = await db.execute(text("""
                    SELECT 
                        query,
                        calls,
                        total_time,
                        mean_time,
                        max_time,
                        stddev_time
                    FROM pg_stat_statements 
                    WHERE mean_time > :threshold * 1000
                    ORDER BY mean_time DESC
                    LIMIT 20
                """), {"threshold": threshold})
                
                slow_queries = []
                for row in slow_queries_result.fetchall():
                    slow_queries.append({
                        "query": row[0][:200] + "..." if len(row[0]) > 200 else row[0],
                        "calls": row[1],
                        "total_time_ms": row[2],
                        "mean_time_ms": row[3],
                        "max_time_ms": row[4],
                        "stddev_time_ms": row[5]
                    })
                
                return {
                    "threshold_seconds": threshold,
                    "slow_queries_count": len(slow_queries),
                    "slow_queries": slow_queries,
                    "analysis_time": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.warning(f"慢查询分析失败 (可能不支持pg_stat_statements): {e}")
            return {
                "threshold_seconds": threshold,
                "slow_queries_count": 0,
                "slow_queries": [],
                "error": str(e),
                "analysis_time": datetime.now().isoformat()
            }
    
    async def optimize_database_indexes(self) -> Dict[str, Any]:
        """数据库索引优化建议"""
        try:
            async with get_db_session() as db:
                optimization_suggestions = []
                
                # 检查缺失的索引（基于查询模式）
                missing_indexes = await self._analyze_missing_indexes(db)
                optimization_suggestions.extend(missing_indexes)
                
                # 检查未使用的索引
                unused_indexes = await self._analyze_unused_indexes(db)
                optimization_suggestions.extend(unused_indexes)
                
                # 检查重复索引
                duplicate_indexes = await self._analyze_duplicate_indexes(db)
                optimization_suggestions.extend(duplicate_indexes)
                
                return {
                    "suggestions": optimization_suggestions,
                    "total_suggestions": len(optimization_suggestions),
                    "analysis_time": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"数据库索引分析失败: {e}")
            return {
                "suggestions": [],
                "total_suggestions": 0,
                "error": str(e),
                "analysis_time": datetime.now().isoformat()
            }
    
    async def batch_process_records(
        self,
        query_func: Callable,
        process_func: Callable,
        batch_size: int = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """批量处理记录"""
        batch_size = batch_size or self.batch_size
        processed_count = 0
        error_count = 0
        start_time = time.time()
        
        try:
            async with get_db_session() as db:
                offset = 0
                
                while True:
                    # 获取一批记录
                    records = await query_func(db, offset, batch_size)
                    
                    if not records:
                        break
                    
                    # 处理这一批记录
                    batch_errors = 0
                    for record in records:
                        try:
                            await process_func(db, record)
                            processed_count += 1
                        except Exception as e:
                            logger.warning(f"处理记录失败: {e}")
                            batch_errors += 1
                            error_count += 1
                    
                    # 提交这一批的更改
                    try:
                        await db.commit()
                    except Exception as e:
                        logger.error(f"批量提交失败: {e}")
                        await db.rollback()
                        error_count += batch_size - batch_errors
                    
                    # 更新进度
                    if progress_callback:
                        await progress_callback(processed_count, error_count)
                    
                    offset += batch_size
                    
                    # 短暂暂停以避免过载
                    await asyncio.sleep(0.1)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            return {
                "processed_count": processed_count,
                "error_count": error_count,
                "processing_time_seconds": processing_time,
                "records_per_second": processed_count / processing_time if processing_time > 0 else 0,
                "completed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"批量处理失败: {e}")
            return {
                "processed_count": processed_count,
                "error_count": error_count,
                "processing_time_seconds": time.time() - start_time,
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            }
    
    async def optimize_query_performance(
        self,
        query_func: Callable,
        cache_key: str,
        cache_ttl: int = None
    ) -> Any:
        """优化查询性能（缓存 + 预加载）"""
        cache_ttl = cache_ttl or self.query_cache_ttl
        
        # 尝试从缓存获取
        cached_result = await cache_manager.get(cache_key)
        if cached_result is not None:
            metrics_collector.record_metric("query_cache_hit", 1.0)
            return cached_result
        
        # 缓存未命中，执行查询
        metrics_collector.record_metric("query_cache_miss", 1.0)
        start_time = time.time()
        
        try:
            result = await query_func()
            query_time = time.time() - start_time
            
            # 记录查询时间指标
            metrics_collector.record_metric("query_execution_time", query_time)
            
            # 如果查询时间超过阈值，记录为慢查询
            if query_time > self.slow_query_threshold:
                metrics_collector.record_metric("slow_query_count", 1.0)
                logger.warning(f"慢查询detected: {cache_key}, 耗时: {query_time:.3f}s")
            
            # 缓存结果
            await cache_manager.set(cache_key, result, ttl=cache_ttl)
            
            return result
            
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            raise
    
    async def preload_related_data(
        self,
        db: AsyncSession,
        query,
        relationships: List[str]
    ):
        """预加载关联数据"""
        # 使用selectinload来预加载关联数据
        for relationship in relationships:
            query = query.options(selectinload(relationship))
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def connection_pool_status(self) -> Dict[str, Any]:
        """获取连接池状态"""
        try:
            # 这里需要根据实际的数据库引擎实现
            return {
                "pool_size": 10,  # 从配置获取
                "checked_out": 0,  # 需要实际实现
                "overflow": 0,     # 需要实际实现
                "checked_in": 10,  # 需要实际实现
                "status": "healthy",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"获取连接池状态失败: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _analyze_missing_indexes(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """分析缺失的索引"""
        suggestions = []
        
        try:
            # 基于常见查询模式的索引建议
            common_queries = [
                {
                    "table": "users",
                    "columns": ["email"],
                    "reason": "用户登录查询频繁"
                },
                {
                    "table": "meetings", 
                    "columns": ["user_id", "created_at"],
                    "reason": "按用户和时间查询会议"
                },
                {
                    "table": "transcriptions",
                    "columns": ["meeting_id"],
                    "reason": "通过会议ID查询转录"
                },
                {
                    "table": "notes",
                    "columns": ["user_id", "created_at"],
                    "reason": "按用户和时间查询笔记"
                }
            ]
            
            for query_pattern in common_queries:
                # 检查索引是否存在
                index_exists = await self._check_index_exists(
                    db, query_pattern["table"], query_pattern["columns"]
                )
                
                if not index_exists:
                    suggestions.append({
                        "type": "missing_index",
                        "table": query_pattern["table"],
                        "columns": query_pattern["columns"],
                        "reason": query_pattern["reason"],
                        "priority": "high",
                        "sql": f"CREATE INDEX idx_{query_pattern['table']}_{'_'.join(query_pattern['columns'])} ON {query_pattern['table']} ({', '.join(query_pattern['columns'])})"
                    })
        
        except Exception as e:
            logger.warning(f"分析缺失索引失败: {e}")
        
        return suggestions
    
    async def _analyze_unused_indexes(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """分析未使用的索引"""
        suggestions = []
        
        try:
            # PostgreSQL示例查询
            result = await db.execute(text("""
                SELECT 
                    schemaname, 
                    tablename, 
                    indexname, 
                    idx_tup_read, 
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                WHERE idx_tup_read = 0 AND idx_tup_fetch = 0
                AND indexname NOT LIKE '%pkey%'
            """))
            
            for row in result.fetchall():
                suggestions.append({
                    "type": "unused_index",
                    "table": row[1],
                    "index_name": row[2],
                    "reason": "索引从未被使用",
                    "priority": "medium",
                    "sql": f"DROP INDEX {row[2]}"
                })
                
        except Exception as e:
            logger.warning(f"分析未使用索引失败 (可能不支持pg_stat_user_indexes): {e}")
        
        return suggestions
    
    async def _analyze_duplicate_indexes(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """分析重复索引"""
        suggestions = []
        
        try:
            # 这里需要实现重复索引检测逻辑
            # 暂时返回空列表
            pass
        except Exception as e:
            logger.warning(f"分析重复索引失败: {e}")
        
        return suggestions
    
    async def _check_index_exists(
        self,
        db: AsyncSession,
        table_name: str,
        columns: List[str]
    ) -> bool:
        """检查索引是否存在"""
        try:
            result = await db.execute(text("""
                SELECT COUNT(*) 
                FROM pg_indexes 
                WHERE tablename = :table_name 
                AND indexdef LIKE :column_pattern
            """), {
                "table_name": table_name,
                "column_pattern": f"%{', '.join(columns)}%"
            })
            
            count = result.scalar()
            return count > 0
            
        except Exception:
            # 如果检查失败，假设索引不存在
            return False


class QueryOptimizer:
    """查询优化器"""
    
    def __init__(self):
        self.cache_enabled = True
    
    def cache_query(self, key: str, ttl: int = 300):
        """查询缓存装饰器"""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.cache_enabled:
                    return await func(*args, **kwargs)
                
                # 生成缓存键
                cache_key = f"query:{key}:{hash(str(args) + str(kwargs))}"
                
                # 尝试从缓存获取
                cached_result = await cache_manager.get(cache_key)
                if cached_result is not None:
                    metrics_collector.record_metric("query_cache_hit", 1.0)
                    return cached_result
                
                # 执行查询
                metrics_collector.record_metric("query_cache_miss", 1.0)
                result = await func(*args, **kwargs)
                
                # 缓存结果
                await cache_manager.set(cache_key, result, ttl=ttl)
                
                return result
            
            return wrapper
        return decorator
    
    def batch_loader(self, batch_size: int = 100):
        """批量加载装饰器"""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(db: AsyncSession, ids: List[int], *args, **kwargs):
                results = {}
                
                # 分批处理
                for i in range(0, len(ids), batch_size):
                    batch_ids = ids[i:i + batch_size]
                    batch_results = await func(db, batch_ids, *args, **kwargs)
                    results.update(batch_results)
                
                return results
            
            return wrapper
        return decorator
    
    def async_executor(self, max_concurrent: int = 10):
        """异步执行器装饰器"""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(items: List[Any], *args, **kwargs):
                semaphore = asyncio.Semaphore(max_concurrent)
                
                async def execute_item(item):
                    async with semaphore:
                        return await func(item, *args, **kwargs)
                
                # 并发执行所有任务
                tasks = [execute_item(item) for item in items]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                return results
            
            return wrapper
        return decorator


class DatabaseOptimizer:
    """数据库优化器"""
    
    async def vacuum_analyze_tables(self) -> Dict[str, Any]:
        """清理和分析表"""
        try:
            async with get_db_session() as db:
                tables = ['users', 'meetings', 'transcriptions', 'notes']
                results = {}
                
                for table in tables:
                    try:
                        # VACUUM ANALYZE (PostgreSQL)
                        await db.execute(text(f"VACUUM ANALYZE {table}"))
                        results[table] = "success"
                        logger.info(f"VACUUM ANALYZE completed for table: {table}")
                    except Exception as e:
                        results[table] = f"error: {str(e)}"
                        logger.warning(f"VACUUM ANALYZE failed for table {table}: {e}")
                
                return {
                    "results": results,
                    "completed_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"VACUUM ANALYZE操作失败: {e}")
            return {
                "results": {},
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            }
    
    async def update_table_statistics(self) -> Dict[str, Any]:
        """更新表统计信息"""
        try:
            async with get_db_session() as db:
                # 更新统计信息 (PostgreSQL)
                await db.execute(text("ANALYZE"))
                
                return {
                    "status": "success",
                    "message": "表统计信息更新完成",
                    "completed_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"更新表统计信息失败: {e}")
            return {
                "status": "error",
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            }
    
    async def reindex_tables(self, tables: List[str] = None) -> Dict[str, Any]:
        """重建索引"""
        if not tables:
            tables = ['users', 'meetings', 'transcriptions', 'notes']
        
        try:
            async with get_db_session() as db:
                results = {}
                
                for table in tables:
                    try:
                        # REINDEX TABLE (PostgreSQL)
                        await db.execute(text(f"REINDEX TABLE {table}"))
                        results[table] = "success"
                        logger.info(f"REINDEX completed for table: {table}")
                    except Exception as e:
                        results[table] = f"error: {str(e)}"
                        logger.warning(f"REINDEX failed for table {table}: {e}")
                
                return {
                    "results": results,
                    "completed_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"REINDEX操作失败: {e}")
            return {
                "results": {},
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            }


# 全局实例
performance_optimizer = PerformanceOptimizer()
query_optimizer = QueryOptimizer()
database_optimizer = DatabaseOptimizer()


__all__ = [
    'PerformanceOptimizer',
    'QueryOptimizer', 
    'DatabaseOptimizer',
    'performance_optimizer',
    'query_optimizer',
    'database_optimizer'
]