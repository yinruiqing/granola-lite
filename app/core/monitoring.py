"""
监控和指标系统 - 应用性能监控、指标收集和告警
"""

import time
import psutil
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import json

from app.core.events import event_emitter, Events
from app.core.cache import cache_manager
from loguru import logger


class MetricType(Enum):
    """指标类型枚举"""
    COUNTER = "counter"        # 计数器
    GAUGE = "gauge"           # 测量值
    HISTOGRAM = "histogram"   # 直方图
    TIMER = "timer"           # 计时器


class AlertLevel(Enum):
    """告警级别枚举"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Metric:
    """指标数据"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)
    help_text: str = ""


@dataclass
class Alert:
    """告警数据"""
    name: str
    level: AlertLevel
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metrics: Dict[str, Metric] = {}
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.alerts: List[Alert] = []
        self.alert_rules: List[Callable] = []
        
        # 性能计数器
        self.request_count = 0
        self.request_duration_sum = 0.0
        self.error_count = 0
        
        # 系统指标更新任务
        self.system_metrics_task: Optional[asyncio.Task] = None
        self.metrics_update_interval = 30  # 30秒
    
    async def start(self):
        """启动指标收集器"""
        try:
            # 启动系统指标收集任务
            self.system_metrics_task = asyncio.create_task(self._collect_system_metrics_loop())
            logger.info("指标收集器启动成功")
            
        except Exception as e:
            logger.error(f"指标收集器启动失败: {e}")
            raise
    
    async def stop(self):
        """停止指标收集器"""
        try:
            if self.system_metrics_task:
                self.system_metrics_task.cancel()
                try:
                    await self.system_metrics_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("指标收集器已停止")
            
        except Exception as e:
            logger.error(f"指标收集器停止失败: {e}")
    
    def record_metric(self, name: str, value: float, metric_type: MetricType, 
                     tags: Dict[str, str] = None, help_text: str = ""):
        """记录指标"""
        try:
            tags = tags or {}
            timestamp = datetime.now()
            
            metric = Metric(
                name=name,
                value=value,
                metric_type=metric_type,
                timestamp=timestamp,
                tags=tags,
                help_text=help_text
            )
            
            # 更新当前指标
            self.metrics[name] = metric
            
            # 添加到历史记录
            self.metric_history[name].append({
                'value': value,
                'timestamp': timestamp.isoformat(),
                'tags': tags
            })
            
            # 检查告警规则
            self._check_alert_rules(metric)
            
        except Exception as e:
            logger.error(f"记录指标失败: {e}")
    
    def increment_counter(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """递增计数器"""
        current_metric = self.metrics.get(name)
        if current_metric and current_metric.metric_type == MetricType.COUNTER:
            new_value = current_metric.value + value
        else:
            new_value = value
        
        self.record_metric(name, new_value, MetricType.COUNTER, tags)
    
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """设置测量值"""
        self.record_metric(name, value, MetricType.GAUGE, tags)
    
    def record_timer(self, name: str, duration: float, tags: Dict[str, str] = None):
        """记录计时器"""
        self.record_metric(name, duration, MetricType.TIMER, tags)
    
    def add_alert_rule(self, rule_func: Callable[[Metric], Optional[Alert]]):
        """添加告警规则"""
        self.alert_rules.append(rule_func)
    
    def _check_alert_rules(self, metric: Metric):
        """检查告警规则"""
        for rule in self.alert_rules:
            try:
                alert = rule(metric)
                if alert:
                    self.alerts.append(alert)
                    # 发射告警事件
                    asyncio.create_task(self._emit_alert_event(alert))
                    
            except Exception as e:
                logger.error(f"告警规则检查失败: {e}")
    
    async def _emit_alert_event(self, alert: Alert):
        """发射告警事件"""
        await event_emitter.emit(Events.SYSTEM_ALERT, {
            'alert_name': alert.name,
            'level': alert.level.value,
            'message': alert.message,
            'timestamp': alert.timestamp.isoformat(),
            'tags': alert.tags
        })
    
    async def _collect_system_metrics_loop(self):
        """系统指标收集循环"""
        while True:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.metrics_update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"系统指标收集失败: {e}")
                await asyncio.sleep(self.metrics_update_interval)
    
    async def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            # CPU指标
            cpu_percent = psutil.cpu_percent(interval=1)
            self.set_gauge("system_cpu_usage_percent", cpu_percent)
            
            # 内存指标
            memory = psutil.virtual_memory()
            self.set_gauge("system_memory_usage_percent", memory.percent)
            self.set_gauge("system_memory_available_bytes", memory.available)
            self.set_gauge("system_memory_used_bytes", memory.used)
            
            # 磁盘指标
            disk = psutil.disk_usage('/')
            self.set_gauge("system_disk_usage_percent", disk.percent)
            self.set_gauge("system_disk_free_bytes", disk.free)
            self.set_gauge("system_disk_used_bytes", disk.used)
            
            # 网络指标
            net_io = psutil.net_io_counters()
            self.set_gauge("system_network_bytes_sent", net_io.bytes_sent)
            self.set_gauge("system_network_bytes_recv", net_io.bytes_recv)
            
            # 进程指标
            process = psutil.Process()
            process_memory = process.memory_info()
            self.set_gauge("process_memory_rss_bytes", process_memory.rss)
            self.set_gauge("process_memory_vms_bytes", process_memory.vms)
            self.set_gauge("process_cpu_percent", process.cpu_percent())
            
            # 数据库连接指标（如果有）
            try:
                # 这里可以添加数据库连接池监控
                pass
            except Exception:
                pass
            
            # 缓存指标
            try:
                cache_stats = cache_manager.get_stats()
                self.set_gauge("cache_hit_rate", cache_stats['hit_rate'])
                self.set_gauge("cache_total_requests", cache_stats['total_requests'])
                self.set_gauge("cache_errors", cache_stats['errors'])
                
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
    
    def get_metrics(self, name_pattern: str = None) -> Dict[str, Any]:
        """获取指标数据"""
        if name_pattern:
            filtered_metrics = {
                name: metric for name, metric in self.metrics.items()
                if name_pattern in name
            }
        else:
            filtered_metrics = self.metrics.copy()
        
        return {
            name: {
                'value': metric.value,
                'type': metric.metric_type.value,
                'timestamp': metric.timestamp.isoformat(),
                'tags': metric.tags,
                'help': metric.help_text
            }
            for name, metric in filtered_metrics.items()
        }
    
    def get_metric_history(self, name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """获取指标历史"""
        history = self.metric_history.get(name, deque())
        return list(history)[-limit:]
    
    def get_alerts(self, level: AlertLevel = None, resolved: bool = None) -> List[Dict[str, Any]]:
        """获取告警列表"""
        alerts = self.alerts
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]
        
        return [
            {
                'name': alert.name,
                'level': alert.level.value,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'tags': alert.tags,
                'resolved': alert.resolved,
                'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
            }
            for alert in alerts
        ]
    
    def resolve_alert(self, alert_name: str):
        """解决告警"""
        for alert in self.alerts:
            if alert.name == alert_name and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                logger.info(f"告警已解决: {alert_name}")
                break


# 全局指标收集器
metrics_collector = MetricsCollector()


# 性能监控装饰器
class PerformanceMonitor:
    """性能监控装饰器"""
    
    @staticmethod
    def monitor_request(endpoint_name: str = None):
        """监控HTTP请求"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                endpoint = endpoint_name or func.__name__
                
                try:
                    # 增加请求计数
                    metrics_collector.increment_counter(
                        'http_requests_total',
                        tags={'endpoint': endpoint}
                    )
                    
                    # 执行请求
                    result = await func(*args, **kwargs)
                    
                    # 记录成功请求
                    metrics_collector.increment_counter(
                        'http_requests_success_total',
                        tags={'endpoint': endpoint}
                    )
                    
                    return result
                    
                except Exception as e:
                    # 记录失败请求
                    metrics_collector.increment_counter(
                        'http_requests_error_total',
                        tags={'endpoint': endpoint, 'error_type': type(e).__name__}
                    )
                    raise
                    
                finally:
                    # 记录请求耗时
                    duration = time.time() - start_time
                    metrics_collector.record_timer(
                        'http_request_duration_seconds',
                        duration,
                        tags={'endpoint': endpoint}
                    )
            
            return wrapper
        return decorator
    
    @staticmethod
    def monitor_function(function_name: str = None):
        """监控函数执行"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                func_name = function_name or f"{func.__module__}.{func.__name__}"
                
                try:
                    # 增加函数调用计数
                    metrics_collector.increment_counter(
                        'function_calls_total',
                        tags={'function': func_name}
                    )
                    
                    # 执行函数
                    result = await func(*args, **kwargs)
                    
                    # 记录成功调用
                    metrics_collector.increment_counter(
                        'function_calls_success_total',
                        tags={'function': func_name}
                    )
                    
                    return result
                    
                except Exception as e:
                    # 记录失败调用
                    metrics_collector.increment_counter(
                        'function_calls_error_total',
                        tags={'function': func_name, 'error_type': type(e).__name__}
                    )
                    raise
                    
                finally:
                    # 记录执行耗时
                    duration = time.time() - start_time
                    metrics_collector.record_timer(
                        'function_duration_seconds',
                        duration,
                        tags={'function': func_name}
                    )
            
            return wrapper
        return decorator


# 预定义告警规则
def high_cpu_usage_rule(metric: Metric) -> Optional[Alert]:
    """高CPU使用率告警规则"""
    if metric.name == 'system_cpu_usage_percent' and metric.value > 80:
        return Alert(
            name='high_cpu_usage',
            level=AlertLevel.WARNING,
            message=f'CPU使用率过高: {metric.value:.2f}%',
            tags={'cpu_percent': str(metric.value)}
        )
    elif metric.name == 'system_cpu_usage_percent' and metric.value > 95:
        return Alert(
            name='critical_cpu_usage',
            level=AlertLevel.CRITICAL,
            message=f'CPU使用率临界: {metric.value:.2f}%',
            tags={'cpu_percent': str(metric.value)}
        )
    return None


def high_memory_usage_rule(metric: Metric) -> Optional[Alert]:
    """高内存使用率告警规则"""
    if metric.name == 'system_memory_usage_percent' and metric.value > 85:
        return Alert(
            name='high_memory_usage',
            level=AlertLevel.WARNING,
            message=f'内存使用率过高: {metric.value:.2f}%',
            tags={'memory_percent': str(metric.value)}
        )
    elif metric.name == 'system_memory_usage_percent' and metric.value > 95:
        return Alert(
            name='critical_memory_usage',
            level=AlertLevel.CRITICAL,
            message=f'内存使用率临界: {metric.value:.2f}%',
            tags={'memory_percent': str(metric.value)}
        )
    return None


def high_disk_usage_rule(metric: Metric) -> Optional[Alert]:
    """高磁盘使用率告警规则"""
    if metric.name == 'system_disk_usage_percent' and metric.value > 90:
        return Alert(
            name='high_disk_usage',
            level=AlertLevel.WARNING,
            message=f'磁盘使用率过高: {metric.value:.2f}%',
            tags={'disk_percent': str(metric.value)}
        )
    elif metric.name == 'system_disk_usage_percent' and metric.value > 98:
        return Alert(
            name='critical_disk_usage',
            level=AlertLevel.CRITICAL,
            message=f'磁盘使用率临界: {metric.value:.2f}%',
            tags={'disk_percent': str(metric.value)}
        )
    return None


def low_cache_hit_rate_rule(metric: Metric) -> Optional[Alert]:
    """低缓存命中率告警规则"""
    if metric.name == 'cache_hit_rate' and metric.value < 50:
        return Alert(
            name='low_cache_hit_rate',
            level=AlertLevel.WARNING,
            message=f'缓存命中率过低: {metric.value:.2f}%',
            tags={'hit_rate': str(metric.value)}
        )
    return None


# 注册默认告警规则
def setup_default_alert_rules():
    """设置默认告警规则"""
    metrics_collector.add_alert_rule(high_cpu_usage_rule)
    metrics_collector.add_alert_rule(high_memory_usage_rule)
    metrics_collector.add_alert_rule(high_disk_usage_rule)
    metrics_collector.add_alert_rule(low_cache_hit_rate_rule)
    
    logger.info("默认告警规则已设置")


# 在模块导入时设置告警规则
setup_default_alert_rules()


__all__ = [
    'metrics_collector',
    'MetricType',
    'AlertLevel',
    'Metric',
    'Alert',
    'MetricsCollector',
    'PerformanceMonitor'
]