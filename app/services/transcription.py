"""
转录服务
"""

import io
from typing import List, Dict, Any, Optional, AsyncGenerator
from fastapi import HTTPException

from app.services.ai.ai_service import get_ai_service
from app.services.audio import get_audio_service, StreamingAudioProcessor
from app.models.transcription import Transcription
from app.models.audio_file import AudioFile
from app.db.session import AsyncSessionLocal
from sqlalchemy import select


class TranscriptionService:
    """转录服务"""
    
    def __init__(self):
        self.ai_service = get_ai_service()
        self.audio_service = get_audio_service()
    
    async def transcribe_audio_file(
        self, 
        audio_id: int, 
        language: str = "auto",
        **kwargs
    ) -> Dict[str, Any]:
        """
        转录音频文件
        
        Args:
            audio_id: 音频文件ID
            language: 语言代码
            **kwargs: 其他参数
            
        Returns:
            Dict[str, Any]: 转录结果
        """
        try:
            # 获取音频文件信息
            audio_info = await self.audio_service.get_audio_file(audio_id)
            if not audio_info:
                raise HTTPException(status_code=404, detail="音频文件不存在")
            
            # 准备音频文件
            prepared_path = await self.audio_service.prepare_for_transcription(audio_id)
            if not prepared_path:
                raise HTTPException(status_code=500, detail="音频文件预处理失败")
            
            # 读取音频文件
            with open(prepared_path, 'rb') as f:
                audio_data = f.read()
            
            audio_stream = io.BytesIO(audio_data)
            
            # 调用AI转录服务
            result = await self.ai_service.transcribe_audio(
                audio_stream, 
                language=language,
                **kwargs
            )
            
            # 保存转录结果到数据库
            transcription_records = []
            
            if result.segments:
                # 有分段信息，保存每个分段
                for i, segment in enumerate(result.segments):
                    transcription = Transcription(
                        meeting_id=audio_info["meeting_id"],
                        content=segment["text"],
                        speaker=result.speaker,
                        start_time=segment["start"],
                        end_time=segment["end"],
                        confidence=segment.get("confidence", result.confidence)
                    )
                    transcription_records.append(transcription)
            else:
                # 没有分段信息，保存整体结果
                transcription = Transcription(
                    meeting_id=audio_info["meeting_id"],
                    content=result.text,
                    speaker=result.speaker,
                    start_time=0.0,
                    end_time=audio_info.get("duration", 0.0),
                    confidence=result.confidence
                )
                transcription_records.append(transcription)
            
            # 批量保存到数据库
            async with AsyncSessionLocal() as session:
                session.add_all(transcription_records)
                await session.commit()
                
                # 刷新以获取ID
                for record in transcription_records:
                    await session.refresh(record)
            
            return {
                "audio_id": audio_id,
                "meeting_id": audio_info["meeting_id"],
                "language": result.language,
                "total_segments": len(transcription_records),
                "full_text": result.text,
                "confidence": result.confidence,
                "transcription_ids": [r.id for r in transcription_records]
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"转录失败: {str(e)}"
            )
    
    async def get_meeting_transcriptions(
        self, 
        meeting_id: int,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        获取会议转录记录
        
        Args:
            meeting_id: 会议ID
            start_time: 开始时间筛选
            end_time: 结束时间筛选
            
        Returns:
            List[Dict[str, Any]]: 转录记录列表
        """
        try:
            async with AsyncSessionLocal() as session:
                query = select(Transcription).where(
                    Transcription.meeting_id == meeting_id
                )
                
                # 添加时间范围筛选
                if start_time is not None:
                    query = query.where(Transcription.start_time >= start_time)
                if end_time is not None:
                    query = query.where(Transcription.end_time <= end_time)
                
                # 按时间排序
                query = query.order_by(Transcription.start_time)
                
                result = await session.execute(query)
                transcriptions = result.scalars().all()
                
                return [
                    {
                        "id": t.id,
                        "content": t.content,
                        "speaker": t.speaker,
                        "start_time": t.start_time,
                        "end_time": t.end_time,
                        "confidence": t.confidence,
                        "created_at": t.created_at
                    }
                    for t in transcriptions
                ]
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"获取转录记录失败: {str(e)}"
            )
    
    async def get_transcription(self, transcription_id: int) -> Optional[Dict[str, Any]]:
        """获取单个转录记录"""
        try:
            async with AsyncSessionLocal() as session:
                transcription = await session.get(Transcription, transcription_id)
                
                if not transcription:
                    return None
                
                return {
                    "id": transcription.id,
                    "meeting_id": transcription.meeting_id,
                    "content": transcription.content,
                    "speaker": transcription.speaker,
                    "start_time": transcription.start_time,
                    "end_time": transcription.end_time,
                    "confidence": transcription.confidence,
                    "created_at": transcription.created_at
                }
                
        except Exception as e:
            print(f"获取转录记录失败: {e}")
            return None
    
    async def update_transcription(
        self, 
        transcription_id: int, 
        content: str
    ) -> Optional[Dict[str, Any]]:
        """
        更新转录内容
        
        Args:
            transcription_id: 转录ID
            content: 新的转录内容
            
        Returns:
            Dict[str, Any]: 更新后的转录记录
        """
        try:
            async with AsyncSessionLocal() as session:
                transcription = await session.get(Transcription, transcription_id)
                
                if not transcription:
                    return None
                
                transcription.content = content
                await session.commit()
                await session.refresh(transcription)
                
                return {
                    "id": transcription.id,
                    "meeting_id": transcription.meeting_id,
                    "content": transcription.content,
                    "speaker": transcription.speaker,
                    "start_time": transcription.start_time,
                    "end_time": transcription.end_time,
                    "confidence": transcription.confidence,
                    "created_at": transcription.created_at,
                    "updated_at": transcription.updated_at
                }
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"更新转录记录失败: {str(e)}"
            )
    
    async def delete_transcription(self, transcription_id: int) -> bool:
        """删除转录记录"""
        try:
            async with AsyncSessionLocal() as session:
                transcription = await session.get(Transcription, transcription_id)
                
                if not transcription:
                    return False
                
                await session.delete(transcription)
                await session.commit()
                return True
                
        except Exception as e:
            print(f"删除转录记录失败: {e}")
            return False
    
    async def get_full_meeting_transcript(self, meeting_id: int) -> str:
        """
        获取会议完整转录文本
        
        Args:
            meeting_id: 会议ID
            
        Returns:
            str: 完整转录文本
        """
        transcriptions = await self.get_meeting_transcriptions(meeting_id)
        
        if not transcriptions:
            return ""
        
        # 按时间顺序拼接转录内容
        full_text = []
        current_speaker = None
        
        for t in transcriptions:
            speaker = t.get("speaker", "未知发言人")
            content = t["content"].strip()
            
            if not content:
                continue
                
            # 如果发言人变化，添加发言人标识
            if speaker != current_speaker:
                if current_speaker is not None:
                    full_text.append("")  # 空行分隔
                full_text.append(f"**{speaker}:**")
                current_speaker = speaker
            
            full_text.append(content)
        
        return "\n".join(full_text)


class StreamingTranscriptionService:
    """流式转录服务"""
    
    def __init__(self):
        self.ai_service = get_ai_service()
        self.processors: Dict[str, StreamingAudioProcessor] = {}
    
    def create_session(self, session_id: str, sample_rate: int = 16000) -> str:
        """
        创建流式转录会话
        
        Args:
            session_id: 会话ID
            sample_rate: 音频采样率
            
        Returns:
            str: 会话ID
        """
        self.processors[session_id] = StreamingAudioProcessor(sample_rate)
        return session_id
    
    async def process_audio_chunk(
        self, 
        session_id: str, 
        audio_data: bytes,
        language: str = "auto"
    ) -> Optional[Dict[str, Any]]:
        """
        处理音频数据块
        
        Args:
            session_id: 会话ID
            audio_data: 音频数据
            language: 语言代码
            
        Returns:
            Dict[str, Any]: 转录结果，如果没有结果返回None
        """
        if session_id not in self.processors:
            return None
        
        processor = self.processors[session_id]
        
        # 添加音频数据
        should_transcribe = await processor.add_audio_chunk(audio_data)
        
        if should_transcribe:
            # 获取音频数据进行转录
            audio_stream = processor.get_audio_for_transcription()
            
            try:
                result = await self.ai_service.transcribe_audio(
                    audio_stream, 
                    language=language
                )
                
                return {
                    "session_id": session_id,
                    "text": result.text,
                    "confidence": result.confidence,
                    "language": result.language,
                    "timestamp": processor.buffer.get_duration()
                }
                
            except Exception as e:
                print(f"流式转录失败: {e}")
                return None
        
        return None
    
    def close_session(self, session_id: str):
        """关闭转录会话"""
        if session_id in self.processors:
            del self.processors[session_id]


# 全局服务实例
transcription_service: Optional[TranscriptionService] = None
streaming_transcription_service: Optional[StreamingTranscriptionService] = None


def get_transcription_service() -> TranscriptionService:
    """获取转录服务实例"""
    global transcription_service
    if transcription_service is None:
        transcription_service = TranscriptionService()
    return transcription_service


def get_streaming_transcription_service() -> StreamingTranscriptionService:
    """获取流式转录服务实例"""
    global streaming_transcription_service
    if streaming_transcription_service is None:
        streaming_transcription_service = StreamingTranscriptionService()
    return streaming_transcription_service