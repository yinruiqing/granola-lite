"""
数据备份和恢复系统
"""

from typing import Dict, Any, List, Optional, Tuple
import json
import asyncio
import zipfile
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from loguru import logger

from app.db.database import get_db_session
from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcription import Transcription
from app.models.note import Note
from app.config import settings
from app.services.storage import storage_service
from app.core.cache import cache_manager
from app.core.monitoring import metrics_collector


class BackupFormat:
    JSON = "json"
    SQL = "sql"
    CSV = "csv"


class BackupScope:
    FULL = "full"
    USER_DATA = "user_data"
    MEETINGS = "meetings"
    TRANSCRIPTIONS = "transcriptions"
    NOTES = "notes"


class BackupManager:
    """备份管理器"""
    
    def __init__(self):
        self.backup_location = Path(settings.data_backup_path or "backups")
        self.backup_location.mkdir(parents=True, exist_ok=True)
        self.retention_days = settings.backup_retention_days or 30
        
    async def create_backup(
        self,
        scope: str = BackupScope.FULL,
        format: str = BackupFormat.JSON,
        user_id: Optional[int] = None,
        include_files: bool = True,
        compress: bool = True
    ) -> Dict[str, Any]:
        """创建备份"""
        backup_id = self._generate_backup_id()
        timestamp = datetime.now()
        
        try:
            # 记录备份开始
            metrics_collector.record_metric("backup_started", 1.0)
            logger.info(f"开始创建备份: {backup_id}, 范围: {scope}, 格式: {format}")
            
            # 创建临时工作目录
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # 根据范围导出数据
                export_result = await self._export_data_by_scope(
                    scope=scope,
                    format=format,
                    user_id=user_id,
                    output_dir=temp_path,
                    include_files=include_files
                )
                
                # 创建备份元数据
                metadata = {
                    "backup_id": backup_id,
                    "timestamp": timestamp.isoformat(),
                    "scope": scope,
                    "format": format,
                    "user_id": user_id,
                    "include_files": include_files,
                    "compressed": compress,
                    "export_info": export_result,
                    "checksum": None
                }
                
                # 写入元数据文件
                metadata_file = temp_path / "backup_metadata.json"
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                
                # 创建最终备份文件
                if compress:
                    backup_file = self.backup_location / f"{backup_id}.zip"
                    await self._create_zip_backup(temp_path, backup_file)
                else:
                    backup_file = self.backup_location / backup_id
                    backup_file.mkdir(exist_ok=True)
                    await self._copy_backup_files(temp_path, backup_file)
                
                # 计算校验和
                checksum = await self._calculate_checksum(backup_file)
                metadata["checksum"] = checksum
                
                # 更新元数据
                if compress:
                    # 对于压缩备份，重新创建包含校验和的压缩文件
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, ensure_ascii=False, indent=2)
                    await self._create_zip_backup(temp_path, backup_file)
                else:
                    # 对于非压缩备份，更新元数据文件
                    metadata_file = backup_file / "backup_metadata.json"
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, ensure_ascii=False, indent=2)
                
                # 记录备份成功
                metrics_collector.record_metric("backup_completed", 1.0)
                logger.info(f"备份创建成功: {backup_id}")
                
                return {
                    "backup_id": backup_id,
                    "file_path": str(backup_file),
                    "file_size": backup_file.stat().st_size if backup_file.exists() else 0,
                    "checksum": checksum,
                    "metadata": metadata
                }
        
        except Exception as e:
            metrics_collector.record_metric("backup_failed", 1.0)
            logger.error(f"创建备份失败: {e}")
            raise
    
    async def restore_backup(
        self,
        backup_id: str,
        target_user_id: Optional[int] = None,
        overwrite: bool = False,
        restore_files: bool = True
    ) -> Dict[str, Any]:
        """恢复备份"""
        try:
            logger.info(f"开始恢复备份: {backup_id}")
            metrics_collector.record_metric("restore_started", 1.0)
            
            # 查找备份文件
            backup_file = await self._find_backup_file(backup_id)
            if not backup_file:
                raise ValueError(f"未找到备份文件: {backup_id}")
            
            # 验证备份完整性
            is_valid, metadata = await self._validate_backup(backup_file)
            if not is_valid:
                raise ValueError("备份文件校验失败")
            
            # 提取备份内容
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                if backup_file.suffix == '.zip':
                    await self._extract_zip_backup(backup_file, temp_path)
                else:
                    await self._copy_backup_files(backup_file, temp_path)
                
                # 根据元数据执行恢复
                restore_result = await self._restore_data_from_backup(
                    backup_dir=temp_path,
                    metadata=metadata,
                    target_user_id=target_user_id,
                    overwrite=overwrite,
                    restore_files=restore_files
                )
                
                # 记录恢复成功
                metrics_collector.record_metric("restore_completed", 1.0)
                logger.info(f"备份恢复成功: {backup_id}")
                
                return {
                    "backup_id": backup_id,
                    "restore_info": restore_result,
                    "restored_at": datetime.now().isoformat()
                }
        
        except Exception as e:
            metrics_collector.record_metric("restore_failed", 1.0)
            logger.error(f"恢复备份失败: {e}")
            raise
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份"""
        backups = []
        
        for backup_file in self.backup_location.iterdir():
            if backup_file.is_file() and backup_file.suffix == '.zip':
                # 压缩备份
                metadata = await self._get_backup_metadata(backup_file)
                if metadata:
                    backups.append({
                        "backup_id": metadata.get("backup_id"),
                        "timestamp": metadata.get("timestamp"),
                        "scope": metadata.get("scope"),
                        "format": metadata.get("format"),
                        "file_size": backup_file.stat().st_size,
                        "compressed": True,
                        "file_path": str(backup_file)
                    })
            elif backup_file.is_dir():
                # 非压缩备份
                metadata_file = backup_file / "backup_metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        # 计算目录大小
                        total_size = sum(f.stat().st_size for f in backup_file.rglob('*') if f.is_file())
                        
                        backups.append({
                            "backup_id": metadata.get("backup_id"),
                            "timestamp": metadata.get("timestamp"),
                            "scope": metadata.get("scope"),
                            "format": metadata.get("format"),
                            "file_size": total_size,
                            "compressed": False,
                            "file_path": str(backup_file)
                        })
                    except Exception as e:
                        logger.warning(f"读取备份元数据失败: {e}")
        
        # 按时间戳倒序排序
        backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return backups
    
    async def delete_backup(self, backup_id: str) -> bool:
        """删除备份"""
        try:
            backup_file = await self._find_backup_file(backup_id)
            if not backup_file:
                return False
            
            if backup_file.is_file():
                backup_file.unlink()
            elif backup_file.is_dir():
                import shutil
                shutil.rmtree(backup_file)
            
            logger.info(f"备份删除成功: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除备份失败: {e}")
            return False
    
    async def cleanup_old_backups(self) -> int:
        """清理过期备份"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        deleted_count = 0
        
        backups = await self.list_backups()
        
        for backup in backups:
            try:
                backup_date = datetime.fromisoformat(backup["timestamp"].replace('Z', '+00:00'))
                if backup_date < cutoff_date:
                    success = await self.delete_backup(backup["backup_id"])
                    if success:
                        deleted_count += 1
                        logger.info(f"清理过期备份: {backup['backup_id']}")
            except Exception as e:
                logger.warning(f"处理备份时出错: {e}")
        
        logger.info(f"清理完成，删除 {deleted_count} 个过期备份")
        return deleted_count
    
    def _generate_backup_id(self) -> str:
        """生成备份ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_part = hashlib.md5(f"{timestamp}_{settings.secret_key}".encode()).hexdigest()[:8]
        return f"backup_{timestamp}_{hash_part}"
    
    async def _export_data_by_scope(
        self,
        scope: str,
        format: str,
        user_id: Optional[int],
        output_dir: Path,
        include_files: bool
    ) -> Dict[str, Any]:
        """根据范围导出数据"""
        export_info = {"tables": {}, "files": {}}
        
        async with get_db_session() as db:
            if scope == BackupScope.FULL:
                # 导出所有数据
                export_info["tables"].update(await self._export_users(db, output_dir, format))
                export_info["tables"].update(await self._export_meetings(db, output_dir, format))
                export_info["tables"].update(await self._export_transcriptions(db, output_dir, format))
                export_info["tables"].update(await self._export_notes(db, output_dir, format))
                
            elif scope == BackupScope.USER_DATA and user_id:
                # 导出指定用户数据
                export_info["tables"].update(await self._export_user_data(db, user_id, output_dir, format))
                
            elif scope == BackupScope.MEETINGS:
                # 导出会议数据
                export_info["tables"].update(await self._export_meetings(db, output_dir, format, user_id))
                
            elif scope == BackupScope.TRANSCRIPTIONS:
                # 导出转录数据
                export_info["tables"].update(await self._export_transcriptions(db, output_dir, format, user_id))
                
            elif scope == BackupScope.NOTES:
                # 导出笔记数据
                export_info["tables"].update(await self._export_notes(db, output_dir, format, user_id))
        
        # 导出文件（如果需要）
        if include_files:
            export_info["files"] = await self._export_files(output_dir, user_id)
        
        return export_info
    
    async def _export_users(
        self,
        db: AsyncSession,
        output_dir: Path,
        format: str,
        user_id: Optional[int] = None
    ) -> Dict[str, int]:
        """导出用户数据"""
        query = select(User)
        if user_id:
            query = query.where(User.id == user_id)
        
        result = await db.execute(query)
        users = result.scalars().all()
        
        if format == BackupFormat.JSON:
            data = [self._serialize_model(user) for user in users]
            output_file = output_dir / "users.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return {"users": len(users)}
    
    async def _export_meetings(
        self,
        db: AsyncSession,
        output_dir: Path,
        format: str,
        user_id: Optional[int] = None
    ) -> Dict[str, int]:
        """导出会议数据"""
        query = select(Meeting)
        if user_id:
            query = query.where(Meeting.user_id == user_id)
        
        result = await db.execute(query)
        meetings = result.scalars().all()
        
        if format == BackupFormat.JSON:
            data = [self._serialize_model(meeting) for meeting in meetings]
            output_file = output_dir / "meetings.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return {"meetings": len(meetings)}
    
    async def _export_transcriptions(
        self,
        db: AsyncSession,
        output_dir: Path,
        format: str,
        user_id: Optional[int] = None
    ) -> Dict[str, int]:
        """导出转录数据"""
        query = select(Transcription)
        if user_id:
            query = query.where(Transcription.user_id == user_id)
        
        result = await db.execute(query)
        transcriptions = result.scalars().all()
        
        if format == BackupFormat.JSON:
            data = [self._serialize_model(transcription) for transcription in transcriptions]
            output_file = output_dir / "transcriptions.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return {"transcriptions": len(transcriptions)}
    
    async def _export_notes(
        self,
        db: AsyncSession,
        output_dir: Path,
        format: str,
        user_id: Optional[int] = None
    ) -> Dict[str, int]:
        """导出笔记数据"""
        query = select(Note)
        if user_id:
            query = query.where(Note.user_id == user_id)
        
        result = await db.execute(query)
        notes = result.scalars().all()
        
        if format == BackupFormat.JSON:
            data = [self._serialize_model(note) for note in notes]
            output_file = output_dir / "notes.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return {"notes": len(notes)}
    
    async def _export_user_data(
        self,
        db: AsyncSession,
        user_id: int,
        output_dir: Path,
        format: str
    ) -> Dict[str, int]:
        """导出指定用户的所有数据"""
        export_counts = {}
        
        # 导出用户信息
        export_counts.update(await self._export_users(db, output_dir, format, user_id))
        
        # 导出用户的会议
        export_counts.update(await self._export_meetings(db, output_dir, format, user_id))
        
        # 导出用户的转录
        export_counts.update(await self._export_transcriptions(db, output_dir, format, user_id))
        
        # 导出用户的笔记
        export_counts.update(await self._export_notes(db, output_dir, format, user_id))
        
        return export_counts
    
    async def _export_files(self, output_dir: Path, user_id: Optional[int] = None) -> Dict[str, int]:
        """导出文件"""
        files_dir = output_dir / "files"
        files_dir.mkdir(exist_ok=True)
        
        # 这里需要根据实际的文件存储实现来导出文件
        # 暂时返回空结果
        return {"files": 0}
    
    def _serialize_model(self, model) -> Dict[str, Any]:
        """序列化SQLAlchemy模型"""
        data = {}
        for column in model.__table__.columns:
            value = getattr(model, column.name)
            if isinstance(value, datetime):
                data[column.name] = value.isoformat()
            else:
                data[column.name] = value
        return data
    
    async def _create_zip_backup(self, source_dir: Path, backup_file: Path):
        """创建ZIP压缩备份"""
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in source_dir.rglob('*'):
                if file_path.is_file():
                    arc_name = file_path.relative_to(source_dir)
                    zf.write(file_path, arc_name)
    
    async def _copy_backup_files(self, source_dir: Path, target_dir: Path):
        """复制备份文件"""
        import shutil
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件校验和"""
        if file_path.is_file():
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        else:
            # 对于目录，计算所有文件的哈希
            hash_md5 = hashlib.md5()
            for file_path in sorted(file_path.rglob('*')):
                if file_path.is_file():
                    with open(file_path, 'rb') as f:
                        hash_md5.update(f.read())
            return hash_md5.hexdigest()
    
    async def _find_backup_file(self, backup_id: str) -> Optional[Path]:
        """查找备份文件"""
        # 查找压缩备份
        zip_file = self.backup_location / f"{backup_id}.zip"
        if zip_file.exists():
            return zip_file
        
        # 查找非压缩备份
        dir_backup = self.backup_location / backup_id
        if dir_backup.exists() and dir_backup.is_dir():
            return dir_backup
        
        return None
    
    async def _validate_backup(self, backup_file: Path) -> Tuple[bool, Dict[str, Any]]:
        """验证备份完整性"""
        try:
            metadata = await self._get_backup_metadata(backup_file)
            if not metadata:
                return False, {}
            
            # 验证校验和
            current_checksum = await self._calculate_checksum(backup_file)
            if metadata.get("checksum") != current_checksum:
                logger.warning("备份文件校验和不匹配")
                return False, metadata
            
            return True, metadata
            
        except Exception as e:
            logger.error(f"验证备份失败: {e}")
            return False, {}
    
    async def _get_backup_metadata(self, backup_file: Path) -> Optional[Dict[str, Any]]:
        """获取备份元数据"""
        try:
            if backup_file.suffix == '.zip':
                with zipfile.ZipFile(backup_file, 'r') as zf:
                    with zf.open('backup_metadata.json') as f:
                        return json.load(f)
            else:
                metadata_file = backup_file / "backup_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
            return None
        except Exception:
            return None
    
    async def _extract_zip_backup(self, zip_file: Path, extract_to: Path):
        """提取ZIP备份"""
        with zipfile.ZipFile(zip_file, 'r') as zf:
            zf.extractall(extract_to)
    
    async def _restore_data_from_backup(
        self,
        backup_dir: Path,
        metadata: Dict[str, Any],
        target_user_id: Optional[int],
        overwrite: bool,
        restore_files: bool
    ) -> Dict[str, Any]:
        """从备份恢复数据"""
        restore_info = {"tables": {}, "files": {}}
        
        # 恢复数据表
        async with get_db_session() as db:
            # 恢复用户数据
            if (backup_dir / "users.json").exists():
                count = await self._restore_table_data(
                    db, backup_dir / "users.json", User, overwrite, target_user_id
                )
                restore_info["tables"]["users"] = count
            
            # 恢复会议数据
            if (backup_dir / "meetings.json").exists():
                count = await self._restore_table_data(
                    db, backup_dir / "meetings.json", Meeting, overwrite, target_user_id
                )
                restore_info["tables"]["meetings"] = count
            
            # 恢复转录数据
            if (backup_dir / "transcriptions.json").exists():
                count = await self._restore_table_data(
                    db, backup_dir / "transcriptions.json", Transcription, overwrite, target_user_id
                )
                restore_info["tables"]["transcriptions"] = count
            
            # 恢复笔记数据
            if (backup_dir / "notes.json").exists():
                count = await self._restore_table_data(
                    db, backup_dir / "notes.json", Note, overwrite, target_user_id
                )
                restore_info["tables"]["notes"] = count
        
        # 恢复文件
        if restore_files and (backup_dir / "files").exists():
            restore_info["files"] = await self._restore_files(backup_dir / "files")
        
        return restore_info
    
    async def _restore_table_data(
        self,
        db: AsyncSession,
        data_file: Path,
        model_class,
        overwrite: bool,
        target_user_id: Optional[int]
    ) -> int:
        """恢复表数据"""
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        restored_count = 0
        
        for item in data:
            # 如果指定了目标用户ID，更新用户ID
            if target_user_id and 'user_id' in item:
                item['user_id'] = target_user_id
            
            # 处理日期时间字段
            for key, value in item.items():
                if isinstance(value, str) and value.endswith('T') or 'T' in value:
                    try:
                        item[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except:
                        pass
            
            # 创建或更新记录
            try:
                if overwrite and 'id' in item:
                    # 检查记录是否存在
                    existing = await db.get(model_class, item['id'])
                    if existing:
                        # 更新现有记录
                        for key, value in item.items():
                            setattr(existing, key, value)
                    else:
                        # 创建新记录
                        new_record = model_class(**item)
                        db.add(new_record)
                else:
                    # 创建新记录（忽略ID字段）
                    item.pop('id', None)
                    new_record = model_class(**item)
                    db.add(new_record)
                
                restored_count += 1
                
            except Exception as e:
                logger.warning(f"恢复记录失败: {e}")
                continue
        
        await db.commit()
        return restored_count
    
    async def _restore_files(self, files_dir: Path) -> Dict[str, int]:
        """恢复文件"""
        # 这里需要根据实际的文件存储实现来恢复文件
        # 暂时返回空结果
        return {"files": 0}


# 全局备份管理器实例
backup_manager = BackupManager()


__all__ = [
    'BackupManager',
    'BackupFormat',
    'BackupScope',
    'backup_manager'
]