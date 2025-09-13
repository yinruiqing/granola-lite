"""
文件存储相关API端点
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
import io
from pathlib import Path

from app.db.database import get_db
from app.core.auth import require_current_user, get_current_user
from app.core.storage import storage_manager
from app.models.user import User
from loguru import logger

router = APIRouter()


@router.post("/upload", summary="上传文件")
async def upload_file(
    file: UploadFile = File(...),
    meeting_id: Optional[int] = Query(None, description="会议ID"),
    compress: bool = Query(True, description="是否压缩文件"),
    current_user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    上传文件
    
    - **file**: 要上传的文件
    - **meeting_id**: 关联的会议ID（可选）
    - **compress**: 是否启用文件压缩
    """
    try:
        # 读取文件内容
        content = await file.read()
        
        # 验证文件大小（最大100MB）
        max_size = 100 * 1024 * 1024  # 100MB
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件大小超出限制（最大 {max_size // (1024*1024)}MB）"
            )
        
        # 验证文件类型
        allowed_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',  # 图片
            '.pdf', '.doc', '.docx', '.txt', '.rtf',           # 文档
            '.mp3', '.wav', '.m4a', '.aac', '.flac',           # 音频
            '.mp4', '.avi', '.mov', '.wmv', '.flv',            # 视频
            '.zip', '.rar', '.7z', '.tar', '.gz',              # 压缩包
            '.json', '.xml', '.csv', '.log'                     # 数据文件
        }
        
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型: {file_ext}"
            )
        
        # 上传文件
        result = await storage_manager.upload_file(
            content=content,
            filename=file.filename,
            user_id=current_user.id,
            meeting_id=meeting_id,
            compress=compress
        )
        
        logger.info(f"用户 {current_user.id} 上传文件: {file.filename}")
        
        return {
            "success": True,
            "message": "文件上传成功",
            "file": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件上传失败"
        )


@router.post("/batch-upload", summary="批量上传文件")
async def batch_upload_files(
    files: List[UploadFile] = File(...),
    meeting_id: Optional[int] = Query(None, description="会议ID"),
    current_user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    批量上传文件
    
    - **files**: 要上传的文件列表
    - **meeting_id**: 关联的会议ID（可选）
    """
    try:
        # 验证文件数量（最多10个文件）
        if len(files) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="最多只能同时上传10个文件"
            )
        
        # 准备文件数据
        file_data = []
        total_size = 0
        
        for file in files:
            content = await file.read()
            total_size += len(content)
            
            file_data.append({
                'content': content,
                'filename': file.filename
            })
        
        # 验证总文件大小（最大500MB）
        max_total_size = 500 * 1024 * 1024  # 500MB
        if total_size > max_total_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"文件总大小超出限制（最大 {max_total_size // (1024*1024)}MB）"
            )
        
        # 批量上传
        results = await storage_manager.batch_upload(
            files=file_data,
            user_id=current_user.id,
            meeting_id=meeting_id
        )
        
        # 统计结果
        success_count = sum(1 for r in results if r['success'])
        failed_count = len(results) - success_count
        
        logger.info(f"用户 {current_user.id} 批量上传: 成功 {success_count}, 失败 {failed_count}")
        
        return {
            "success": True,
            "message": f"批量上传完成: 成功 {success_count}, 失败 {failed_count}",
            "results": results,
            "summary": {
                "total": len(results),
                "success": success_count,
                "failed": failed_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量上传失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量上传失败"
        )


@router.get("/download/{file_path:path}", summary="下载文件")
async def download_file(
    file_path: str,
    backend: Optional[str] = Query(None, description="存储后端"),
    current_user: Optional[User] = Depends(get_current_user)
) -> StreamingResponse:
    """
    下载文件
    
    - **file_path**: 文件路径
    - **backend**: 存储后端（可选）
    """
    try:
        # 检查文件是否存在
        if not await storage_manager.file_exists(file_path, backend):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )
        
        # 下载文件
        content = await storage_manager.download_file(file_path, backend)
        
        # 获取文件名和MIME类型
        filename = Path(file_path).name
        import mimetypes
        media_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        
        # 返回文件流
        return StreamingResponse(
            io.BytesIO(content),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件下载失败"
        )


@router.get("/url/{file_path:path}", summary="获取文件访问URL")
async def get_file_url(
    file_path: str,
    expires_in: int = Query(3600, description="URL过期时间（秒）"),
    backend: Optional[str] = Query(None, description="存储后端"),
    current_user: Optional[User] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取文件访问URL
    
    - **file_path**: 文件路径
    - **expires_in**: URL过期时间（秒，默认1小时）
    - **backend**: 存储后端（可选）
    """
    try:
        # 检查文件是否存在
        if not await storage_manager.file_exists(file_path, backend):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )
        
        # 获取访问URL
        url = await storage_manager.get_file_url(file_path, backend, expires_in)
        
        return {
            "success": True,
            "url": url,
            "expires_in": expires_in
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件URL失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文件URL失败"
        )


@router.delete("/delete/{file_path:path}", summary="删除文件")
async def delete_file(
    file_path: str,
    backend: Optional[str] = Query(None, description="存储后端"),
    current_user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    删除文件
    
    - **file_path**: 文件路径
    - **backend**: 存储后端（可选）
    """
    try:
        # 检查文件是否存在
        if not await storage_manager.file_exists(file_path, backend):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )
        
        # 删除文件
        success = await storage_manager.delete_file(file_path, backend)
        
        if success:
            logger.info(f"用户 {current_user.id} 删除文件: {file_path}")
            return {
                "success": True,
                "message": "文件删除成功"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="文件删除失败"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除文件失败"
        )


@router.post("/archive", summary="创建文件归档包")
async def create_archive(
    file_paths: List[str],
    backend: Optional[str] = Query(None, description="存储后端"),
    current_user: User = Depends(require_current_user)
) -> StreamingResponse:
    """
    创建文件归档包（ZIP）
    
    - **file_paths**: 文件路径列表
    - **backend**: 存储后端（可选）
    """
    try:
        if len(file_paths) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="最多只能归档50个文件"
            )
        
        # 创建归档包
        archive_content = await storage_manager.create_file_archive(file_paths, backend)
        
        # 生成归档文件名
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_filename = f"files_archive_{timestamp}.zip"
        
        logger.info(f"用户 {current_user.id} 创建归档包: {len(file_paths)} 个文件")
        
        return StreamingResponse(
            io.BytesIO(archive_content),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={archive_filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建归档包失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建归档包失败"
        )


@router.get("/info/{file_path:path}", summary="获取文件信息")
async def get_file_info(
    file_path: str,
    backend: Optional[str] = Query(None, description="存储后端"),
    current_user: Optional[User] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取文件信息
    
    - **file_path**: 文件路径
    - **backend**: 存储后端（可选）
    """
    try:
        # 检查文件是否存在
        if not await storage_manager.file_exists(file_path, backend):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )
        
        # 获取文件基本信息
        filename = Path(file_path).name
        file_ext = Path(filename).suffix.lower()
        
        import mimetypes
        content_type = mimetypes.guess_type(filename)[0]
        
        return {
            "success": True,
            "file_info": {
                "file_path": file_path,
                "filename": filename,
                "extension": file_ext,
                "content_type": content_type,
                "backend": backend or storage_manager.default_backend
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文件信息失败"
        )