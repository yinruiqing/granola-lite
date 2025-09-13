"""
会议数据模型
"""

from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, Index, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db.base import BaseModel


class MeetingStatus(enum.Enum):
    """会议状态枚举"""
    ACTIVE = "active"
    COMPLETED = "completed" 
    CANCELLED = "cancelled"


class Meeting(BaseModel):
    """会议模型"""
    __tablename__ = "meetings"
    title = Column(String(255), nullable=False, comment="会议标题")
    description = Column(Text, comment="会议描述")
    start_time = Column(DateTime(timezone=True), nullable=False, comment="开始时间")
    end_time = Column(DateTime(timezone=True), comment="结束时间")
    status = Column(Enum(MeetingStatus), default=MeetingStatus.ACTIVE, comment="会议状态")
    template_id = Column(Integer, ForeignKey("templates.id"), comment="使用的模板ID")
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="创建者ID")
    
    # 会议元数据
    participants_count = Column(Integer, default=0, comment="参与者数量")
    recording_duration = Column(Integer, default=0, comment="录音时长（秒）")
    is_private = Column(Boolean, default=False, comment="是否为私人会议")
    meeting_type = Column(String(50), default="general", comment="会议类型")
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # 关系
    creator = relationship("User", back_populates="meetings")
    template = relationship("Template", back_populates="meetings")
    transcriptions = relationship("Transcription", back_populates="meeting", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="meeting", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="meeting", cascade="all, delete-orphan")
    audio_files = relationship("AudioFile", back_populates="meeting", cascade="all, delete-orphan")
    
    # 索引优化
    __table_args__ = (
        Index('ix_meetings_creator_status', 'creator_id', 'status'),
        Index('ix_meetings_start_time', 'start_time'),
        Index('ix_meetings_title_search', 'title'),  # 用于文本搜索
        Index('ix_meetings_created_at', 'created_at'),
    )