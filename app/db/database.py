"""
数据库连接和会话管理
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
from typing import AsyncGenerator
import logging

from app.config import settings

# 数据库元数据配置
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
)

class Base(DeclarativeBase):
    """数据库模型基类"""
    metadata = metadata


# 数据库引擎配置
def create_database_engine():
    """创建数据库引擎"""
    engine_kwargs = {
        "echo": settings.database_echo,
        "future": True
    }
    
    # 根据数据库类型配置连接池
    if settings.database_url.startswith("postgresql"):
        engine_kwargs.update({
            "pool_size": settings.database_pool_size,
            "max_overflow": settings.database_max_overflow,
            "pool_pre_ping": True,
            "pool_recycle": 3600,  # 1小时回收连接
        })
    elif settings.database_url.startswith("sqlite"):
        # SQLite特殊配置
        engine_kwargs.update({
            "connect_args": {"check_same_thread": False}
        })
    
    return create_async_engine(settings.database_url, **engine_kwargs)


# 创建数据库引擎和会话工厂
engine = create_database_engine()
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False
)

# 数据库日志配置
if settings.database_echo:
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的依赖项"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """初始化数据库表"""
    async with engine.begin() as conn:
        # 导入所有模型以确保它们被注册
        from app.models import (
            meeting, note, transcription, conversation, 
            template, audio_file, user
        )
        
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)


async def drop_db():
    """删除所有数据库表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)