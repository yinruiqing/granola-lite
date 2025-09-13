"""
性能优化管理API端点
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db.database import get_db
from app.core.auth import require_admin_user, get_current_user
from app.core.performance import performance_optimizer, database_optimizer
from app.core.async_optimizer import async_optimizer, resource_optimizer, TaskPriority
from app.models.user import User
from loguru import logger


router = APIRouter()


class OptimizationRequest(BaseModel):
    """优化请求模型"""
    operation: str
    parameters: Dict[str, Any] = {}


class AsyncTaskRequest(BaseModel):
    """异步任务请求模型"""
    task_type: str
    parameters: Dict[str, Any] = {}
    priority: str = "normal"
    timeout: Optional[float] = None
    max_retries: int = 3


# ==================== 数据库性能优化 ====================

@router.get("/database/slow-queries", summary="分析慢查询")
async def analyze_slow_queries(
    threshold: float = Query(1.0, description="慢查询阈值（秒）"),
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    分析数据库慢查询（需要管理员权限）
    
    - **threshold**: 慢查询阈值（秒）
    """
    try:
        result = await performance_optimizer.analyze_slow_queries(threshold)
        
        return {
            "success": True,
            "analysis": result,
            "message": f"分析完成，发现 {result['slow_queries_count']} 个慢查询"
        }
        
    except Exception as e:
        logger.error(f"分析慢查询失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分析慢查询失败: {str(e)}"
        )


@router.get("/database/index-optimization", summary="索引优化建议")
async def get_index_optimization_suggestions(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取数据库索引优化建议（需要管理员权限）
    """
    try:
        result = await performance_optimizer.optimize_database_indexes()
        
        return {
            "success": True,
            "suggestions": result,
            "message": f"分析完成，共 {result['total_suggestions']} 条优化建议"
        }
        
    except Exception as e:
        logger.error(f"获取索引优化建议失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取索引优化建议失败: {str(e)}"
        )


@router.post("/database/vacuum", summary="清理数据库表")
async def vacuum_database_tables(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    清理数据库表（需要管理员权限）
    """
    try:
        # 在后台执行VACUUM操作
        background_tasks.add_task(database_optimizer.vacuum_analyze_tables)
        
        return {
            "success": True,
            "message": "数据库清理任务已提交，正在后台执行"
        }
        
    except Exception as e:
        logger.error(f"提交数据库清理任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交数据库清理任务失败: {str(e)}"
        )


@router.post("/database/reindex", summary="重建数据库索引")
async def reindex_database_tables(
    tables: Optional[List[str]] = Query(None, description="要重建索引的表名列表"),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    重建数据库索引（需要管理员权限）
    
    - **tables**: 要重建索引的表名列表（可选）
    """
    try:
        # 在后台执行REINDEX操作
        background_tasks.add_task(database_optimizer.reindex_tables, tables)
        
        return {
            "success": True,
            "message": f"索引重建任务已提交，表: {tables or '所有表'}"
        }
        
    except Exception as e:
        logger.error(f"提交索引重建任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交索引重建任务失败: {str(e)}"
        )


@router.post("/database/analyze", summary="更新表统计信息")
async def update_table_statistics(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    更新数据库表统计信息（需要管理员权限）
    """
    try:
        result = await database_optimizer.update_table_statistics()
        
        return {
            "success": True,
            "result": result,
            "message": "表统计信息更新完成"
        }
        
    except Exception as e:
        logger.error(f"更新表统计信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新表统计信息失败: {str(e)}"
        )


@router.get("/database/connection-pool", summary="获取数据库连接池状态")
async def get_connection_pool_status(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取数据库连接池状态（需要管理员权限）
    """
    try:
        result = await performance_optimizer.connection_pool_status()
        
        return {
            "success": True,
            "connection_pool": result
        }
        
    except Exception as e:
        logger.error(f"获取连接池状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取连接池状态失败: {str(e)}"
        )


# ==================== 异步任务优化 ====================

@router.post("/async/submit-task", summary="提交异步任务")
async def submit_async_task(
    request: AsyncTaskRequest,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    提交异步任务（需要管理员权限）
    
    - **task_type**: 任务类型
    - **parameters**: 任务参数
    - **priority**: 任务优先级 (low, normal, high, critical)
    - **timeout**: 任务超时时间（秒）
    - **max_retries**: 最大重试次数
    """
    try:
        # 解析优先级
        priority_map = {
            "low": TaskPriority.LOW,
            "normal": TaskPriority.NORMAL,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL
        }
        
        priority = priority_map.get(request.priority.lower(), TaskPriority.NORMAL)
        
        # 这里需要根据task_type创建实际的任务函数
        # 暂时创建一个示例任务
        async def example_task(**kwargs):
            import asyncio
            await asyncio.sleep(1)  # 模拟任务执行
            return {"result": "task completed", "parameters": kwargs}
        
        task_id = await async_optimizer.submit_task(
            func=example_task,
            kwargs=request.parameters,
            priority=priority,
            timeout=request.timeout,
            max_retries=request.max_retries
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "异步任务已提交"
        }
        
    except Exception as e:
        logger.error(f"提交异步任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交异步任务失败: {str(e)}"
        )


@router.get("/async/task/{task_id}/status", summary="获取异步任务状态")
async def get_async_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取异步任务状态
    
    - **task_id**: 任务ID
    """
    try:
        status_info = await async_optimizer.get_task_status(task_id)
        
        return {
            "success": True,
            "task_status": status_info
        }
        
    except Exception as e:
        logger.error(f"获取异步任务状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取异步任务状态失败: {str(e)}"
        )


@router.delete("/async/task/{task_id}", summary="取消异步任务")
async def cancel_async_task(
    task_id: str,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    取消异步任务（需要管理员权限）
    
    - **task_id**: 任务ID
    """
    try:
        success = await async_optimizer.cancel_task(task_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务不存在或无法取消: {task_id}"
            )
        
        return {
            "success": True,
            "message": f"任务已取消: {task_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消异步任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消异步任务失败: {str(e)}"
        )


@router.get("/async/queue-status", summary="获取任务队列状态")
async def get_async_queue_status(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取异步任务队列状态（需要管理员权限）
    """
    try:
        status_info = await async_optimizer.get_queue_status()
        
        return {
            "success": True,
            "queue_status": status_info
        }
        
    except Exception as e:
        logger.error(f"获取任务队列状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务队列状态失败: {str(e)}"
        )


# ==================== 系统资源优化 ====================

@router.get("/system/resources", summary="获取系统资源状态")
async def get_system_resources(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取系统资源使用状态（需要管理员权限）
    """
    try:
        resources = await resource_optimizer.monitor_resources()
        
        return {
            "success": True,
            "resources": resources
        }
        
    except Exception as e:
        logger.error(f"获取系统资源状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统资源状态失败: {str(e)}"
        )


@router.post("/system/optimize-memory", summary="优化内存使用")
async def optimize_system_memory(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    优化系统内存使用（需要管理员权限）
    """
    try:
        result = await resource_optimizer.optimize_memory_usage()
        
        return {
            "success": True,
            "optimization": result,
            "message": "内存优化完成"
        }
        
    except Exception as e:
        logger.error(f"内存优化失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"内存优化失败: {str(e)}"
        )


# ==================== 性能分析和报告 ====================

@router.get("/analysis/performance-report", summary="获取性能分析报告")
async def get_performance_report(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取综合性能分析报告（需要管理员权限）
    """
    try:
        # 综合各种性能指标
        slow_queries = await performance_optimizer.analyze_slow_queries()
        index_suggestions = await performance_optimizer.optimize_database_indexes()
        connection_pool = await performance_optimizer.connection_pool_status()
        queue_status = await async_optimizer.get_queue_status()
        resources = await resource_optimizer.monitor_resources()
        
        # 生成综合评分
        performance_score = 100
        issues = []
        
        # 基于慢查询扣分
        if slow_queries['slow_queries_count'] > 0:
            performance_score -= slow_queries['slow_queries_count'] * 5
            issues.append(f"发现 {slow_queries['slow_queries_count']} 个慢查询")
        
        # 基于索引优化建议扣分
        if index_suggestions['total_suggestions'] > 0:
            performance_score -= index_suggestions['total_suggestions'] * 2
            issues.append(f"有 {index_suggestions['total_suggestions']} 条索引优化建议")
        
        # 基于资源使用率扣分
        if 'cpu' in resources and resources['cpu']['status'] == 'warning':
            performance_score -= 10
            issues.append(f"CPU使用率高: {resources['cpu']['percent']:.1f}%")
        
        if 'memory' in resources and resources['memory']['status'] == 'warning':
            performance_score -= 10
            issues.append(f"内存使用率高: {resources['memory']['percent']:.1f}%")
        
        # 基于任务队列状态
        if queue_status['failed_tasks'] > queue_status['completed_tasks'] * 0.1:
            performance_score -= 5
            issues.append(f"任务失败率较高: {queue_status['failed_tasks']} 失败任务")
        
        # 确保分数在0-100范围内
        performance_score = max(0, min(100, performance_score))
        
        # 确定性能等级
        if performance_score >= 90:
            performance_grade = "优秀"
        elif performance_score >= 80:
            performance_grade = "良好" 
        elif performance_score >= 70:
            performance_grade = "一般"
        elif performance_score >= 60:
            performance_grade = "较差"
        else:
            performance_grade = "差"
        
        report = {
            "summary": {
                "performance_score": performance_score,
                "performance_grade": performance_grade,
                "issues_count": len(issues),
                "issues": issues
            },
            "database": {
                "slow_queries": slow_queries,
                "index_suggestions": index_suggestions,
                "connection_pool": connection_pool
            },
            "async_tasks": queue_status,
            "system_resources": resources,
            "generated_at": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "report": report,
            "message": f"性能分析完成，综合评分: {performance_score} ({performance_grade})"
        }
        
    except Exception as e:
        logger.error(f"生成性能分析报告失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成性能分析报告失败: {str(e)}"
        )


@router.post("/optimization/auto-optimize", summary="自动性能优化")
async def auto_optimize_performance(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    自动执行性能优化（需要管理员权限）
    """
    try:
        # 在后台执行多个优化任务
        background_tasks.add_task(database_optimizer.vacuum_analyze_tables)
        background_tasks.add_task(database_optimizer.update_table_statistics)
        background_tasks.add_task(resource_optimizer.optimize_memory_usage)
        
        return {
            "success": True,
            "message": "自动性能优化任务已提交，正在后台执行",
            "tasks": [
                "数据库表清理和分析",
                "更新表统计信息", 
                "内存使用优化"
            ]
        }
        
    except Exception as e:
        logger.error(f"提交自动优化任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交自动优化任务失败: {str(e)}"
        )