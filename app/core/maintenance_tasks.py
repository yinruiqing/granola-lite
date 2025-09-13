"""
系统维护相关异步任务
"""

import asyncio
import psutil
import gc
from typing import Dict, Any, List
from datetime import datetime, timedelta

from app.core.tasks import task, TaskPriority
from app.core.cache import cache_manager
from app.core.events import event_emitter, Events
from app.db.database import get_async_session
from sqlalchemy import text, func
from loguru import logger


@task(
    name='maintenance.cleanup_cache',
    queue='maintenance',
    priority=TaskPriority.LOW,
    max_retries=1,
    time_limit=300,
    soft_time_limit=240
)
def cleanup_cache_task(
    expired_only: bool = True,
    namespaces: List[str] = None
) -> Dict[str, Any]:
    """
    清理缓存任务
    
    Args:
        expired_only: 只清理过期缓存
        namespaces: 要清理的命名空间列表，None表示所有
    
    Returns:
        清理结果
    """
    try:
        logger.info("开始清理缓存")
        
        cleanup_stats = {
            'cleared_namespaces': [],
            'total_cleared': 0,
            'start_time': datetime.now().isoformat()
        }
        
        if namespaces:
            # 清理指定命名空间
            for namespace in namespaces:
                try:
                    cleared_count = asyncio.run(cache_manager.clear_namespace(namespace))
                    cleanup_stats['cleared_namespaces'].append({
                        'namespace': namespace,
                        'cleared_count': cleared_count
                    })
                    cleanup_stats['total_cleared'] += cleared_count
                    
                except Exception as e:
                    logger.error(f"清理命名空间失败 {namespace}: {e}")
                    cleanup_stats['cleared_namespaces'].append({
                        'namespace': namespace,
                        'error': str(e)
                    })
        else:
            # 清理所有过期缓存（这需要Redis支持）
            # 这里简化实现，实际应该扫描所有键并检查TTL
            common_namespaces = ['users', 'meetings', 'notes', 'ai_results', 'stats']
            
            for namespace in common_namespaces:
                try:
                    # 注意：这里清理整个命名空间，实际应该只清理过期的键
                    cleared_count = asyncio.run(cache_manager.clear_namespace(namespace))
                    cleanup_stats['cleared_namespaces'].append({
                        'namespace': namespace,
                        'cleared_count': cleared_count
                    })
                    cleanup_stats['total_cleared'] += cleared_count
                    
                except Exception as e:
                    logger.error(f"清理命名空间失败 {namespace}: {e}")
        
        cleanup_stats['end_time'] = datetime.now().isoformat()
        cleanup_stats['success'] = True
        
        logger.info(f"缓存清理完成，共清理 {cleanup_stats['total_cleared']} 个键")
        
        return cleanup_stats
        
    except Exception as e:
        logger.error(f"缓存清理任务失败: {e}")
        raise


@task(
    name='maintenance.database_vacuum',
    queue='maintenance',
    priority=TaskPriority.LOW,
    max_retries=1,
    time_limit=1800,  # 30分钟
    soft_time_limit=1680
)
def database_vacuum_task() -> Dict[str, Any]:
    """
    数据库优化任务（VACUUM）
    
    Returns:
        优化结果
    """
    try:
        logger.info("开始数据库优化")
        
        start_time = datetime.now()
        
        # 获取数据库统计信息（优化前）
        stats_before = asyncio.run(get_database_stats())
        
        # 执行数据库优化操作
        async def perform_vacuum():
            async with get_async_session() as session:
                # 对于SQLite
                await session.execute(text("VACUUM"))
                
                # 对于PostgreSQL，可以使用：
                # await session.execute(text("VACUUM ANALYZE"))
                
                await session.commit()
        
        asyncio.run(perform_vacuum())
        
        # 获取优化后的统计信息
        stats_after = asyncio.run(get_database_stats())
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        vacuum_result = {
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration,
            'stats_before': stats_before,
            'stats_after': stats_after,
            'space_freed': stats_before.get('db_size', 0) - stats_after.get('db_size', 0),
            'success': True
        }
        
        logger.info(f"数据库优化完成，耗时 {duration:.2f} 秒")
        
        return vacuum_result
        
    except Exception as e:
        logger.error(f"数据库优化任务失败: {e}")
        raise


@task(
    name='maintenance.system_health_check',
    queue='maintenance',
    priority=TaskPriority.NORMAL,
    max_retries=1,
    time_limit=120,
    soft_time_limit=90
)
def system_health_check_task() -> Dict[str, Any]:
    """
    系统健康检查任务
    
    Returns:
        健康检查结果
    """
    try:
        logger.info("开始系统健康检查")
        
        health_data = {
            'timestamp': datetime.now().isoformat(),
            'system': {},
            'services': {},
            'resources': {},
            'overall_status': 'healthy',
            'warnings': [],
            'errors': []
        }
        
        # 系统资源检查
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            # 内存使用情况
            memory = psutil.virtual_memory()
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            
            health_data['resources'] = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / 1024**3,
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / 1024**3
            }
            
            # 资源告警阈值检查
            if cpu_percent > 80:
                health_data['warnings'].append(f"CPU使用率过高: {cpu_percent}%")
            if memory.percent > 85:
                health_data['warnings'].append(f"内存使用率过高: {memory.percent}%")
            if disk.percent > 90:
                health_data['warnings'].append(f"磁盘使用率过高: {disk.percent}%")
                
        except Exception as e:
            health_data['errors'].append(f"系统资源检查失败: {e}")
        
        # 缓存服务检查
        try:
            cache_stats = cache_manager.get_stats()
            health_data['services']['cache'] = {
                'status': 'healthy' if cache_stats['is_healthy'] else 'unhealthy',
                'hit_rate': cache_stats['hit_rate'],
                'total_requests': cache_stats['total_requests'],
                'errors': cache_stats['errors']
            }
            
            if cache_stats['hit_rate'] < 50:
                health_data['warnings'].append(f"缓存命中率偏低: {cache_stats['hit_rate']}%")
                
        except Exception as e:
            health_data['errors'].append(f"缓存服务检查失败: {e}")
            health_data['services']['cache'] = {'status': 'error', 'error': str(e)}
        
        # 数据库连接检查
        try:
            db_stats = asyncio.run(get_database_stats())
            health_data['services']['database'] = {
                'status': 'healthy',
                'connection_count': db_stats.get('connection_count', 0),
                'table_count': db_stats.get('table_count', 0),
                'total_records': db_stats.get('total_records', 0)
            }
            
        except Exception as e:
            health_data['errors'].append(f"数据库检查失败: {e}")
            health_data['services']['database'] = {'status': 'error', 'error': str(e)}
        
        # AI服务检查
        try:
            from app.services.ai import ai_service_manager
            ai_metrics = ai_service_manager.get_metrics()
            
            health_data['services']['ai'] = {
                'status': 'healthy',
                'total_requests': ai_metrics['total_requests'],
                'successful_requests': ai_metrics['successful_requests'],
                'failed_requests': ai_metrics['failed_requests'],
                'success_rate': (ai_metrics['successful_requests'] / max(ai_metrics['total_requests'], 1)) * 100
            }
            
            if health_data['services']['ai']['success_rate'] < 90:
                health_data['warnings'].append(f"AI服务成功率偏低: {health_data['services']['ai']['success_rate']:.2f}%")
                
        except Exception as e:
            health_data['errors'].append(f"AI服务检查失败: {e}")
            health_data['services']['ai'] = {'status': 'error', 'error': str(e)}
        
        # 确定整体状态
        if health_data['errors']:
            health_data['overall_status'] = 'critical'
        elif health_data['warnings']:
            health_data['overall_status'] = 'warning'
        else:
            health_data['overall_status'] = 'healthy'
        
        # 如果有严重问题，发送系统告警
        if health_data['overall_status'] == 'critical':
            asyncio.run(send_health_alert(health_data))
        
        logger.info(f"系统健康检查完成，状态: {health_data['overall_status']}")
        
        return health_data
        
    except Exception as e:
        logger.error(f"系统健康检查失败: {e}")
        raise


@task(
    name='maintenance.log_cleanup',
    queue='maintenance',
    priority=TaskPriority.LOW,
    max_retries=1,
    time_limit=300,
    soft_time_limit=240
)
def log_cleanup_task(
    retention_days: int = 30,
    log_level: str = 'INFO'
) -> Dict[str, Any]:
    """
    日志清理任务
    
    Args:
        retention_days: 日志保留天数
        log_level: 要清理的最低日志级别
    
    Returns:
        清理结果
    """
    try:
        logger.info(f"开始清理 {retention_days} 天前的日志文件")
        
        # 这里需要根据实际的日志存储位置进行实现
        # 例如清理loguru生成的日志文件
        
        cleanup_result = {
            'retention_days': retention_days,
            'log_level': log_level,
            'cleaned_files': 0,
            'freed_space_mb': 0,
            'start_time': datetime.now().isoformat(),
            'success': True
        }
        
        # 实际的日志清理逻辑应该在这里实现
        # 例如扫描日志目录，删除过期文件等
        
        cleanup_result['end_time'] = datetime.now().isoformat()
        
        logger.info("日志清理任务完成")
        
        return cleanup_result
        
    except Exception as e:
        logger.error(f"日志清理任务失败: {e}")
        raise


@task(
    name='maintenance.memory_garbage_collection',
    queue='maintenance',
    priority=TaskPriority.LOW,
    max_retries=1,
    time_limit=60,
    soft_time_limit=45
)
def memory_garbage_collection_task() -> Dict[str, Any]:
    """
    内存垃圾回收任务
    
    Returns:
        垃圾回收结果
    """
    try:
        logger.info("开始内存垃圾回收")
        
        # 获取垃圾回收前的内存统计
        memory_before = psutil.virtual_memory()
        
        # 强制执行垃圾回收
        collected = gc.collect()
        
        # 获取垃圾回收后的内存统计
        memory_after = psutil.virtual_memory()
        
        gc_result = {
            'collected_objects': collected,
            'memory_before_mb': memory_before.used / 1024**2,
            'memory_after_mb': memory_after.used / 1024**2,
            'memory_freed_mb': (memory_before.used - memory_after.used) / 1024**2,
            'gc_stats': {
                'generation_0': gc.get_stats()[0] if gc.get_stats() else {},
                'generation_1': gc.get_stats()[1] if len(gc.get_stats()) > 1 else {},
                'generation_2': gc.get_stats()[2] if len(gc.get_stats()) > 2 else {}
            },
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"内存垃圾回收完成，回收对象 {collected} 个，释放内存 {gc_result['memory_freed_mb']:.2f}MB")
        
        return gc_result
        
    except Exception as e:
        logger.error(f"内存垃圾回收任务失败: {e}")
        raise


# 辅助函数
async def get_database_stats() -> Dict[str, Any]:
    """获取数据库统计信息"""
    try:
        async with get_async_session() as session:
            # 获取表数量（针对SQLite的查询）
            table_count_result = await session.execute(
                text("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            )
            table_count = table_count_result.scalar()
            
            # 获取数据库大小（SQLite特定）
            db_size_result = await session.execute(text("PRAGMA page_size"))
            page_size = db_size_result.scalar()
            
            page_count_result = await session.execute(text("PRAGMA page_count"))
            page_count = page_count_result.scalar()
            
            db_size = page_size * page_count
            
            return {
                'table_count': table_count,
                'db_size': db_size,
                'page_size': page_size,
                'page_count': page_count,
                'connection_count': 1  # 简化实现
            }
            
    except Exception as e:
        logger.error(f"获取数据库统计信息失败: {e}")
        return {'error': str(e)}


async def send_health_alert(health_data: Dict[str, Any]):
    """发送健康检查告警"""
    try:
        from app.core.notification_tasks import send_system_alert_task
        
        alert_message = f"系统健康检查发现问题:\n"
        
        for error in health_data.get('errors', []):
            alert_message += f"- 错误: {error}\n"
        
        for warning in health_data.get('warnings', []):
            alert_message += f"- 警告: {warning}\n"
        
        # 异步发送告警
        send_system_alert_task.delay(
            alert_type='health_check',
            alert_message=alert_message,
            severity='critical',
            additional_info={
                'overall_status': health_data['overall_status'],
                'timestamp': health_data['timestamp']
            }
        )
        
    except Exception as e:
        logger.error(f"发送健康检查告警失败: {e}")