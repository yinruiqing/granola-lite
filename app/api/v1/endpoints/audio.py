"""
音频相关API端点
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Path
from typing import List, Dict, Any

from app.services.audio import get_audio_service, AudioService


router = APIRouter()


@router.post("/upload/{meeting_id}", summary="上传音频文件")
async def upload_audio(
    meeting_id: int = Path(..., description="会议ID"),
    file: UploadFile = File(..., description="音频文件"),
    audio_service: AudioService = Depends(get_audio_service)
) -> Dict[str, Any]:
    """
    上传音频文件到指定会议
    
    - **meeting_id**: 会议ID
    - **file**: 音频文件（支持 WAV, MP3, M4A, FLAC 等格式）
    
    返回上传的音频文件信息
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="未选择文件")
    
    result = await audio_service.upload_audio_file(file, meeting_id)
    
    return {
        "success": True,
        "message": "音频文件上传成功",
        "data": result
    }


@router.get("/{audio_id}", summary="获取音频文件信息")
async def get_audio_info(
    audio_id: int = Path(..., description="音频文件ID"),
    audio_service: AudioService = Depends(get_audio_service)
) -> Dict[str, Any]:
    """获取音频文件信息"""
    result = await audio_service.get_audio_file(audio_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="音频文件不存在")
    
    return {
        "success": True,
        "data": result
    }


@router.delete("/{audio_id}", summary="删除音频文件")
async def delete_audio(
    audio_id: int = Path(..., description="音频文件ID"),
    audio_service: AudioService = Depends(get_audio_service)
) -> Dict[str, Any]:
    """删除音频文件"""
    success = await audio_service.delete_audio_file(audio_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="音频文件不存在或删除失败")
    
    return {
        "success": True,
        "message": "音频文件删除成功"
    }


@router.get("/meeting/{meeting_id}", summary="获取会议音频文件列表")
async def get_meeting_audio_files(
    meeting_id: int = Path(..., description="会议ID"),
    audio_service: AudioService = Depends(get_audio_service)
) -> Dict[str, Any]:
    """获取指定会议的所有音频文件"""
    result = await audio_service.get_meeting_audio_files(meeting_id)
    
    return {
        "success": True,
        "data": result,
        "total": len(result)
    }


@router.post("/{audio_id}/prepare", summary="准备音频文件用于转录")
async def prepare_audio_for_transcription(
    audio_id: int = Path(..., description="音频文件ID"),
    audio_service: AudioService = Depends(get_audio_service)
) -> Dict[str, Any]:
    """
    准备音频文件用于转录
    
    可能会进行格式转换以确保兼容性
    """
    result = await audio_service.prepare_for_transcription(audio_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="音频文件不存在或处理失败")
    
    return {
        "success": True,
        "message": "音频文件准备完成",
        "data": {
            "processed_file_path": result
        }
    }