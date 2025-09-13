"""
数据导入导出和迁移管理API端点
"""

from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime, date
import tempfile
from pathlib import Path

from app.db.database import get_db
from app.core.auth import require_admin_user, get_current_user
from app.core.backup import backup_manager, BackupScope, BackupFormat
from app.core.data_export import data_exporter, ExportFormat
from app.core.data_import import data_importer, ImportFormat, ImportMode
from app.core.migration import data_migrator
from app.models.user import User
from loguru import logger


router = APIRouter()


class BackupRequest(BaseModel):
    """备份请求模型"""
    scope: str = BackupScope.FULL
    format: str = BackupFormat.JSON
    user_id: Optional[int] = None
    include_files: bool = True
    compress: bool = True


class RestoreRequest(BaseModel):
    """恢复请求模型"""
    backup_id: str
    target_user_id: Optional[int] = None
    overwrite: bool = False
    restore_files: bool = True


class ExportRequest(BaseModel):
    """导出请求模型"""
    format: str = ExportFormat.JSON
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    include_files: bool = True


class ImportConfigRequest(BaseModel):
    """导入配置请求模型"""
    format: str = ImportFormat.JSON
    mode: str = ImportMode.UPSERT
    validate_only: bool = False
    mapping_config: Optional[Dict[str, str]] = None


class MigrationRequest(BaseModel):
    """迁移请求模型"""
    target_version: Optional[str] = None
    dry_run: bool = False
    create_backup: bool = True


# ==================== 备份管理 ====================

@router.post("/backup", summary="创建数据备份")
async def create_backup(
    request: BackupRequest,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    创建数据备份（需要管理员权限）
    
    - **scope**: 备份范围 (full, user_data, meetings, transcriptions, notes)
    - **format**: 备份格式 (json, sql, csv)
    - **user_id**: 用户ID（用于用户数据备份）
    - **include_files**: 是否包含文件
    - **compress**: 是否压缩
    """
    try:
        result = await backup_manager.create_backup(
            scope=request.scope,
            format=request.format,
            user_id=request.user_id,
            include_files=request.include_files,
            compress=request.compress
        )
        
        return {
            "success": True,
            "message": "备份创建成功",
            "backup": result
        }
        
    except Exception as e:
        logger.error(f"创建备份失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建备份失败: {str(e)}"
        )


@router.get("/backup", summary="获取备份列表")
async def list_backups(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取所有备份列表（需要管理员权限）
    """
    try:
        backups = await backup_manager.list_backups()
        
        return {
            "success": True,
            "backups": backups,
            "count": len(backups)
        }
        
    except Exception as e:
        logger.error(f"获取备份列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取备份列表失败"
        )


@router.post("/backup/{backup_id}/restore", summary="恢复备份")
async def restore_backup(
    backup_id: str,
    request: RestoreRequest,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    恢复指定备份（需要管理员权限）
    
    - **backup_id**: 备份ID
    - **target_user_id**: 目标用户ID（可选）
    - **overwrite**: 是否覆盖现有数据
    - **restore_files**: 是否恢复文件
    """
    try:
        result = await backup_manager.restore_backup(
            backup_id=backup_id,
            target_user_id=request.target_user_id,
            overwrite=request.overwrite,
            restore_files=request.restore_files
        )
        
        return {
            "success": True,
            "message": "备份恢复成功",
            "restore": result
        }
        
    except Exception as e:
        logger.error(f"恢复备份失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"恢复备份失败: {str(e)}"
        )


@router.delete("/backup/{backup_id}", summary="删除备份")
async def delete_backup(
    backup_id: str,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    删除指定备份（需要管理员权限）
    """
    try:
        success = await backup_manager.delete_backup(backup_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"备份不存在: {backup_id}"
            )
        
        return {
            "success": True,
            "message": f"备份删除成功: {backup_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除备份失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除备份失败"
        )


@router.post("/backup/cleanup", summary="清理过期备份")
async def cleanup_old_backups(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    清理过期备份（需要管理员权限）
    """
    try:
        deleted_count = await backup_manager.cleanup_old_backups()
        
        return {
            "success": True,
            "message": "过期备份清理完成",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.error(f"清理过期备份失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="清理过期备份失败"
        )


# ==================== 数据导出 ====================

@router.post("/export/user-data", summary="导出用户数据")
async def export_user_data(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    导出当前用户的数据
    
    - **format**: 导出格式 (json, csv, txt, pdf, xlsx)
    - **start_date**: 开始日期
    - **end_date**: 结束日期
    - **include_files**: 是否包含文件
    """
    try:
        date_range = None
        if request.start_date and request.end_date:
            date_range = (request.start_date, request.end_date)
        
        result = await data_exporter.export_user_data(
            user_id=current_user.id,
            format=request.format,
            date_range=date_range,
            include_files=request.include_files
        )
        
        return {
            "success": True,
            "message": "用户数据导出成功",
            "export": result
        }
        
    except Exception as e:
        logger.error(f"导出用户数据失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出用户数据失败: {str(e)}"
        )


@router.post("/export/meeting/{meeting_id}/transcript", summary="导出会议转录")
async def export_meeting_transcript(
    meeting_id: int,
    format: str = Query(ExportFormat.TXT, description="导出格式"),
    include_timestamps: bool = Query(True, description="是否包含时间戳"),
    include_speakers: bool = Query(True, description="是否包含说话人"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    导出指定会议的转录
    
    - **meeting_id**: 会议ID
    - **format**: 导出格式 (txt, json)
    - **include_timestamps**: 是否包含时间戳
    - **include_speakers**: 是否包含说话人
    """
    try:
        result = await data_exporter.export_meeting_transcript(
            meeting_id=meeting_id,
            format=format,
            include_timestamps=include_timestamps,
            include_speakers=include_speakers
        )
        
        return {
            "success": True,
            "message": "会议转录导出成功",
            "export": result
        }
        
    except Exception as e:
        logger.error(f"导出会议转录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出会议转录失败: {str(e)}"
        )


@router.post("/export/notes/summary", summary="导出笔记摘要")
async def export_notes_summary(
    format: str = Query(ExportFormat.JSON, description="导出格式"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    group_by: str = Query("date", description="分组方式"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    导出笔记摘要
    
    - **format**: 导出格式 (json, txt, pdf)
    - **start_date**: 开始日期
    - **end_date**: 结束日期
    - **group_by**: 分组方式 (date, meeting, category)
    """
    try:
        date_range = None
        if start_date and end_date:
            date_range = (start_date, end_date)
        
        result = await data_exporter.export_notes_summary(
            user_id=current_user.id,
            date_range=date_range,
            format=format,
            group_by=group_by
        )
        
        return {
            "success": True,
            "message": "笔记摘要导出成功",
            "export": result
        }
        
    except Exception as e:
        logger.error(f"导出笔记摘要失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出笔记摘要失败: {str(e)}"
        )


@router.get("/export/{export_id}/status", summary="获取导出状态")
async def get_export_status(
    export_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取导出状态
    
    - **export_id**: 导出ID
    """
    try:
        status_info = await data_exporter.get_export_status(export_id)
        
        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"导出不存在: {export_id}"
            )
        
        return {
            "success": True,
            "export_status": status_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取导出状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取导出状态失败"
        )


# ==================== 数据导入 ====================

@router.post("/import/validate", summary="验证导入文件")
async def validate_import_file(
    file: UploadFile = File(...),
    format: str = Query(ImportFormat.JSON, description="文件格式"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    验证导入文件格式和内容
    
    - **file**: 导入文件
    - **format**: 文件格式 (json, csv, zip)
    """
    try:
        # 保存上传的文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        
        # 验证文件
        validation_result = await data_importer.validate_import_file(
            import_file=temp_path,
            format=format,
            user_id=current_user.id
        )
        
        # 清理临时文件
        temp_path.unlink()
        
        return {
            "success": True,
            "validation": validation_result,
            "filename": file.filename
        }
        
    except Exception as e:
        logger.error(f"验证导入文件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证导入文件失败: {str(e)}"
        )


@router.post("/import/user-data", summary="导入用户数据")
async def import_user_data(
    file: UploadFile = File(...),
    config: ImportConfigRequest = Depends(),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    导入用户数据
    
    - **file**: 导入文件
    - **format**: 文件格式 (json, csv, zip)
    - **mode**: 导入模式 (create_only, update_only, upsert, merge)
    - **validate_only**: 仅验证不导入
    - **mapping_config**: 字段映射配置
    """
    try:
        # 保存上传的文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{config.format}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        
        # 执行导入
        result = await data_importer.import_user_data(
            user_id=current_user.id,
            import_file=temp_path,
            format=config.format,
            mode=config.mode,
            validate_only=config.validate_only,
            mapping_config=config.mapping_config
        )
        
        # 清理临时文件
        temp_path.unlink()
        
        return {
            "success": True,
            "message": "用户数据导入成功" if not config.validate_only else "数据验证完成",
            "import": result,
            "filename": file.filename
        }
        
    except Exception as e:
        logger.error(f"导入用户数据失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导入用户数据失败: {str(e)}"
        )


@router.post("/import/meeting-transcript", summary="导入会议转录")
async def import_meeting_transcript(
    file: UploadFile = File(...),
    meeting_title: str = Query(..., description="会议标题"),
    format: str = Query(ImportFormat.JSON, description="文件格式"),
    language: str = Query("auto", description="语言"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    导入会议转录
    
    - **file**: 转录文件
    - **meeting_title**: 会议标题
    - **format**: 文件格式 (json, txt)
    - **language**: 语言
    """
    try:
        # 保存上传的文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        
        # 执行导入
        result = await data_importer.import_meeting_transcript(
            user_id=current_user.id,
            transcript_file=temp_path,
            meeting_title=meeting_title,
            format=format,
            language=language
        )
        
        # 清理临时文件
        temp_path.unlink()
        
        return {
            "success": True,
            "message": "会议转录导入成功",
            "import": result,
            "filename": file.filename
        }
        
    except Exception as e:
        logger.error(f"导入会议转录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导入会议转录失败: {str(e)}"
        )


@router.post("/import/notes/batch", summary="批量导入笔记")
async def import_notes_batch(
    file: UploadFile = File(...),
    format: str = Query(ImportFormat.JSON, description="文件格式"),
    mode: str = Query(ImportMode.CREATE_ONLY, description="导入模式"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    批量导入笔记
    
    - **file**: 笔记文件
    - **format**: 文件格式 (json, csv)
    - **mode**: 导入模式 (create_only, upsert)
    """
    try:
        # 保存上传的文件到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        
        # 执行导入
        result = await data_importer.import_notes_batch(
            user_id=current_user.id,
            notes_file=temp_path,
            format=format,
            mode=mode
        )
        
        # 清理临时文件
        temp_path.unlink()
        
        return {
            "success": True,
            "message": "笔记批量导入成功",
            "import": result,
            "filename": file.filename
        }
        
    except Exception as e:
        logger.error(f"批量导入笔记失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量导入笔记失败: {str(e)}"
        )


@router.get("/import/{import_id}/status", summary="获取导入状态")
async def get_import_status(
    import_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取导入状态
    
    - **import_id**: 导入ID
    """
    try:
        status_info = await data_importer.get_import_status(import_id)
        
        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"导入不存在: {import_id}"
            )
        
        return {
            "success": True,
            "import_status": status_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取导入状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取导入状态失败"
        )


# ==================== 数据迁移 ====================

@router.post("/migration/migrate", summary="执行数据迁移")
async def migrate_up(
    request: MigrationRequest,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    执行数据迁移（需要管理员权限）
    
    - **target_version**: 目标版本（可选）
    - **dry_run**: 是否为干运行
    - **create_backup**: 是否在迁移前创建备份
    """
    try:
        result = await data_migrator.migrate_up(
            target_version=request.target_version,
            dry_run=request.dry_run,
            create_backup=request.create_backup
        )
        
        return {
            "success": True,
            "message": "数据迁移完成" if not request.dry_run else "数据迁移模拟完成",
            "migration": result
        }
        
    except Exception as e:
        logger.error(f"数据迁移失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据迁移失败: {str(e)}"
        )


@router.post("/migration/rollback", summary="回滚数据迁移")
async def migrate_down(
    target_version: str = Query(..., description="目标版本"),
    dry_run: bool = Query(False, description="是否为干运行"),
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    回滚数据迁移（需要管理员权限）
    
    - **target_version**: 目标版本
    - **dry_run**: 是否为干运行
    """
    try:
        result = await data_migrator.migrate_down(
            target_version=target_version,
            dry_run=dry_run
        )
        
        return {
            "success": True,
            "message": "数据迁移回滚完成" if not dry_run else "数据迁移回滚模拟完成",
            "rollback": result
        }
        
    except Exception as e:
        logger.error(f"数据迁移回滚失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据迁移回滚失败: {str(e)}"
        )


@router.get("/migration/status", summary="获取迁移状态")
async def get_migration_status(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取数据迁移状态（需要管理员权限）
    """
    try:
        status_info = await data_migrator.get_migration_status()
        
        return {
            "success": True,
            "migration_status": status_info
        }
        
    except Exception as e:
        logger.error(f"获取迁移状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取迁移状态失败"
        )


@router.post("/migration/validate", summary="验证数据完整性")
async def validate_data_integrity(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    验证数据完整性（需要管理员权限）
    """
    try:
        result = await data_migrator.validate_data_integrity()
        
        return {
            "success": True,
            "message": "数据完整性验证完成",
            "validation": result
        }
        
    except Exception as e:
        logger.error(f"数据完整性验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"数据完整性验证失败: {str(e)}"
        )