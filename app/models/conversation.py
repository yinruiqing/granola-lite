"""
AI对话数据模型
"""

from sqlalchemy import Column, Text, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class Conversation(BaseModel):
    """AI对话模型"""
    __tablename__ = "conversations"
    
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False, comment="会议ID")
    question = Column(Text, nullable=False, comment="用户问题")
    answer = Column(Text, nullable=False, comment="AI回答")
    context_used = Column(Text, comment="使用的会议上下文")
    model_used = Column(String(100), comment="使用的AI模型")
    
    # 关系
    meeting = relationship("Meeting", back_populates="conversations")