"""
音频处理工具函数
"""

import io
import os
import asyncio
from pathlib import Path
from typing import Tuple, Optional
import mimetypes
import wave
import subprocess


async def get_audio_duration(file_path: str) -> float:
    """
    获取音频文件时长(秒)
    
    Args:
        file_path: 音频文件路径
        
    Returns:
        float: 音频时长(秒)
    """
    try:
        # 使用ffprobe获取音频信息
        cmd = [
            "ffprobe", 
            "-v", "quiet", 
            "-show_entries", "format=duration", 
            "-of", "csv=p=0", 
            file_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            duration_str = stdout.decode().strip()
            return float(duration_str)
        else:
            # 回退到使用wave库(仅支持WAV格式)
            if file_path.lower().endswith('.wav'):
                with wave.open(file_path, 'rb') as wav_file:
                    frames = wav_file.getnframes()
                    rate = wav_file.getframerate()
                    return frames / float(rate)
            else:
                return 0.0
                
    except Exception as e:
        print(f"获取音频时长失败: {e}")
        return 0.0


def validate_audio_file(file_content: bytes, filename: str, allowed_types: list) -> Tuple[bool, str]:
    """
    验证音频文件
    
    Args:
        file_content: 文件内容
        filename: 文件名
        allowed_types: 允许的MIME类型列表
        
    Returns:
        Tuple[bool, str]: (是否有效, 错误信息)
    """
    try:
        # 检查文件大小
        if len(file_content) == 0:
            return False, "文件为空"
        
        # 检查文件扩展名
        file_extension = Path(filename).suffix.lower()
        valid_extensions = ['.wav', '.mp3', '.m4a', '.flac', '.aac', '.ogg']
        
        if file_extension not in valid_extensions:
            return False, f"不支持的文件格式: {file_extension}"
        
        # 检查MIME类型
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type and mime_type not in allowed_types:
            return False, f"不允许的文件类型: {mime_type}"
        
        # 基础文件头检查
        if not _check_audio_header(file_content, file_extension):
            return False, "文件格式损坏或无效"
        
        return True, ""
        
    except Exception as e:
        return False, f"文件验证失败: {str(e)}"


def _check_audio_header(file_content: bytes, extension: str) -> bool:
    """检查音频文件头"""
    if len(file_content) < 12:
        return False
    
    if extension == '.wav':
        # WAV文件头检查: RIFF + 4字节 + WAVE
        return file_content[:4] == b'RIFF' and file_content[8:12] == b'WAVE'
    elif extension == '.mp3':
        # MP3文件头检查: ID3 或 同步帧
        return (file_content[:3] == b'ID3' or 
                (file_content[0] == 0xFF and (file_content[1] & 0xE0) == 0xE0))
    elif extension == '.m4a':
        # M4A文件头检查: ftypM4A
        return b'ftypM4A' in file_content[:20]
    elif extension == '.flac':
        # FLAC文件头检查: fLaC
        return file_content[:4] == b'fLaC'
    elif extension == '.ogg':
        # OGG文件头检查: OggS
        return file_content[:4] == b'OggS'
    
    return True  # 其他格式暂不检查


async def convert_to_wav(input_path: str, output_path: str) -> bool:
    """
    将音频文件转换为WAV格式
    
    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径
        
    Returns:
        bool: 是否转换成功
    """
    try:
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-acodec", "pcm_s16le",  # 16位PCM编码
            "-ar", "16000",          # 16kHz采样率
            "-ac", "1",              # 单声道
            "-y",                    # 覆盖输出文件
            output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return process.returncode == 0
        
    except Exception as e:
        print(f"音频转换失败: {e}")
        return False


def split_audio_chunks(file_path: str, chunk_duration: int = 60) -> list:
    """
    将音频文件分割为指定时长的块
    
    Args:
        file_path: 音频文件路径
        chunk_duration: 每个块的时长(秒)
        
    Returns:
        list: 分割后的文件路径列表
    """
    try:
        base_name = Path(file_path).stem
        output_dir = Path(file_path).parent / "chunks"
        output_dir.mkdir(exist_ok=True)
        
        # 生成分割命令
        output_pattern = str(output_dir / f"{base_name}_chunk_%03d.wav")
        
        cmd = [
            "ffmpeg",
            "-i", file_path,
            "-f", "segment",
            "-segment_time", str(chunk_duration),
            "-c", "copy",
            "-y",
            output_pattern
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # 返回生成的文件列表
            chunk_files = list(output_dir.glob(f"{base_name}_chunk_*.wav"))
            return [str(f) for f in sorted(chunk_files)]
        else:
            print(f"音频分割失败: {result.stderr}")
            return []
            
    except Exception as e:
        print(f"音频分割异常: {e}")
        return []


class AudioBuffer:
    """音频缓冲区，用于实时音频处理"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.buffer = io.BytesIO()
        self.total_frames = 0
    
    def add_audio_data(self, data: bytes):
        """添加音频数据"""
        self.buffer.write(data)
        # 假设16位采样
        self.total_frames += len(data) // (2 * self.channels)
    
    def get_duration(self) -> float:
        """获取缓冲区音频时长"""
        return self.total_frames / self.sample_rate
    
    def get_audio_data(self) -> bytes:
        """获取音频数据"""
        self.buffer.seek(0)
        return self.buffer.read()
    
    def clear(self):
        """清空缓冲区"""
        self.buffer = io.BytesIO()
        self.total_frames = 0