"""
会议管理相关API端点
"""

from fastapi import APIRouter, HTTPException, Depends, Path, Query
from typing import Dict, Any, Optional
from datetime import datetime

from app.services.meeting import get_meeting_service, MeetingService
from app.schemas.meeting import (
    MeetingCreate,
    MeetingUpdate,
    MeetingResponse,
    MeetingListResponse,
    MeetingSummaryResponse,
    MeetingSearchRequest,
    DashboardStats,
    MeetingBatchOperation,
    MeetingBatchOperationResponse
)


router = APIRouter()


@router.post("/", summary="创建会议")
async def create_meeting(
    request: MeetingCreate,
    service: MeetingService = Depends(get_meeting_service)
) -> Dict[str, Any]:
    """
    创建新会议
    
    - **title**: 会议标题
    - **description**: 会议描述（可选）
    - **start_time**: 开始时间（可选，默认为当前时间）
    - **template_id**: 使用的模板ID（可选）
    """
    result = await service.create_meeting(
        title=request.title,
        description=request.description,
        start_time=request.start_time,
        template_id=request.template_id
    )
    
    return {
        "success": True,
        "message": "会议创建成功",
        "data": result
    }


@router.get("/{meeting_id}", summary="获取会议详情")
async def get_meeting(
    meeting_id: int = Path(..., description="会议ID"),
    service: MeetingService = Depends(get_meeting_service)
) -> Dict[str, Any]:
    """获取指定会议的详细信息，包括统计数据"""
    result = await service.get_meeting(meeting_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    return {
        "success": True,
        "data": result
    }


@router.put("/{meeting_id}", summary="更新会议")
async def update_meeting(
    meeting_id: int = Path(..., description="会议ID"),
    request: MeetingUpdate,
    service: MeetingService = Depends(get_meeting_service)
) -> Dict[str, Any]:
    """
    更新会议信息
    
    - 只需提供要更新的字段
    - **status**: 会议状态（active、completed、cancelled）
    """
    result = await service.update_meeting(
        meeting_id=meeting_id,
        title=request.title,
        description=request.description,
        start_time=request.start_time,
        end_time=request.end_time,
        status=request.status,
        template_id=request.template_id
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    return {
        "success": True,
        "message": "会议更新成功",
        "data": result
    }


@router.delete("/{meeting_id}", summary="删除会议")
async def delete_meeting(
    meeting_id: int = Path(..., description="会议ID"),
    service: MeetingService = Depends(get_meeting_service)
) -> Dict[str, Any]:
    """
    删除会议及其所有相关数据
    
    ⚠️ 警告：此操作会永久删除会议的所有相关数据，包括：
    - 音频文件
    - 转录记录
    - 笔记
    - AI对话记录
    """
    success = await service.delete_meeting(meeting_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    return {
        "success": True,
        "message": "会议删除成功"
    }


@router.get("/", summary="获取会议列表")
async def get_meetings(
    status: Optional[str] = Query(None, description="状态筛选", regex="^(active|completed|cancelled)$"),
    template_id: Optional[int] = Query(None, description="模板ID筛选"),
    start_date: Optional[datetime] = Query(None, description="开始日期筛选"),
    end_date: Optional[datetime] = Query(None, description="结束日期筛选"),
    limit: int = Query(50, description="返回数量限制", ge=1, le=200),
    offset: int = Query(0, description="偏移量", ge=0),
    service: MeetingService = Depends(get_meeting_service)
) -> Dict[str, Any]:
    """
    获取会议列表，支持多种筛选条件
    
    - **status**: 按状态筛选会议
    - **template_id**: 按模板筛选会议
    - **start_date**: 筛选指定日期之后创建的会议
    - **end_date**: 筛选指定日期之前创建的会议
    """
    result = await service.get_meetings(
        status=status,
        template_id=template_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    
    return {
        "success": True,
        "data": result
    }


@router.post("/{meeting_id}/start", summary="开始会议")
async def start_meeting(
    meeting_id: int = Path(..., description="会议ID"),
    service: MeetingService = Depends(get_meeting_service)
) -> Dict[str, Any]:
    """
    开始会议
    
    将会议状态设置为active，并记录开始时间
    """
    result = await service.start_meeting(meeting_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    return {
        "success": True,
        "message": "会议已开始",
        "data": result
    }


@router.post("/{meeting_id}/end", summary="结束会议")
async def end_meeting(
    meeting_id: int = Path(..., description="会议ID"),
    service: MeetingService = Depends(get_meeting_service)
) -> Dict[str, Any]:
    """
    结束会议
    
    将会议状态设置为completed，并记录结束时间
    """
    result = await service.end_meeting(meeting_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    return {
        "success": True,
        "message": "会议已结束",
        "data": result
    }


@router.get("/{meeting_id}/summary", summary="获取会议总结")
async def get_meeting_summary(
    meeting_id: int = Path(..., description="会议ID"),
    service: MeetingService = Depends(get_meeting_service)
) -> Dict[str, Any]:
    """
    获取会议完整总结
    
    包括详细统计信息、最近的笔记样例、对话样例等
    """
    result = await service.get_meeting_summary(meeting_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    return {
        "success": True,
        "data": result
    }


@router.post("/search", summary="搜索会议")
async def search_meetings(
    request: MeetingSearchRequest,
    service: MeetingService = Depends(get_meeting_service)
) -> Dict[str, Any]:
    """
    搜索会议
    
    - **keyword**: 在会议标题和描述中搜索关键词
    - **status**: 按状态筛选搜索结果
    """
    result = await service.search_meetings(
        keyword=request.keyword,
        status=request.status,
        limit=request.limit,
        offset=request.offset
    )
    
    return {
        "success": True,
        "data": result
    }


@router.get("/dashboard/stats", summary="获取仪表板统计")
async def get_dashboard_stats(
    service: MeetingService = Depends(get_meeting_service)
) -> Dict[str, Any]:
    """
    获取仪表板统计信息
    
    包括总会议数、状态分布、最近活动、内容统计等
    """
    result = await service.get_dashboard_stats()
    
    return {
        "success": True,
        "data": result
    }


@router.post("/batch", summary="批量操作会议")
async def batch_operation_meetings(
    request: MeetingBatchOperation,
    service: MeetingService = Depends(get_meeting_service)
) -> Dict[str, Any]:
    """
    批量操作会议
    
    - **meeting_ids**: 要操作的会议ID列表
    - **operation**: 操作类型（delete、complete、cancel）
    """
    successful_meetings = []
    failed_meetings = []
    
    for meeting_id in request.meeting_ids:
        try:
            if request.operation == "delete":
                success = await service.delete_meeting(meeting_id)
                if success:
                    successful_meetings.append(meeting_id)
                else:
                    failed_meetings.append({"meeting_id": meeting_id, "error": "会议不存在"})
            
            elif request.operation == "complete":
                result = await service.end_meeting(meeting_id)
                if result:
                    successful_meetings.append(meeting_id)
                else:
                    failed_meetings.append({"meeting_id": meeting_id, "error": "会议不存在"})
            
            elif request.operation == "cancel":
                result = await service.update_meeting(meeting_id, status="cancelled")
                if result:
                    successful_meetings.append(meeting_id)
                else:
                    failed_meetings.append({"meeting_id": meeting_id, "error": "会议不存在"})
                    
        except Exception as e:
            failed_meetings.append({"meeting_id": meeting_id, "error": str(e)})
    
    return {
        "success": True,
        "message": f"批量{request.operation}完成，成功 {len(successful_meetings)} 个，失败 {len(failed_meetings)} 个",
        "data": {
            "total_requested": len(request.meeting_ids),
            "successful_count": len(successful_meetings),
            "failed_count": len(failed_meetings),
            "successful_meetings": successful_meetings,
            "failed_meetings": failed_meetings,
            "operation": request.operation
        }
    }


@router.get("/{meeting_id}/export", summary="导出会议完整记录")
async def export_meeting(
    meeting_id: int = Path(..., description="会议ID"),
    include_transcripts: bool = Query(True, description="是否包含转录内容"),
    include_notes: bool = Query(True, description="是否包含笔记"),
    include_conversations: bool = Query(True, description="是否包含对话记录"),
    format: str = Query("markdown", description="导出格式", regex="^(markdown|json)$"),
    service: MeetingService = Depends(get_meeting_service)
) -> Dict[str, Any]:
    """
    导出会议的完整记录
    
    - **include_transcripts**: 是否包含转录内容
    - **include_notes**: 是否包含用户笔记
    - **include_conversations**: 是否包含AI对话记录
    - **format**: 导出格式（markdown、json）
    """
    # 获取会议信息
    meeting = await service.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    # 构建导出内容
    sections = []
    included_sections = []
    
    # 基本信息
    basic_info = f"""# {meeting['title']}

**开始时间**: {meeting['start_time']}
**结束时间**: {meeting['end_time'] or '进行中'}
**状态**: {meeting['status']}
**描述**: {meeting['description'] or '无'}
"""
    sections.append(basic_info)
    included_sections.append("基本信息")
    
    # 统计信息
    stats = meeting['stats']
    stats_info = f"""
## 会议统计

- 音频文件: {stats['audio_files']} 个
- 转录段数: {stats['transcriptions']} 段
- 笔记数量: {stats['notes']} 条
- 对话记录: {stats['conversations']} 次
"""
    sections.append(stats_info)
    included_sections.append("统计信息")
    
    # 获取并包含转录内容
    if include_transcripts:
        from app.services.transcription import get_transcription_service
        transcription_service = get_transcription_service()
        full_transcript = await transcription_service.get_full_meeting_transcript(meeting_id)
        
        if full_transcript:
            sections.append(f"\n## 会议转录\n\n{full_transcript}")
            included_sections.append("转录内容")
    
    # 获取并包含笔记
    if include_notes:
        from app.services.note import get_note_service
        note_service = get_note_service()
        notes = await note_service.get_meeting_notes(meeting_id)
        
        if notes:
            notes_content = "\n## 会议笔记\n\n"
            for i, note in enumerate(notes, 1):
                enhanced_marker = " [AI增强]" if note["is_ai_enhanced"] else ""
                notes_content += f"### 笔记 {i}{enhanced_marker}\n\n{note['content']}\n\n"
            sections.append(notes_content)
            included_sections.append("笔记内容")
    
    # 获取并包含对话记录
    if include_conversations:
        from app.services.conversation import get_conversation_service
        conversation_service = get_conversation_service()
        conversations_data = await conversation_service.get_meeting_conversations(meeting_id, limit=1000)
        conversations = conversations_data["conversations"]
        
        if conversations:
            conv_content = "\n## AI对话记录\n\n"
            for i, conv in enumerate(conversations, 1):
                conv_content += f"### 对话 {i}\n\n**问题**: {conv['question']}\n\n**回答**: {conv['answer']}\n\n"
            sections.append(conv_content)
            included_sections.append("对话记录")
    
    # 生成最终内容
    if format == "json":
        import json
        export_data = {
            "meeting": meeting,
            "sections": {section: content for section, content in zip(included_sections, sections[1:]) if section != "基本信息"}
        }
        content = json.dumps(export_data, ensure_ascii=False, indent=2, default=str)
    else:  # markdown
        content = "\n".join(sections)
    
    return {
        "success": True,
        "data": {
            "meeting_id": meeting_id,
            "meeting_title": meeting["title"],
            "format": format,
            "content": content,
            "exported_at": datetime.now(),
            "included_sections": included_sections
        }
    }