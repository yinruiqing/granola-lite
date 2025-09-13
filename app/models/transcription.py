"""
转录数据模型
"""

from sqlalchemy import Column, String, Text, Integer, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class Transcription(BaseModel):
    """转录模型"""
    __tablename__ = "transcriptions"
    
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False, comment="会议ID")
    content = Column(Text, nullable=False, comment="转录内容")
    speaker = Column(String(100), comment="发言人")
    start_time = Column(Float, comment="开始时间(相对会议开始的秒数)")
    end_time = Column(Float, comment="结束时间(相对会议开始的秒数)")
    confidence = Column(Float, comment="转录置信度")
    
    # 关系
    meeting = relationship("Meeting", back_populates="transcriptions")