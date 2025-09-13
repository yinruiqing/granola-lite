"""
转录相关API端点
"""

import uuid
from fastapi import APIRouter, HTTPException, Depends, Path, Query, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any, Optional
import json

from app.services.transcription import (
    get_transcription_service, 
    get_streaming_transcription_service,
    TranscriptionService,
    StreamingTranscriptionService
)
from app.schemas.transcription import (
    TranscriptionRequest,
    TranscriptionResult,
    TranscriptionResponse,
    TranscriptionUpdate,
    StreamingTranscriptionRequest,
    StreamingTranscriptionResponse,
    FullTranscriptResponse
)


router = APIRouter()


@router.post("/transcribe", summary="转录音频文件")
async def transcribe_audio(
    request: TranscriptionRequest,
    service: TranscriptionService = Depends(get_transcription_service)
) -> Dict[str, Any]:
    """
    转录指定的音频文件
    
    - **audio_id**: 音频文件ID
    - **language**: 语言代码（zh, en, auto等）
    - **temperature**: 温度参数，控制输出的随机性
    - **prompt**: 转录提示，可以提供上下文
    
    返回转录结果和保存的转录记录ID列表
    """
    result = await service.transcribe_audio_file(
        request.audio_id,
        request.language,
        temperature=request.temperature,
        prompt=request.prompt
    )
    
    return {
        "success": True,
        "message": "转录完成",
        "data": result
    }


@router.get("/meeting/{meeting_id}", summary="获取会议转录记录")
async def get_meeting_transcriptions(
    meeting_id: int = Path(..., description="会议ID"),
    start_time: Optional[float] = Query(None, description="开始时间筛选(秒)"),
    end_time: Optional[float] = Query(None, description="结束时间筛选(秒)"),
    service: TranscriptionService = Depends(get_transcription_service)
) -> Dict[str, Any]:
    """获取会议的转录记录列表"""
    result = await service.get_meeting_transcriptions(
        meeting_id, 
        start_time, 
        end_time
    )
    
    return {
        "success": True,
        "data": result,
        "total": len(result)
    }


@router.get("/meeting/{meeting_id}/full", summary="获取会议完整转录")
async def get_full_meeting_transcript(
    meeting_id: int = Path(..., description="会议ID"),
    service: TranscriptionService = Depends(get_transcription_service)
) -> Dict[str, Any]:
    """获取会议的完整转录文本"""
    full_text = await service.get_full_meeting_transcript(meeting_id)
    
    if not full_text:
        raise HTTPException(status_code=404, detail="没有找到转录记录")
    
    return {
        "success": True,
        "data": {
            "meeting_id": meeting_id,
            "full_text": full_text
        }
    }


@router.get("/{transcription_id}", summary="获取转录记录详情")
async def get_transcription(
    transcription_id: int = Path(..., description="转录ID"),
    service: TranscriptionService = Depends(get_transcription_service)
) -> Dict[str, Any]:
    """获取单个转录记录的详细信息"""
    result = await service.get_transcription(transcription_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="转录记录不存在")
    
    return {
        "success": True,
        "data": result
    }


@router.put("/{transcription_id}", summary="更新转录记录")
async def update_transcription(
    request: TranscriptionUpdate,
    transcription_id: int = Path(..., description="转录ID"),
    service: TranscriptionService = Depends(get_transcription_service)
) -> Dict[str, Any]:
    """
    更新转录记录的内容
    
    通常用于手动修正转录错误
    """
    result = await service.update_transcription(
        transcription_id, 
        request.content
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="转录记录不存在")
    
    return {
        "success": True,
        "message": "转录记录更新成功",
        "data": result
    }


@router.delete("/{transcription_id}", summary="删除转录记录")
async def delete_transcription(
    transcription_id: int = Path(..., description="转录ID"),
    service: TranscriptionService = Depends(get_transcription_service)
) -> Dict[str, Any]:
    """删除转录记录"""
    success = await service.delete_transcription(transcription_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="转录记录不存在")
    
    return {
        "success": True,
        "message": "转录记录删除成功"
    }


@router.websocket("/stream/{meeting_id}")
async def streaming_transcription(
    websocket: WebSocket,
    meeting_id: int = Path(..., description="会议ID"),
    service: StreamingTranscriptionService = Depends(get_streaming_transcription_service)
):
    """
    WebSocket实时转录接口
    
    客户端发送音频数据，服务端返回实时转录结果
    
    消息格式：
    - 客户端发送: {"type": "audio", "data": "base64编码的音频数据", "language": "zh"}
    - 服务端返回: {"type": "transcription", "data": {...转录结果...}}
    """
    await websocket.accept()
    
    # 创建会话ID
    session_id = f"meeting_{meeting_id}_{str(uuid.uuid4())[:8]}"
    
    try:
        # 等待客户端初始化消息
        init_message = await websocket.receive_text()
        init_data = json.loads(init_message)
        
        if init_data.get("type") != "init":
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "期望初始化消息"
            }))
            return
        
        # 创建转录会话
        sample_rate = init_data.get("sample_rate", 16000)
        language = init_data.get("language", "auto")
        
        service.create_session(session_id, sample_rate)
        
        # 发送会话创建确认
        await websocket.send_text(json.dumps({
            "type": "session_created",
            "session_id": session_id,
            "meeting_id": meeting_id
        }))
        
        # 处理音频数据流
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                if data.get("type") == "audio":
                    import base64
                    
                    # 解码音频数据
                    audio_data = base64.b64decode(data["data"])
                    
                    # 处理音频块
                    result = await service.process_audio_chunk(
                        session_id,
                        audio_data,
                        data.get("language", language)
                    )
                    
                    # 如果有转录结果，发送给客户端
                    if result:
                        await websocket.send_text(json.dumps({
                            "type": "transcription",
                            "data": result
                        }))
                
                elif data.get("type") == "end":
                    # 结束转录
                    await websocket.send_text(json.dumps({
                        "type": "session_ended",
                        "session_id": session_id
                    }))
                    break
                    
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error", 
                    "message": "无效的JSON格式"
                }))
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"处理音频数据失败: {str(e)}"
                }))
                
    except WebSocketDisconnect:
        print(f"WebSocket连接断开: {session_id}")
    except Exception as e:
        print(f"WebSocket错误: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"服务器错误: {str(e)}"
            }))
        except:
            pass
    finally:
        # 清理会话
        service.close_session(session_id)


@router.get("/stream/status/{session_id}", summary="获取流式转录会话状态")
async def get_streaming_session_status(
    session_id: str = Path(..., description="会话ID"),
    service: StreamingTranscriptionService = Depends(get_streaming_transcription_service)
) -> Dict[str, Any]:
    """获取流式转录会话状态"""
    is_active = session_id in service.processors
    
    return {
        "success": True,
        "data": {
            "session_id": session_id,
            "is_active": is_active
        }
    }