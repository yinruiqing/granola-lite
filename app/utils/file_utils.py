"""
文件处理工具函数
"""

import os
import uuid
import aiofiles
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime
import hashlib

from app.config import settings


def generate_unique_filename(original_filename: str, prefix: str = "") -> str:
    """
    生成唯一文件名
    
    Args:
        original_filename: 原始文件名
        prefix: 文件名前缀
        
    Returns:
        str: 唯一文件名
    """
    file_extension = Path(original_filename).suffix
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    
    if prefix:
        return f"{prefix}_{timestamp}_{unique_id}{file_extension}"
    else:
        return f"{timestamp}_{unique_id}{file_extension}"


def get_file_hash(file_content: bytes) -> str:
    """
    计算文件MD5哈希值
    
    Args:
        file_content: 文件内容
        
    Returns:
        str: MD5哈希值
    """
    return hashlib.md5(file_content).hexdigest()


async def save_upload_file(
    file_content: bytes, 
    filename: str, 
    subdirectory: str = "audio"
) -> Tuple[str, str]:
    """
    保存上传的文件
    
    Args:
        file_content: 文件内容
        filename: 原始文件名
        subdirectory: 子目录名
        
    Returns:
        Tuple[str, str]: (文件路径, 唯一文件名)
    """
    # 生成唯一文件名
    unique_filename = generate_unique_filename(filename, "audio")
    
    # 创建完整路径
    upload_dir = Path(settings.upload_dir) / subdirectory
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / unique_filename
    
    # 异步保存文件
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_content)
    
    return str(file_path), unique_filename


async def delete_file(file_path: str) -> bool:
    """
    删除文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否删除成功
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        print(f"删除文件失败: {e}")
        return False


async def get_file_info(file_path: str) -> dict:
    """
    获取文件信息
    
    Args:
        file_path: 文件路径
        
    Returns:
        dict: 文件信息
    """
    try:
        if not os.path.exists(file_path):
            return {}
        
        stat = os.stat(file_path)
        
        return {
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime),
            "modified_at": datetime.fromtimestamp(stat.st_mtime),
            "extension": Path(file_path).suffix,
            "filename": Path(file_path).name
        }
    except Exception as e:
        print(f"获取文件信息失败: {e}")
        return {}


def ensure_directory(directory: str):
    """
    确保目录存在
    
    Args:
        directory: 目录路径
    """
    Path(directory).mkdir(parents=True, exist_ok=True)


async def cleanup_temp_files(directory: str, max_age_hours: int = 24):
    """
    清理临时文件
    
    Args:
        directory: 临时文件目录
        max_age_hours: 文件最大保留时间(小时)
    """
    try:
        temp_dir = Path(directory)
        if not temp_dir.exists():
            return
        
        current_time = datetime.now().timestamp()
        max_age_seconds = max_age_hours * 3600
        
        for file_path in temp_dir.iterdir():
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    await delete_file(str(file_path))
                    print(f"已清理临时文件: {file_path}")
                    
    except Exception as e:
        print(f"清理临时文件失败: {e}")


class FileManager:
    """文件管理器"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or settings.upload_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_file(
        self, 
        content: bytes, 
        filename: str, 
        category: str = "misc"
    ) -> dict:
        """
        保存文件并返回文件信息
        
        Args:
            content: 文件内容
            filename: 原始文件名
            category: 文件分类
            
        Returns:
            dict: 文件信息
        """
        # 创建分类目录
        category_dir = self.base_dir / category
        category_dir.mkdir(exist_ok=True)
        
        # 生成唯一文件名
        unique_filename = generate_unique_filename(filename, category)
        file_path = category_dir / unique_filename
        
        # 保存文件
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # 返回文件信息
        return {
            "file_path": str(file_path),
            "filename": unique_filename,
            "original_filename": filename,
            "size": len(content),
            "hash": get_file_hash(content),
            "category": category
        }
    
    async def get_file(self, file_path: str) -> Optional[bytes]:
        """
        读取文件内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            bytes: 文件内容，如果文件不存在返回None
        """
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                return await f.read()
        except FileNotFoundError:
            return None
        except Exception as e:
            print(f"读取文件失败: {e}")
            return None
    
    async def delete_file(self, file_path: str) -> bool:
        """删除文件"""
        return await delete_file(file_path)
    
    async def list_files(self, category: str = None) -> list:
        """
        列出文件
        
        Args:
            category: 文件分类，None表示列出所有
            
        Returns:
            list: 文件信息列表
        """
        files = []
        search_dir = self.base_dir / category if category else self.base_dir
        
        if not search_dir.exists():
            return files
        
        for file_path in search_dir.rglob("*"):
            if file_path.is_file():
                info = await get_file_info(str(file_path))
                if info:
                    info["file_path"] = str(file_path)
                    files.append(info)
        
        return files