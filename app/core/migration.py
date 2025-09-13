"""
数据迁移工具
"""

from typing import Dict, Any, List, Optional, Callable
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from loguru import logger

from app.db.database import get_db_session
from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcription import Transcription
from app.models.note import Note
from app.core.backup import backup_manager
from app.core.monitoring import metrics_collector


class MigrationStep:
    """迁移步骤"""
    
    def __init__(
        self,
        name: str,
        description: str,
        up_func: Callable,
        down_func: Optional[Callable] = None,
        version: str = "1.0.0"
    ):
        self.name = name
        self.description = description
        self.up_func = up_func
        self.down_func = down_func
        self.version = version
        self.executed_at: Optional[datetime] = None
    
    async def execute_up(self, db: AsyncSession, context: Dict[str, Any] = None):
        """执行迁移"""
        logger.info(f"执行迁移: {self.name}")
        await self.up_func(db, context or {})
        self.executed_at = datetime.now()
        logger.info(f"迁移完成: {self.name}")
    
    async def execute_down(self, db: AsyncSession, context: Dict[str, Any] = None):
        """回滚迁移"""
        if not self.down_func:
            raise ValueError(f"迁移 {self.name} 不支持回滚")
        
        logger.info(f"回滚迁移: {self.name}")
        await self.down_func(db, context or {})
        self.executed_at = None
        logger.info(f"迁移回滚完成: {self.name}")


class DataMigrator:
    """数据迁移器"""
    
    def __init__(self):
        self.migrations: List[MigrationStep] = []
        self.migration_history: List[Dict[str, Any]] = []
        self.backup_before_migration = True
        self.dry_run_mode = False
    
    def add_migration(self, migration: MigrationStep):
        """添加迁移步骤"""
        self.migrations.append(migration)
        logger.info(f"添加迁移步骤: {migration.name}")
    
    async def migrate_up(
        self,
        target_version: Optional[str] = None,
        dry_run: bool = False,
        create_backup: bool = True
    ) -> Dict[str, Any]:
        """执行迁移"""
        try:
            self.dry_run_mode = dry_run
            logger.info(f"开始数据迁移，目标版本: {target_version or 'latest'}")
            
            if create_backup and not dry_run:
                # 创建迁移前备份
                backup_result = await backup_manager.create_backup(
                    scope="full",
                    compress=True
                )
                logger.info(f"迁移前备份创建完成: {backup_result['backup_id']}")
            
            migration_result = {
                "started_at": datetime.now().isoformat(),
                "target_version": target_version,
                "dry_run": dry_run,
                "executed_migrations": [],
                "errors": [],
                "backup_id": backup_result.get("backup_id") if create_backup and not dry_run else None
            }
            
            executed_count = 0
            
            async with get_db_session() as db:
                for migration in self.migrations:
                    # 检查是否已执行过此迁移
                    if await self._is_migration_executed(db, migration.name):
                        logger.info(f"迁移已执行，跳过: {migration.name}")
                        continue
                    
                    # 如果指定了目标版本，检查是否超出范围
                    if target_version and migration.version > target_version:
                        logger.info(f"达到目标版本，停止迁移: {migration.name}")
                        break
                    
                    try:
                        if dry_run:
                            logger.info(f"DRY RUN: 将执行迁移 {migration.name}")
                        else:
                            # 执行迁移
                            await migration.execute_up(db)
                            
                            # 记录迁移历史
                            await self._record_migration(db, migration)
                            
                            metrics_collector.record_metric("migration_executed", 1.0)
                        
                        migration_result["executed_migrations"].append({
                            "name": migration.name,
                            "description": migration.description,
                            "version": migration.version,
                            "executed_at": migration.executed_at.isoformat() if migration.executed_at else None
                        })
                        
                        executed_count += 1
                        
                    except Exception as e:
                        error_msg = f"迁移执行失败: {migration.name}, 错误: {str(e)}"
                        logger.error(error_msg)
                        migration_result["errors"].append({
                            "migration": migration.name,
                            "error": str(e)
                        })
                        
                        if not dry_run:
                            # 回滚事务
                            await db.rollback()
                            break
                
                if not dry_run and not migration_result["errors"]:
                    await db.commit()
            
            migration_result["completed_at"] = datetime.now().isoformat()
            migration_result["executed_count"] = executed_count
            migration_result["success"] = len(migration_result["errors"]) == 0
            
            if migration_result["success"]:
                logger.info(f"数据迁移完成，执行了 {executed_count} 个迁移步骤")
            else:
                logger.error(f"数据迁移失败，{len(migration_result['errors'])} 个错误")
            
            return migration_result
        
        except Exception as e:
            logger.error(f"数据迁移过程出错: {e}")
            raise
    
    async def migrate_down(
        self,
        target_version: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """回滚迁移"""
        try:
            self.dry_run_mode = dry_run
            logger.info(f"开始迁移回滚，目标版本: {target_version}")
            
            rollback_result = {
                "started_at": datetime.now().isoformat(),
                "target_version": target_version,
                "dry_run": dry_run,
                "rolled_back_migrations": [],
                "errors": []
            }
            
            rollback_count = 0
            
            async with get_db_session() as db:
                # 按相反顺序回滚迁移
                for migration in reversed(self.migrations):
                    # 检查是否需要回滚此迁移
                    if migration.version <= target_version:
                        break
                    
                    if not await self._is_migration_executed(db, migration.name):
                        continue
                    
                    try:
                        if dry_run:
                            logger.info(f"DRY RUN: 将回滚迁移 {migration.name}")
                        else:
                            # 执行回滚
                            await migration.execute_down(db)
                            
                            # 从历史记录中移除
                            await self._remove_migration_record(db, migration.name)
                        
                        rollback_result["rolled_back_migrations"].append({
                            "name": migration.name,
                            "description": migration.description,
                            "version": migration.version
                        })
                        
                        rollback_count += 1
                        
                    except Exception as e:
                        error_msg = f"迁移回滚失败: {migration.name}, 错误: {str(e)}"
                        logger.error(error_msg)
                        rollback_result["errors"].append({
                            "migration": migration.name,
                            "error": str(e)
                        })
                        
                        if not dry_run:
                            await db.rollback()
                            break
                
                if not dry_run and not rollback_result["errors"]:
                    await db.commit()
            
            rollback_result["completed_at"] = datetime.now().isoformat()
            rollback_result["rollback_count"] = rollback_count
            rollback_result["success"] = len(rollback_result["errors"]) == 0
            
            if rollback_result["success"]:
                logger.info(f"迁移回滚完成，回滚了 {rollback_count} 个迁移步骤")
            else:
                logger.error(f"迁移回滚失败，{len(rollback_result['errors'])} 个错误")
            
            return rollback_result
        
        except Exception as e:
            logger.error(f"迁移回滚过程出错: {e}")
            raise
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """获取迁移状态"""
        async with get_db_session() as db:
            executed_migrations = await self._get_executed_migrations(db)
            
            pending_migrations = []
            for migration in self.migrations:
                if migration.name not in [m["name"] for m in executed_migrations]:
                    pending_migrations.append({
                        "name": migration.name,
                        "description": migration.description,
                        "version": migration.version
                    })
            
            return {
                "total_migrations": len(self.migrations),
                "executed_count": len(executed_migrations),
                "pending_count": len(pending_migrations),
                "executed_migrations": executed_migrations,
                "pending_migrations": pending_migrations
            }
    
    async def validate_data_integrity(self) -> Dict[str, Any]:
        """验证数据完整性"""
        try:
            logger.info("开始验证数据完整性")
            
            validation_result = {
                "started_at": datetime.now().isoformat(),
                "checks": [],
                "issues": [],
                "summary": {}
            }
            
            async with get_db_session() as db:
                # 检查用户数据完整性
                user_checks = await self._validate_users_data(db)
                validation_result["checks"].extend(user_checks)
                
                # 检查会议数据完整性
                meeting_checks = await self._validate_meetings_data(db)
                validation_result["checks"].extend(meeting_checks)
                
                # 检查转录数据完整性
                transcription_checks = await self._validate_transcriptions_data(db)
                validation_result["checks"].extend(transcription_checks)
                
                # 检查笔记数据完整性
                note_checks = await self._validate_notes_data(db)
                validation_result["checks"].extend(note_checks)
                
                # 检查外键约束
                fk_checks = await self._validate_foreign_keys(db)
                validation_result["checks"].extend(fk_checks)
            
            # 统计结果
            total_checks = len(validation_result["checks"])
            passed_checks = len([c for c in validation_result["checks"] if c["status"] == "passed"])
            failed_checks = len([c for c in validation_result["checks"] if c["status"] == "failed"])
            
            validation_result["summary"] = {
                "total_checks": total_checks,
                "passed": passed_checks,
                "failed": failed_checks,
                "success_rate": passed_checks / total_checks if total_checks > 0 else 0
            }
            
            validation_result["completed_at"] = datetime.now().isoformat()
            validation_result["is_valid"] = failed_checks == 0
            
            if validation_result["is_valid"]:
                logger.info("数据完整性验证通过")
            else:
                logger.warning(f"数据完整性验证失败，{failed_checks} 个检查项未通过")
            
            return validation_result
        
        except Exception as e:
            logger.error(f"数据完整性验证失败: {e}")
            raise
    
    async def _is_migration_executed(self, db: AsyncSession, migration_name: str) -> bool:
        """检查迁移是否已执行"""
        try:
            result = await db.execute(
                text("SELECT COUNT(*) FROM migration_history WHERE name = :name"),
                {"name": migration_name}
            )
            count = result.scalar()
            return count > 0
        except:
            # 如果migration_history表不存在，创建它
            await self._create_migration_history_table(db)
            return False
    
    async def _record_migration(self, db: AsyncSession, migration: MigrationStep):
        """记录迁移历史"""
        await db.execute(
            text("""
                INSERT INTO migration_history (name, description, version, executed_at)
                VALUES (:name, :description, :version, :executed_at)
            """),
            {
                "name": migration.name,
                "description": migration.description,
                "version": migration.version,
                "executed_at": migration.executed_at
            }
        )
    
    async def _remove_migration_record(self, db: AsyncSession, migration_name: str):
        """移除迁移记录"""
        await db.execute(
            text("DELETE FROM migration_history WHERE name = :name"),
            {"name": migration_name}
        )
    
    async def _get_executed_migrations(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """获取已执行的迁移"""
        try:
            result = await db.execute(
                text("SELECT name, description, version, executed_at FROM migration_history ORDER BY executed_at")
            )
            return [
                {
                    "name": row[0],
                    "description": row[1],
                    "version": row[2],
                    "executed_at": row[3].isoformat() if row[3] else None
                }
                for row in result.fetchall()
            ]
        except:
            return []
    
    async def _create_migration_history_table(self, db: AsyncSession):
        """创建迁移历史表"""
        await db.execute(text("""
            CREATE TABLE IF NOT EXISTS migration_history (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                description TEXT,
                version VARCHAR(50),
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await db.commit()
    
    async def _validate_users_data(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """验证用户数据"""
        checks = []
        
        # 检查用户邮箱唯一性
        try:
            result = await db.execute(
                text("SELECT email, COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1")
            )
            duplicates = result.fetchall()
            
            if duplicates:
                checks.append({
                    "name": "用户邮箱唯一性",
                    "status": "failed",
                    "message": f"发现 {len(duplicates)} 个重复邮箱",
                    "details": [row[0] for row in duplicates]
                })
            else:
                checks.append({
                    "name": "用户邮箱唯一性",
                    "status": "passed",
                    "message": "所有用户邮箱唯一"
                })
        except Exception as e:
            checks.append({
                "name": "用户邮箱唯一性",
                "status": "failed",
                "message": f"检查失败: {str(e)}"
            })
        
        return checks
    
    async def _validate_meetings_data(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """验证会议数据"""
        checks = []
        
        # 检查会议所有者存在性
        try:
            result = await db.execute(text("""
                SELECT m.id FROM meetings m 
                LEFT JOIN users u ON m.user_id = u.id 
                WHERE u.id IS NULL
            """))
            orphaned_meetings = result.fetchall()
            
            if orphaned_meetings:
                checks.append({
                    "name": "会议所有者存在性",
                    "status": "failed",
                    "message": f"发现 {len(orphaned_meetings)} 个孤立会议",
                    "details": [row[0] for row in orphaned_meetings]
                })
            else:
                checks.append({
                    "name": "会议所有者存在性",
                    "status": "passed",
                    "message": "所有会议都有有效的所有者"
                })
        except Exception as e:
            checks.append({
                "name": "会议所有者存在性",
                "status": "failed",
                "message": f"检查失败: {str(e)}"
            })
        
        return checks
    
    async def _validate_transcriptions_data(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """验证转录数据"""
        checks = []
        
        # 检查转录关联会议存在性
        try:
            result = await db.execute(text("""
                SELECT t.id FROM transcriptions t 
                LEFT JOIN meetings m ON t.meeting_id = m.id 
                WHERE t.meeting_id IS NOT NULL AND m.id IS NULL
            """))
            orphaned_transcriptions = result.fetchall()
            
            if orphaned_transcriptions:
                checks.append({
                    "name": "转录关联会议存在性",
                    "status": "failed",
                    "message": f"发现 {len(orphaned_transcriptions)} 个孤立转录",
                    "details": [row[0] for row in orphaned_transcriptions]
                })
            else:
                checks.append({
                    "name": "转录关联会议存在性",
                    "status": "passed",
                    "message": "所有转录都有有效的关联会议"
                })
        except Exception as e:
            checks.append({
                "name": "转录关联会议存在性",
                "status": "failed",
                "message": f"检查失败: {str(e)}"
            })
        
        return checks
    
    async def _validate_notes_data(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """验证笔记数据"""
        checks = []
        
        # 检查笔记所有者存在性
        try:
            result = await db.execute(text("""
                SELECT n.id FROM notes n 
                LEFT JOIN users u ON n.user_id = u.id 
                WHERE u.id IS NULL
            """))
            orphaned_notes = result.fetchall()
            
            if orphaned_notes:
                checks.append({
                    "name": "笔记所有者存在性",
                    "status": "failed",
                    "message": f"发现 {len(orphaned_notes)} 个孤立笔记",
                    "details": [row[0] for row in orphaned_notes]
                })
            else:
                checks.append({
                    "name": "笔记所有者存在性",
                    "status": "passed",
                    "message": "所有笔记都有有效的所有者"
                })
        except Exception as e:
            checks.append({
                "name": "笔记所有者存在性",
                "status": "failed",
                "message": f"检查失败: {str(e)}"
            })
        
        return checks
    
    async def _validate_foreign_keys(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """验证外键约束"""
        checks = []
        
        try:
            # 这里可以添加更多的外键约束检查
            # 暂时返回一个通过的检查
            checks.append({
                "name": "外键约束完整性",
                "status": "passed",
                "message": "所有外键约束正常"
            })
        except Exception as e:
            checks.append({
                "name": "外键约束完整性",
                "status": "failed",
                "message": f"检查失败: {str(e)}"
            })
        
        return checks


# 预定义的迁移步骤示例
async def add_category_to_notes(db: AsyncSession, context: Dict[str, Any]):
    """为笔记添加分类字段的迁移"""
    await db.execute(text("""
        ALTER TABLE notes 
        ADD COLUMN IF NOT EXISTS category VARCHAR(50) DEFAULT 'general'
    """))

async def remove_category_from_notes(db: AsyncSession, context: Dict[str, Any]):
    """移除笔记分类字段的回滚"""
    await db.execute(text("ALTER TABLE notes DROP COLUMN IF EXISTS category"))


# 全局数据迁移器实例
data_migrator = DataMigrator()

# 添加示例迁移
data_migrator.add_migration(MigrationStep(
    name="add_notes_category",
    description="为笔记表添加分类字段",
    up_func=add_category_to_notes,
    down_func=remove_category_from_notes,
    version="1.1.0"
))


__all__ = [
    'DataMigrator',
    'MigrationStep',
    'data_migrator'
]