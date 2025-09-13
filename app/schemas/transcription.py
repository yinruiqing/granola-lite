"""
转录相关的Pydantic模式
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TranscriptionBase(BaseModel):
    """转录基础模式"""
    content: str = Field(..., description="转录内容")
    speaker: Optional[str] = Field(None, description="发言人")
    start_time: Optional[float] = Field(None, description="开始时间(秒)")
    end_time: Optional[float] = Field(None, description="结束时间(秒)")
    confidence: Optional[float] = Field(None, description="置信度", ge=0, le=1)


class TranscriptionCreate(TranscriptionBase):
    """创建转录请求模式"""
    meeting_id: int = Field(..., description="会议ID")


class TranscriptionUpdate(BaseModel):
    """更新转录请求模式"""
    content: str = Field(..., description="转录内容")


class TranscriptionResponse(TranscriptionBase):
    """转录响应模式"""
    id: int = Field(..., description="转录ID")
    meeting_id: int = Field(..., description="会议ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    class Config:
        from_attributes = True


class TranscriptionRequest(BaseModel):
    """转录请求模式"""
    audio_id: int = Field(..., description="音频文件ID")
    language: str = Field(default="auto", description="语言代码，如 'zh', 'en', 'auto'")
    temperature: Optional[float] = Field(default=0, description="温度参数", ge=0, le=1)
    prompt: Optional[str] = Field(None, description="转录提示")


class TranscriptionResult(BaseModel):
    """转录结果模式"""
    audio_id: int = Field(..., description="音频文件ID")
    meeting_id: int = Field(..., description="会议ID")
    language: str = Field(..., description="检测到的语言")
    total_segments: int = Field(..., description="分段总数")
    full_text: str = Field(..., description="完整转录文本")
    confidence: float = Field(..., description="整体置信度", ge=0, le=1)
    transcription_ids: List[int] = Field(..., description="转录记录ID列表")


class StreamingTranscriptionRequest(BaseModel):
    """流式转录请求模式"""
    session_id: str = Field(..., description="会话ID")
    sample_rate: int = Field(default=16000, description="音频采样率")
    language: str = Field(default="auto", description="语言代码")


class StreamingTranscriptionResponse(BaseModel):
    """流式转录响应模式"""
    session_id: str = Field(..., description="会话ID")
    text: str = Field(..., description="转录文本")
    confidence: float = Field(..., description="置信度", ge=0, le=1)
    language: str = Field(..., description="检测到的语言")
    timestamp: float = Field(..., description="时间戳(秒)")
    is_final: bool = Field(default=False, description="是否为最终结果")


class TranscriptionQuery(BaseModel):
    """转录查询参数"""
    meeting_id: int = Field(..., description="会议ID")
    start_time: Optional[float] = Field(None, description="开始时间筛选(秒)")
    end_time: Optional[float] = Field(None, description="结束时间筛选(秒)")
    speaker: Optional[str] = Field(None, description="发言人筛选")
    limit: Optional[int] = Field(default=100, description="返回数量限制", ge=1, le=1000)
    offset: Optional[int] = Field(default=0, description="偏移量", ge=0)


class FullTranscriptResponse(BaseModel):
    """完整转录响应模式"""
    meeting_id: int = Field(..., description="会议ID")
    full_text: str = Field(..., description="完整转录文本")
    total_segments: int = Field(..., description="总分段数")
    total_duration: Optional[float] = Field(None, description="总时长(秒)")
    speakers: List[str] = Field(..., description="发言人列表")
    language: Optional[str] = Field(None, description="主要语言")
    generated_at: datetime = Field(..., description="生成时间")