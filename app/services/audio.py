"""
音频处理服务
"""

import io
from typing import Optional, Dict, Any
from fastapi import UploadFile, HTTPException
from pathlib import Path

from app.config import settings
from app.utils.audio_utils import (
    validate_audio_file, 
    get_audio_duration,
    convert_to_wav,
    AudioBuffer
)
from app.utils.file_utils import save_upload_file, FileManager
from app.models.audio_file import AudioFile
from app.db.session import AsyncSessionLocal


class AudioService:
    """音频处理服务"""
    
    def __init__(self):
        self.file_manager = FileManager(settings.upload_dir)
        self.max_file_size = settings.max_file_size
        self.allowed_types = settings.allowed_audio_types
    
    async def upload_audio_file(
        self, 
        file: UploadFile, 
        meeting_id: int
    ) -> Dict[str, Any]:
        """
        上传音频文件
        
        Args:
            file: 上传的文件
            meeting_id: 会议ID
            
        Returns:
            Dict[str, Any]: 上传结果
        """
        try:
            # 检查文件大小
            if file.size and file.size > self.max_file_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"文件太大，最大允许 {self.max_file_size // 1024 // 1024}MB"
                )
            
            # 读取文件内容
            file_content = await file.read()
            
            # 验证文件
            is_valid, error_message = validate_audio_file(
                file_content, 
                file.filename, 
                self.allowed_types
            )
            
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_message)
            
            # 保存文件
            file_info = await self.file_manager.save_file(
                file_content,
                file.filename,
                "audio"
            )
            
            # 获取音频时长
            duration = await get_audio_duration(file_info["file_path"])
            
            # 保存到数据库
            async with AsyncSessionLocal() as session:
                audio_file = AudioFile(
                    meeting_id=meeting_id,
                    file_path=file_info["file_path"],
                    file_size=file_info["size"],
                    duration=duration,
                    format=Path(file.filename).suffix[1:].lower()  # 去掉点号
                )
                
                session.add(audio_file)
                await session.commit()
                await session.refresh(audio_file)
                
                return {
                    "id": audio_file.id,
                    "filename": file_info["filename"],
                    "original_filename": file_info["original_filename"],
                    "file_path": file_info["file_path"],
                    "file_size": file_info["size"],
                    "duration": duration,
                    "format": audio_file.format,
                    "upload_time": audio_file.created_at
                }
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"文件上传失败: {str(e)}"
            )
    
    async def get_audio_file(self, audio_id: int) -> Optional[Dict[str, Any]]:
        """
        获取音频文件信息
        
        Args:
            audio_id: 音频文件ID
            
        Returns:
            Dict[str, Any]: 音频文件信息
        """
        try:
            async with AsyncSessionLocal() as session:
                audio_file = await session.get(AudioFile, audio_id)
                
                if not audio_file:
                    return None
                
                return {
                    "id": audio_file.id,
                    "meeting_id": audio_file.meeting_id,
                    "file_path": audio_file.file_path,
                    "file_size": audio_file.file_size,
                    "duration": audio_file.duration,
                    "format": audio_file.format,
                    "created_at": audio_file.created_at
                }
                
        except Exception as e:
            print(f"获取音频文件信息失败: {e}")
            return None
    
    async def delete_audio_file(self, audio_id: int) -> bool:
        """
        删除音频文件
        
        Args:
            audio_id: 音频文件ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            async with AsyncSessionLocal() as session:
                audio_file = await session.get(AudioFile, audio_id)
                
                if not audio_file:
                    return False
                
                # 删除物理文件
                await self.file_manager.delete_file(audio_file.file_path)
                
                # 删除数据库记录
                await session.delete(audio_file)
                await session.commit()
                
                return True
                
        except Exception as e:
            print(f"删除音频文件失败: {e}")
            return False
    
    async def prepare_for_transcription(self, audio_id: int) -> Optional[str]:
        """
        为转录准备音频文件（可能需要格式转换）
        
        Args:
            audio_id: 音频文件ID
            
        Returns:
            str: 处理后的音频文件路径
        """
        try:
            audio_info = await self.get_audio_file(audio_id)
            if not audio_info:
                return None
            
            original_path = audio_info["file_path"]
            
            # 如果已经是WAV格式且符合要求，直接返回
            if audio_info["format"].lower() == "wav":
                return original_path
            
            # 转换为WAV格式
            wav_path = original_path.replace(
                f".{audio_info['format']}", 
                "_converted.wav"
            )
            
            success = await convert_to_wav(original_path, wav_path)
            
            if success:
                return wav_path
            else:
                # 转换失败，返回原文件
                return original_path
                
        except Exception as e:
            print(f"音频预处理失败: {e}")
            return None
    
    async def get_meeting_audio_files(self, meeting_id: int) -> list:
        """
        获取会议的所有音频文件
        
        Args:
            meeting_id: 会议ID
            
        Returns:
            list: 音频文件列表
        """
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                
                result = await session.execute(
                    select(AudioFile).where(AudioFile.meeting_id == meeting_id)
                )
                audio_files = result.scalars().all()
                
                return [
                    {
                        "id": af.id,
                        "file_path": af.file_path,
                        "file_size": af.file_size,
                        "duration": af.duration,
                        "format": af.format,
                        "created_at": af.created_at
                    }
                    for af in audio_files
                ]
                
        except Exception as e:
            print(f"获取会议音频文件失败: {e}")
            return []


class StreamingAudioProcessor:
    """流式音频处理器"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.buffer = AudioBuffer(sample_rate, channels)
        self.chunk_duration = 5.0  # 5秒分块
    
    async def add_audio_chunk(self, audio_data: bytes) -> bool:
        """
        添加音频数据块
        
        Args:
            audio_data: 音频数据
            
        Returns:
            bool: 是否应该进行转录
        """
        self.buffer.add_audio_data(audio_data)
        
        # 当缓冲区达到指定时长时，返回True表示可以进行转录
        return self.buffer.get_duration() >= self.chunk_duration
    
    def get_audio_for_transcription(self) -> io.BytesIO:
        """
        获取用于转录的音频数据
        
        Returns:
            io.BytesIO: 音频数据流
        """
        audio_data = self.buffer.get_audio_data()
        self.buffer.clear()
        return io.BytesIO(audio_data)
    
    def clear_buffer(self):
        """清空缓冲区"""
        self.buffer.clear()


# 全局音频服务实例
audio_service: Optional[AudioService] = None


def get_audio_service() -> AudioService:
    """获取音频服务实例"""
    global audio_service
    if audio_service is None:
        audio_service = AudioService()
    return audio_service