"""
数据导出系统
"""

from typing import Dict, Any, List, Optional, AsyncGenerator
import json
import csv
import io
import zipfile
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from loguru import logger

from app.db.database import get_db_session
from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcription import Transcription
from app.models.note import Note
from app.core.monitoring import metrics_collector


class ExportFormat:
    JSON = "json"
    CSV = "csv"
    TXT = "txt"
    PDF = "pdf"
    EXCEL = "xlsx"


class DataExporter:
    """数据导出器"""
    
    def __init__(self):
        self.export_location = Path("exports")
        self.export_location.mkdir(parents=True, exist_ok=True)
    
    async def export_user_data(
        self,
        user_id: int,
        format: str = ExportFormat.JSON,
        date_range: Optional[tuple] = None,
        include_files: bool = True
    ) -> Dict[str, Any]:
        """导出用户数据"""
        try:
            logger.info(f"开始导出用户数据: {user_id}, 格式: {format}")
            metrics_collector.record_metric("data_export_started", 1.0)
            
            export_id = self._generate_export_id(user_id)
            
            # 创建导出目录
            export_dir = self.export_location / export_id
            export_dir.mkdir(exist_ok=True)
            
            async with get_db_session() as db:
                # 获取用户信息
                user = await db.get(User, user_id)
                if not user:
                    raise ValueError(f"用户不存在: {user_id}")
                
                export_data = {
                    "export_id": export_id,
                    "user_id": user_id,
                    "user_email": user.email,
                    "export_timestamp": datetime.now().isoformat(),
                    "format": format,
                    "date_range": date_range,
                    "data": {}
                }
                
                # 导出会议数据
                meetings_data = await self._export_meetings_for_user(
                    db, user_id, date_range, format
                )
                export_data["data"]["meetings"] = meetings_data
                
                # 导出转录数据
                transcriptions_data = await self._export_transcriptions_for_user(
                    db, user_id, date_range, format
                )
                export_data["data"]["transcriptions"] = transcriptions_data
                
                # 导出笔记数据
                notes_data = await self._export_notes_for_user(
                    db, user_id, date_range, format
                )
                export_data["data"]["notes"] = notes_data
                
                # 导出统计信息
                stats = await self._generate_user_stats(db, user_id, date_range)
                export_data["statistics"] = stats
                
                # 根据格式保存数据
                if format == ExportFormat.JSON:
                    output_file = export_dir / "user_data.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(export_data, f, ensure_ascii=False, indent=2)
                
                elif format == ExportFormat.CSV:
                    await self._export_to_csv(export_data, export_dir)
                
                elif format == ExportFormat.TXT:
                    await self._export_to_txt(export_data, export_dir)
                
                # 创建ZIP压缩包
                zip_file = self.export_location / f"{export_id}.zip"
                await self._create_export_zip(export_dir, zip_file)
                
                # 清理临时目录
                import shutil
                shutil.rmtree(export_dir)
                
                metrics_collector.record_metric("data_export_completed", 1.0)
                logger.info(f"用户数据导出完成: {export_id}")
                
                return {
                    "export_id": export_id,
                    "file_path": str(zip_file),
                    "file_size": zip_file.stat().st_size,
                    "format": format,
                    "records_count": {
                        "meetings": len(meetings_data),
                        "transcriptions": len(transcriptions_data),
                        "notes": len(notes_data)
                    }
                }
        
        except Exception as e:
            metrics_collector.record_metric("data_export_failed", 1.0)
            logger.error(f"导出用户数据失败: {e}")
            raise
    
    async def export_meeting_transcript(
        self,
        meeting_id: int,
        format: str = ExportFormat.TXT,
        include_timestamps: bool = True,
        include_speakers: bool = True
    ) -> Dict[str, Any]:
        """导出会议转录"""
        try:
            logger.info(f"开始导出会议转录: {meeting_id}, 格式: {format}")
            
            async with get_db_session() as db:
                # 获取会议信息
                meeting = await db.get(Meeting, meeting_id)
                if not meeting:
                    raise ValueError(f"会议不存在: {meeting_id}")
                
                # 获取转录数据
                transcription_query = select(Transcription).where(
                    Transcription.meeting_id == meeting_id
                )
                result = await db.execute(transcription_query)
                transcription = result.scalar_one_or_none()
                
                if not transcription:
                    raise ValueError(f"会议转录不存在: {meeting_id}")
                
                export_id = f"transcript_{meeting_id}_{int(datetime.now().timestamp())}"
                
                if format == ExportFormat.TXT:
                    content = await self._format_transcript_text(
                        transcription, include_timestamps, include_speakers
                    )
                    output_file = self.export_location / f"{export_id}.txt"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                
                elif format == ExportFormat.JSON:
                    data = {
                        "meeting_id": meeting_id,
                        "meeting_title": meeting.title,
                        "meeting_date": meeting.created_at.isoformat(),
                        "transcription_id": transcription.id,
                        "language": transcription.language,
                        "duration": transcription.duration,
                        "text": transcription.text,
                        "segments": transcription.segments or [],
                        "export_timestamp": datetime.now().isoformat()
                    }
                    
                    output_file = self.export_location / f"{export_id}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                
                return {
                    "export_id": export_id,
                    "file_path": str(output_file),
                    "file_size": output_file.stat().st_size,
                    "format": format,
                    "meeting_title": meeting.title,
                    "duration": transcription.duration
                }
        
        except Exception as e:
            logger.error(f"导出会议转录失败: {e}")
            raise
    
    async def export_notes_summary(
        self,
        user_id: int,
        date_range: Optional[tuple] = None,
        format: str = ExportFormat.PDF,
        group_by: str = "date"  # date, meeting, category
    ) -> Dict[str, Any]:
        """导出笔记摘要"""
        try:
            logger.info(f"开始导出笔记摘要: {user_id}, 格式: {format}")
            
            async with get_db_session() as db:
                # 构建查询
                query = select(Note).where(Note.user_id == user_id)
                
                if date_range:
                    start_date, end_date = date_range
                    query = query.where(Note.created_at.between(start_date, end_date))
                
                query = query.order_by(Note.created_at.desc())
                result = await db.execute(query)
                notes = result.scalars().all()
                
                if not notes:
                    raise ValueError("没有找到符合条件的笔记")
                
                export_id = f"notes_summary_{user_id}_{int(datetime.now().timestamp())}"
                
                # 根据分组方式组织笔记
                grouped_notes = await self._group_notes(notes, group_by, db)
                
                if format == ExportFormat.JSON:
                    data = {
                        "export_id": export_id,
                        "user_id": user_id,
                        "export_timestamp": datetime.now().isoformat(),
                        "date_range": date_range,
                        "group_by": group_by,
                        "notes_count": len(notes),
                        "grouped_notes": grouped_notes
                    }
                    
                    output_file = self.export_location / f"{export_id}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                
                elif format == ExportFormat.TXT:
                    content = await self._format_notes_summary_text(grouped_notes, group_by)
                    output_file = self.export_location / f"{export_id}.txt"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                
                return {
                    "export_id": export_id,
                    "file_path": str(output_file),
                    "file_size": output_file.stat().st_size,
                    "format": format,
                    "notes_count": len(notes),
                    "groups_count": len(grouped_notes)
                }
        
        except Exception as e:
            logger.error(f"导出笔记摘要失败: {e}")
            raise
    
    async def get_export_status(self, export_id: str) -> Optional[Dict[str, Any]]:
        """获取导出状态"""
        # 查找导出文件
        for file_path in self.export_location.iterdir():
            if file_path.stem.startswith(export_id) or export_id in file_path.name:
                return {
                    "export_id": export_id,
                    "status": "completed",
                    "file_path": str(file_path),
                    "file_size": file_path.stat().st_size,
                    "created_at": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat()
                }
        
        return None
    
    async def cleanup_old_exports(self, days: int = 7) -> int:
        """清理过期导出文件"""
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        deleted_count = 0
        
        for file_path in self.export_location.iterdir():
            if file_path.stat().st_ctime < cutoff_time:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"清理过期导出文件: {file_path.name}")
                except Exception as e:
                    logger.warning(f"删除导出文件失败: {e}")
        
        logger.info(f"清理完成，删除 {deleted_count} 个过期导出文件")
        return deleted_count
    
    def _generate_export_id(self, user_id: int) -> str:
        """生成导出ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"export_{user_id}_{timestamp}"
    
    async def _export_meetings_for_user(
        self,
        db: AsyncSession,
        user_id: int,
        date_range: Optional[tuple],
        format: str
    ) -> List[Dict[str, Any]]:
        """导出用户会议数据"""
        query = select(Meeting).where(Meeting.user_id == user_id)
        
        if date_range:
            start_date, end_date = date_range
            query = query.where(Meeting.created_at.between(start_date, end_date))
        
        result = await db.execute(query)
        meetings = result.scalars().all()
        
        return [self._serialize_model(meeting) for meeting in meetings]
    
    async def _export_transcriptions_for_user(
        self,
        db: AsyncSession,
        user_id: int,
        date_range: Optional[tuple],
        format: str
    ) -> List[Dict[str, Any]]:
        """导出用户转录数据"""
        query = select(Transcription).where(Transcription.user_id == user_id)
        
        if date_range:
            start_date, end_date = date_range
            query = query.where(Transcription.created_at.between(start_date, end_date))
        
        result = await db.execute(query)
        transcriptions = result.scalars().all()
        
        return [self._serialize_model(transcription) for transcription in transcriptions]
    
    async def _export_notes_for_user(
        self,
        db: AsyncSession,
        user_id: int,
        date_range: Optional[tuple],
        format: str
    ) -> List[Dict[str, Any]]:
        """导出用户笔记数据"""
        query = select(Note).where(Note.user_id == user_id)
        
        if date_range:
            start_date, end_date = date_range
            query = query.where(Note.created_at.between(start_date, end_date))
        
        result = await db.execute(query)
        notes = result.scalars().all()
        
        return [self._serialize_model(note) for note in notes]
    
    async def _generate_user_stats(
        self,
        db: AsyncSession,
        user_id: int,
        date_range: Optional[tuple]
    ) -> Dict[str, Any]:
        """生成用户统计信息"""
        stats = {
            "total_meetings": 0,
            "total_transcriptions": 0,
            "total_notes": 0,
            "total_duration": 0,
            "languages_used": [],
            "date_range": date_range
        }
        
        # 统计会议数量
        query = select(Meeting).where(Meeting.user_id == user_id)
        if date_range:
            start_date, end_date = date_range
            query = query.where(Meeting.created_at.between(start_date, end_date))
        
        result = await db.execute(query)
        meetings = result.scalars().all()
        stats["total_meetings"] = len(meetings)
        
        # 统计转录数量和时长
        query = select(Transcription).where(Transcription.user_id == user_id)
        if date_range:
            query = query.where(Transcription.created_at.between(start_date, end_date))
        
        result = await db.execute(query)
        transcriptions = result.scalars().all()
        stats["total_transcriptions"] = len(transcriptions)
        stats["total_duration"] = sum(t.duration or 0 for t in transcriptions)
        
        # 统计使用的语言
        languages = set(t.language for t in transcriptions if t.language)
        stats["languages_used"] = list(languages)
        
        # 统计笔记数量
        query = select(Note).where(Note.user_id == user_id)
        if date_range:
            query = query.where(Note.created_at.between(start_date, end_date))
        
        result = await db.execute(query)
        notes = result.scalars().all()
        stats["total_notes"] = len(notes)
        
        return stats
    
    async def _export_to_csv(self, export_data: Dict[str, Any], export_dir: Path):
        """导出为CSV格式"""
        # 导出会议数据
        if export_data["data"]["meetings"]:
            meetings_csv = export_dir / "meetings.csv"
            with open(meetings_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=export_data["data"]["meetings"][0].keys())
                writer.writeheader()
                writer.writerows(export_data["data"]["meetings"])
        
        # 导出转录数据
        if export_data["data"]["transcriptions"]:
            transcriptions_csv = export_dir / "transcriptions.csv"
            with open(transcriptions_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=export_data["data"]["transcriptions"][0].keys())
                writer.writeheader()
                writer.writerows(export_data["data"]["transcriptions"])
        
        # 导出笔记数据
        if export_data["data"]["notes"]:
            notes_csv = export_dir / "notes.csv"
            with open(notes_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=export_data["data"]["notes"][0].keys())
                writer.writeheader()
                writer.writerows(export_data["data"]["notes"])
    
    async def _export_to_txt(self, export_data: Dict[str, Any], export_dir: Path):
        """导出为TXT格式"""
        txt_file = export_dir / "user_data.txt"
        
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"用户数据导出报告\n")
            f.write(f"导出时间: {export_data['export_timestamp']}\n")
            f.write(f"用户ID: {export_data['user_id']}\n")
            f.write(f"用户邮箱: {export_data['user_email']}\n\n")
            
            # 统计信息
            stats = export_data.get("statistics", {})
            f.write("=== 统计信息 ===\n")
            f.write(f"会议总数: {stats.get('total_meetings', 0)}\n")
            f.write(f"转录总数: {stats.get('total_transcriptions', 0)}\n")
            f.write(f"笔记总数: {stats.get('total_notes', 0)}\n")
            f.write(f"总时长: {stats.get('total_duration', 0):.2f} 秒\n")
            f.write(f"使用语言: {', '.join(stats.get('languages_used', []))}\n\n")
            
            # 会议列表
            if export_data["data"]["meetings"]:
                f.write("=== 会议列表 ===\n")
                for meeting in export_data["data"]["meetings"]:
                    f.write(f"- {meeting['title']} ({meeting['created_at']})\n")
                f.write("\n")
            
            # 笔记内容
            if export_data["data"]["notes"]:
                f.write("=== 笔记内容 ===\n")
                for note in export_data["data"]["notes"]:
                    f.write(f"标题: {note['title']}\n")
                    f.write(f"时间: {note['created_at']}\n")
                    f.write(f"内容: {note['content'][:200]}...\n")
                    f.write("-" * 40 + "\n")
    
    async def _format_transcript_text(
        self,
        transcription,
        include_timestamps: bool,
        include_speakers: bool
    ) -> str:
        """格式化转录文本"""
        content = []
        content.append("会议转录")
        content.append("=" * 50)
        content.append(f"转录ID: {transcription.id}")
        content.append(f"语言: {transcription.language}")
        content.append(f"时长: {transcription.duration:.2f} 秒")
        content.append(f"创建时间: {transcription.created_at}")
        content.append("")
        
        # 如果有分段信息，按分段显示
        if transcription.segments:
            for segment in transcription.segments:
                line = ""
                if include_timestamps and segment.get("start_time"):
                    line += f"[{segment['start_time']:.2f}s] "
                if include_speakers and segment.get("speaker"):
                    line += f"{segment['speaker']}: "
                line += segment.get("text", "")
                content.append(line)
        else:
            # 没有分段信息，直接显示全文
            content.append("转录内容:")
            content.append(transcription.text or "")
        
        return "\n".join(content)
    
    async def _group_notes(
        self,
        notes: List,
        group_by: str,
        db: AsyncSession
    ) -> Dict[str, List[Dict[str, Any]]]:
        """按指定方式分组笔记"""
        grouped = {}
        
        for note in notes:
            if group_by == "date":
                key = note.created_at.strftime("%Y-%m-%d")
            elif group_by == "meeting":
                # 需要获取关联的会议信息
                if note.meeting_id:
                    meeting = await db.get(Meeting, note.meeting_id)
                    key = meeting.title if meeting else "未知会议"
                else:
                    key = "独立笔记"
            else:  # category
                key = getattr(note, 'category', '未分类')
            
            if key not in grouped:
                grouped[key] = []
            
            grouped[key].append(self._serialize_model(note))
        
        return grouped
    
    async def _format_notes_summary_text(
        self,
        grouped_notes: Dict[str, List[Dict[str, Any]]],
        group_by: str
    ) -> str:
        """格式化笔记摘要文本"""
        content = []
        content.append("笔记摘要报告")
        content.append("=" * 50)
        content.append(f"分组方式: {group_by}")
        content.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        content.append("")
        
        for group_key, notes in grouped_notes.items():
            content.append(f"=== {group_key} ({len(notes)} 条笔记) ===")
            content.append("")
            
            for note in notes:
                content.append(f"标题: {note['title']}")
                content.append(f"时间: {note['created_at']}")
                content.append(f"内容: {note['content'][:300]}...")
                content.append("-" * 30)
                content.append("")
        
        return "\n".join(content)
    
    async def _create_export_zip(self, source_dir: Path, zip_file: Path):
        """创建导出压缩包"""
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in source_dir.rglob('*'):
                if file_path.is_file():
                    arc_name = file_path.relative_to(source_dir)
                    zf.write(file_path, arc_name)
    
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


# 全局数据导出器实例
data_exporter = DataExporter()


__all__ = [
    'DataExporter',
    'ExportFormat',
    'data_exporter'
]