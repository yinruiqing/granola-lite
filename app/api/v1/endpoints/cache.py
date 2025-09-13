"""
缓存管理API端点
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.db.database import get_db
from app.core.auth import require_admin_user, get_current_user
from app.core.cache import cache_manager
from app.models.user import User
from loguru import logger


router = APIRouter()


class CacheSetRequest(BaseModel):
    """缓存设置请求模型"""
    namespace: str
    key: str
    value: Any
    ttl: Optional[int] = None


class CacheGetRequest(BaseModel):
    """缓存获取请求模型"""
    namespace: str
    key: str


class CacheBatchRequest(BaseModel):
    """批量缓存操作请求模型"""
    namespace: str
    keys: List[str]


class CacheBatchSetRequest(BaseModel):
    """批量缓存设置请求模型"""
    namespace: str
    data: Dict[str, Any]
    ttl: Optional[int] = None


@router.get("/stats", summary="获取缓存统计信息")
async def get_cache_stats(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取缓存统计信息（需要管理员权限）
    """
    try:
        stats = cache_manager.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取缓存统计失败"
        )


@router.post("/reset-stats", summary="重置缓存统计")
async def reset_cache_stats(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    重置缓存统计信息（需要管理员权限）
    """
    try:
        cache_manager.reset_stats()
        
        return {
            "success": True,
            "message": "缓存统计信息已重置"
        }
        
    except Exception as e:
        logger.error(f"重置缓存统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重置缓存统计失败"
        )


@router.get("/health", summary="获取缓存健康状态")
async def get_cache_health(
    current_user: Optional[User] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取缓存服务健康状态
    """
    try:
        stats = cache_manager.get_stats()
        
        return {
            "success": True,
            "health": {
                "is_healthy": stats["is_healthy"],
                "hit_rate": stats["hit_rate"],
                "total_requests": stats["total_requests"],
                "errors": stats["errors"]
            }
        }
        
    except Exception as e:
        logger.error(f"获取缓存健康状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取缓存健康状态失败"
        )


@router.post("/get", summary="获取缓存值")
async def get_cache_value(
    request: CacheGetRequest,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取指定的缓存值（需要管理员权限）
    
    - **namespace**: 命名空间
    - **key**: 缓存键
    """
    try:
        value = await cache_manager.get(request.namespace, request.key)
        exists = await cache_manager.exists(request.namespace, request.key)
        ttl = await cache_manager.get_ttl(request.namespace, request.key)
        
        return {
            "success": True,
            "exists": exists,
            "value": value,
            "ttl": ttl if exists else None
        }
        
    except Exception as e:
        logger.error(f"获取缓存值失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取缓存值失败"
        )


@router.post("/set", summary="设置缓存值")
async def set_cache_value(
    request: CacheSetRequest,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    设置缓存值（需要管理员权限）
    
    - **namespace**: 命名空间
    - **key**: 缓存键
    - **value**: 缓存值
    - **ttl**: 过期时间（秒，可选）
    """
    try:
        success = await cache_manager.set(
            request.namespace,
            request.key,
            request.value,
            ttl=request.ttl
        )
        
        if success:
            return {
                "success": True,
                "message": "缓存设置成功"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="缓存设置失败"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置缓存值失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="设置缓存值失败"
        )


@router.post("/delete", summary="删除缓存值")
async def delete_cache_value(
    request: CacheGetRequest,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    删除指定的缓存值（需要管理员权限）
    
    - **namespace**: 命名空间
    - **key**: 缓存键
    """
    try:
        success = await cache_manager.delete(request.namespace, request.key)
        
        return {
            "success": True,
            "deleted": success,
            "message": "缓存删除成功" if success else "缓存不存在或删除失败"
        }
        
    except Exception as e:
        logger.error(f"删除缓存值失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除缓存值失败"
        )


@router.post("/batch-get", summary="批量获取缓存值")
async def batch_get_cache_values(
    request: CacheBatchRequest,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    批量获取缓存值（需要管理员权限）
    
    - **namespace**: 命名空间
    - **keys**: 缓存键列表
    """
    try:
        values = await cache_manager.mget(request.namespace, request.keys)
        
        return {
            "success": True,
            "values": values,
            "found_count": len(values),
            "requested_count": len(request.keys)
        }
        
    except Exception as e:
        logger.error(f"批量获取缓存值失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量获取缓存值失败"
        )


@router.post("/batch-set", summary="批量设置缓存值")
async def batch_set_cache_values(
    request: CacheBatchSetRequest,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    批量设置缓存值（需要管理员权限）
    
    - **namespace**: 命名空间
    - **data**: 键值对数据
    - **ttl**: 过期时间（秒，可选）
    """
    try:
        if not request.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="数据不能为空"
            )
        
        success = await cache_manager.mset(
            request.namespace,
            request.data,
            ttl=request.ttl
        )
        
        if success:
            return {
                "success": True,
                "message": f"成功设置 {len(request.data)} 个缓存项",
                "count": len(request.data)
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="批量设置缓存失败"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量设置缓存值失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量设置缓存值失败"
        )


@router.delete("/clear/{namespace}", summary="清空命名空间")
async def clear_namespace(
    namespace: str,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    清空指定命名空间下的所有缓存（需要管理员权限）
    
    - **namespace**: 要清空的命名空间
    """
    try:
        deleted_count = await cache_manager.clear_namespace(namespace)
        
        return {
            "success": True,
            "message": f"成功删除 {deleted_count} 个缓存项",
            "deleted_count": deleted_count,
            "namespace": namespace
        }
        
    except Exception as e:
        logger.error(f"清空命名空间失败 {namespace}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="清空命名空间失败"
        )


@router.post("/extend-ttl", summary="延长缓存TTL")
async def extend_cache_ttl(
    namespace: str,
    key: str,
    ttl: int,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    延长缓存的TTL时间（需要管理员权限）
    
    - **namespace**: 命名空间
    - **key**: 缓存键
    - **ttl**: 新的过期时间（秒）
    """
    try:
        if ttl <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="TTL必须大于0"
            )
        
        success = await cache_manager.extend_ttl(namespace, key, ttl)
        
        if success:
            return {
                "success": True,
                "message": f"TTL已延长到 {ttl} 秒",
                "ttl": ttl
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="缓存不存在或延长TTL失败"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"延长缓存TTL失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="延长缓存TTL失败"
        )


@router.get("/info/{namespace}/{key}", summary="获取缓存信息")
async def get_cache_info(
    namespace: str,
    key: str,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取缓存的详细信息（需要管理员权限）
    
    - **namespace**: 命名空间
    - **key**: 缓存键
    """
    try:
        exists = await cache_manager.exists(namespace, key)
        
        if not exists:
            return {
                "success": True,
                "exists": False,
                "namespace": namespace,
                "key": key
            }
        
        ttl = await cache_manager.get_ttl(namespace, key)
        value = await cache_manager.get(namespace, key)
        
        # 获取值的基本信息
        value_info = {
            "type": type(value).__name__,
            "size": len(str(value)) if value is not None else 0
        }
        
        if isinstance(value, (list, dict)):
            value_info["length"] = len(value)
        
        return {
            "success": True,
            "exists": True,
            "namespace": namespace,
            "key": key,
            "ttl": ttl,
            "value_info": value_info,
            "preview": str(value)[:200] + "..." if len(str(value)) > 200 else str(value)
        }
        
    except Exception as e:
        logger.error(f"获取缓存信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取缓存信息失败"
        )