"""
FastAPI应用入口点
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.services.ai import initialize_ai_services, shutdown_ai_services
from app.core.cache import cache_manager
from app.core.simple_tasks import simple_task_manager
from app.core.monitoring import metrics_collector
from app.core.logging_system import advanced_logging
from app.core import (
    setup_logging,
    RequestLoggingMiddleware,
    ExceptionHandlingMiddleware,
    api_logger
)
from app.core.security_middleware import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    InputValidationMiddleware
)
from app.db.init_db import init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    api_logger.info("Starting Granola API...")
    
    try:
        # 初始化高级日志系统
        advanced_logging.setup()
        await advanced_logging.start()
        api_logger.info("Advanced logging system initialized successfully")
        
        # 初始化监控系统
        await metrics_collector.start()
        api_logger.info("Monitoring system initialized successfully")
        
        # 初始化数据库
        await init_database()
        api_logger.info("Database initialized successfully")
        
        # 初始化缓存系统
        await cache_manager.initialize(settings.redis_url)
        api_logger.info("Cache system initialized successfully")
        
        # 初始化任务队列系统
        await simple_task_manager.start()
        api_logger.info("Task queue system initialized successfully")
        
        # 初始化AI服务
        await initialize_ai_services(settings.ai_config)
        api_logger.info("AI service initialized successfully")
        
    except Exception as e:
        api_logger.error(f"Failed to initialize application: {e}")
        raise
    
    api_logger.info("Granola API started successfully")
    
    yield
    
    # 关闭时清理
    api_logger.info("Shutting down Granola API...")
    
    try:
        # 关闭AI服务
        await shutdown_ai_services()
        api_logger.info("AI service shutdown successfully")
    except Exception as e:
        api_logger.error(f"Error shutting down AI service: {e}")
    
    try:
        # 关闭任务队列系统
        await simple_task_manager.stop()
        api_logger.info("Task queue system shutdown successfully")
    except Exception as e:
        api_logger.error(f"Error shutting down task queue system: {e}")
    
    try:
        # 关闭缓存系统
        await cache_manager.shutdown()
        api_logger.info("Cache system shutdown successfully")
    except Exception as e:
        api_logger.error(f"Error shutting down cache system: {e}")
    
    try:
        # 关闭监控系统
        await metrics_collector.stop()
        api_logger.info("Monitoring system shutdown successfully")
    except Exception as e:
        api_logger.error(f"Error shutting down monitoring system: {e}")
    
    try:
        # 关闭高级日志系统
        await advanced_logging.stop()
        api_logger.info("Advanced logging system shutdown successfully")
    except Exception as e:
        api_logger.error(f"Error shutting down advanced logging system: {e}")
    
    api_logger.info("Granola API shutdown completed")


# 设置日志
setup_logging()

# 创建FastAPI应用实例
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Granola AI-powered meeting notes API",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# 添加中间件（注意顺序很重要）
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(InputValidationMiddleware)
app.add_middleware(ExceptionHandlingMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# 生产环境添加速率限制
if not settings.debug:
    app.add_middleware(RateLimitMiddleware, calls=100, period=60)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置信任主机中间件
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.debug else ["localhost", "127.0.0.1"]
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to Granola API",
        "version": settings.app_version,
        "docs_url": "/docs" if settings.debug else None
    }


@app.get("/health")
async def health_check():
    """简单健康检查"""
    return {"status": "healthy", "version": settings.app_version}


@app.get("/health/detailed")
async def detailed_health_check():
    """详细健康检查"""
    from app.core.health import health_checker
    
    result = await health_checker.full_health_check()
    
    # 根据健康状态返回不同的HTTP状态码
    status_code = 200
    if result["status"] == "unhealthy":
        status_code = 503
    elif result["status"] == "critical":
        status_code = 500
    elif result["status"] == "warning":
        status_code = 200
    
    from fastapi import Response
    return Response(
        content=f"""{{
    "status": "{result['status']}",
    "data": {result}
}}""",
        status_code=status_code,
        media_type="application/json"
    )


# 导入路由
from app.api.v1.api import api_router
app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )