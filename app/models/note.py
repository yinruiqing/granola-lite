"""
笔记数据模型
"""

from sqlalchemy import Column, Text, Integer, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class Note(BaseModel):
    """笔记模型"""
    __tablename__ = "notes"
    
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False, comment="会议ID")
    content = Column(Text, nullable=False, comment="笔记内容")
    original_content = Column(Text, comment="AI增强前的原始内容")
    position = Column(Integer, default=0, comment="笔记在会议中的位置顺序")
    timestamp = Column(Float, comment="相对会议开始的时间点(秒)")
    is_ai_enhanced = Column(Boolean, default=False, comment="是否已AI增强")
    
    # 关系
    meeting = relationship("Meeting", back_populates="notes")