"""
AI增强相关的Pydantic模式
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class NoteEnhancementRequest(BaseModel):
    """笔记增强请求模式"""
    use_template: bool = Field(default=True, description="是否使用会议模板")
    custom_prompt: Optional[str] = Field(None, description="自定义提示词")
    
    class Config:
        schema_extra = {
            "example": {
                "use_template": True,
                "custom_prompt": "请重点突出讨论的技术要点和行动项"
            }
        }


class MeetingNotesEnhancementRequest(BaseModel):
    """会议笔记批量增强请求模式"""
    only_unenhanced: bool = Field(default=True, description="是否只增强未增强过的笔记")
    use_template: bool = Field(default=True, description="是否使用会议模板")
    custom_prompt: Optional[str] = Field(None, description="自定义提示词")
    
    class Config:
        schema_extra = {
            "example": {
                "only_unenhanced": True,
                "use_template": True,
                "custom_prompt": None
            }
        }


class NoteEnhancementResponse(BaseModel):
    """笔记增强响应模式"""
    id: int = Field(..., description="笔记ID")
    meeting_id: int = Field(..., description="会议ID")
    original_content: str = Field(..., description="原始内容")
    enhanced_content: str = Field(..., description="增强后内容")
    is_ai_enhanced: bool = Field(..., description="是否已AI增强")
    enhancement_method: str = Field(..., description="增强方法")
    template_used: bool = Field(..., description="是否使用了模板")
    updated_at: datetime = Field(..., description="更新时间")


class MeetingEnhancementResult(BaseModel):
    """单个笔记增强结果"""
    note_id: int = Field(..., description="笔记ID")
    status: str = Field(..., description="增强状态", regex="^(success|failed)$")
    original_length: Optional[int] = Field(None, description="原始内容长度")
    enhanced_length: Optional[int] = Field(None, description="增强后内容长度")
    error: Optional[str] = Field(None, description="错误信息")


class MeetingNotesEnhancementResponse(BaseModel):
    """会议笔记批量增强响应模式"""
    meeting_id: int = Field(..., description="会议ID")
    total_notes: int = Field(..., description="总笔记数")
    enhanced_count: int = Field(..., description="成功增强数量")
    skipped_count: int = Field(..., description="跳过数量")
    failed_count: int = Field(..., description="失败数量")
    results: List[MeetingEnhancementResult] = Field(..., description="详细结果")
    enhancement_method: str = Field(..., description="增强方法")
    template_used: bool = Field(..., description="是否使用了模板")
    message: Optional[str] = Field(None, description="额外信息")


class NoteComparisonResponse(BaseModel):
    """笔记比较响应模式"""
    note_id: int = Field(..., description="笔记ID")
    original_content: str = Field(..., description="原始内容")
    enhanced_content: str = Field(..., description="增强后内容")
    original_length: int = Field(..., description="原始内容长度")
    enhanced_length: int = Field(..., description="增强后内容长度")
    length_increase: int = Field(..., description="长度增加量")
    length_increase_percentage: float = Field(..., description="长度增加百分比")
    is_ai_enhanced: bool = Field(..., description="是否已AI增强")


class NoteRevertResponse(BaseModel):
    """笔记还原响应模式"""
    id: int = Field(..., description="笔记ID")
    meeting_id: int = Field(..., description="会议ID")
    content: str = Field(..., description="还原后内容")
    original_content: str = Field(..., description="原始内容")
    is_ai_enhanced: bool = Field(..., description="是否已AI增强")
    reverted_at: datetime = Field(..., description="还原时间")


class EnhancementStatsResponse(BaseModel):
    """增强统计响应模式"""
    meeting_id: int = Field(..., description="会议ID")
    total_notes: int = Field(..., description="总笔记数")
    enhanced_notes: int = Field(..., description="已增强笔记数")
    unenhanced_notes: int = Field(..., description="未增强笔记数")
    enhancement_percentage: float = Field(..., description="增强比例")
    average_length_increase: float = Field(..., description="平均长度增加量")
    total_original_length: int = Field(..., description="原始内容总长度")
    total_enhanced_length: int = Field(..., description="增强后内容总长度")


class CustomEnhancementPrompt(BaseModel):
    """自定义增强提示模式"""
    prompt: str = Field(..., description="提示内容", min_length=10, max_length=2000)
    focus_areas: Optional[List[str]] = Field(None, description="重点关注领域")
    output_format: Optional[str] = Field(None, description="输出格式要求")
    
    class Config:
        schema_extra = {
            "example": {
                "prompt": "请将这些笔记整理成结构化的会议纪要，重点突出决策和行动项",
                "focus_areas": ["决策", "行动项", "时间节点"],
                "output_format": "markdown"
            }
        }


class BatchEnhancementRequest(BaseModel):
    """批量增强请求模式"""
    note_ids: List[int] = Field(..., description="笔记ID列表", min_items=1)
    use_template: bool = Field(default=True, description="是否使用会议模板")
    custom_prompt: Optional[str] = Field(None, description="自定义提示词")
    
    class Config:
        schema_extra = {
            "example": {
                "note_ids": [1, 2, 3],
                "use_template": True,
                "custom_prompt": None
            }
        }


class BatchEnhancementResponse(BaseModel):
    """批量增强响应模式"""
    total_requested: int = Field(..., description="请求处理总数")
    successful_count: int = Field(..., description="成功数量")
    failed_count: int = Field(..., description="失败数量")
    results: List[Dict[str, Any]] = Field(..., description="详细结果")
    enhancement_method: str = Field(..., description="增强方法")
    template_used: bool = Field(..., description="是否使用了模板")