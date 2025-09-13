"""
音频文件数据模型
"""

from sqlalchemy import Column, String, Integer, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.db.base import BaseModel


class AudioFile(BaseModel):
    """音频文件模型"""
    __tablename__ = "audio_files"
    
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False, comment="会议ID")
    file_path = Column(String(500), nullable=False, comment="文件路径")
    file_size = Column(Integer, comment="文件大小(字节)")
    duration = Column(Float, comment="音频时长(秒)")
    format = Column(String(50), comment="音频格式: wav, mp3, m4a等")
    
    # 关系
    meeting = relationship("Meeting", back_populates="audio_files")