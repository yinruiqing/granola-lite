"""
数据导入系统
"""

from typing import Dict, Any, List, Optional, Tuple
import json
import csv
import zipfile
import tempfile
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.db.database import get_db_session
from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcription import Transcription
from app.models.note import Note
from app.core.monitoring import metrics_collector


class ImportFormat:
    JSON = "json"
    CSV = "csv"
    ZIP = "zip"


class ImportMode:
    CREATE_ONLY = "create_only"       # 只创建新记录
    UPDATE_ONLY = "update_only"       # 只更新现有记录
    UPSERT = "upsert"                 # 创建或更新
    MERGE = "merge"                   # 智能合并


class ValidationError(Exception):
    """数据验证错误"""
    pass


class DataImporter:
    """数据导入器"""
    
    def __init__(self):
        self.import_location = Path("imports")
        self.import_location.mkdir(parents=True, exist_ok=True)
    
    async def import_user_data(
        self,
        user_id: int,
        import_file: Path,
        format: str = ImportFormat.JSON,
        mode: str = ImportMode.UPSERT,
        validate_only: bool = False,
        mapping_config: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """导入用户数据"""
        try:
            logger.info(f"开始导入用户数据: {user_id}, 文件: {import_file}, 格式: {format}")
            metrics_collector.record_metric("data_import_started", 1.0)
            
            import_id = self._generate_import_id(user_id)
            
            # 解析导入文件
            raw_data = await self._parse_import_file(import_file, format)
            
            # 验证数据
            validation_result = await self._validate_import_data(raw_data, user_id)
            
            if not validation_result["is_valid"]:
                raise ValidationError(f"数据验证失败: {validation_result['errors']}")
            
            if validate_only:
                return {
                    "import_id": import_id,
                    "validation": validation_result,
                    "status": "validation_only"
                }
            
            # 数据清洗和转换
            cleaned_data = await self._clean_and_transform_data(
                raw_data, user_id, mapping_config
            )
            
            # 执行导入
            import_result = await self._execute_import(
                cleaned_data, user_id, mode, import_id
            )
            
            metrics_collector.record_metric("data_import_completed", 1.0)
            logger.info(f"用户数据导入完成: {import_id}")
            
            return {
                "import_id": import_id,
                "status": "completed",
                "validation": validation_result,
                "import_result": import_result,
                "imported_at": datetime.now().isoformat()
            }
        
        except Exception as e:
            metrics_collector.record_metric("data_import_failed", 1.0)
            logger.error(f"导入用户数据失败: {e}")
            raise
    
    async def import_meeting_transcript(
        self,
        user_id: int,
        transcript_file: Path,
        meeting_title: str,
        format: str = ImportFormat.JSON,
        language: str = "auto"
    ) -> Dict[str, Any]:
        """导入会议转录"""
        try:
            logger.info(f"开始导入会议转录: {user_id}, 文件: {transcript_file}")
            
            import_id = f"transcript_{user_id}_{int(datetime.now().timestamp())}"
            
            # 解析转录文件
            transcript_data = await self._parse_transcript_file(transcript_file, format)
            
            # 验证转录数据
            if not transcript_data.get("text") and not transcript_data.get("segments"):
                raise ValidationError("转录文件缺少文本内容")
            
            async with get_db_session() as db:
                # 创建会议记录
                meeting = Meeting(
                    title=meeting_title,
                    user_id=user_id,
                    status="completed",
                    created_at=datetime.now()
                )
                db.add(meeting)
                await db.flush()  # 获取会议ID
                
                # 创建转录记录
                transcription = Transcription(
                    meeting_id=meeting.id,
                    user_id=user_id,
                    text=transcript_data.get("text", ""),
                    language=transcript_data.get("language", language),
                    duration=transcript_data.get("duration", 0),
                    segments=transcript_data.get("segments"),
                    confidence=transcript_data.get("confidence", 0.9),
                    status="completed",
                    created_at=datetime.now()
                )
                db.add(transcription)
                
                await db.commit()
                
                logger.info(f"会议转录导入成功: {import_id}")
                
                return {
                    "import_id": import_id,
                    "meeting_id": meeting.id,
                    "transcription_id": transcription.id,
                    "status": "completed",
                    "meeting_title": meeting_title,
                    "text_length": len(transcript_data.get("text", "")),
                    "imported_at": datetime.now().isoformat()
                }
        
        except Exception as e:
            logger.error(f"导入会议转录失败: {e}")
            raise
    
    async def import_notes_batch(
        self,
        user_id: int,
        notes_file: Path,
        format: str = ImportFormat.JSON,
        mode: str = ImportMode.CREATE_ONLY
    ) -> Dict[str, Any]:
        """批量导入笔记"""
        try:
            logger.info(f"开始批量导入笔记: {user_id}, 文件: {notes_file}")
            
            import_id = f"notes_{user_id}_{int(datetime.now().timestamp())}"
            
            # 解析笔记文件
            notes_data = await self._parse_notes_file(notes_file, format)
            
            if not notes_data:
                raise ValidationError("笔记文件为空或格式错误")
            
            async with get_db_session() as db:
                imported_count = 0
                skipped_count = 0
                error_count = 0
                
                for note_data in notes_data:
                    try:
                        # 验证必需字段
                        if not note_data.get("title") or not note_data.get("content"):
                            skipped_count += 1
                            continue
                        
                        # 处理导入模式
                        if mode == ImportMode.CREATE_ONLY:
                            # 只创建新笔记
                            note = Note(
                                title=note_data["title"],
                                content=note_data["content"],
                                user_id=user_id,
                                meeting_id=note_data.get("meeting_id"),
                                category=note_data.get("category", "imported"),
                                created_at=datetime.now()
                            )
                            db.add(note)
                            imported_count += 1
                        
                        elif mode == ImportMode.UPSERT:
                            # 检查是否已存在相同标题的笔记
                            existing_query = select(Note).where(
                                Note.user_id == user_id,
                                Note.title == note_data["title"]
                            )
                            result = await db.execute(existing_query)
                            existing_note = result.scalar_one_or_none()
                            
                            if existing_note:
                                # 更新现有笔记
                                existing_note.content = note_data["content"]
                                existing_note.category = note_data.get("category", existing_note.category)
                                existing_note.updated_at = datetime.now()
                            else:
                                # 创建新笔记
                                note = Note(
                                    title=note_data["title"],
                                    content=note_data["content"],
                                    user_id=user_id,
                                    meeting_id=note_data.get("meeting_id"),
                                    category=note_data.get("category", "imported"),
                                    created_at=datetime.now()
                                )
                                db.add(note)
                            
                            imported_count += 1
                    
                    except Exception as e:
                        logger.warning(f"导入笔记失败: {e}")
                        error_count += 1
                        continue
                
                await db.commit()
                
                logger.info(f"批量导入笔记完成: {import_id}")
                
                return {
                    "import_id": import_id,
                    "status": "completed",
                    "total_notes": len(notes_data),
                    "imported_count": imported_count,
                    "skipped_count": skipped_count,
                    "error_count": error_count,
                    "imported_at": datetime.now().isoformat()
                }
        
        except Exception as e:
            logger.error(f"批量导入笔记失败: {e}")
            raise
    
    async def validate_import_file(
        self,
        import_file: Path,
        format: str,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """验证导入文件"""
        try:
            logger.info(f"开始验证导入文件: {import_file}, 格式: {format}")
            
            # 检查文件是否存在
            if not import_file.exists():
                return {
                    "is_valid": False,
                    "errors": ["文件不存在"]
                }
            
            # 检查文件大小
            file_size = import_file.stat().st_size
            max_size = 50 * 1024 * 1024  # 50MB
            if file_size > max_size:
                return {
                    "is_valid": False,
                    "errors": [f"文件大小超过限制 ({file_size / 1024 / 1024:.2f}MB > 50MB)"]
                }
            
            # 解析和验证文件内容
            try:
                data = await self._parse_import_file(import_file, format)
                validation_result = await self._validate_import_data(data, user_id)
                
                return {
                    "is_valid": validation_result["is_valid"],
                    "errors": validation_result.get("errors", []),
                    "warnings": validation_result.get("warnings", []),
                    "file_info": {
                        "size": file_size,
                        "format": format,
                        "records_count": len(data) if isinstance(data, list) else 1
                    }
                }
            
            except Exception as e:
                return {
                    "is_valid": False,
                    "errors": [f"文件解析失败: {str(e)}"]
                }
        
        except Exception as e:
            logger.error(f"验证导入文件失败: {e}")
            return {
                "is_valid": False,
                "errors": [f"验证过程出错: {str(e)}"]
            }
    
    async def get_import_status(self, import_id: str) -> Optional[Dict[str, Any]]:
        """获取导入状态"""
        # 这里可以从数据库或缓存中获取导入状态
        # 暂时返回基本信息
        return {
            "import_id": import_id,
            "status": "unknown",
            "message": "导入状态查询功能待实现"
        }
    
    def _generate_import_id(self, user_id: int) -> str:
        """生成导入ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"import_{user_id}_{timestamp}"
    
    async def _parse_import_file(self, file_path: Path, format: str) -> Any:
        """解析导入文件"""
        if format == ImportFormat.JSON:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        elif format == ImportFormat.CSV:
            data = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
            return data
        
        elif format == ImportFormat.ZIP:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # 解压ZIP文件
                with zipfile.ZipFile(file_path, 'r') as zf:
                    zf.extractall(temp_path)
                
                # 查找并解析数据文件
                data_files = list(temp_path.glob('*.json')) + list(temp_path.glob('*.csv'))
                if not data_files:
                    raise ValueError("ZIP文件中没有找到有效的数据文件")
                
                # 解析第一个数据文件
                data_file = data_files[0]
                if data_file.suffix == '.json':
                    with open(data_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                else:
                    data = []
                    with open(data_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            data.append(row)
                    return data
        
        else:
            raise ValueError(f"不支持的导入格式: {format}")
    
    async def _parse_transcript_file(self, file_path: Path, format: str) -> Dict[str, Any]:
        """解析转录文件"""
        if format == ImportFormat.JSON:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        elif format == ImportFormat.TXT:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            return {"text": text}
        
        else:
            raise ValueError(f"不支持的转录文件格式: {format}")
    
    async def _parse_notes_file(self, file_path: Path, format: str) -> List[Dict[str, Any]]:
        """解析笔记文件"""
        if format == ImportFormat.JSON:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 如果是单个笔记对象，转换为列表
            if isinstance(data, dict):
                return [data]
            elif isinstance(data, list):
                return data
            else:
                raise ValueError("无效的JSON格式")
        
        elif format == ImportFormat.CSV:
            notes = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    notes.append(row)
            return notes
        
        else:
            raise ValueError(f"不支持的笔记文件格式: {format}")
    
    async def _validate_import_data(
        self,
        data: Any,
        user_id: Optional[int]
    ) -> Dict[str, Any]:
        """验证导入数据"""
        errors = []
        warnings = []
        
        try:
            # 基本格式验证
            if not data:
                errors.append("数据为空")
                return {"is_valid": False, "errors": errors}
            
            # 如果是列表，验证每个项目
            if isinstance(data, list):
                for i, item in enumerate(data):
                    if not isinstance(item, dict):
                        errors.append(f"第{i+1}项数据格式错误")
                        continue
                    
                    # 验证必需字段
                    if "title" not in item and "text" not in item and "content" not in item:
                        errors.append(f"第{i+1}项缺少必需字段")
            
            # 如果是字典，验证必需字段
            elif isinstance(data, dict):
                if not any(key in data for key in ["title", "text", "content", "meetings", "notes"]):
                    errors.append("数据缺少必需字段")
            
            # 数据量检查
            if isinstance(data, list) and len(data) > 10000:
                warnings.append(f"数据量较大 ({len(data)} 条记录)，导入可能需要较长时间")
            
            # 用户权限检查
            if user_id:
                async with get_db_session() as db:
                    user = await db.get(User, user_id)
                    if not user:
                        errors.append(f"用户不存在: {user_id}")
            
        except Exception as e:
            errors.append(f"数据验证过程出错: {str(e)}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    async def _clean_and_transform_data(
        self,
        data: Any,
        user_id: int,
        mapping_config: Optional[Dict[str, str]]
    ) -> Any:
        """清洗和转换数据"""
        # 应用字段映射
        if mapping_config and isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    # 应用字段重命名
                    for old_key, new_key in mapping_config.items():
                        if old_key in item:
                            item[new_key] = item.pop(old_key)
        
        # 添加用户ID
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "user_id" not in item:
                    item["user_id"] = user_id
        elif isinstance(data, dict) and "user_id" not in data:
            data["user_id"] = user_id
        
        # 数据清洗
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    # 清理空字符串和None值
                    item = {k: v for k, v in item.items() if v is not None and v != ""}
                    
                    # 日期格式转换
                    for key in ["created_at", "updated_at"]:
                        if key in item and isinstance(item[key], str):
                            try:
                                item[key] = datetime.fromisoformat(item[key].replace('Z', '+00:00'))
                            except:
                                # 如果解析失败，移除该字段
                                item.pop(key, None)
        
        return data
    
    async def _execute_import(
        self,
        data: Any,
        user_id: int,
        mode: str,
        import_id: str
    ) -> Dict[str, Any]:
        """执行导入操作"""
        result = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0
        }
        
        try:
            async with get_db_session() as db:
                if isinstance(data, dict) and "meetings" in data:
                    # 导入会议数据
                    for meeting_data in data.get("meetings", []):
                        try:
                            await self._import_meeting(db, meeting_data, mode, result)
                        except Exception as e:
                            logger.warning(f"导入会议失败: {e}")
                            result["errors"] += 1
                
                if isinstance(data, dict) and "notes" in data:
                    # 导入笔记数据
                    for note_data in data.get("notes", []):
                        try:
                            await self._import_note(db, note_data, mode, result)
                        except Exception as e:
                            logger.warning(f"导入笔记失败: {e}")
                            result["errors"] += 1
                
                await db.commit()
            
        except Exception as e:
            logger.error(f"执行导入操作失败: {e}")
            raise
        
        return result
    
    async def _import_meeting(
        self,
        db: AsyncSession,
        meeting_data: Dict[str, Any],
        mode: str,
        result: Dict[str, int]
    ):
        """导入单个会议"""
        if mode == ImportMode.CREATE_ONLY:
            meeting = Meeting(**meeting_data)
            db.add(meeting)
            result["created"] += 1
        
        # 其他导入模式的实现...
    
    async def _import_note(
        self,
        db: AsyncSession,
        note_data: Dict[str, Any],
        mode: str,
        result: Dict[str, int]
    ):
        """导入单个笔记"""
        if mode == ImportMode.CREATE_ONLY:
            note = Note(**note_data)
            db.add(note)
            result["created"] += 1
        
        # 其他导入模式的实现...


# 全局数据导入器实例
data_importer = DataImporter()


__all__ = [
    'DataImporter',
    'ImportFormat',
    'ImportMode',
    'ValidationError',
    'data_importer'
]