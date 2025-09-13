"""
AI对话相关API端点
"""

from fastapi import APIRouter, HTTPException, Depends, Path, Query
from typing import Dict, Any, List

from app.services.conversation import get_conversation_service, ConversationService
from app.schemas.conversation import (
    QuestionRequest,
    ConversationResponse,
    ConversationDetail,
    BatchQuestionRequest,
    BatchConversationResponse,
    ConversationSearchRequest,
    SuggestedQuestionsResponse,
    QuestionSuggestionRequest
)


router = APIRouter()


@router.post("/meetings/{meeting_id}/ask", summary="向会议内容提问")
async def ask_question(
    meeting_id: int = Path(..., description="会议ID"),
    request: QuestionRequest,
    service: ConversationService = Depends(get_conversation_service)
) -> Dict[str, Any]:
    """
    基于会议内容回答问题
    
    - **question**: 要询问的问题
    - **include_notes**: 是否在上下文中包含用户笔记
    - **include_transcripts**: 是否在上下文中包含会议转录
    - **context_limit**: 上下文内容的最大长度限制
    
    AI会基于会议的转录和笔记内容来回答问题
    """
    result = await service.ask_question(
        meeting_id=meeting_id,
        question=request.question,
        include_notes=request.include_notes,
        include_transcripts=request.include_transcripts,
        context_limit=request.context_limit
    )
    
    return {
        "success": True,
        "message": "问题回答完成",
        "data": result
    }


@router.get("/{conversation_id}", summary="获取对话详情")
async def get_conversation(
    conversation_id: int = Path(..., description="对话ID"),
    service: ConversationService = Depends(get_conversation_service)
) -> Dict[str, Any]:
    """获取单个对话的详细信息，包括使用的上下文内容"""
    result = await service.get_conversation(conversation_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="对话记录不存在")
    
    return {
        "success": True,
        "data": result
    }


@router.delete("/{conversation_id}", summary="删除对话记录")
async def delete_conversation(
    conversation_id: int = Path(..., description="对话ID"),
    service: ConversationService = Depends(get_conversation_service)
) -> Dict[str, Any]:
    """删除指定的对话记录"""
    success = await service.delete_conversation(conversation_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="对话记录不存在")
    
    return {
        "success": True,
        "message": "对话记录删除成功"
    }


@router.get("/meetings/{meeting_id}/conversations", summary="获取会议对话历史")
async def get_meeting_conversations(
    meeting_id: int = Path(..., description="会议ID"),
    limit: int = Query(50, description="返回数量限制", ge=1, le=200),
    offset: int = Query(0, description="偏移量", ge=0),
    service: ConversationService = Depends(get_conversation_service)
) -> Dict[str, Any]:
    """获取指定会议的所有对话记录"""
    result = await service.get_meeting_conversations(
        meeting_id=meeting_id,
        limit=limit,
        offset=offset
    )
    
    return {
        "success": True,
        "data": result
    }


@router.post("/meetings/{meeting_id}/batch-ask", summary="批量提问")
async def batch_ask_questions(
    meeting_id: int = Path(..., description="会议ID"),
    request: BatchQuestionRequest,
    service: ConversationService = Depends(get_conversation_service)
) -> Dict[str, Any]:
    """
    批量向会议内容提问
    
    - **questions**: 问题列表（最多10个）
    - **include_notes**: 是否包含笔记内容
    - **include_transcripts**: 是否包含转录内容
    
    适合一次性询问多个相关问题的场景
    """
    result = await service.batch_ask_questions(
        meeting_id=meeting_id,
        questions=request.questions,
        include_notes=request.include_notes,
        include_transcripts=request.include_transcripts
    )
    
    return {
        "success": True,
        "message": f"批量提问完成，成功 {result['successful_count']} 个，失败 {result['failed_count']} 个",
        "data": result
    }


@router.get("/meetings/{meeting_id}/suggested-questions", summary="获取建议问题")
async def get_suggested_questions(
    meeting_id: int = Path(..., description="会议ID"),
    question_count: int = Query(5, description="建议问题数量", ge=1, le=10),
    service: ConversationService = Depends(get_conversation_service)
) -> Dict[str, Any]:
    """
    基于会议内容生成建议问题
    
    AI会分析会议的转录和笔记内容，生成可能有价值的问题
    """
    questions = await service.get_suggested_questions(
        meeting_id=meeting_id,
        question_count=question_count
    )
    
    if not questions:
        return {
            "success": True,
            "message": "没有足够的会议内容来生成建议问题",
            "data": {
                "meeting_id": meeting_id,
                "questions": [],
                "question_count": 0
            }
        }
    
    from datetime import datetime
    
    return {
        "success": True,
        "data": {
            "meeting_id": meeting_id,
            "questions": questions,
            "generated_at": datetime.now(),
            "question_count": len(questions)
        }
    }


@router.post("/search", summary="搜索对话记录")
async def search_conversations(
    request: ConversationSearchRequest,
    service: ConversationService = Depends(get_conversation_service)
) -> Dict[str, Any]:
    """
    搜索对话记录
    
    - **meeting_id**: 会议ID筛选（可选）
    - **keyword**: 在问题和答案中搜索关键词
    - **limit**: 返回数量限制
    - **offset**: 偏移量
    """
    result = await service.search_conversations(
        meeting_id=request.meeting_id,
        keyword=request.keyword,
        limit=request.limit,
        offset=request.offset
    )
    
    return {
        "success": True,
        "data": result
    }


@router.get("/meetings/{meeting_id}/stats", summary="获取会议对话统计")
async def get_conversation_stats(
    meeting_id: int = Path(..., description="会议ID"),
    service: ConversationService = Depends(get_conversation_service)
) -> Dict[str, Any]:
    """
    获取会议的对话统计信息
    
    包括对话数量、常见问题主题、使用的模型等统计数据
    """
    from app.db.session import AsyncSessionLocal
    from app.models.conversation import Conversation
    from sqlalchemy import select, func
    from datetime import datetime
    
    async with AsyncSessionLocal() as session:
        # 基础统计
        total_result = await session.execute(
            select(func.count(Conversation.id)).where(Conversation.meeting_id == meeting_id)
        )
        total_conversations = total_result.scalar() or 0
        
        if total_conversations == 0:
            return {
                "success": True,
                "data": {
                    "meeting_id": meeting_id,
                    "total_conversations": 0,
                    "most_asked_topics": [],
                    "average_answer_length": 0.0,
                    "models_used": [],
                    "first_question_at": None,
                    "last_question_at": None
                }
            }
        
        # 平均答案长度
        conversations_result = await session.execute(
            select(Conversation.answer, Conversation.model_used, Conversation.created_at)
            .where(Conversation.meeting_id == meeting_id)
        )
        conversations = conversations_result.fetchall()
        
        answer_lengths = [len(c.answer) for c in conversations]
        average_answer_length = sum(answer_lengths) / len(answer_lengths)
        
        # 模型使用统计
        models_count = {}
        for c in conversations:
            model = c.model_used or "unknown"
            models_count[model] = models_count.get(model, 0) + 1
        
        models_used = [
            {"model": model, "count": count, "percentage": round((count / total_conversations) * 100, 2)}
            for model, count in models_count.items()
        ]
        
        # 时间统计
        created_times = [c.created_at for c in conversations]
        first_question_at = min(created_times) if created_times else None
        last_question_at = max(created_times) if created_times else None
    
    return {
        "success": True,
        "data": {
            "meeting_id": meeting_id,
            "total_conversations": total_conversations,
            "most_asked_topics": [],  # TODO: 实现主题分析
            "average_answer_length": round(average_answer_length, 2),
            "models_used": models_used,
            "first_question_at": first_question_at,
            "last_question_at": last_question_at
        }
    }


@router.get("/meetings/{meeting_id}/export", summary="导出会议对话记录")
async def export_conversations(
    meeting_id: int = Path(..., description="会议ID"),
    format: str = Query("markdown", description="导出格式", regex="^(markdown|json|text)$"),
    include_context: bool = Query(False, description="是否包含上下文信息"),
    service: ConversationService = Depends(get_conversation_service)
) -> Dict[str, Any]:
    """
    导出会议的对话记录
    
    - **format**: 导出格式（markdown、json、text）
    - **include_context**: 是否包含每次对话使用的上下文内容
    """
    conversations_data = await service.get_meeting_conversations(
        meeting_id=meeting_id,
        limit=1000  # 导出时获取所有记录
    )
    
    conversations = conversations_data["conversations"]
    
    if not conversations:
        return {
            "success": True,
            "message": "该会议没有对话记录",
            "data": {
                "meeting_id": meeting_id,
                "format": format,
                "content": "",
                "total_conversations": 0
            }
        }
    
    # 根据格式生成内容
    if format == "markdown":
        lines = [f"# 会议 {meeting_id} 对话记录\n"]
        for i, conv in enumerate(conversations, 1):
            lines.append(f"## 对话 {i}")
            lines.append(f"**时间**: {conv['created_at']}")
            lines.append(f"**问题**: {conv['question']}")
            lines.append(f"**回答**: {conv['answer']}")
            lines.append(f"**模型**: {conv['model_used']}")
            lines.append("")
        content = "\n".join(lines)
    
    elif format == "json":
        import json
        content = json.dumps(conversations, ensure_ascii=False, indent=2, default=str)
    
    else:  # text
        lines = [f"会议 {meeting_id} 对话记录\n{'='*50}\n"]
        for i, conv in enumerate(conversations, 1):
            lines.append(f"对话 {i}")
            lines.append(f"时间: {conv['created_at']}")
            lines.append(f"问题: {conv['question']}")
            lines.append(f"回答: {conv['answer']}")
            lines.append(f"模型: {conv['model_used']}")
            lines.append("-" * 50)
        content = "\n".join(lines)
    
    from datetime import datetime
    
    return {
        "success": True,
        "data": {
            "meeting_id": meeting_id,
            "format": format,
            "content": content,
            "total_conversations": len(conversations),
            "exported_at": datetime.now()
        }
    }