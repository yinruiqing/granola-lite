"""
简化版任务管理器 - 避免复杂导入
"""

from typing import Dict, Any, Optional
import asyncio
from datetime import datetime
from loguru import logger


class SimpleTaskManager:
    """简化任务管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, Any] = {}
        self.running = False
    
    async def start(self):
        """启动任务管理器"""
        self.running = True
        logger.info("Simple task manager started")
    
    async def stop(self):
        """停止任务管理器"""
        self.running = False
        logger.info("Simple task manager stopped")
    
    def add_task(self, name: str, func, *args, **kwargs):
        """添加任务"""
        self.tasks[name] = {
            'func': func,
            'args': args,
            'kwargs': kwargs,
            'created_at': datetime.now()
        }
        logger.info(f"Task '{name}' added")
    
    async def run_task(self, name: str) -> Any:
        """运行任务"""
        if name not in self.tasks:
            raise ValueError(f"Task '{name}' not found")
        
        task = self.tasks[name]
        try:
            if asyncio.iscoroutinefunction(task['func']):
                result = await task['func'](*task['args'], **task['kwargs'])
            else:
                result = task['func'](*task['args'], **task['kwargs'])
            
            logger.info(f"Task '{name}' completed successfully")
            return result
        except Exception as e:
            logger.error(f"Task '{name}' failed: {str(e)}")
            raise


# 全局实例
simple_task_manager = SimpleTaskManager()