"""
Celery配置和任务定义
"""

from celery import Celery
from app.config import settings

# 创建Celery实例
celery_app = Celery(
    "granola",
    broker=settings.redis_url if hasattr(settings, 'redis_url') else "redis://localhost:6379/0",
    backend=settings.redis_url if hasattr(settings, 'redis_url') else "redis://localhost:6379/0",
    include=[
        'app.tasks.transcription',
        'app.tasks.ai_processing',
        'app.tasks.file_processing',
        'app.tasks.notifications'
    ]
)

# Celery配置
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # 任务路由
    task_routes={
        'app.tasks.transcription.*': {'queue': 'transcription'},
        'app.tasks.ai_processing.*': {'queue': 'ai'},
        'app.tasks.file_processing.*': {'queue': 'files'},
        'app.tasks.notifications.*': {'queue': 'notifications'},
    },
    
    # 任务过期时间
    task_time_limit=300,  # 5分钟
    task_soft_time_limit=240,  # 4分钟
    
    # 结果过期时间
    result_expires=3600,  # 1小时
    
    # 任务重试配置
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # 定时任务
    beat_schedule={
        'cleanup-old-tasks': {
            'task': 'app.tasks.maintenance.cleanup_old_tasks',
            'schedule': 3600.0,  # 每小时执行一次
        },
        'health-check': {
            'task': 'app.tasks.maintenance.health_check',
            'schedule': 300.0,  # 每5分钟执行一次
        },
    },
)