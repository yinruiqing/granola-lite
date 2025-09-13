"""
文件存储系统 - 支持本地存储和云存储
"""

import os
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, BinaryIO, List
from pathlib import Path
import hashlib
import mimetypes
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError
from PIL import Image
from fastapi import HTTPException
import io
import zipfile
import gzip

from app.config import settings
from loguru import logger


class StorageBackend(ABC):
    """存储后端抽象基类"""
    
    @abstractmethod
    async def upload(self, file_path: str, content: bytes, metadata: Optional[Dict] = None) -> str:
        """上传文件"""
        pass
    
    @abstractmethod
    async def download(self, file_path: str) -> bytes:
        """下载文件"""
        pass
    
    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """删除文件"""
        pass
    
    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        pass
    
    @abstractmethod
    async def get_url(self, file_path: str, expires_in: int = 3600) -> str:
        """获取文件访问URL"""
        pass


class LocalStorageBackend(StorageBackend):
    """本地文件存储后端"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_full_path(self, file_path: str) -> Path:
        """获取完整文件路径"""
        return self.base_path / file_path
    
    async def upload(self, file_path: str, content: bytes, metadata: Optional[Dict] = None) -> str:
        """上传文件到本地存储"""
        full_path = self._get_full_path(file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 异步写入文件
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, full_path.write_bytes, content)
        
        return str(full_path)
    
    async def download(self, file_path: str) -> bytes:
        """从本地存储下载文件"""
        full_path = self._get_full_path(file_path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, full_path.read_bytes)
    
    async def delete(self, file_path: str) -> bool:
        """从本地存储删除文件"""
        full_path = self._get_full_path(file_path)
        try:
            if full_path.exists():
                full_path.unlink()
                return True
        except Exception as e:
            logger.error(f"删除文件失败 {file_path}: {e}")
        return False
    
    async def exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        full_path = self._get_full_path(file_path)
        return full_path.exists()
    
    async def get_url(self, file_path: str, expires_in: int = 3600) -> str:
        """获取文件访问URL（本地存储返回相对路径）"""
        return f"/files/{file_path}"


class S3StorageBackend(StorageBackend):
    """S3云存储后端"""
    
    def __init__(self, bucket_name: str, region_name: str = 'us-east-1'):
        self.bucket_name = bucket_name
        self.region_name = region_name
        self.s3_client = boto3.client(
            's3',
            region_name=region_name,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
    
    async def upload(self, file_path: str, content: bytes, metadata: Optional[Dict] = None) -> str:
        """上传文件到S3"""
        try:
            # 准备上传参数
            upload_args = {
                'Bucket': self.bucket_name,
                'Key': file_path,
                'Body': content
            }
            
            # 添加元数据
            if metadata:
                upload_args['Metadata'] = {
                    k: str(v) for k, v in metadata.items()
                }
            
            # 设置内容类型
            content_type = metadata.get('content_type') if metadata else None
            if content_type:
                upload_args['ContentType'] = content_type
            
            # 异步上传
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                lambda: self.s3_client.put_object(**upload_args)
            )
            
            return f"s3://{self.bucket_name}/{file_path}"
            
        except ClientError as e:
            logger.error(f"S3上传失败: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"文件上传失败: {str(e)}"
            )
    
    async def download(self, file_path: str) -> bytes:
        """从S3下载文件"""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=file_path
                )
            )
            return response['Body'].read()
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File not found: {file_path}")
            logger.error(f"S3下载失败: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"文件下载失败: {str(e)}"
            )
    
    async def delete(self, file_path: str) -> bool:
        """从S3删除文件"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=file_path
                )
            )
            return True
            
        except ClientError as e:
            logger.error(f"S3删除失败: {e}")
            return False
    
    async def exists(self, file_path: str) -> bool:
        """检查S3文件是否存在"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=file_path
                )
            )
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"S3检查文件存在失败: {e}")
            return False
    
    async def get_url(self, file_path: str, expires_in: int = 3600) -> str:
        """获取S3预签名URL"""
        try:
            loop = asyncio.get_event_loop()
            url = await loop.run_in_executor(
                None,
                lambda: self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': file_path},
                    ExpiresIn=expires_in
                )
            )
            return url
            
        except ClientError as e:
            logger.error(f"S3生成URL失败: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"生成访问URL失败: {str(e)}"
            )


class FileCompressor:
    """文件压缩工具"""
    
    @staticmethod
    async def compress_image(image_data: bytes, quality: int = 85, max_width: int = 1920) -> bytes:
        """压缩图片"""
        try:
            # 异步处理图片压缩
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, 
                FileCompressor._compress_image_sync, 
                image_data, quality, max_width
            )
        except Exception as e:
            logger.error(f"图片压缩失败: {e}")
            return image_data  # 返回原数据
    
    @staticmethod
    def _compress_image_sync(image_data: bytes, quality: int, max_width: int) -> bytes:
        """同步压缩图片"""
        try:
            # 打开图片
            image = Image.open(io.BytesIO(image_data))
            
            # 转换为RGB模式（如果是RGBA或其他模式）
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # 调整尺寸
            if image.width > max_width:
                ratio = max_width / image.width
                new_height = int(image.height * ratio)
                image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # 压缩并保存到内存
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=quality, optimize=True)
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"同步图片压缩失败: {e}")
            raise e
    
    @staticmethod
    async def create_zip_archive(files: Dict[str, bytes]) -> bytes:
        """创建ZIP压缩包"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                FileCompressor._create_zip_sync,
                files
            )
        except Exception as e:
            logger.error(f"创建ZIP压缩包失败: {e}")
            raise e
    
    @staticmethod
    def _create_zip_sync(files: Dict[str, bytes]) -> bytes:
        """同步创建ZIP压缩包"""
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, content in files.items():
                zip_file.writestr(filename, content)
        
        return zip_buffer.getvalue()
    
    @staticmethod
    async def compress_text(text_data: bytes) -> bytes:
        """GZIP压缩文本数据"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                gzip.compress,
                text_data
            )
        except Exception as e:
            logger.error(f"文本压缩失败: {e}")
            return text_data


class FileStorageManager:
    """文件存储管理器"""
    
    def __init__(self):
        self.backends: Dict[str, StorageBackend] = {}
        self.default_backend = 'local'
        self.compressor = FileCompressor()
        self._setup_backends()
    
    def _setup_backends(self):
        """设置存储后端"""
        # 本地存储
        self.backends['local'] = LocalStorageBackend(settings.upload_dir)
        
        # S3存储（如果配置了）
        if hasattr(settings, 'aws_s3_bucket_name') and settings.aws_s3_bucket_name:
            self.backends['s3'] = S3StorageBackend(
                bucket_name=settings.aws_s3_bucket_name,
                region_name=getattr(settings, 'aws_region', 'us-east-1')
            )
            self.default_backend = 's3'  # 优先使用S3
    
    def get_backend(self, backend_name: Optional[str] = None) -> StorageBackend:
        """获取存储后端"""
        backend_name = backend_name or self.default_backend
        if backend_name not in self.backends:
            raise ValueError(f"Unknown storage backend: {backend_name}")
        return self.backends[backend_name]
    
    def generate_file_path(self, filename: str, user_id: Optional[int] = None, 
                          meeting_id: Optional[int] = None) -> str:
        """生成文件存储路径"""
        # 生成基于日期的目录结构
        now = datetime.now()
        date_path = now.strftime("%Y/%m/%d")
        
        # 生成文件哈希作为文件名
        file_hash = hashlib.md5(f"{filename}_{now.isoformat()}".encode()).hexdigest()
        file_ext = Path(filename).suffix
        
        # 构建完整路径
        if meeting_id:
            path = f"meetings/{meeting_id}/{date_path}/{file_hash}{file_ext}"
        elif user_id:
            path = f"users/{user_id}/{date_path}/{file_hash}{file_ext}"
        else:
            path = f"general/{date_path}/{file_hash}{file_ext}"
        
        return path
    
    async def upload_file(self, content: bytes, filename: str, 
                         user_id: Optional[int] = None, meeting_id: Optional[int] = None,
                         backend_name: Optional[str] = None, compress: bool = True) -> Dict[str, Any]:
        """上传文件"""
        backend = self.get_backend(backend_name)
        file_path = self.generate_file_path(filename, user_id, meeting_id)
        
        # 文件压缩处理
        original_size = len(content)
        if compress:
            content = await self._compress_file_if_needed(content, filename)
        
        # 准备元数据
        metadata = {
            'original_filename': filename,
            'upload_time': datetime.now().isoformat(),
            'user_id': user_id,
            'meeting_id': meeting_id,
            'file_size': len(content),
            'original_size': original_size,
            'content_type': mimetypes.guess_type(filename)[0],
            'compressed': compress and len(content) < original_size
        }
        
        # 上传文件
        storage_path = await backend.upload(file_path, content, metadata)
        
        return {
            'file_path': file_path,
            'storage_path': storage_path,
            'filename': filename,
            'file_size': len(content),
            'original_size': original_size,
            'content_type': metadata['content_type'],
            'backend': backend_name or self.default_backend,
            'compressed': metadata['compressed']
        }
    
    async def _compress_file_if_needed(self, content: bytes, filename: str) -> bytes:
        """根据文件类型进行压缩"""
        file_ext = Path(filename).suffix.lower()
        
        # 图片文件压缩
        if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
            return await self.compressor.compress_image(content)
        
        # 文本文件压缩
        elif file_ext in ['.txt', '.json', '.xml', '.csv', '.log', '.md']:
            compressed = await self.compressor.compress_text(content)
            # 只有压缩效果明显时才返回压缩后的数据
            if len(compressed) < len(content) * 0.8:
                return compressed
        
        return content
    
    async def download_file(self, file_path: str, backend_name: Optional[str] = None) -> bytes:
        """下载文件"""
        backend = self.get_backend(backend_name)
        return await backend.download(file_path)
    
    async def delete_file(self, file_path: str, backend_name: Optional[str] = None) -> bool:
        """删除文件"""
        backend = self.get_backend(backend_name)
        return await backend.delete(file_path)
    
    async def get_file_url(self, file_path: str, backend_name: Optional[str] = None, 
                          expires_in: int = 3600) -> str:
        """获取文件访问URL"""
        backend = self.get_backend(backend_name)
        return await backend.get_url(file_path, expires_in)
    
    async def file_exists(self, file_path: str, backend_name: Optional[str] = None) -> bool:
        """检查文件是否存在"""
        backend = self.get_backend(backend_name)
        return await backend.exists(file_path)
    
    async def batch_upload(self, files: List[Dict[str, Any]], 
                          user_id: Optional[int] = None, meeting_id: Optional[int] = None,
                          backend_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """批量上传文件"""
        results = []
        
        for file_info in files:
            try:
                result = await self.upload_file(
                    content=file_info['content'],
                    filename=file_info['filename'],
                    user_id=user_id,
                    meeting_id=meeting_id,
                    backend_name=backend_name
                )
                results.append({
                    'success': True,
                    'filename': file_info['filename'],
                    'result': result
                })
            except Exception as e:
                logger.error(f"批量上传失败 {file_info['filename']}: {e}")
                results.append({
                    'success': False,
                    'filename': file_info['filename'],
                    'error': str(e)
                })
        
        return results
    
    async def create_file_archive(self, file_paths: List[str], 
                                 backend_name: Optional[str] = None) -> bytes:
        """创建文件归档包"""
        files_data = {}
        
        # 下载所有文件
        for file_path in file_paths:
            try:
                content = await self.download_file(file_path, backend_name)
                filename = Path(file_path).name
                files_data[filename] = content
            except Exception as e:
                logger.error(f"下载文件失败 {file_path}: {e}")
                continue
        
        # 创建ZIP包
        if files_data:
            return await self.compressor.create_zip_archive(files_data)
        else:
            raise ValueError("没有可用的文件创建归档包")


# 全局存储管理器实例
storage_manager = FileStorageManager()