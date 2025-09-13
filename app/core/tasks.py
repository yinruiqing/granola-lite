"""
任务队列系统 - Celery集成和异步任务处理
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass, asdict
from celery import Celery, Task
from celery.result import AsyncResult
from kombu import Queue
import redis.asyncio as aioredis

from app.config import settings
from app.core.events import event_emitter, Events
from loguru import logger


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    REVOKED = "revoked"


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    traceback: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = None


@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    name: str
    args: List[Any]
    kwargs: Dict[str, Any]
    priority: TaskPriority
    eta: Optional[datetime] = None
    expires: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = None
    user_id: Optional[int] = None
    metadata: Dict[str, Any] = None


class CeleryConfig:
    """Celery配置"""
    
    # Redis作为消息代理和结果后端
    broker_url = settings.redis_url
    result_backend = settings.redis_url
    
    # 任务序列化
    task_serializer = 'json'
    accept_content = ['json']
    result_serializer = 'json'
    timezone = 'UTC'
    enable_utc = True
    
    # 队列配置
    task_routes = {
        'app.tasks.ai.*': {'queue': 'ai'},
        'app.tasks.audio.*': {'queue': 'audio'},
        'app.tasks.file.*': {'queue': 'file'},
        'app.tasks.notification.*': {'queue': 'notification'},
        'app.tasks.maintenance.*': {'queue': 'maintenance'},
    }
    
    # 队列定义
    task_queues = (
        Queue('default', routing_key='default'),
        Queue('ai', routing_key='ai'),
        Queue('audio', routing_key='audio'), 
        Queue('file', routing_key='file'),
        Queue('notification', routing_key='notification'),
        Queue('maintenance', routing_key='maintenance'),
    )
    
    # 工作进程配置
    worker_prefetch_multiplier = 2
    worker_max_tasks_per_child = 1000
    worker_disable_rate_limits = False
    
    # 任务执行配置
    task_acks_late = True
    task_reject_on_worker_lost = True
    task_time_limit = 300  # 5分钟硬限制
    task_soft_time_limit = 240  # 4分钟软限制
    
    # 结果过期设置
    result_expires = 3600  # 1小时
    
    # 监控配置
    worker_send_task_events = True
    task_send_sent_event = True
    
    # 错误处理
    task_annotations = {
        '*': {'rate_limit': '100/m'},  # 默认限流
        'app.tasks.ai.transcribe_audio': {'rate_limit': '10/m'},
        'app.tasks.notification.send_email': {'rate_limit': '50/m'},
    }


# 创建Celery应用
celery_app = Celery('granola', config_source=CeleryConfig)


class BaseTask(Task):
    """基础任务类"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """任务成功时的回调"""
        logger.info(f"Task {task_id} ({self.name}) succeeded")
        
        # 发射任务完成事件
        asyncio.create_task(event_emitter.emit(Events.TASK_SUCCESS, {
            'task_id': task_id,
            'task_name': self.name,
            'result': retval,
            'args': args,
            'kwargs': kwargs
        }))
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的回调"""
        logger.error(f"Task {task_id} ({self.name}) failed: {exc}")
        
        # 发射任务失败事件
        asyncio.create_task(event_emitter.emit(Events.TASK_FAILURE, {
            'task_id': task_id,
            'task_name': self.name,
            'error': str(exc),
            'traceback': einfo.traceback,
            'args': args,
            'kwargs': kwargs
        }))
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """任务重试时的回调"""
        logger.warning(f"Task {task_id} ({self.name}) retrying: {exc}")
        
        # 发射任务重试事件
        asyncio.create_task(event_emitter.emit(Events.TASK_RETRY, {
            'task_id': task_id,
            'task_name': self.name,
            'error': str(exc),
            'retry_count': self.request.retries,
            'args': args,
            'kwargs': kwargs
        }))


# 设置基础任务类
celery_app.Task = BaseTask


class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self.task_registry: Dict[str, Callable] = {}
        
        # 任务统计
        self.stats = {
            'total_submitted': 0,
            'total_completed': 0,
            'total_failed': 0,
            'total_retried': 0,
            'active_tasks': 0
        }
    
    async def initialize(self):
        """初始化任务管理器"""
        try:
            # 初始化Redis连接用于任务状态追踪
            self.redis_client = await aioredis.from_url(settings.redis_url)
            await self.redis_client.ping()
            
            logger.info("任务管理器初始化成功")
            
        except Exception as e:
            logger.error(f"任务管理器初始化失败: {e}")
            raise
    
    async def shutdown(self):
        """关闭任务管理器"""
        try:
            if self.redis_client:
                await self.redis_client.close()
            
            logger.info("任务管理器已关闭")
            
        except Exception as e:
            logger.error(f"任务管理器关闭失败: {e}")
    
    def submit_task(
        self,
        task_name: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        eta: Optional[datetime] = None,
        expires: Optional[datetime] = None,
        retry_count: int = 0,
        max_retries: int = 3,
        user_id: Optional[int] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """提交任务"""
        try:
            args = args or []
            kwargs = kwargs or {}
            metadata = metadata or {}
            
            # 获取Celery任务
            task = celery_app.tasks.get(task_name)
            if not task:
                raise ValueError(f"任务 {task_name} 不存在")
            
            # 设置任务选项
            task_options = {
                'priority': priority.value,
                'eta': eta,
                'expires': expires,
                'retry': True,
                'max_retries': max_retries,
            }
            
            # 添加元数据到kwargs
            kwargs['_task_metadata'] = {
                'user_id': user_id,
                'created_at': datetime.now().isoformat(),
                'priority': priority.value,
                'metadata': metadata
            }
            
            # 提交任务
            result = task.apply_async(
                args=args,
                kwargs=kwargs,
                **{k: v for k, v in task_options.items() if v is not None}
            )
            
            # 更新统计
            self.stats['total_submitted'] += 1
            self.stats['active_tasks'] += 1
            
            logger.info(f"任务已提交: {task_name} (ID: {result.id})")
            
            return result.id
            
        except Exception as e:
            logger.error(f"提交任务失败: {e}")
            raise
    
    def get_task_result(self, task_id: str) -> TaskResult:
        """获取任务结果"""
        try:
            result = AsyncResult(task_id, app=celery_app)
            
            # 转换状态
            status_mapping = {
                'PENDING': TaskStatus.PENDING,
                'STARTED': TaskStatus.STARTED,
                'SUCCESS': TaskStatus.SUCCESS,
                'FAILURE': TaskStatus.FAILURE,
                'RETRY': TaskStatus.RETRY,
                'REVOKED': TaskStatus.REVOKED,
            }
            
            status = status_mapping.get(result.status, TaskStatus.PENDING)
            
            # 构建任务结果
            task_result = TaskResult(
                task_id=task_id,
                status=status,
                result=result.result if status == TaskStatus.SUCCESS else None,
                error=str(result.result) if status == TaskStatus.FAILURE else None,
                traceback=result.traceback if status == TaskStatus.FAILURE else None,
                retry_count=getattr(result, 'retries', 0)
            )
            
            # 获取任务信息
            info = result.info
            if isinstance(info, dict):
                task_result.metadata = info.get('metadata', {})
            
            return task_result
            
        except Exception as e:
            logger.error(f"获取任务结果失败: {e}")
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILURE,
                error=str(e)
            )
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            celery_app.control.revoke(task_id, terminate=True)
            logger.info(f"任务已取消: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"取消任务失败: {e}")
            return False
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """获取活跃任务列表"""
        try:
            active = celery_app.control.inspect().active()
            if not active:
                return []
            
            tasks = []
            for worker, task_list in active.items():
                for task in task_list:
                    tasks.append({
                        'worker': worker,
                        'task_id': task['id'],
                        'name': task['name'],
                        'args': task['args'],
                        'kwargs': task['kwargs'],
                        'time_start': task.get('time_start'),
                    })
            
            return tasks
            
        except Exception as e:
            logger.error(f"获取活跃任务失败: {e}")
            return []
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        try:
            stats = celery_app.control.inspect().stats()
            reserved = celery_app.control.inspect().reserved()
            active = celery_app.control.inspect().active()
            
            queue_stats = {}
            
            if stats:
                for worker, worker_stats in stats.items():
                    queue_name = worker.split('@')[0] if '@' in worker else 'default'
                    if queue_name not in queue_stats:
                        queue_stats[queue_name] = {
                            'workers': 0,
                            'active_tasks': 0,
                            'reserved_tasks': 0,
                            'total_tasks': worker_stats.get('total', {}).get('tasks', 0)
                        }
                    
                    queue_stats[queue_name]['workers'] += 1
            
            if active:
                for worker, task_list in active.items():
                    queue_name = worker.split('@')[0] if '@' in worker else 'default'
                    if queue_name in queue_stats:
                        queue_stats[queue_name]['active_tasks'] += len(task_list)
            
            if reserved:
                for worker, task_list in reserved.items():
                    queue_name = worker.split('@')[0] if '@' in worker else 'default'
                    if queue_name in queue_stats:
                        queue_stats[queue_name]['reserved_tasks'] += len(task_list)
            
            return queue_stats
            
        except Exception as e:
            logger.error(f"获取队列统计失败: {e}")
            return {}
    
    def get_worker_stats(self) -> Dict[str, Any]:
        """获取工作进程统计信息"""
        try:
            stats = celery_app.control.inspect().stats()
            if not stats:
                return {}
            
            worker_stats = {}
            for worker, worker_info in stats.items():
                worker_stats[worker] = {
                    'status': 'online',
                    'processed_tasks': worker_info.get('total', {}).get('tasks', 0),
                    'active_tasks': len(self.get_active_tasks()),
                    'load_avg': worker_info.get('rusage', {}).get('utime', 0),
                    'memory_usage': worker_info.get('rusage', {}).get('maxrss', 0),
                    'pool_processes': worker_info.get('pool', {}).get('max-concurrency', 0)
                }
            
            return worker_stats
            
        except Exception as e:
            logger.error(f"获取工作进程统计失败: {e}")
            return {}


# 全局任务管理器实例
task_manager = TaskManager()


# 任务装饰器
def task(
    name: str = None,
    queue: str = 'default',
    priority: TaskPriority = TaskPriority.NORMAL,
    max_retries: int = 3,
    time_limit: int = 300,
    soft_time_limit: int = 240
):
    """任务装饰器"""
    def decorator(func):
        task_name = name or f"{func.__module__}.{func.__name__}"
        
        @celery_app.task(
            name=task_name,
            queue=queue,
            max_retries=max_retries,
            time_limit=time_limit,
            soft_time_limit=soft_time_limit,
            bind=True,
            base=BaseTask
        )
        def wrapper(self, *args, **kwargs):
            # 提取元数据
            metadata = kwargs.pop('_task_metadata', {})
            
            try:
                # 更新任务状态
                self.update_state(
                    state='STARTED',
                    meta={'started_at': datetime.now().isoformat()}
                )
                
                # 执行任务
                result = func(*args, **kwargs)
                
                # 更新统计
                task_manager.stats['total_completed'] += 1
                task_manager.stats['active_tasks'] = max(0, task_manager.stats['active_tasks'] - 1)
                
                return result
                
            except Exception as exc:
                # 更新统计
                task_manager.stats['total_failed'] += 1
                task_manager.stats['active_tasks'] = max(0, task_manager.stats['active_tasks'] - 1)
                
                # 重试逻辑
                if self.request.retries < self.max_retries:
                    task_manager.stats['total_retried'] += 1
                    
                    # 计算重试延迟（指数退避）
                    countdown = 2 ** self.request.retries
                    
                    raise self.retry(exc=exc, countdown=countdown)
                else:
                    raise exc
        
        return wrapper
    return decorator


# 导入任务模块（在文件末尾避免循环导入）
def register_tasks():
    """注册所有任务"""
    try:
        from . import ai_tasks, audio_tasks, file_tasks, notification_tasks, maintenance_tasks
        logger.info("所有任务模块已注册")
    except ImportError as e:
        logger.warning(f"部分任务模块注册失败: {e}")


# 在模块加载时注册任务
register_tasks()


__all__ = [
    'celery_app',
    'task_manager',
    'TaskStatus',
    'TaskPriority',
    'TaskResult',
    'TaskInfo',
    'BaseTask',
    'task'
]