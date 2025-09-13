"""
对话相关的Pydantic模式
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ConversationBase(BaseModel):
    """对话基础模式"""
    question: str = Field(..., description="用户问题", min_length=1, max_length=1000)


class QuestionRequest(ConversationBase):
    """提问请求模式"""
    include_notes: bool = Field(default=True, description="是否包含笔记内容")
    include_transcripts: bool = Field(default=True, description="是否包含转录内容")
    context_limit: int = Field(default=8000, description="上下文长度限制", ge=1000, le=16000)
    
    class Config:
        schema_extra = {
            "example": {
                "question": "这次会议讨论的主要问题是什么？",
                "include_notes": True,
                "include_transcripts": True,
                "context_limit": 8000
            }
        }


class ConversationResponse(BaseModel):
    """对话响应模式"""
    conversation_id: int = Field(..., description="对话ID")
    meeting_id: int = Field(..., description="会议ID")
    question: str = Field(..., description="用户问题")
    answer: str = Field(..., description="AI回答")
    context_summary: Dict[str, Any] = Field(..., description="上下文摘要信息")
    model_used: str = Field(..., description="使用的AI模型")
    created_at: datetime = Field(..., description="创建时间")


class ConversationDetail(BaseModel):
    """对话详情模式"""
    id: int = Field(..., description="对话ID")
    meeting_id: int = Field(..., description="会议ID")
    question: str = Field(..., description="用户问题")
    answer: str = Field(..., description="AI回答")
    context_used: Optional[str] = Field(None, description="使用的上下文内容")
    model_used: str = Field(..., description="使用的AI模型")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """对话列表响应模式"""
    conversations: List[Dict[str, Any]] = Field(..., description="对话列表")
    total: int = Field(..., description="总数量")
    limit: int = Field(..., description="限制数量")
    offset: int = Field(..., description="偏移量")
    has_more: bool = Field(..., description="是否还有更多数据")


class BatchQuestionRequest(BaseModel):
    """批量提问请求模式"""
    questions: List[str] = Field(..., description="问题列表", min_items=1, max_items=10)
    include_notes: bool = Field(default=True, description="是否包含笔记内容")
    include_transcripts: bool = Field(default=True, description="是否包含转录内容")
    
    class Config:
        schema_extra = {
            "example": {
                "questions": [
                    "这次会议的主要决策是什么？",
                    "有哪些具体的行动项？",
                    "讨论中提到了哪些技术方案？"
                ],
                "include_notes": True,
                "include_transcripts": True
            }
        }


class BatchConversationResponse(BaseModel):
    """批量对话响应模式"""
    meeting_id: int = Field(..., description="会议ID")
    total_questions: int = Field(..., description="总问题数")
    successful_count: int = Field(..., description="成功处理数量")
    failed_count: int = Field(..., description="失败数量")
    results: List[ConversationResponse] = Field(..., description="成功的对话结果")
    failed: List[Dict[str, str]] = Field(..., description="失败的问题及错误信息")


class ConversationSearchRequest(BaseModel):
    """对话搜索请求模式"""
    meeting_id: Optional[int] = Field(None, description="会议ID筛选")
    keyword: str = Field(default="", description="搜索关键词")
    limit: int = Field(default=50, description="返回数量限制", ge=1, le=200)
    offset: int = Field(default=0, description="偏移量", ge=0)
    
    class Config:
        schema_extra = {
            "example": {
                "meeting_id": 1,
                "keyword": "决策",
                "limit": 20,
                "offset": 0
            }
        }


class SuggestedQuestionsResponse(BaseModel):
    """建议问题响应模式"""
    meeting_id: int = Field(..., description="会议ID")
    questions: List[str] = Field(..., description="建议问题列表")
    generated_at: datetime = Field(..., description="生成时间")
    question_count: int = Field(..., description="问题数量")


class ConversationStatsResponse(BaseModel):
    """对话统计响应模式"""
    meeting_id: int = Field(..., description="会议ID")
    total_conversations: int = Field(..., description="总对话数")
    most_asked_topics: List[Dict[str, Any]] = Field(..., description="最常询问的话题")
    average_answer_length: float = Field(..., description="平均回答长度")
    models_used: List[Dict[str, Any]] = Field(..., description="使用的模型统计")
    first_question_at: Optional[datetime] = Field(None, description="第一次提问时间")
    last_question_at: Optional[datetime] = Field(None, description="最后提问时间")


class ConversationExportRequest(BaseModel):
    """对话导出请求模式"""
    meeting_id: int = Field(..., description="会议ID")
    format: str = Field(default="markdown", description="导出格式", regex="^(markdown|json|text)$")
    include_context: bool = Field(default=False, description="是否包含上下文信息")
    
    class Config:
        schema_extra = {
            "example": {
                "meeting_id": 1,
                "format": "markdown",
                "include_context": False
            }
        }


class ConversationExportResponse(BaseModel):
    """对话导出响应模式"""
    meeting_id: int = Field(..., description="会议ID")
    format: str = Field(..., description="导出格式")
    content: str = Field(..., description="导出内容")
    total_conversations: int = Field(..., description="导出对话数")
    exported_at: datetime = Field(..., description="导出时间")


class QuestionSuggestionRequest(BaseModel):
    """问题建议请求模式"""
    question_count: int = Field(default=5, description="建议问题数量", ge=1, le=10)
    focus_areas: Optional[List[str]] = Field(None, description="关注领域")
    
    class Config:
        schema_extra = {
            "example": {
                "question_count": 5,
                "focus_areas": ["决策", "行动项", "技术方案"]
            }
        }


class ConversationFeedback(BaseModel):
    """对话反馈模式"""
    conversation_id: int = Field(..., description="对话ID")
    rating: int = Field(..., description="评分", ge=1, le=5)
    feedback: Optional[str] = Field(None, description="反馈内容", max_length=500)
    helpful: bool = Field(..., description="是否有帮助")
    
    class Config:
        schema_extra = {
            "example": {
                "conversation_id": 1,
                "rating": 4,
                "feedback": "回答很准确，但可以更详细一些",
                "helpful": True
            }
        }