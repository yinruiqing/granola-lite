"""
笔记相关的Pydantic模式
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class NoteBase(BaseModel):
    """笔记基础模式"""
    content: str = Field(..., description="笔记内容", min_length=1)
    position: int = Field(default=0, description="笔记位置顺序", ge=0)
    timestamp: Optional[float] = Field(None, description="时间戳(相对会议开始的秒数)", ge=0)


class NoteCreate(NoteBase):
    """创建笔记请求模式"""
    meeting_id: int = Field(..., description="会议ID")


class NoteUpdate(BaseModel):
    """更新笔记请求模式"""
    content: Optional[str] = Field(None, description="笔记内容", min_length=1)
    position: Optional[int] = Field(None, description="笔记位置顺序", ge=0)
    timestamp: Optional[float] = Field(None, description="时间戳(秒)", ge=0)


class NoteResponse(NoteBase):
    """笔记响应模式"""
    id: int = Field(..., description="笔记ID")
    meeting_id: int = Field(..., description="会议ID")
    original_content: Optional[str] = Field(None, description="AI增强前的原始内容")
    is_ai_enhanced: bool = Field(..., description="是否已AI增强")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class NoteReorderRequest(BaseModel):
    """笔记重新排序请求模式"""
    note_orders: List[dict] = Field(
        ..., 
        description="笔记顺序列表",
        example=[{"note_id": 1, "position": 1}, {"note_id": 2, "position": 2}]
    )
    
    class Config:
        schema_extra = {
            "example": {
                "note_orders": [
                    {"note_id": 1, "position": 1},
                    {"note_id": 2, "position": 2},
                    {"note_id": 3, "position": 3}
                ]
            }
        }


class NoteSearchRequest(BaseModel):
    """笔记搜索请求模式"""
    meeting_id: Optional[int] = Field(None, description="会议ID筛选")
    keyword: str = Field(default="", description="搜索关键词")
    is_ai_enhanced: Optional[bool] = Field(None, description="AI增强状态筛选")
    limit: int = Field(default=50, description="返回数量限制", ge=1, le=200)
    offset: int = Field(default=0, description="偏移量", ge=0)


class NoteSearchResponse(BaseModel):
    """笔记搜索响应模式"""
    notes: List[NoteResponse] = Field(..., description="笔记列表")
    total: int = Field(..., description="总数量")
    limit: int = Field(..., description="限制数量")
    offset: int = Field(..., description="偏移量")
    has_more: bool = Field(..., description="是否还有更多数据")


class NoteSummaryResponse(BaseModel):
    """笔记摘要响应模式"""
    meeting_id: int = Field(..., description="会议ID")
    total_notes: int = Field(..., description="总笔记数")
    ai_enhanced_notes: int = Field(..., description="AI增强笔记数")
    original_notes: int = Field(..., description="原始笔记数")
    latest_update: Optional[datetime] = Field(None, description="最后更新时间")
    total_content_length: int = Field(..., description="总内容长度")


class NoteBatchOperation(BaseModel):
    """笔记批量操作模式"""
    note_ids: List[int] = Field(..., description="笔记ID列表", min_items=1)
    operation: str = Field(..., description="操作类型", regex="^(delete|duplicate|enhance)$")
    
    class Config:
        schema_extra = {
            "example": {
                "note_ids": [1, 2, 3],
                "operation": "delete"
            }
        }


class NoteExportRequest(BaseModel):
    """笔记导出请求模式"""
    meeting_id: int = Field(..., description="会议ID")
    format: str = Field(default="markdown", description="导出格式", regex="^(markdown|text|json)$")
    include_timestamps: bool = Field(default=True, description="是否包含时间戳")
    include_ai_enhanced: bool = Field(default=True, description="是否包含AI增强内容")
    include_original: bool = Field(default=False, description="是否包含原始内容")


class NoteExportResponse(BaseModel):
    """笔记导出响应模式"""
    meeting_id: int = Field(..., description="会议ID")
    format: str = Field(..., description="导出格式")
    content: str = Field(..., description="导出内容")
    total_notes: int = Field(..., description="导出笔记数")
    generated_at: datetime = Field(..., description="生成时间")