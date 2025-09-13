"""
数据库基础配置
"""

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime, func

# 创建基础模型类
Base = declarative_base()


class BaseModel(Base):
    """数据库模型基类"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)