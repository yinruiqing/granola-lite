"""
笔记相关API端点
"""

from fastapi import APIRouter, HTTPException, Depends, Path, Query
from typing import List, Dict, Any, Optional

from app.services.note import get_note_service, NoteService
from app.schemas.note import (
    NoteCreate,
    NoteUpdate, 
    NoteResponse,
    NoteReorderRequest,
    NoteSearchRequest,
    NoteSearchResponse,
    NoteBatchOperation
)


router = APIRouter()


@router.post("/", summary="创建笔记")
async def create_note(
    request: NoteCreate,
    service: NoteService = Depends(get_note_service)
) -> Dict[str, Any]:
    """
    创建新笔记
    
    - **meeting_id**: 会议ID
    - **content**: 笔记内容
    - **position**: 笔记位置顺序（可选，默认追加到最后）
    - **timestamp**: 时间戳，相对会议开始的秒数（可选）
    """
    result = await service.create_note(
        meeting_id=request.meeting_id,
        content=request.content,
        position=request.position,
        timestamp=request.timestamp
    )
    
    return {
        "success": True,
        "message": "笔记创建成功",
        "data": result
    }


@router.get("/{note_id}", summary="获取笔记详情")
async def get_note(
    note_id: int = Path(..., description="笔记ID"),
    service: NoteService = Depends(get_note_service)
) -> Dict[str, Any]:
    """获取单个笔记的详细信息"""
    result = await service.get_note(note_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="笔记不存在")
    
    return {
        "success": True,
        "data": result
    }


@router.put("/{note_id}", summary="更新笔记")
async def update_note(
    note_id: int = Path(..., description="笔记ID"),
    request: NoteUpdate,
    service: NoteService = Depends(get_note_service)
) -> Dict[str, Any]:
    """
    更新笔记内容
    
    - **content**: 新的笔记内容（可选）
    - **position**: 新的位置顺序（可选）
    - **timestamp**: 新的时间戳（可选）
    """
    result = await service.update_note(
        note_id=note_id,
        content=request.content,
        position=request.position,
        timestamp=request.timestamp
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="笔记不存在")
    
    return {
        "success": True,
        "message": "笔记更新成功",
        "data": result
    }


@router.delete("/{note_id}", summary="删除笔记")
async def delete_note(
    note_id: int = Path(..., description="笔记ID"),
    service: NoteService = Depends(get_note_service)
) -> Dict[str, Any]:
    """删除指定笔记"""
    success = await service.delete_note(note_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="笔记不存在")
    
    return {
        "success": True,
        "message": "笔记删除成功"
    }


@router.get("/meeting/{meeting_id}", summary="获取会议笔记列表")
async def get_meeting_notes(
    meeting_id: int = Path(..., description="会议ID"),
    include_ai_enhanced: bool = Query(True, description="是否包含AI增强笔记"),
    service: NoteService = Depends(get_note_service)
) -> Dict[str, Any]:
    """获取指定会议的所有笔记"""
    result = await service.get_meeting_notes(
        meeting_id=meeting_id,
        include_ai_enhanced=include_ai_enhanced
    )
    
    return {
        "success": True,
        "data": result,
        "total": len(result)
    }


@router.post("/meeting/{meeting_id}/reorder", summary="重新排序笔记")
async def reorder_notes(
    meeting_id: int = Path(..., description="会议ID"),
    request: NoteReorderRequest,
    service: NoteService = Depends(get_note_service)
) -> Dict[str, Any]:
    """
    重新排序会议笔记
    
    - **note_orders**: 笔记顺序列表，包含note_id和position
    """
    result = await service.reorder_notes(
        meeting_id=meeting_id,
        note_orders=request.note_orders
    )
    
    return {
        "success": True,
        "message": "笔记排序更新成功",
        "data": result
    }


@router.post("/{note_id}/duplicate", summary="复制笔记")
async def duplicate_note(
    note_id: int = Path(..., description="笔记ID"),
    service: NoteService = Depends(get_note_service)
) -> Dict[str, Any]:
    """复制指定笔记"""
    result = await service.duplicate_note(note_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="笔记不存在")
    
    return {
        "success": True,
        "message": "笔记复制成功",
        "data": result
    }


@router.post("/search", summary="搜索笔记")
async def search_notes(
    request: NoteSearchRequest,
    service: NoteService = Depends(get_note_service)
) -> Dict[str, Any]:
    """
    搜索笔记
    
    - **meeting_id**: 会议ID筛选（可选）
    - **keyword**: 搜索关键词
    - **is_ai_enhanced**: AI增强状态筛选（可选）
    - **limit**: 返回数量限制
    - **offset**: 偏移量
    """
    result = await service.search_notes(
        meeting_id=request.meeting_id,
        keyword=request.keyword,
        is_ai_enhanced=request.is_ai_enhanced,
        limit=request.limit,
        offset=request.offset
    )
    
    return {
        "success": True,
        "data": result
    }


@router.post("/batch", summary="批量操作笔记")
async def batch_operation(
    request: NoteBatchOperation,
    service: NoteService = Depends(get_note_service)
) -> Dict[str, Any]:
    """
    批量操作笔记
    
    - **note_ids**: 笔记ID列表
    - **operation**: 操作类型 (delete, duplicate)
    """
    results = []
    failed = []
    
    if request.operation == "delete":
        for note_id in request.note_ids:
            success = await service.delete_note(note_id)
            if success:
                results.append(note_id)
            else:
                failed.append(note_id)
    
    elif request.operation == "duplicate":
        for note_id in request.note_ids:
            try:
                result = await service.duplicate_note(note_id)
                if result:
                    results.append({"original_id": note_id, "new_note": result})
                else:
                    failed.append(note_id)
            except Exception:
                failed.append(note_id)
    
    else:
        raise HTTPException(status_code=400, detail="不支持的操作类型")
    
    return {
        "success": True,
        "message": f"批量{request.operation}完成",
        "data": {
            "operation": request.operation,
            "successful": results,
            "failed": failed,
            "total_requested": len(request.note_ids),
            "total_successful": len(results),
            "total_failed": len(failed)
        }
    }