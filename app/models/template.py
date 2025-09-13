"""
模板数据模型
"""

from sqlalchemy import Column, String, Text, Boolean, JSON
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class Template(BaseModel):
    """模板模型"""
    __tablename__ = "templates"
    
    name = Column(String(255), nullable=False, comment="模板名称")
    description = Column(Text, comment="模板描述")
    category = Column(String(100), comment="模板分类: 1on1, retrospective, interview, sales等")
    structure = Column(JSON, comment="模板结构定义")
    prompt_template = Column(Text, comment="AI处理时使用的提示模板")
    is_default = Column(Boolean, default=False, comment="是否为默认模板")
    
    # 关系
    meetings = relationship("Meeting", back_populates="template")