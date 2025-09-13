"""
异步处理优化系统
"""

from typing import Dict, Any, List, Optional, Callable, AsyncGenerator, Union
import asyncio
import time
import functools
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from app.core.monitoring import metrics_collector


class TaskPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AsyncTask:
    """异步任务"""
    id: str
    func: Callable
    args: tuple
    kwargs: dict
    priority: TaskPriority
    created_at: datetime
    timeout: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3


class AsyncOptimizer:
    """异步处理优化器"""
    
    def __init__(self):
        self.max_concurrent_tasks = 50
        self.task_timeout = 300  # 5分钟
        self.retry_delay = 1.0
        self.semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.completed_tasks: Dict[str, Any] = {}
        self.failed_tasks: Dict[str, Exception] = {}
        
    async def submit_task(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: Optional[float] = None,
        max_retries: int = 3
    ) -> str:
        """提交异步任务"""
        task_id = f"task_{int(time.time() * 1000000)}"
        
        task = AsyncTask(
            id=task_id,
            func=func,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            created_at=datetime.now(),
            timeout=timeout or self.task_timeout,
            max_retries=max_retries
        )
        
        await self.task_queue.put(task)
        metrics_collector.record_metric("async_task_submitted", 1.0)
        
        logger.info(f"异步任务已提交: {task_id}")
        return task_id
    
    async def process_tasks(self):
        """处理任务队列"""
        while True:
            try:
                # 获取任务（按优先级排序）
                tasks_to_process = []
                
                # 从队列中获取所有可用任务
                while not self.task_queue.empty():
                    try:
                        task = self.task_queue.get_nowait()
                        tasks_to_process.append(task)
                    except asyncio.QueueEmpty:
                        break
                
                # 按优先级排序
                tasks_to_process.sort(key=lambda t: t.priority.value, reverse=True)
                
                # 处理任务
                for task in tasks_to_process:
                    if len(self.running_tasks) >= self.max_concurrent_tasks:
                        # 重新放回队列
                        await self.task_queue.put(task)
                    else:
                        # 启动任务
                        asyncio_task = asyncio.create_task(self._execute_task(task))
                        self.running_tasks[task.id] = asyncio_task
                
                # 短暂等待
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"处理任务队列时出错: {e}")
                await asyncio.sleep(1.0)
    
    async def _execute_task(self, task: AsyncTask):
        """执行单个任务"""
        start_time = time.time()
        
        try:
            async with self.semaphore:
                # 执行任务
                if asyncio.iscoroutinefunction(task.func):
                    result = await asyncio.wait_for(
                        task.func(*task.args, **task.kwargs),
                        timeout=task.timeout
                    )
                else:
                    # 在线程池中执行同步函数
                    loop = asyncio.get_event_loop()
                    with ThreadPoolExecutor() as executor:
                        result = await loop.run_in_executor(
                            executor,
                            functools.partial(task.func, *task.args, **task.kwargs)
                        )
                
                # 记录成功结果
                self.completed_tasks[task.id] = {
                    "result": result,
                    "execution_time": time.time() - start_time,
                    "completed_at": datetime.now().isoformat()
                }
                
                metrics_collector.record_metric("async_task_completed", 1.0)
                metrics_collector.record_metric("async_task_execution_time", time.time() - start_time)
                
                logger.info(f"任务完成: {task.id}, 耗时: {time.time() - start_time:.3f}s")
        
        except asyncio.TimeoutError:
            logger.warning(f"任务超时: {task.id}")
            await self._handle_task_failure(task, TimeoutError("Task timeout"))
            
        except Exception as e:
            logger.error(f"任务执行失败: {task.id}, 错误: {e}")
            await self._handle_task_failure(task, e)
        
        finally:
            # 清理运行中的任务
            self.running_tasks.pop(task.id, None)
    
    async def _handle_task_failure(self, task: AsyncTask, error: Exception):
        """处理任务失败"""
        task.retry_count += 1
        
        if task.retry_count <= task.max_retries:
            # 重试任务
            logger.info(f"重试任务: {task.id}, 第{task.retry_count}次重试")
            
            # 等待一段时间后重试
            await asyncio.sleep(self.retry_delay * task.retry_count)
            await self.task_queue.put(task)
            
            metrics_collector.record_metric("async_task_retried", 1.0)
        else:
            # 记录失败
            self.failed_tasks[task.id] = error
            metrics_collector.record_metric("async_task_failed", 1.0)
            logger.error(f"任务最终失败: {task.id}, 已达到最大重试次数")
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        if task_id in self.running_tasks:
            return {
                "status": "running",
                "task_id": task_id,
                "started_at": datetime.now().isoformat()  # 实际应该记录真实的开始时间
            }
        elif task_id in self.completed_tasks:
            return {
                "status": "completed",
                "task_id": task_id,
                **self.completed_tasks[task_id]
            }
        elif task_id in self.failed_tasks:
            return {
                "status": "failed",
                "task_id": task_id,
                "error": str(self.failed_tasks[task_id])
            }
        else:
            return {
                "status": "not_found",
                "task_id": task_id
            }
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.cancel()
            self.running_tasks.pop(task_id, None)
            
            metrics_collector.record_metric("async_task_cancelled", 1.0)
            logger.info(f"任务已取消: {task_id}")
            return True
        
        return False
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return {
            "queue_size": self.task_queue.qsize(),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "max_concurrent": self.max_concurrent_tasks,
            "timestamp": datetime.now().isoformat()
        }


class ConcurrencyOptimizer:
    """并发优化器"""
    
    def __init__(self):
        self.default_batch_size = 100
        self.default_max_concurrent = 10
    
    async def parallel_execute(
        self,
        func: Callable,
        items: List[Any],
        max_concurrent: int = None,
        batch_size: int = None
    ) -> List[Any]:
        """并行执行函数"""
        max_concurrent = max_concurrent or self.default_max_concurrent
        batch_size = batch_size or self.default_batch_size
        
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []
        
        async def execute_item(item):
            async with semaphore:
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(item)
                    else:
                        loop = asyncio.get_event_loop()
                        with ThreadPoolExecutor() as executor:
                            return await loop.run_in_executor(executor, func, item)
                except Exception as e:
                    logger.warning(f"并行执行项目失败: {e}")
                    return None
        
        # 分批处理
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_tasks = [execute_item(item) for item in batch]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            results.extend(batch_results)
            
            # 短暂暂停以避免过载
            await asyncio.sleep(0.01)
        
        return results
    
    async def batch_process_async(
        self,
        async_generator: AsyncGenerator,
        process_func: Callable,
        batch_size: int = None
    ) -> AsyncGenerator[List[Any], None]:
        """批量处理异步生成器"""
        batch_size = batch_size or self.default_batch_size
        batch = []
        
        async for item in async_generator:
            batch.append(item)
            
            if len(batch) >= batch_size:
                # 处理这一批
                processed_batch = await self.parallel_execute(
                    process_func,
                    batch,
                    max_concurrent=10
                )
                yield processed_batch
                batch = []
        
        # 处理剩余的项目
        if batch:
            processed_batch = await self.parallel_execute(
                process_func,
                batch,
                max_concurrent=10
            )
            yield processed_batch
    
    def throttle(self, calls_per_second: float):
        """限流装饰器"""
        min_interval = 1.0 / calls_per_second
        last_call_time = 0
        
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                nonlocal last_call_time
                
                current_time = time.time()
                elapsed = current_time - last_call_time
                
                if elapsed < min_interval:
                    await asyncio.sleep(min_interval - elapsed)
                
                last_call_time = time.time()
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def circuit_breaker(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60,
        expected_exception: type = Exception
    ):
        """熔断器装饰器"""
        failure_count = 0
        last_failure_time = 0
        state = "closed"  # closed, open, half-open
        
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                nonlocal failure_count, last_failure_time, state
                
                current_time = time.time()
                
                # 检查是否应该从open状态转换到half-open状态
                if state == "open" and current_time - last_failure_time > recovery_timeout:
                    state = "half-open"
                    failure_count = 0
                
                # 如果熔断器是open状态，直接抛出异常
                if state == "open":
                    raise Exception("Circuit breaker is open")
                
                try:
                    result = await func(*args, **kwargs)
                    
                    # 成功执行，重置状态
                    if state == "half-open":
                        state = "closed"
                        failure_count = 0
                    
                    return result
                    
                except expected_exception as e:
                    failure_count += 1
                    last_failure_time = current_time
                    
                    # 检查是否达到失败阈值
                    if failure_count >= failure_threshold:
                        state = "open"
                        logger.warning(f"熔断器开启: {func.__name__}")
                    
                    raise e
            
            return wrapper
        return decorator


class ResourceOptimizer:
    """资源优化器"""
    
    def __init__(self):
        self.memory_threshold = 0.8  # 80%
        self.cpu_threshold = 0.8     # 80%
    
    async def monitor_resources(self) -> Dict[str, Any]:
        """监控资源使用"""
        import psutil
        
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.used / disk.total * 100
            
            # 网络IO
            network = psutil.net_io_counters()
            
            resource_status = {
                "cpu": {
                    "percent": cpu_percent,
                    "cores": psutil.cpu_count(),
                    "status": "warning" if cpu_percent > self.cpu_threshold * 100 else "normal"
                },
                "memory": {
                    "percent": memory_percent,
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "status": "warning" if memory_percent > self.memory_threshold * 100 else "normal"
                },
                "disk": {
                    "percent": disk_percent,
                    "total_gb": disk.total / (1024**3),
                    "free_gb": disk.free / (1024**3),
                    "status": "warning" if disk_percent > 90 else "normal"
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # 记录指标
            metrics_collector.record_metric("system_cpu_usage_percent", cpu_percent)
            metrics_collector.record_metric("system_memory_usage_percent", memory_percent)
            metrics_collector.record_metric("system_disk_usage_percent", disk_percent)
            
            return resource_status
            
        except Exception as e:
            logger.error(f"监控系统资源失败: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def optimize_memory_usage(self) -> Dict[str, Any]:
        """优化内存使用"""
        try:
            import gc
            
            # 强制垃圾回收
            collected = gc.collect()
            
            # 获取当前内存使用
            import psutil
            memory = psutil.virtual_memory()
            
            result = {
                "garbage_collected": collected,
                "current_memory_percent": memory.percent,
                "optimization_time": datetime.now().isoformat()
            }
            
            logger.info(f"内存优化完成，回收了 {collected} 个对象")
            return result
            
        except Exception as e:
            logger.error(f"内存优化失败: {e}")
            return {
                "error": str(e),
                "optimization_time": datetime.now().isoformat()
            }
    
    def memory_profiler(self, enable_profiling: bool = True):
        """内存分析装饰器"""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                if not enable_profiling:
                    return await func(*args, **kwargs)
                
                import psutil
                import os
                
                process = psutil.Process(os.getpid())
                memory_before = process.memory_info().rss
                
                start_time = time.time()
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                memory_after = process.memory_info().rss
                memory_diff = memory_after - memory_before
                
                logger.info(
                    f"函数 {func.__name__} - "
                    f"执行时间: {execution_time:.3f}s, "
                    f"内存变化: {memory_diff / 1024 / 1024:.2f}MB"
                )
                
                metrics_collector.record_metric("function_execution_time", execution_time)
                metrics_collector.record_metric("function_memory_usage", memory_diff)
                
                return result
            
            return wrapper
        return decorator


# 全局实例
async_optimizer = AsyncOptimizer()
concurrency_optimizer = ConcurrencyOptimizer()
resource_optimizer = ResourceOptimizer()


__all__ = [
    'AsyncOptimizer',
    'ConcurrencyOptimizer', 
    'ResourceOptimizer',
    'TaskPriority',
    'AsyncTask',
    'async_optimizer',
    'concurrency_optimizer',
    'resource_optimizer'
]