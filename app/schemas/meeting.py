"""
会议相关的Pydantic模式
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class MeetingBase(BaseModel):
    """会议基础模式"""
    title: str = Field(..., description="会议标题", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="会议描述", max_length=1000)
    start_time: Optional[datetime] = Field(None, description="开始时间")
    template_id: Optional[int] = Field(None, description="使用的模板ID")


class MeetingCreate(MeetingBase):
    """创建会议请求模式"""
    
    class Config:
        schema_extra = {
            "example": {
                "title": "团队周会",
                "description": "讨论本周工作进展和下周计划",
                "start_time": "2024-01-15T10:00:00",
                "template_id": 1
            }
        }


class MeetingUpdate(BaseModel):
    """更新会议请求模式"""
    title: Optional[str] = Field(None, description="会议标题", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="会议描述", max_length=1000)
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    status: Optional[str] = Field(None, description="会议状态", regex="^(active|completed|cancelled)$")
    template_id: Optional[int] = Field(None, description="模板ID")


class MeetingStats(BaseModel):
    """会议统计模式"""
    audio_files: int = Field(..., description="音频文件数量")
    transcriptions: int = Field(..., description="转录段数")
    notes: int = Field(..., description="笔记数量")
    conversations: int = Field(..., description="对话数量")


class MeetingDetailedStats(MeetingStats):
    """会议详细统计模式"""
    audio_duration_minutes: float = Field(..., description="音频总时长(分钟)")
    ai_enhanced_notes: int = Field(..., description="AI增强笔记数")
    note_enhancement_rate: float = Field(..., description="笔记增强率(%)")
    transcription_confidence: Dict[str, Optional[float]] = Field(..., description="转录置信度统计")


class TemplateInfo(BaseModel):
    """模板信息模式"""
    id: int = Field(..., description="模板ID")
    name: str = Field(..., description="模板名称")
    category: str = Field(..., description="模板分类")


class MeetingResponse(MeetingBase):
    """会议响应模式"""
    id: int = Field(..., description="会议ID")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    status: str = Field(..., description="会议状态")
    template: Optional[TemplateInfo] = Field(None, description="模板信息")
    stats: MeetingStats = Field(..., description="基础统计信息")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class MeetingListResponse(BaseModel):
    """会议列表响应模式"""
    meetings: List[MeetingResponse] = Field(..., description="会议列表")
    total: int = Field(..., description="总数量")
    limit: int = Field(..., description="限制数量")
    offset: int = Field(..., description="偏移量")
    has_more: bool = Field(..., description="是否还有更多数据")


class MeetingQuery(BaseModel):
    """会议查询参数"""
    status: Optional[str] = Field(None, description="状态筛选", regex="^(active|completed|cancelled)$")
    template_id: Optional[int] = Field(None, description="模板ID筛选")
    start_date: Optional[datetime] = Field(None, description="开始日期筛选")
    end_date: Optional[datetime] = Field(None, description="结束日期筛选")
    limit: int = Field(default=50, description="返回数量限制", ge=1, le=200)
    offset: int = Field(default=0, description="偏移量", ge=0)


class MeetingSummaryResponse(BaseModel):
    """会议总结响应模式"""
    id: int = Field(..., description="会议ID")
    title: str = Field(..., description="会议标题")
    description: Optional[str] = Field(None, description="会议描述")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    status: str = Field(..., description="会议状态")
    template: Optional[TemplateInfo] = Field(None, description="模板信息")
    detailed_stats: MeetingDetailedStats = Field(..., description="详细统计信息")
    recent_notes_sample: List[str] = Field(..., description="最近笔记样例")
    recent_conversations_sample: List[Dict[str, str]] = Field(..., description="最近对话样例")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class MeetingSearchRequest(BaseModel):
    """会议搜索请求模式"""
    keyword: str = Field(default="", description="搜索关键词")
    status: Optional[str] = Field(None, description="状态筛选", regex="^(active|completed|cancelled)$")
    limit: int = Field(default=50, description="返回数量限制", ge=1, le=200)
    offset: int = Field(default=0, description="偏移量", ge=0)
    
    class Config:
        schema_extra = {
            "example": {
                "keyword": "周会",
                "status": "completed",
                "limit": 20,
                "offset": 0
            }
        }


class DashboardStats(BaseModel):
    """仪表板统计响应模式"""
    total_meetings: int = Field(..., description="总会议数")
    status_breakdown: Dict[str, int] = Field(..., description="状态分布")
    recent_activity: Dict[str, int] = Field(..., description="最近活动统计")
    content_stats: Dict[str, Any] = Field(..., description="内容统计")


class MeetingStatusUpdate(BaseModel):
    """会议状态更新模式"""
    status: str = Field(..., description="新状态", regex="^(active|completed|cancelled)$")
    end_time: Optional[datetime] = Field(None, description="结束时间（结束会议时使用）")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "completed",
                "end_time": "2024-01-15T11:30:00"
            }
        }


class MeetingExportRequest(BaseModel):
    """会议导出请求模式"""
    meeting_id: int = Field(..., description="会议ID")
    include_transcripts: bool = Field(default=True, description="是否包含转录内容")
    include_notes: bool = Field(default=True, description="是否包含笔记")
    include_conversations: bool = Field(default=True, description="是否包含对话记录")
    format: str = Field(default="markdown", description="导出格式", regex="^(markdown|json|pdf)$")
    
    class Config:
        schema_extra = {
            "example": {
                "meeting_id": 1,
                "include_transcripts": True,
                "include_notes": True,
                "include_conversations": True,
                "format": "markdown"
            }
        }


class MeetingExportResponse(BaseModel):
    """会议导出响应模式"""
    meeting_id: int = Field(..., description="会议ID")
    meeting_title: str = Field(..., description="会议标题")
    format: str = Field(..., description="导出格式")
    content: str = Field(..., description="导出内容")
    exported_at: datetime = Field(..., description="导出时间")
    included_sections: List[str] = Field(..., description="包含的内容部分")


class MeetingBatchOperation(BaseModel):
    """会议批量操作模式"""
    meeting_ids: List[int] = Field(..., description="会议ID列表", min_items=1)
    operation: str = Field(..., description="操作类型", regex="^(delete|complete|cancel)$")
    
    class Config:
        schema_extra = {
            "example": {
                "meeting_ids": [1, 2, 3],
                "operation": "complete"
            }
        }


class MeetingBatchOperationResponse(BaseModel):
    """会议批量操作响应模式"""
    total_requested: int = Field(..., description="请求处理总数")
    successful_count: int = Field(..., description="成功数量")
    failed_count: int = Field(..., description="失败数量")
    successful_meetings: List[int] = Field(..., description="成功处理的会议ID")
    failed_meetings: List[Dict[str, Any]] = Field(..., description="失败的会议及错误信息")
    operation: str = Field(..., description="执行的操作类型")


class MeetingArchiveRequest(BaseModel):
    """会议归档请求模式"""
    archive_before: datetime = Field(..., description="归档此日期之前的会议")
    status_filter: Optional[str] = Field(None, description="只归档指定状态的会议")
    
    class Config:
        schema_extra = {
            "example": {
                "archive_before": "2024-01-01T00:00:00",
                "status_filter": "completed"
            }
        }