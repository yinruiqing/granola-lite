"""
任务队列管理API端点
"""

from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db.database import get_db
from app.core.auth import require_admin_user, require_current_user, get_current_user
from app.core.tasks import task_manager, TaskPriority, TaskStatus
from app.models.user import User
from loguru import logger


router = APIRouter()


class TaskSubmitRequest(BaseModel):
    """任务提交请求模型"""
    task_name: str
    args: List[Any] = []
    kwargs: Dict[str, Any] = {}
    priority: str = "normal"
    max_retries: int = 3
    eta: Optional[str] = None  # ISO格式时间字符串
    metadata: Dict[str, Any] = {}


class BatchTaskSubmitRequest(BaseModel):
    """批量任务提交请求模型"""
    tasks: List[TaskSubmitRequest]


@router.post("/submit", summary="提交任务")
async def submit_task(
    request: TaskSubmitRequest,
    current_user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    提交异步任务
    
    - **task_name**: 任务名称
    - **args**: 任务参数列表
    - **kwargs**: 任务关键字参数
    - **priority**: 优先级 (low, normal, high, critical)
    - **max_retries**: 最大重试次数
    - **eta**: 预定执行时间 (ISO格式)
    - **metadata**: 元数据
    """
    try:
        # 解析优先级
        priority_mapping = {
            'low': TaskPriority.LOW,
            'normal': TaskPriority.NORMAL,
            'high': TaskPriority.HIGH,
            'critical': TaskPriority.CRITICAL
        }
        
        priority = priority_mapping.get(request.priority.lower(), TaskPriority.NORMAL)
        
        # 解析ETA时间
        eta = None
        if request.eta:
            try:
                eta = datetime.fromisoformat(request.eta.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ETA时间格式无效，请使用ISO格式"
                )
        
        # 提交任务
        task_id = task_manager.submit_task(
            task_name=request.task_name,
            args=request.args,
            kwargs=request.kwargs,
            priority=priority,
            eta=eta,
            max_retries=request.max_retries,
            user_id=current_user.id,
            metadata=request.metadata
        )
        
        logger.info(f"用户 {current_user.id} 提交任务: {request.task_name} (ID: {task_id})")
        
        return {
            "success": True,
            "task_id": task_id,
            "task_name": request.task_name,
            "message": "任务提交成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"任务提交失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="任务提交失败"
        )


@router.post("/batch-submit", summary="批量提交任务")
async def batch_submit_tasks(
    request: BatchTaskSubmitRequest,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    批量提交异步任务（需要管理员权限）
    
    - **tasks**: 任务列表
    """
    try:
        if not request.tasks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="任务列表不能为空"
            )
        
        if len(request.tasks) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="单次最多提交100个任务"
            )
        
        results = []
        successful_count = 0
        failed_count = 0
        
        for i, task_req in enumerate(request.tasks):
            try:
                # 提交单个任务
                submit_result = await submit_task(task_req, current_user, None)
                results.append({
                    'index': i,
                    'task_name': task_req.task_name,
                    'success': True,
                    'task_id': submit_result['task_id']
                })
                successful_count += 1
                
            except Exception as e:
                logger.error(f"批量任务提交失败 (索引 {i}): {e}")
                results.append({
                    'index': i,
                    'task_name': task_req.task_name,
                    'success': False,
                    'error': str(e)
                })
                failed_count += 1
        
        return {
            "success": True,
            "total_tasks": len(request.tasks),
            "successful_count": successful_count,
            "failed_count": failed_count,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量任务提交失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量任务提交失败"
        )


@router.get("/status/{task_id}", summary="获取任务状态")
async def get_task_status(
    task_id: str,
    current_user: Optional[User] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取任务状态
    
    - **task_id**: 任务ID
    """
    try:
        task_result = task_manager.get_task_result(task_id)
        
        return {
            "success": True,
            "task_id": task_id,
            "status": task_result.status.value,
            "result": task_result.result,
            "error": task_result.error,
            "traceback": task_result.traceback,
            "started_at": task_result.started_at.isoformat() if task_result.started_at else None,
            "completed_at": task_result.completed_at.isoformat() if task_result.completed_at else None,
            "retry_count": task_result.retry_count,
            "metadata": task_result.metadata
        }
        
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取任务状态失败"
        )


@router.delete("/cancel/{task_id}", summary="取消任务")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(require_current_user)
) -> Dict[str, Any]:
    """
    取消指定任务
    
    - **task_id**: 任务ID
    """
    try:
        success = task_manager.cancel_task(task_id)
        
        if success:
            logger.info(f"用户 {current_user.id} 取消任务: {task_id}")
            return {
                "success": True,
                "task_id": task_id,
                "message": "任务取消成功"
            }
        else:
            return {
                "success": False,
                "task_id": task_id,
                "message": "任务取消失败或任务已完成"
            }
        
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="取消任务失败"
        )


@router.get("/active", summary="获取活跃任务列表")
async def get_active_tasks(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取活跃任务列表（需要管理员权限）
    """
    try:
        active_tasks = task_manager.get_active_tasks()
        
        return {
            "success": True,
            "active_tasks": active_tasks,
            "count": len(active_tasks)
        }
        
    except Exception as e:
        logger.error(f"获取活跃任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取活跃任务失败"
        )


@router.get("/queue-stats", summary="获取队列统计信息")
async def get_queue_stats(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取队列统计信息（需要管理员权限）
    """
    try:
        queue_stats = task_manager.get_queue_stats()
        
        return {
            "success": True,
            "queue_stats": queue_stats
        }
        
    except Exception as e:
        logger.error(f"获取队列统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取队列统计失败"
        )


@router.get("/worker-stats", summary="获取工作进程统计信息")
async def get_worker_stats(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取工作进程统计信息（需要管理员权限）
    """
    try:
        worker_stats = task_manager.get_worker_stats()
        
        return {
            "success": True,
            "worker_stats": worker_stats
        }
        
    except Exception as e:
        logger.error(f"获取工作进程统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取工作进程统计失败"
        )


@router.get("/stats", summary="获取任务系统统计信息")
async def get_task_stats(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取任务系统统计信息（需要管理员权限）
    """
    try:
        stats = task_manager.stats.copy()
        
        # 计算成功率
        total_completed = stats['total_completed'] + stats['total_failed']
        success_rate = (stats['total_completed'] / max(total_completed, 1)) * 100
        
        stats['success_rate'] = round(success_rate, 2)
        stats['total_processed'] = total_completed
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"获取任务统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取任务统计失败"
        )


# 预定义任务提交端点
@router.post("/transcribe", summary="提交音频转录任务")
async def submit_transcribe_task(
    file: UploadFile = File(...),
    language: str = "auto",
    provider: Optional[str] = None,
    use_cache: bool = True,
    current_user: User = Depends(require_current_user)
) -> Dict[str, Any]:
    """
    提交音频转录任务
    
    - **file**: 音频文件
    - **language**: 语言代码
    - **provider**: AI提供商
    - **use_cache**: 是否使用缓存
    """
    try:
        # 读取文件内容
        content = await file.read()
        
        # 验证文件类型和大小
        allowed_types = ['audio/wav', 'audio/mp3', 'audio/m4a', 'audio/aac', 'audio/flac']
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的音频格式: {file.content_type}"
            )
        
        if len(content) > 200 * 1024 * 1024:  # 200MB
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="音频文件过大，最大支持200MB"
            )
        
        # 提交转录任务
        task_id = task_manager.submit_task(
            task_name='ai.transcribe_audio',
            args=[content, file.filename, language, provider, current_user.id],
            kwargs={
                'use_cache': use_cache
            },
            priority=TaskPriority.HIGH,
            user_id=current_user.id,
            metadata={
                'filename': file.filename,
                'file_size': len(content),
                'content_type': file.content_type
            }
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "filename": file.filename,
            "message": "转录任务提交成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交转录任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="提交转录任务失败"
        )


@router.post("/enhance-notes", summary="提交笔记增强任务")
async def submit_enhance_notes_task(
    original_notes: str,
    transcription: str,
    template_prompt: Optional[str] = None,
    provider: Optional[str] = None,
    temperature: float = 0.3,
    current_user: User = Depends(require_current_user)
) -> Dict[str, Any]:
    """
    提交笔记增强任务
    
    - **original_notes**: 原始笔记
    - **transcription**: 转录内容
    - **template_prompt**: 模板提示
    - **provider**: AI提供商
    - **temperature**: 温度参数
    """
    try:
        if not original_notes.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="原始笔记不能为空"
            )
        
        if not transcription.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="转录内容不能为空"
            )
        
        # 提交笔记增强任务
        task_id = task_manager.submit_task(
            task_name='ai.enhance_notes',
            kwargs={
                'original_notes': original_notes,
                'transcription': transcription,
                'template_prompt': template_prompt,
                'provider': provider,
                'user_id': current_user.id,
                'temperature': temperature
            },
            priority=TaskPriority.NORMAL,
            user_id=current_user.id,
            metadata={
                'original_notes_length': len(original_notes),
                'transcription_length': len(transcription)
            }
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "笔记增强任务提交成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交笔记增强任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="提交笔记增强任务失败"
        )