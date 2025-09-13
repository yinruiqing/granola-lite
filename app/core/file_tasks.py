"""
文件处理相关异步任务
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path

from app.core.tasks import task, TaskPriority
from app.core.storage import storage_manager
from app.core.events import event_emitter, Events
from loguru import logger


@task(
    name='file.batch_upload',
    queue='file',
    priority=TaskPriority.NORMAL,
    max_retries=2,
    time_limit=600,
    soft_time_limit=540
)
def batch_file_upload_task(
    files_data: List[Dict[str, Any]],
    user_id: int,
    meeting_id: int = None
) -> Dict[str, Any]:
    """
    批量文件上传任务
    
    Args:
        files_data: 文件数据列表 [{'content': bytes, 'filename': str}]
        user_id: 用户ID
        meeting_id: 会议ID
    
    Returns:
        批量上传结果
    """
    try:
        logger.info(f"开始批量上传文件: {len(files_data)} 个文件 (用户: {user_id})")
        
        # 使用存储管理器的批量上传功能
        results = asyncio.run(storage_manager.batch_upload(
            files=files_data,
            user_id=user_id,
            meeting_id=meeting_id
        ))
        
        # 统计结果
        successful_count = sum(1 for r in results if r['success'])
        failed_count = len(results) - successful_count
        
        # 计算总大小
        total_size = sum(len(f['content']) for f in files_data)
        
        batch_result = {
            'total_files': len(files_data),
            'successful_count': successful_count,
            'failed_count': failed_count,
            'results': results,
            'total_size': total_size,
            'user_id': user_id,
            'meeting_id': meeting_id,
            'uploaded_at': datetime.now().isoformat()
        }
        
        logger.info(f"批量上传完成: 成功 {successful_count}, 失败 {failed_count}")
        
        return batch_result
        
    except Exception as e:
        logger.error(f"批量文件上传失败: {e}")
        raise


@task(
    name='file.compress_images',
    queue='file',
    priority=TaskPriority.LOW,
    max_retries=2,
    time_limit=300,
    soft_time_limit=240
)
def compress_images_task(
    file_paths: List[str],
    quality: int = 85,
    max_width: int = 1920,
    user_id: int = None
) -> Dict[str, Any]:
    """
    批量压缩图片任务
    
    Args:
        file_paths: 图片文件路径列表
        quality: 压缩质量 (1-100)
        max_width: 最大宽度
        user_id: 用户ID
    
    Returns:
        压缩结果
    """
    try:
        logger.info(f"开始压缩图片: {len(file_paths)} 个文件")
        
        results = []
        total_original_size = 0
        total_compressed_size = 0
        
        for file_path in file_paths:
            try:
                # 下载原文件
                original_data = asyncio.run(storage_manager.download_file(file_path))
                total_original_size += len(original_data)
                
                # 压缩图片
                from app.core.storage import FileCompressor
                compressed_data = asyncio.run(
                    FileCompressor.compress_image(original_data, quality, max_width)
                )
                total_compressed_size += len(compressed_data)
                
                # 生成压缩后的文件名
                path_obj = Path(file_path)
                compressed_filename = f"{path_obj.stem}_compressed{path_obj.suffix}"
                
                # 上传压缩后的文件
                upload_result = asyncio.run(storage_manager.upload_file(
                    content=compressed_data,
                    filename=compressed_filename,
                    user_id=user_id
                ))
                
                results.append({
                    'original_path': file_path,
                    'compressed_path': upload_result['file_path'],
                    'original_size': len(original_data),
                    'compressed_size': len(compressed_data),
                    'compression_ratio': len(original_data) / len(compressed_data),
                    'success': True
                })
                
            except Exception as e:
                logger.error(f"压缩图片失败 {file_path}: {e}")
                results.append({
                    'original_path': file_path,
                    'success': False,
                    'error': str(e)
                })
        
        # 计算整体压缩比
        overall_ratio = total_original_size / total_compressed_size if total_compressed_size > 0 else 1.0
        
        compression_result = {
            'processed_files': len(file_paths),
            'successful_files': sum(1 for r in results if r['success']),
            'failed_files': sum(1 for r in results if not r['success']),
            'total_original_size': total_original_size,
            'total_compressed_size': total_compressed_size,
            'overall_compression_ratio': overall_ratio,
            'quality': quality,
            'max_width': max_width,
            'results': results,
            'user_id': user_id,
            'compressed_at': datetime.now().isoformat()
        }
        
        logger.info(f"图片压缩完成: 压缩比 {overall_ratio:.2f}")
        
        return compression_result
        
    except Exception as e:
        logger.error(f"批量图片压缩失败: {e}")
        raise


@task(
    name='file.create_archive',
    queue='file',
    priority=TaskPriority.NORMAL,
    max_retries=1,
    time_limit=900,
    soft_time_limit=840
)
def create_file_archive_task(
    file_paths: List[str],
    archive_name: str,
    user_id: int,
    include_metadata: bool = True
) -> Dict[str, Any]:
    """
    创建文件归档任务
    
    Args:
        file_paths: 文件路径列表
        archive_name: 归档文件名
        user_id: 用户ID
        include_metadata: 是否包含元数据
    
    Returns:
        归档结果
    """
    try:
        logger.info(f"开始创建文件归档: {archive_name} ({len(file_paths)} 个文件)")
        
        # 创建归档
        archive_data = asyncio.run(
            storage_manager.create_file_archive(file_paths)
        )
        
        # 添加时间戳到归档名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_filename = f"{Path(archive_name).stem}_{timestamp}.zip"
        
        # 上传归档文件
        upload_result = asyncio.run(storage_manager.upload_file(
            content=archive_data,
            filename=archive_filename,
            user_id=user_id,
            compress=False  # 归档文件通常已经压缩
        ))
        
        # 创建归档元数据
        metadata = {
            'created_by': user_id,
            'created_at': datetime.now().isoformat(),
            'original_files': file_paths,
            'file_count': len(file_paths),
            'archive_size': len(archive_data)
        }
        
        if include_metadata:
            # 创建元数据文件
            import json
            metadata_content = json.dumps(metadata, indent=2, ensure_ascii=False)
            metadata_filename = f"{Path(archive_name).stem}_{timestamp}_metadata.json"
            
            asyncio.run(storage_manager.upload_file(
                content=metadata_content.encode('utf-8'),
                filename=metadata_filename,
                user_id=user_id
            ))
        
        archive_result = {
            'archive_path': upload_result['file_path'],
            'archive_filename': archive_filename,
            'archive_size': len(archive_data),
            'file_count': len(file_paths),
            'original_files': file_paths,
            'metadata_included': include_metadata,
            'user_id': user_id,
            'created_at': datetime.now().isoformat()
        }
        
        logger.info(f"文件归档创建完成: {archive_filename}")
        
        return archive_result
        
    except Exception as e:
        logger.error(f"创建文件归档失败: {e}")
        raise


@task(
    name='file.cleanup_expired',
    queue='maintenance',
    priority=TaskPriority.LOW,
    max_retries=1,
    time_limit=600,
    soft_time_limit=540
)
def cleanup_expired_files_task(
    retention_days: int = 30,
    file_patterns: List[str] = None
) -> Dict[str, Any]:
    """
    清理过期文件任务
    
    Args:
        retention_days: 保留天数
        file_patterns: 要清理的文件模式列表
    
    Returns:
        清理结果
    """
    try:
        logger.info(f"开始清理 {retention_days} 天前的过期文件")
        
        # 计算过期时间
        expiry_date = datetime.now() - timedelta(days=retention_days)
        
        # 这里需要实现具体的文件系统扫描逻辑
        # 由于我们使用的是抽象的存储系统，这个实现会依赖于具体的存储后端
        
        # 临时实现：记录清理任务
        cleanup_result = {
            'retention_days': retention_days,
            'expiry_date': expiry_date.isoformat(),
            'file_patterns': file_patterns or ['*'],
            'scanned_files': 0,
            'deleted_files': 0,
            'freed_space': 0,
            'errors': [],
            'cleaned_at': datetime.now().isoformat(),
            'note': '文件清理功能需要根据具体存储后端实现'
        }
        
        logger.info("过期文件清理任务完成")
        
        return cleanup_result
        
    except Exception as e:
        logger.error(f"清理过期文件失败: {e}")
        raise


@task(
    name='file.generate_thumbnails',
    queue='file',
    priority=TaskPriority.LOW,
    max_retries=2,
    time_limit=300,
    soft_time_limit=240
)
def generate_thumbnails_task(
    image_paths: List[str],
    thumbnail_size: tuple = (150, 150),
    user_id: int = None
) -> Dict[str, Any]:
    """
    生成缩略图任务
    
    Args:
        image_paths: 图片路径列表
        thumbnail_size: 缩略图尺寸 (width, height)
        user_id: 用户ID
    
    Returns:
        缩略图生成结果
    """
    try:
        logger.info(f"开始生成缩略图: {len(image_paths)} 个图片")
        
        results = []
        
        for image_path in image_paths:
            try:
                # 下载原图
                image_data = asyncio.run(storage_manager.download_file(image_path))
                
                # 生成缩略图
                thumbnail_data = await generate_thumbnail_async(
                    image_data, thumbnail_size
                )
                
                # 生成缩略图文件名
                path_obj = Path(image_path)
                thumbnail_filename = f"{path_obj.stem}_thumb_{thumbnail_size[0]}x{thumbnail_size[1]}{path_obj.suffix}"
                
                # 上传缩略图
                upload_result = asyncio.run(storage_manager.upload_file(
                    content=thumbnail_data,
                    filename=thumbnail_filename,
                    user_id=user_id
                ))
                
                results.append({
                    'original_path': image_path,
                    'thumbnail_path': upload_result['file_path'],
                    'thumbnail_size': thumbnail_size,
                    'original_size': len(image_data),
                    'thumbnail_file_size': len(thumbnail_data),
                    'success': True
                })
                
            except Exception as e:
                logger.error(f"生成缩略图失败 {image_path}: {e}")
                results.append({
                    'original_path': image_path,
                    'success': False,
                    'error': str(e)
                })
        
        thumbnail_result = {
            'processed_images': len(image_paths),
            'successful_thumbnails': sum(1 for r in results if r['success']),
            'failed_thumbnails': sum(1 for r in results if not r['success']),
            'thumbnail_size': thumbnail_size,
            'results': results,
            'user_id': user_id,
            'generated_at': datetime.now().isoformat()
        }
        
        logger.info(f"缩略图生成完成: 成功 {thumbnail_result['successful_thumbnails']} 个")
        
        return thumbnail_result
        
    except Exception as e:
        logger.error(f"批量生成缩略图失败: {e}")
        raise


# 辅助函数
async def generate_thumbnail_async(image_data: bytes, size: tuple) -> bytes:
    """异步生成缩略图"""
    try:
        from PIL import Image
        import io
        
        # 打开图片
        image = Image.open(io.BytesIO(image_data))
        
        # 生成缩略图
        image.thumbnail(size, Image.Resampling.LANCZOS)
        
        # 保存到字节流
        output = io.BytesIO()
        
        # 保持原格式，如果是RGBA转换为RGB
        if image.mode == 'RGBA':
            # 创建白色背景
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        
        image.save(output, format='JPEG', quality=85, optimize=True)
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"生成缩略图失败: {e}")
        raise