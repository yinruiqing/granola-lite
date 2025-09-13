"""
简化版的FastAPI应用入口点
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    
    # 启动时初始化
    try:
        # 初始化数据库
        await init_db()
        print("Database initialized successfully")
        
    except Exception as e:
        print(f"Failed to initialize application: {e}")
        raise
    
    print("Granola API started successfully")
    yield
    
    # 关闭时清理
    print("Shutting down Granola API...")


# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Granola Meeting Notes API - 智能会议笔记系统",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to Granola API",
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z"
    }


# 暂时注释掉认证路由以避免复杂依赖
# from app.api.v1.endpoints import auth
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])