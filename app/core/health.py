"""
健康检查和监控
"""

import time
import asyncio
from typing import Dict, Any
from datetime import datetime
from fastapi import HTTPException

from app.config import settings
from app.services.ai.ai_service import get_ai_service
from app.db.session import AsyncSessionLocal
from app.core.logging import service_logger


class HealthChecker:
    """健康检查器"""
    
    async def check_database(self) -> Dict[str, Any]:
        """检查数据库连接"""
        try:
            start_time = time.time()
            
            async with AsyncSessionLocal() as session:
                await session.execute("SELECT 1")
            
            response_time = round((time.time() - start_time) * 1000, 2)
            
            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "database_url": settings.database_url.split("://")[0] + "://***"
            }
            
        except Exception as e:
            service_logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "database_url": settings.database_url.split("://")[0] + "://***"
            }
    
    async def check_ai_service(self) -> Dict[str, Any]:
        """检查AI服务"""
        try:
            start_time = time.time()
            
            ai_service = get_ai_service()
            
            # 测试LLM服务
            messages = [{"role": "user", "content": "Hello, this is a health check."}]
            response = await ai_service.chat_completion(
                messages=messages,
                max_tokens=10,
                temperature=0
            )
            
            response_time = round((time.time() - start_time) * 1000, 2)
            
            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "providers": ai_service.get_provider_info(),
                "response_length": len(response.content)
            }
            
        except Exception as e:
            service_logger.error(f"AI service health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def check_storage(self) -> Dict[str, Any]:
        """检查存储空间"""
        try:
            import shutil
            
            # 检查上传目录存储空间
            disk_usage = shutil.disk_usage(settings.upload_dir)
            
            total_gb = round(disk_usage.total / (1024**3), 2)
            free_gb = round(disk_usage.free / (1024**3), 2)
            used_gb = round((disk_usage.total - disk_usage.free) / (1024**3), 2)
            usage_percent = round((used_gb / total_gb) * 100, 2)
            
            status = "healthy"
            if usage_percent > 90:
                status = "critical"
            elif usage_percent > 80:
                status = "warning"
            
            return {
                "status": status,
                "total_gb": total_gb,
                "free_gb": free_gb,
                "used_gb": used_gb,
                "usage_percent": usage_percent,
                "upload_dir": settings.upload_dir
            }
            
        except Exception as e:
            service_logger.error(f"Storage health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            import psutil
            import platform
            
            # CPU信息
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # 内存信息
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_total = round(memory.total / (1024**3), 2)
            memory_used = round(memory.used / (1024**3), 2)
            
            # 系统信息
            system_info = {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "python_version": platform.python_version(),
                "cpu_percent": cpu_percent,
                "cpu_count": cpu_count,
                "memory_percent": memory_percent,
                "memory_total_gb": memory_total,
                "memory_used_gb": memory_used,
                "uptime": time.time() - psutil.boot_time()
            }
            
            return system_info
            
        except ImportError:
            return {"error": "psutil not installed"}
        except Exception as e:
            service_logger.error(f"System info collection failed: {e}")
            return {"error": str(e)}
    
    async def full_health_check(self) -> Dict[str, Any]:
        """完整健康检查"""
        start_time = time.time()
        
        # 并发执行所有检查
        database_task = asyncio.create_task(self.check_database())
        ai_service_task = asyncio.create_task(self.check_ai_service())
        storage_task = asyncio.create_task(self.check_storage())
        system_task = asyncio.create_task(self.get_system_info())
        
        database_health = await database_task
        ai_service_health = await ai_service_task
        storage_health = await storage_task
        system_info = await system_task
        
        # 确定总体状态
        overall_status = "healthy"
        if any(check.get("status") == "unhealthy" for check in [database_health, ai_service_health, storage_health]):
            overall_status = "unhealthy"
        elif any(check.get("status") == "critical" for check in [storage_health]):
            overall_status = "critical"
        elif any(check.get("status") == "warning" for check in [storage_health]):
            overall_status = "warning"
        
        total_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "version": settings.app_version,
            "environment": "development" if settings.debug else "production",
            "total_check_time_ms": total_time,
            "services": {
                "database": database_health,
                "ai_service": ai_service_health,
                "storage": storage_health
            },
            "system": system_info
        }


# 全局健康检查器实例
health_checker = HealthChecker()