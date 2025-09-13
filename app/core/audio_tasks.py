"""
音频处理相关异步任务
"""

import os
import asyncio
import tempfile
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from app.core.tasks import task, TaskPriority
from app.core.storage import storage_manager
from app.core.events import event_emitter, Events
from loguru import logger


@task(
    name='audio.process_upload',
    queue='audio',
    priority=TaskPriority.HIGH,
    max_retries=2,
    time_limit=300,
    soft_time_limit=240
)
def process_audio_upload_task(
    audio_data: bytes,
    filename: str,
    user_id: int,
    meeting_id: int = None,
    compress: bool = True
) -> Dict[str, Any]:
    """
    处理音频上传任务
    
    Args:
        audio_data: 音频数据
        filename: 文件名
        user_id: 用户ID
        meeting_id: 会议ID
        compress: 是否压缩
    
    Returns:
        处理结果
    """
    try:
        logger.info(f"开始处理音频上传: {filename} (用户: {user_id})")
        
        # 验证音频格式
        allowed_formats = ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg']
        file_ext = Path(filename).suffix.lower()
        
        if file_ext not in allowed_formats:
            raise ValueError(f"不支持的音频格式: {file_ext}")
        
        # 验证文件大小 (最大200MB)
        if len(audio_data) > 200 * 1024 * 1024:
            raise ValueError("音频文件过大，最大支持200MB")
        
        # 上传到存储系统
        async def _upload():
            return await storage_manager.upload_file(
                content=audio_data,
                filename=filename,
                user_id=user_id,
                meeting_id=meeting_id,
                compress=compress
            )
        
        upload_result = asyncio.run(_upload())
        
        # 获取音频基本信息 - 使用异步版本并在任务内运行
        audio_info = asyncio.run(get_audio_info_async(audio_data, filename))
        
        # 构建结果
        result = {
            'file_path': upload_result['file_path'],
            'storage_path': upload_result['storage_path'],
            'filename': filename,
            'original_size': upload_result['original_size'],
            'compressed_size': upload_result['file_size'],
            'compression_ratio': upload_result['original_size'] / upload_result['file_size'] if upload_result['file_size'] > 0 else 1.0,
            'audio_info': audio_info,
            'user_id': user_id,
            'meeting_id': meeting_id,
            'uploaded_at': datetime.now().isoformat()
        }
        
        # 发射音频上传完成事件
        asyncio.run(event_emitter.emit(Events.AUDIO_UPLOADED, {
            'user_id': user_id,
            'meeting_id': meeting_id,
            'filename': filename,
            'file_size': upload_result['file_size'],
            'duration': audio_info.get('duration', 0)
        }))
        
        logger.info(f"音频上传处理完成: {filename}")
        
        return result
        
    except Exception as e:
        logger.error(f"音频上传处理失败: {e}")
        raise


@task(
    name='audio.convert_format',
    queue='audio',
    priority=TaskPriority.NORMAL,
    max_retries=2,
    time_limit=600,
    soft_time_limit=540
)
def convert_audio_format_task(
    source_path: str,
    target_format: str,
    user_id: int,
    quality: str = 'medium'
) -> Dict[str, Any]:
    """
    音频格式转换任务
    
    Args:
        source_path: 源文件路径
        target_format: 目标格式 (mp3, wav, m4a等)
        user_id: 用户ID
        quality: 转换质量 (low, medium, high)
    
    Returns:
        转换结果
    """
    try:
        logger.info(f"开始转换音频格式: {source_path} -> {target_format}")
        
        # 下载源文件
        source_data = asyncio.run(storage_manager.download_file(source_path))
        
        # 执行格式转换
        converted_data = asyncio.run(convert_audio_async(
            source_data,
            target_format,
            quality
        ))
        
        # 生成新文件名
        source_filename = Path(source_path).stem
        target_filename = f"{source_filename}_converted.{target_format}"
        
        # 上传转换后的文件
        upload_result = asyncio.run(storage_manager.upload_file(
            content=converted_data,
            filename=target_filename,
            user_id=user_id
        ))
        
        # 构建结果
        result = {
            'source_path': source_path,
            'target_path': upload_result['file_path'],
            'target_format': target_format,
            'source_size': len(source_data),
            'target_size': len(converted_data),
            'quality': quality,
            'user_id': user_id,
            'converted_at': datetime.now().isoformat()
        }
        
        logger.info(f"音频格式转换完成: {target_filename}")
        
        return result
        
    except Exception as e:
        logger.error(f"音频格式转换失败: {e}")
        raise


@task(
    name='audio.extract_features',
    queue='audio',
    priority=TaskPriority.LOW,
    max_retries=1,
    time_limit=300,
    soft_time_limit=240
)
def extract_audio_features_task(
    audio_data: bytes,
    filename: str,
    user_id: int
) -> Dict[str, Any]:
    """
    提取音频特征任务
    
    Args:
        audio_data: 音频数据
        filename: 文件名
        user_id: 用户ID
    
    Returns:
        音频特征
    """
    try:
        logger.info(f"开始提取音频特征: {filename}")
        
        # 提取基本音频信息
        audio_info = await get_audio_info_async(audio_data, filename)
        
        # 提取高级特征（这里可以集成librosa等音频处理库）
        features = await extract_advanced_features_async(audio_data, filename)
        
        # 构建结果
        result = {
            'filename': filename,
            'user_id': user_id,
            'basic_info': audio_info,
            'features': features,
            'extracted_at': datetime.now().isoformat()
        }
        
        logger.info(f"音频特征提取完成: {filename}")
        
        return result
        
    except Exception as e:
        logger.error(f"音频特征提取失败: {e}")
        raise


@task(
    name='audio.cleanup_temp_files',
    queue='maintenance',
    priority=TaskPriority.LOW,
    max_retries=1,
    time_limit=180,
    soft_time_limit=150
)
def cleanup_audio_temp_files_task() -> Dict[str, Any]:
    """
    清理临时音频文件任务
    
    Returns:
        清理结果统计
    """
    try:
        logger.info("开始清理临时音频文件")
        
        temp_dir = tempfile.gettempdir()
        audio_temp_files = []
        
        # 查找临时音频文件
        for pattern in ['*.tmp', '*.temp', 'audio_*', 'converted_*']:
            audio_temp_files.extend(Path(temp_dir).glob(pattern))
        
        # 清理文件
        cleaned_count = 0
        total_size = 0
        
        for temp_file in audio_temp_files:
            try:
                if temp_file.is_file():
                    file_size = temp_file.stat().st_size
                    temp_file.unlink()
                    cleaned_count += 1
                    total_size += file_size
                    
            except Exception as e:
                logger.warning(f"清理临时文件失败 {temp_file}: {e}")
        
        result = {
            'cleaned_files': cleaned_count,
            'total_size_freed': total_size,
            'temp_dir': temp_dir,
            'cleaned_at': datetime.now().isoformat()
        }
        
        logger.info(f"临时音频文件清理完成: {cleaned_count} 个文件, {total_size / 1024 / 1024:.2f}MB")
        
        return result
        
    except Exception as e:
        logger.error(f"临时文件清理失败: {e}")
        raise


# 辅助函数
async def get_audio_info_async(audio_data: bytes, filename: str) -> Dict[str, Any]:
    """异步获取音频信息"""
    try:
        # 这里应该集成音频处理库来获取真实的音频信息
        # 例如使用ffmpeg-python、librosa或pydub
        
        # 临时实现：基于文件大小和格式的基本信息
        file_ext = Path(filename).suffix.lower()
        file_size = len(audio_data)
        
        # 估算时长（这是一个粗略估算，实际应该解析音频文件）
        estimated_bitrate = 128000  # 128kbps估算
        estimated_duration = (file_size * 8) / estimated_bitrate
        
        return {
            'format': file_ext[1:] if file_ext else 'unknown',
            'size': file_size,
            'estimated_duration': estimated_duration,
            'estimated_bitrate': estimated_bitrate,
            'channels': 2,  # 默认立体声
            'sample_rate': 44100,  # 默认采样率
            'analyzed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取音频信息失败: {e}")
        return {
            'format': 'unknown',
            'size': len(audio_data),
            'error': str(e)
        }


async def extract_advanced_features_async(audio_data: bytes, filename: str) -> Dict[str, Any]:
    """异步提取高级音频特征"""
    try:
        # 这里应该实现真实的音频特征提取
        # 例如使用librosa提取MFCC、频谱图等特征
        
        # 临时实现：返回基本特征
        return {
            'spectral_features': {
                'spectral_centroid': 2000.0,
                'spectral_bandwidth': 1500.0,
                'spectral_rolloff': 3000.0
            },
            'temporal_features': {
                'zero_crossing_rate': 0.1,
                'energy': 0.5
            },
            'quality_indicators': {
                'noise_level': 'low',
                'clarity': 'good'
            }
        }
        
    except Exception as e:
        logger.error(f"提取音频特征失败: {e}")
        return {'error': str(e)}


async def convert_audio_async(
    source_data: bytes, 
    target_format: str, 
    quality: str
) -> bytes:
    """异步音频格式转换"""
    try:
        # 这里应该实现真实的音频格式转换
        # 例如使用ffmpeg-python或pydub
        
        logger.warning("音频格式转换功能需要集成ffmpeg或类似工具")
        
        # 临时实现：直接返回源数据（不进行实际转换）
        return source_data
        
    except Exception as e:
        logger.error(f"音频格式转换失败: {e}")
        raise