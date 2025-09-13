"""
监控和日志管理API端点
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.db.database import get_db
from app.core.auth import require_admin_user, get_current_user
from app.core.monitoring import metrics_collector, MetricType, AlertLevel
from app.core.logging_system import advanced_logging, LogLevel
from app.models.user import User
from loguru import logger


router = APIRouter()


class MetricRequest(BaseModel):
    """指标记录请求模型"""
    name: str
    value: float
    metric_type: str  # counter, gauge, histogram, timer
    tags: Dict[str, str] = {}
    help_text: str = ""


class AlertResolveRequest(BaseModel):
    """告警解决请求模型"""
    alert_name: str


@router.get("/metrics", summary="获取系统指标")
async def get_metrics(
    pattern: Optional[str] = Query(None, description="指标名称过滤模式"),
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取系统指标（需要管理员权限）
    
    - **pattern**: 指标名称过滤模式
    """
    try:
        metrics = metrics_collector.get_metrics(pattern)
        
        return {
            "success": True,
            "metrics": metrics,
            "count": len(metrics)
        }
        
    except Exception as e:
        logger.error(f"获取系统指标失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取系统指标失败"
        )


@router.get("/metrics/{metric_name}/history", summary="获取指标历史")
async def get_metric_history(
    metric_name: str,
    limit: int = Query(100, description="历史记录数量限制"),
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取指定指标的历史数据（需要管理员权限）
    
    - **metric_name**: 指标名称
    - **limit**: 返回记录数量限制
    """
    try:
        history = metrics_collector.get_metric_history(metric_name, limit)
        
        return {
            "success": True,
            "metric_name": metric_name,
            "history": history,
            "count": len(history)
        }
        
    except Exception as e:
        logger.error(f"获取指标历史失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取指标历史失败"
        )


@router.post("/metrics", summary="记录自定义指标")
async def record_custom_metric(
    request: MetricRequest,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    记录自定义指标（需要管理员权限）
    
    - **name**: 指标名称
    - **value**: 指标值
    - **metric_type**: 指标类型 (counter, gauge, histogram, timer)
    - **tags**: 标签
    - **help_text**: 帮助文本
    """
    try:
        # 解析指标类型
        type_mapping = {
            'counter': MetricType.COUNTER,
            'gauge': MetricType.GAUGE,
            'histogram': MetricType.HISTOGRAM,
            'timer': MetricType.TIMER
        }
        
        metric_type = type_mapping.get(request.metric_type.lower())
        if not metric_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的指标类型: {request.metric_type}"
            )
        
        # 记录指标
        metrics_collector.record_metric(
            name=request.name,
            value=request.value,
            metric_type=metric_type,
            tags=request.tags,
            help_text=request.help_text
        )
        
        return {
            "success": True,
            "message": "自定义指标记录成功",
            "metric": {
                "name": request.name,
                "value": request.value,
                "type": request.metric_type
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"记录自定义指标失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="记录自定义指标失败"
        )


@router.get("/alerts", summary="获取系统告警")
async def get_alerts(
    level: Optional[str] = Query(None, description="告警级别过滤"),
    resolved: Optional[bool] = Query(None, description="是否已解决"),
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取系统告警（需要管理员权限）
    
    - **level**: 告警级别 (info, warning, error, critical)
    - **resolved**: 是否已解决
    """
    try:
        # 解析告警级别
        alert_level = None
        if level:
            try:
                alert_level = AlertLevel(level.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的告警级别: {level}"
                )
        
        # 获取告警
        alerts = metrics_collector.get_alerts(alert_level, resolved)
        
        return {
            "success": True,
            "alerts": alerts,
            "count": len(alerts)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取系统告警失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取系统告警失败"
        )


@router.post("/alerts/resolve", summary="解决告警")
async def resolve_alert(
    request: AlertResolveRequest,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    解决指定告警（需要管理员权限）
    
    - **alert_name**: 告警名称
    """
    try:
        metrics_collector.resolve_alert(request.alert_name)
        
        return {
            "success": True,
            "message": f"告警 {request.alert_name} 已解决"
        }
        
    except Exception as e:
        logger.error(f"解决告警失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="解决告警失败"
        )


@router.get("/logs", summary="获取系统日志")
async def get_system_logs(
    level: Optional[str] = Query(None, description="日志级别过滤"),
    limit: int = Query(100, description="日志数量限制"),
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取系统日志（需要管理员权限）
    
    - **level**: 日志级别 (TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL)
    - **limit**: 返回日志数量限制
    """
    try:
        # 解析日志级别
        log_level = None
        if level:
            try:
                log_level = LogLevel(level.upper())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的日志级别: {level}"
                )
        
        # 获取日志
        logs = advanced_logging.log_aggregator.get_recent_logs(log_level, limit)
        
        return {
            "success": True,
            "logs": logs,
            "count": len(logs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取系统日志失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取系统日志失败"
        )


@router.get("/logs/stats", summary="获取日志统计")
async def get_log_stats(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取日志统计信息（需要管理员权限）
    """
    try:
        stats = advanced_logging.log_aggregator.get_log_stats()
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"获取日志统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取日志统计失败"
        )


@router.get("/logs/errors", summary="获取错误模式")
async def get_error_patterns(
    limit: int = Query(10, description="错误模式数量限制"),
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取错误模式分析（需要管理员权限）
    
    - **limit**: 返回错误模式数量限制
    """
    try:
        patterns = advanced_logging.log_aggregator.get_error_patterns(limit)
        
        return {
            "success": True,
            "error_patterns": patterns,
            "count": len(patterns)
        }
        
    except Exception as e:
        logger.error(f"获取错误模式失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取错误模式失败"
        )


@router.get("/logs/slow-queries", summary="获取慢查询日志")
async def get_slow_queries(
    limit: int = Query(50, description="慢查询数量限制"),
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取慢查询日志（需要管理员权限）
    
    - **limit**: 返回慢查询数量限制
    """
    try:
        slow_queries = advanced_logging.log_aggregator.get_slow_queries(limit)
        
        return {
            "success": True,
            "slow_queries": slow_queries,
            "count": len(slow_queries)
        }
        
    except Exception as e:
        logger.error(f"获取慢查询日志失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取慢查询日志失败"
        )


@router.get("/health", summary="获取系统健康状态")
async def get_system_health(
    current_user: Optional[User] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取系统健康状态概览
    """
    try:
        # 获取基本健康指标
        metrics = metrics_collector.get_metrics()
        alerts = metrics_collector.get_alerts(resolved=False)
        log_stats = advanced_logging.log_aggregator.get_log_stats()
        
        # 计算健康分数
        health_score = 100
        
        # 根据CPU使用率扣分
        cpu_usage = metrics.get('system_cpu_usage_percent', {}).get('value', 0)
        if cpu_usage > 80:
            health_score -= 20
        elif cpu_usage > 60:
            health_score -= 10
        
        # 根据内存使用率扣分
        memory_usage = metrics.get('system_memory_usage_percent', {}).get('value', 0)
        if memory_usage > 85:
            health_score -= 20
        elif memory_usage > 70:
            health_score -= 10
        
        # 根据告警数量扣分
        critical_alerts = len([a for a in alerts if a.get('level') == 'critical'])
        error_alerts = len([a for a in alerts if a.get('level') == 'error'])
        
        health_score -= critical_alerts * 15
        health_score -= error_alerts * 5
        
        # 根据错误日志数量扣分
        error_log_count = log_stats.get('levels', {}).get('ERROR', 0)
        if error_log_count > 100:
            health_score -= 10
        elif error_log_count > 50:
            health_score -= 5
        
        # 确保健康分数在0-100范围内
        health_score = max(0, min(100, health_score))
        
        # 确定健康状态
        if health_score >= 90:
            status = "excellent"
        elif health_score >= 75:
            status = "good"
        elif health_score >= 50:
            status = "warning"
        else:
            status = "critical"
        
        return {
            "success": True,
            "health": {
                "status": status,
                "score": health_score,
                "timestamp": datetime.now().isoformat(),
                "metrics": {
                    "cpu_usage": cpu_usage,
                    "memory_usage": memory_usage,
                    "active_alerts": len(alerts),
                    "critical_alerts": critical_alerts,
                    "error_alerts": error_alerts,
                    "recent_errors": error_log_count
                }
            }
        }
        
    except Exception as e:
        logger.error(f"获取系统健康状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取系统健康状态失败"
        )


@router.get("/dashboard", summary="获取监控仪表板数据")
async def get_monitoring_dashboard(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取监控仪表板数据（需要管理员权限）
    """
    try:
        # 获取各种监控数据
        metrics = metrics_collector.get_metrics()
        alerts = metrics_collector.get_alerts(resolved=False)
        log_stats = advanced_logging.log_aggregator.get_log_stats()
        error_patterns = advanced_logging.log_aggregator.get_error_patterns(5)
        slow_queries = advanced_logging.log_aggregator.get_slow_queries(10)
        
        # 系统资源使用情况
        system_resources = {
            'cpu_usage': metrics.get('system_cpu_usage_percent', {}).get('value', 0),
            'memory_usage': metrics.get('system_memory_usage_percent', {}).get('value', 0),
            'disk_usage': metrics.get('system_disk_usage_percent', {}).get('value', 0),
            'cache_hit_rate': metrics.get('cache_hit_rate', {}).get('value', 0)
        }
        
        # 告警统计
        alert_stats = {
            'total': len(alerts),
            'critical': len([a for a in alerts if a.get('level') == 'critical']),
            'error': len([a for a in alerts if a.get('level') == 'error']),
            'warning': len([a for a in alerts if a.get('level') == 'warning'])
        }
        
        # 日志统计
        log_summary = {
            'total_logs': log_stats.get('levels', {}).get('total', 0),
            'error_logs': log_stats.get('levels', {}).get('ERROR', 0),
            'warning_logs': log_stats.get('levels', {}).get('WARNING', 0),
            'info_logs': log_stats.get('levels', {}).get('INFO', 0)
        }
        
        return {
            "success": True,
            "dashboard": {
                "timestamp": datetime.now().isoformat(),
                "system_resources": system_resources,
                "alerts": {
                    "stats": alert_stats,
                    "recent": alerts[:10]  # 最近10个告警
                },
                "logs": {
                    "stats": log_summary,
                    "error_patterns": error_patterns,
                    "slow_queries": slow_queries
                },
                "performance": {
                    "metrics_count": len(metrics),
                    "log_buffer_size": log_stats.get('buffer_size', 0),
                    "analysis_interval": log_stats.get('analysis_interval', 300)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"获取监控仪表板数据失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取监控仪表板数据失败"
        )