"""
优化的数据库查询示例
"""

from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from datetime import datetime, timedelta

from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcription import Transcription
from app.models.note import Note
from app.core.performance import query_optimizer
from app.core.cache import cache_manager


class OptimizedQueries:
    """优化的查询类"""
    
    def __init__(self):
        self.optimizer = query_optimizer
    
    @query_optimizer.cache_query("user_meetings", ttl=600)
    async def get_user_meetings_optimized(
        self, 
        db: AsyncSession, 
        user_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取用户会议（优化版）"""
        # 使用索引优化的查询
        query = (
            select(Meeting)
            .where(Meeting.user_id == user_id)
            .order_by(Meeting.created_at.desc())
            .limit(limit)
            .offset(offset)
            .options(
                # 预加载关联的转录数据
                selectinload(Meeting.transcription)
            )
        )
        
        result = await db.execute(query)
        meetings = result.scalars().all()
        
        return [
            {
                "id": meeting.id,
                "title": meeting.title,
                "created_at": meeting.created_at.isoformat(),
                "status": meeting.status,
                "has_transcription": meeting.transcription is not None
            }
            for meeting in meetings
        ]
    
    @query_optimizer.cache_query("user_notes_summary", ttl=300)
    async def get_user_notes_summary_optimized(
        self,
        db: AsyncSession,
        user_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """获取用户笔记摘要（优化版）"""
        # 构建查询条件
        conditions = [Note.user_id == user_id]
        
        if date_from:
            conditions.append(Note.created_at >= date_from)
        if date_to:
            conditions.append(Note.created_at <= date_to)
        
        # 使用聚合查询获取统计信息
        stats_query = (
            select(
                func.count(Note.id).label('total_notes'),
                func.count(func.distinct(Note.meeting_id)).label('unique_meetings'),
                func.avg(func.length(Note.content)).label('avg_content_length'),
                func.max(Note.created_at).label('last_note_date')
            )
            .where(and_(*conditions))
        )
        
        stats_result = await db.execute(stats_query)
        stats = stats_result.first()
        
        # 获取最近的笔记
        recent_notes_query = (
            select(Note.id, Note.title, Note.created_at)
            .where(and_(*conditions))
            .order_by(Note.created_at.desc())
            .limit(5)
        )
        
        recent_result = await db.execute(recent_notes_query)
        recent_notes = recent_result.all()
        
        return {
            "total_notes": stats.total_notes or 0,
            "unique_meetings": stats.unique_meetings or 0,
            "avg_content_length": int(stats.avg_content_length or 0),
            "last_note_date": stats.last_note_date.isoformat() if stats.last_note_date else None,
            "recent_notes": [
                {
                    "id": note.id,
                    "title": note.title,
                    "created_at": note.created_at.isoformat()
                }
                for note in recent_notes
            ]
        }
    
    @query_optimizer.batch_loader(batch_size=50)
    async def batch_load_transcriptions_by_ids(
        self,
        db: AsyncSession,
        transcription_ids: List[int]
    ) -> Dict[int, Dict[str, Any]]:
        """批量加载转录数据"""
        query = (
            select(Transcription)
            .where(Transcription.id.in_(transcription_ids))
            .options(
                # 预加载关联的会议数据
                joinedload(Transcription.meeting)
            )
        )
        
        result = await db.execute(query)
        transcriptions = result.scalars().all()
        
        return {
            transcription.id: {
                "id": transcription.id,
                "text": transcription.text[:500] + "..." if len(transcription.text) > 500 else transcription.text,
                "language": transcription.language,
                "duration": transcription.duration,
                "confidence": transcription.confidence,
                "meeting_title": transcription.meeting.title if transcription.meeting else None,
                "created_at": transcription.created_at.isoformat()
            }
            for transcription in transcriptions
        }
    
    async def get_meeting_with_relations_optimized(
        self,
        db: AsyncSession,
        meeting_id: int
    ) -> Optional[Dict[str, Any]]:
        """获取会议及其关联数据（优化版）"""
        cache_key = f"meeting_full:{meeting_id}"
        
        # 尝试从缓存获取
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        # 一次查询获取所有相关数据
        query = (
            select(Meeting)
            .where(Meeting.id == meeting_id)
            .options(
                selectinload(Meeting.transcription),
                selectinload(Meeting.notes)
            )
        )
        
        result = await db.execute(query)
        meeting = result.scalar_one_or_none()
        
        if not meeting:
            return None
        
        meeting_data = {
            "id": meeting.id,
            "title": meeting.title,
            "description": meeting.description,
            "status": meeting.status,
            "created_at": meeting.created_at.isoformat(),
            "updated_at": meeting.updated_at.isoformat() if meeting.updated_at else None,
            "transcription": None,
            "notes": []
        }
        
        # 添加转录数据
        if meeting.transcription:
            meeting_data["transcription"] = {
                "id": meeting.transcription.id,
                "text": meeting.transcription.text,
                "language": meeting.transcription.language,
                "duration": meeting.transcription.duration,
                "confidence": meeting.transcription.confidence,
                "status": meeting.transcription.status
            }
        
        # 添加笔记数据
        meeting_data["notes"] = [
            {
                "id": note.id,
                "title": note.title,
                "content": note.content[:200] + "..." if len(note.content) > 200 else note.content,
                "created_at": note.created_at.isoformat()
            }
            for note in meeting.notes
        ]
        
        # 缓存结果
        await cache_manager.set(cache_key, meeting_data, ttl=300)
        
        return meeting_data
    
    async def search_content_optimized(
        self,
        db: AsyncSession,
        user_id: int,
        search_query: str,
        content_types: List[str] = None,
        limit: int = 20
    ) -> Dict[str, List[Dict[str, Any]]]:
        """优化的内容搜索"""
        if not content_types:
            content_types = ["meetings", "transcriptions", "notes"]
        
        results = {
            "meetings": [],
            "transcriptions": [],
            "notes": []
        }
        
        # 使用全文搜索（如果数据库支持）
        search_pattern = f"%{search_query}%"
        
        # 搜索会议
        if "meetings" in content_types:
            meetings_query = (
                select(Meeting.id, Meeting.title, Meeting.description, Meeting.created_at)
                .where(
                    and_(
                        Meeting.user_id == user_id,
                        or_(
                            Meeting.title.ilike(search_pattern),
                            Meeting.description.ilike(search_pattern)
                        )
                    )
                )
                .order_by(Meeting.created_at.desc())
                .limit(limit)
            )
            
            meetings_result = await db.execute(meetings_query)
            results["meetings"] = [
                {
                    "id": row.id,
                    "title": row.title,
                    "description": row.description[:100] + "..." if row.description and len(row.description) > 100 else row.description,
                    "created_at": row.created_at.isoformat(),
                    "type": "meeting"
                }
                for row in meetings_result.all()
            ]
        
        # 搜索转录
        if "transcriptions" in content_types:
            transcriptions_query = (
                select(
                    Transcription.id, 
                    Transcription.text, 
                    Transcription.created_at,
                    Meeting.title.label('meeting_title')
                )
                .join(Meeting, Transcription.meeting_id == Meeting.id)
                .where(
                    and_(
                        Transcription.user_id == user_id,
                        Transcription.text.ilike(search_pattern)
                    )
                )
                .order_by(Transcription.created_at.desc())
                .limit(limit)
            )
            
            transcriptions_result = await db.execute(transcriptions_query)
            results["transcriptions"] = [
                {
                    "id": row.id,
                    "text_snippet": row.text[:200] + "..." if len(row.text) > 200 else row.text,
                    "meeting_title": row.meeting_title,
                    "created_at": row.created_at.isoformat(),
                    "type": "transcription"
                }
                for row in transcriptions_result.all()
            ]
        
        # 搜索笔记
        if "notes" in content_types:
            notes_query = (
                select(Note.id, Note.title, Note.content, Note.created_at)
                .where(
                    and_(
                        Note.user_id == user_id,
                        or_(
                            Note.title.ilike(search_pattern),
                            Note.content.ilike(search_pattern)
                        )
                    )
                )
                .order_by(Note.created_at.desc())
                .limit(limit)
            )
            
            notes_result = await db.execute(notes_query)
            results["notes"] = [
                {
                    "id": row.id,
                    "title": row.title,
                    "content_snippet": row.content[:200] + "..." if len(row.content) > 200 else row.content,
                    "created_at": row.created_at.isoformat(),
                    "type": "note"
                }
                for row in notes_result.all()
            ]
        
        return results
    
    async def get_user_activity_stats(
        self,
        db: AsyncSession,
        user_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """获取用户活动统计（优化版）"""
        cache_key = f"user_activity:{user_id}:{days}"
        
        # 尝试从缓存获取
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 使用CTE进行复杂统计查询
        stats_query = text("""
            WITH daily_stats AS (
                SELECT 
                    DATE(created_at) as activity_date,
                    'meeting' as activity_type,
                    COUNT(*) as count
                FROM meetings 
                WHERE user_id = :user_id 
                    AND created_at >= :start_date 
                    AND created_at <= :end_date
                GROUP BY DATE(created_at)
                
                UNION ALL
                
                SELECT 
                    DATE(created_at) as activity_date,
                    'note' as activity_type,
                    COUNT(*) as count
                FROM notes 
                WHERE user_id = :user_id 
                    AND created_at >= :start_date 
                    AND created_at <= :end_date
                GROUP BY DATE(created_at)
                
                UNION ALL
                
                SELECT 
                    DATE(created_at) as activity_date,
                    'transcription' as activity_type,
                    COUNT(*) as count
                FROM transcriptions 
                WHERE user_id = :user_id 
                    AND created_at >= :start_date 
                    AND created_at <= :end_date
                GROUP BY DATE(created_at)
            )
            SELECT 
                activity_date,
                activity_type,
                SUM(count) as total_count
            FROM daily_stats 
            GROUP BY activity_date, activity_type
            ORDER BY activity_date DESC
        """)
        
        result = await db.execute(stats_query, {
            "user_id": user_id,
            "start_date": start_date,
            "end_date": end_date
        })
        
        # 处理结果
        daily_activity = {}
        totals = {"meetings": 0, "notes": 0, "transcriptions": 0}
        
        for row in result.all():
            date_str = row.activity_date.strftime("%Y-%m-%d")
            activity_type = row.activity_type
            count = row.total_count
            
            if date_str not in daily_activity:
                daily_activity[date_str] = {}
            
            daily_activity[date_str][activity_type] = count
            
            if activity_type in totals:
                totals[activity_type] += count
        
        activity_stats = {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "totals": totals,
            "daily_activity": daily_activity,
            "most_active_day": max(daily_activity.keys(), key=lambda d: sum(daily_activity[d].values())) if daily_activity else None
        }
        
        # 缓存结果
        await cache_manager.set(cache_key, activity_stats, ttl=3600)  # 1小时缓存
        
        return activity_stats


# 全局优化查询实例
optimized_queries = OptimizedQueries()


__all__ = [
    'OptimizedQueries',
    'optimized_queries'
]