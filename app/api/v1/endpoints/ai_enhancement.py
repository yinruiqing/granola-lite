"""
AI笔记增强相关API端点
"""

from fastapi import APIRouter, HTTPException, Depends, Path
from typing import Dict, Any

from app.services.ai_enhancement import get_ai_enhancement_service, AIEnhancementService
from app.schemas.ai_enhancement import (
    NoteEnhancementRequest,
    NoteEnhancementResponse,
    MeetingNotesEnhancementRequest,
    MeetingNotesEnhancementResponse,
    NoteComparisonResponse,
    NoteRevertResponse,
    BatchEnhancementRequest,
    BatchEnhancementResponse
)


router = APIRouter()


@router.post("/notes/{note_id}/enhance", summary="增强单个笔记")
async def enhance_note(
    note_id: int = Path(..., description="笔记ID"),
    request: NoteEnhancementRequest = NoteEnhancementRequest(),
    service: AIEnhancementService = Depends(get_ai_enhancement_service)
) -> Dict[str, Any]:
    """
    使用AI增强单个笔记
    
    - **use_template**: 是否使用会议模板的提示词
    - **custom_prompt**: 自定义提示词，会覆盖模板提示
    
    增强过程会结合用户的原始笔记和会议转录内容，生成更详细、结构化的笔记
    """
    result = await service.enhance_note(
        note_id=note_id,
        use_template=request.use_template,
        custom_prompt=request.custom_prompt
    )
    
    return {
        "success": True,
        "message": "笔记增强完成",
        "data": result
    }


@router.post("/meetings/{meeting_id}/enhance", summary="增强会议所有笔记")
async def enhance_meeting_notes(
    meeting_id: int = Path(..., description="会议ID"),
    request: MeetingNotesEnhancementRequest = MeetingNotesEnhancementRequest(),
    service: AIEnhancementService = Depends(get_ai_enhancement_service)
) -> Dict[str, Any]:
    """
    批量增强会议的所有笔记
    
    - **only_unenhanced**: 是否只增强未增强过的笔记
    - **use_template**: 是否使用会议模板的提示词
    - **custom_prompt**: 自定义提示词
    
    这是一个批量操作，会处理会议中的所有符合条件的笔记
    """
    result = await service.enhance_meeting_notes(
        meeting_id=meeting_id,
        only_unenhanced=request.only_unenhanced,
        use_template=request.use_template,
        custom_prompt=request.custom_prompt
    )
    
    return {
        "success": True,
        "message": f"会议笔记增强完成，成功 {result['enhanced_count']} 个，失败 {result['failed_count']} 个",
        "data": result
    }


@router.post("/notes/{note_id}/revert", summary="还原笔记增强")
async def revert_note_enhancement(
    note_id: int = Path(..., description="笔记ID"),
    service: AIEnhancementService = Depends(get_ai_enhancement_service)
) -> Dict[str, Any]:
    """
    还原笔记的AI增强，恢复到原始内容
    
    只有已经被AI增强过的笔记才能还原
    """
    result = await service.revert_note_enhancement(note_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="笔记不存在")
    
    return {
        "success": True,
        "message": "笔记增强已还原",
        "data": result
    }


@router.get("/notes/{note_id}/compare", summary="比较笔记增强前后")
async def compare_note_enhancement(
    note_id: int = Path(..., description="笔记ID"),
    service: AIEnhancementService = Depends(get_ai_enhancement_service)
) -> Dict[str, Any]:
    """
    比较笔记增强前后的内容差异
    
    显示原始内容、增强内容以及统计信息
    """
    result = await service.compare_enhancement(note_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="笔记不存在")
    
    return {
        "success": True,
        "data": result
    }


@router.post("/batch/enhance", summary="批量增强指定笔记")
async def batch_enhance_notes(
    request: BatchEnhancementRequest,
    service: AIEnhancementService = Depends(get_ai_enhancement_service)
) -> Dict[str, Any]:
    """
    批量增强指定的笔记列表
    
    - **note_ids**: 要增强的笔记ID列表
    - **use_template**: 是否使用会议模板
    - **custom_prompt**: 自定义提示词
    
    适用于跨会议或选择性增强笔记的场景
    """
    results = []
    successful_count = 0
    failed_count = 0
    
    for note_id in request.note_ids:
        try:
            result = await service.enhance_note(
                note_id=note_id,
                use_template=request.use_template,
                custom_prompt=request.custom_prompt
            )
            
            results.append({
                "note_id": note_id,
                "status": "success",
                "enhanced_length": len(result["enhanced_content"]),
                "original_length": len(result["original_content"])
            })
            successful_count += 1
            
        except Exception as e:
            results.append({
                "note_id": note_id,
                "status": "failed",
                "error": str(e)
            })
            failed_count += 1
    
    return {
        "success": True,
        "message": f"批量增强完成，成功 {successful_count} 个，失败 {failed_count} 个",
        "data": {
            "total_requested": len(request.note_ids),
            "successful_count": successful_count,
            "failed_count": failed_count,
            "results": results,
            "enhancement_method": "template" if request.use_template else "custom",
            "template_used": request.use_template and request.custom_prompt is None
        }
    }


@router.get("/meetings/{meeting_id}/stats", summary="获取会议笔记增强统计")
async def get_meeting_enhancement_stats(
    meeting_id: int = Path(..., description="会议ID"),
    service: AIEnhancementService = Depends(get_ai_enhancement_service)
) -> Dict[str, Any]:
    """
    获取会议笔记的AI增强统计信息
    
    包括总笔记数、增强数量、平均增强效果等
    """
    from app.services.note import get_note_service
    
    note_service = get_note_service()
    notes = await note_service.get_meeting_notes(meeting_id)
    
    if not notes:
        return {
            "success": True,
            "data": {
                "meeting_id": meeting_id,
                "total_notes": 0,
                "enhanced_notes": 0,
                "unenhanced_notes": 0,
                "enhancement_percentage": 0.0,
                "average_length_increase": 0.0,
                "total_original_length": 0,
                "total_enhanced_length": 0
            }
        }
    
    # 统计信息
    total_notes = len(notes)
    enhanced_notes = sum(1 for note in notes if note["is_ai_enhanced"])
    unenhanced_notes = total_notes - enhanced_notes
    enhancement_percentage = (enhanced_notes / total_notes) * 100 if total_notes > 0 else 0
    
    # 长度统计
    total_original_length = 0
    total_enhanced_length = 0
    length_increases = []
    
    for note in notes:
        if note["is_ai_enhanced"] and note["original_content"]:
            original_len = len(note["original_content"])
            enhanced_len = len(note["content"])
            total_original_length += original_len
            total_enhanced_length += enhanced_len
            length_increases.append(enhanced_len - original_len)
        else:
            total_enhanced_length += len(note["content"])
    
    average_length_increase = sum(length_increases) / len(length_increases) if length_increases else 0
    
    return {
        "success": True,
        "data": {
            "meeting_id": meeting_id,
            "total_notes": total_notes,
            "enhanced_notes": enhanced_notes,
            "unenhanced_notes": unenhanced_notes,
            "enhancement_percentage": round(enhancement_percentage, 2),
            "average_length_increase": round(average_length_increase, 2),
            "total_original_length": total_original_length,
            "total_enhanced_length": total_enhanced_length
        }
    }