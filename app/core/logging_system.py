"""
高级日志系统 - 结构化日志、日志聚合和分析
"""

import sys
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import gzip
import shutil
from collections import defaultdict, deque

from loguru import logger
from app.core.events import event_emitter, Events
from app.config import settings


class LogLevel(Enum):
    """日志级别枚举"""
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: LogLevel
    message: str
    module: str
    function: str
    line: int
    extra: Dict[str, Any] = None
    exception: Optional[str] = None
    trace_id: Optional[str] = None
    user_id: Optional[int] = None
    request_id: Optional[str] = None


class LogAggregator:
    """日志聚合器"""
    
    def __init__(self):
        self.log_buffer: deque = deque(maxlen=10000)  # 内存中保留最近的日志
        self.log_stats: Dict[str, int] = defaultdict(int)
        self.error_patterns: Dict[str, int] = defaultdict(int)
        self.slow_queries: deque = deque(maxlen=100)  # 慢查询日志
        
        # 日志分析任务
        self.analysis_task: Optional[asyncio.Task] = None
        self.analysis_interval = 300  # 5分钟分析一次
    
    async def start(self):
        """启动日志聚合器"""
        try:
            self.analysis_task = asyncio.create_task(self._analysis_loop())
            logger.info("日志聚合器启动成功")
            
        except Exception as e:
            logger.error(f"日志聚合器启动失败: {e}")
            raise
    
    async def stop(self):
        """停止日志聚合器"""
        try:
            if self.analysis_task:
                self.analysis_task.cancel()
                try:
                    await self.analysis_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("日志聚合器已停止")
            
        except Exception as e:
            logger.error(f"日志聚合器停止失败: {e}")
    
    def add_log_entry(self, entry: LogEntry):
        """添加日志条目"""
        try:
            # 添加到缓冲区
            self.log_buffer.append(entry)
            
            # 更新统计
            self.log_stats[entry.level.value] += 1
            self.log_stats['total'] += 1
            
            # 错误模式分析
            if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                pattern_key = f"{entry.module}.{entry.function}"
                self.error_patterns[pattern_key] += 1
            
            # 慢查询检测
            if entry.extra and entry.extra.get('query_duration', 0) > 1.0:
                self.slow_queries.append({
                    'timestamp': entry.timestamp.isoformat(),
                    'query': entry.extra.get('query', ''),
                    'duration': entry.extra.get('query_duration'),
                    'module': entry.module
                })
            
        except Exception as e:
            print(f"添加日志条目失败: {e}")  # 避免递归日志
    
    async def _analysis_loop(self):
        """日志分析循环"""
        while True:
            try:
                await asyncio.sleep(self.analysis_interval)
                await self._analyze_logs()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"日志分析失败: {e}")
    
    async def _analyze_logs(self):
        """分析日志模式"""
        try:
            # 分析错误频率
            if self.error_patterns:
                # 找出错误频率最高的模块
                top_error_pattern = max(self.error_patterns.items(), key=lambda x: x[1])
                
                if top_error_pattern[1] > 10:  # 错误次数超过阈值
                    await event_emitter.emit(Events.SYSTEM_ERROR, {
                        'pattern': top_error_pattern[0],
                        'error_count': top_error_pattern[1],
                        'analysis_type': 'high_error_frequency'
                    })
            
            # 分析慢查询
            if len(self.slow_queries) > 10:
                avg_duration = sum(q['duration'] for q in self.slow_queries) / len(self.slow_queries)
                
                if avg_duration > 2.0:  # 平均查询时间超过2秒
                    await event_emitter.emit(Events.SYSTEM_ERROR, {
                        'average_query_duration': avg_duration,
                        'slow_query_count': len(self.slow_queries),
                        'analysis_type': 'slow_query_pattern'
                    })
            
            # 重置部分统计（避免无限累积）
            if self.log_stats['total'] > 100000:
                # 保留错误和警告统计，重置其他
                preserved_stats = {
                    'ERROR': self.log_stats.get('ERROR', 0),
                    'CRITICAL': self.log_stats.get('CRITICAL', 0),
                    'WARNING': self.log_stats.get('WARNING', 0)
                }
                
                self.log_stats.clear()
                self.log_stats.update(preserved_stats)
                self.log_stats['total'] = sum(preserved_stats.values())
            
        except Exception as e:
            logger.error(f"日志分析处理失败: {e}")
    
    def get_log_stats(self) -> Dict[str, Any]:
        """获取日志统计"""
        return {
            'levels': dict(self.log_stats),
            'buffer_size': len(self.log_buffer),
            'error_patterns': dict(self.error_patterns),
            'slow_queries_count': len(self.slow_queries),
            'analysis_interval': self.analysis_interval
        }
    
    def get_recent_logs(self, level: LogLevel = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近的日志"""
        logs = list(self.log_buffer)
        
        if level:
            logs = [log for log in logs if log.level == level]
        
        # 按时间倒序排列
        logs.sort(key=lambda x: x.timestamp, reverse=True)
        
        return [
            {
                'timestamp': log.timestamp.isoformat(),
                'level': log.level.value,
                'message': log.message,
                'module': log.module,
                'function': log.function,
                'line': log.line,
                'extra': log.extra,
                'exception': log.exception,
                'trace_id': log.trace_id,
                'user_id': log.user_id,
                'request_id': log.request_id
            }
            for log in logs[:limit]
        ]
    
    def get_error_patterns(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取错误模式"""
        sorted_patterns = sorted(
            self.error_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {'pattern': pattern, 'count': count}
            for pattern, count in sorted_patterns[:limit]
        ]
    
    def get_slow_queries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取慢查询"""
        return list(self.slow_queries)[-limit:]


class StructuredLogHandler:
    """结构化日志处理器"""
    
    def __init__(self, log_aggregator: LogAggregator):
        self.log_aggregator = log_aggregator
    
    def handle_log_record(self, record):
        """处理日志记录"""
        try:
            # 解析日志级别
            try:
                level = LogLevel(record["level"].name)
            except (ValueError, KeyError):
                level = LogLevel.INFO
            
            # 提取额外信息
            extra = record.get("extra", {})
            
            # 创建日志条目
            log_entry = LogEntry(
                timestamp=record["time"],
                level=level,
                message=record["message"],
                module=record.get("name", ""),
                function=record.get("function", ""),
                line=record.get("line", 0),
                extra=extra,
                exception=record.get("exception", {}).get("repr") if record.get("exception") else None,
                trace_id=extra.get("trace_id"),
                user_id=extra.get("user_id"),
                request_id=extra.get("request_id")
            )
            
            # 添加到聚合器
            self.log_aggregator.add_log_entry(log_entry)
            
        except Exception as e:
            print(f"处理日志记录失败: {e}")


class LogRotator:
    """日志轮转器"""
    
    def __init__(self, log_dir: str = "logs", max_size_mb: int = 100, keep_days: int = 30):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.keep_days = keep_days
        
        # 轮转任务
        self.rotation_task: Optional[asyncio.Task] = None
        self.rotation_interval = 3600  # 每小时检查一次
    
    async def start(self):
        """启动日志轮转器"""
        try:
            self.rotation_task = asyncio.create_task(self._rotation_loop())
            logger.info("日志轮转器启动成功")
            
        except Exception as e:
            logger.error(f"日志轮转器启动失败: {e}")
            raise
    
    async def stop(self):
        """停止日志轮转器"""
        try:
            if self.rotation_task:
                self.rotation_task.cancel()
                try:
                    await self.rotation_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("日志轮转器已停止")
            
        except Exception as e:
            logger.error(f"日志轮转器停止失败: {e}")
    
    async def _rotation_loop(self):
        """日志轮转循环"""
        while True:
            try:
                await asyncio.sleep(self.rotation_interval)
                await self._rotate_logs()
                await self._cleanup_old_logs()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"日志轮转失败: {e}")
    
    async def _rotate_logs(self):
        """轮转日志文件"""
        try:
            for log_file in self.log_dir.glob("*.log"):
                if log_file.stat().st_size > self.max_size_bytes:
                    # 压缩并重命名
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    compressed_name = f"{log_file.stem}_{timestamp}.log.gz"
                    compressed_path = self.log_dir / compressed_name
                    
                    # 压缩文件
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(compressed_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # 清空原文件
                    log_file.write_text("")
                    
                    logger.info(f"日志文件已轮转: {log_file.name} -> {compressed_name}")
            
        except Exception as e:
            logger.error(f"日志轮转处理失败: {e}")
    
    async def _cleanup_old_logs(self):
        """清理旧日志文件"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.keep_days)
            
            for log_file in self.log_dir.glob("*.log.gz"):
                # 从文件名提取时间戳
                try:
                    parts = log_file.stem.split('_')
                    if len(parts) >= 3:
                        timestamp_str = f"{parts[-2]}_{parts[-1]}"
                        file_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        
                        if file_date < cutoff_date:
                            log_file.unlink()
                            logger.info(f"已删除旧日志文件: {log_file.name}")
                
                except (ValueError, IndexError):
                    # 无法解析时间戳，跳过
                    continue
            
        except Exception as e:
            logger.error(f"清理旧日志失败: {e}")


class AdvancedLoggingSystem:
    """高级日志系统"""
    
    def __init__(self):
        self.log_aggregator = LogAggregator()
        self.log_rotator = LogRotator()
        self.structured_handler = StructuredLogHandler(self.log_aggregator)
        
        # 是否已初始化
        self.initialized = False
    
    def setup(self):
        """设置日志系统"""
        try:
            if self.initialized:
                return
            
            # 移除默认处理器
            logger.remove()
            
            # 添加控制台处理器（开发环境）
            if getattr(settings, 'debug', False):
                logger.add(
                    sys.stdout,
                    colorize=True,
                    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                           "<level>{level: <8}</level> | "
                           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                           "<level>{message}</level>",
                    level="DEBUG"
                )
            
            # 添加文件处理器
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            # 应用日志
            logger.add(
                log_dir / "app.log",
                rotation="100 MB",
                retention="30 days",
                compression="gz",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                level="INFO",
                backtrace=True,
                diagnose=True
            )
            
            # 错误日志
            logger.add(
                log_dir / "error.log",
                rotation="50 MB",
                retention="60 days",
                compression="gz",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                level="ERROR",
                backtrace=True,
                diagnose=True
            )
            
            # JSON格式日志（用于日志分析）
            logger.add(
                log_dir / "app.json.log",
                rotation="200 MB",
                retention="15 days",
                compression="gz",
                format=lambda record: json.dumps({
                    "timestamp": record["time"].isoformat(),
                    "level": record["level"].name,
                    "module": record["name"],
                    "function": record["function"],
                    "line": record["line"],
                    "message": record["message"],
                    "extra": record.get("extra", {}),
                    "exception": record.get("exception", {}).get("repr") if record.get("exception") else None
                }) + "\n",
                level="INFO"
            )
            
            # 添加结构化日志处理器
            logger.add(
                self.structured_handler.handle_log_record,
                level="INFO",
                format="{message}",
                serialize=True
            )
            
            self.initialized = True
            logger.info("高级日志系统初始化成功")
            
        except Exception as e:
            print(f"日志系统初始化失败: {e}")
            raise
    
    async def start(self):
        """启动日志系统"""
        try:
            await self.log_aggregator.start()
            await self.log_rotator.start()
            logger.info("高级日志系统启动成功")
            
        except Exception as e:
            logger.error(f"高级日志系统启动失败: {e}")
            raise
    
    async def stop(self):
        """停止日志系统"""
        try:
            await self.log_aggregator.stop()
            await self.log_rotator.stop()
            logger.info("高级日志系统已停止")
            
        except Exception as e:
            logger.error(f"高级日志系统停止失败: {e}")
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        return {
            'log_stats': self.log_aggregator.get_log_stats(),
            'initialized': self.initialized
        }


# 全局高级日志系统实例
advanced_logging = AdvancedLoggingSystem()


# 日志上下文管理器
class LogContext:
    """日志上下文管理器"""
    
    def __init__(self, **context):
        self.context = context
        self.original_context = {}
    
    def __enter__(self):
        # 保存原始上下文并设置新上下文
        self.original_context = logger._core.extra.copy()
        logger.configure(extra=self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 恢复原始上下文
        logger.configure(extra=self.original_context)


# 便捷函数
def log_with_context(**context):
    """带上下文的日志装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            with LogContext(**context):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


def setup_logging():
    """设置日志系统（向后兼容）"""
    advanced_logging.setup()


__all__ = [
    'advanced_logging',
    'LogLevel',
    'LogEntry',
    'LogAggregator',
    'LogContext',
    'log_with_context',
    'setup_logging'
]