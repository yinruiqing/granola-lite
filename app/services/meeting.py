"""
会议管理服务
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy import select, and_, or_, func, desc

from app.models.meeting import Meeting
from app.models.template import Template
from app.models.transcription import Transcription
from app.models.note import Note
from app.models.conversation import Conversation
from app.models.audio_file import AudioFile
from app.db.session import AsyncSessionLocal


class MeetingService:
    """会议管理服务"""
    
    async def create_meeting(
        self,
        title: str,
        description: Optional[str] = None,
        start_time: Optional[datetime] = None,
        template_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        创建会议
        
        Args:
            title: 会议标题
            description: 会议描述
            start_time: 开始时间
            template_id: 使用的模板ID
            
        Returns:
            Dict[str, Any]: 创建的会议信息
        """
        try:
            async with AsyncSessionLocal() as session:
                # 验证模板是否存在
                if template_id:
                    template = await session.get(Template, template_id)
                    if not template:
                        raise HTTPException(status_code=404, detail="模板不存在")
                
                # 创建会议
                meeting = Meeting(
                    title=title,
                    description=description,
                    start_time=start_time or datetime.now(),
                    template_id=template_id,
                    status="active"
                )
                
                session.add(meeting)
                await session.commit()
                await session.refresh(meeting)
                
                return {
                    "id": meeting.id,
                    "title": meeting.title,
                    "description": meeting.description,
                    "start_time": meeting.start_time,
                    "end_time": meeting.end_time,
                    "status": meeting.status,
                    "template_id": meeting.template_id,
                    "created_at": meeting.created_at,
                    "updated_at": meeting.updated_at
                }
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"创建会议失败: {str(e)}"
            )
    
    async def get_meeting(self, meeting_id: int) -> Optional[Dict[str, Any]]:
        """获取单个会议详情"""
        try:
            async with AsyncSessionLocal() as session:
                # 查询会议及相关模板信息
                query = select(Meeting).where(Meeting.id == meeting_id)
                result = await session.execute(query)
                meeting = result.scalar_one_or_none()
                
                if not meeting:
                    return None
                
                # 获取关联的模板信息
                template_info = None
                if meeting.template_id:
                    template = await session.get(Template, meeting.template_id)
                    if template:
                        template_info = {
                            "id": template.id,
                            "name": template.name,
                            "category": template.category
                        }
                
                # 获取统计信息
                stats = await self._get_meeting_stats(session, meeting_id)
                
                return {
                    "id": meeting.id,
                    "title": meeting.title,
                    "description": meeting.description,
                    "start_time": meeting.start_time,
                    "end_time": meeting.end_time,
                    "status": meeting.status,
                    "template_id": meeting.template_id,
                    "template": template_info,
                    "stats": stats,
                    "created_at": meeting.created_at,
                    "updated_at": meeting.updated_at
                }
                
        except Exception as e:
            print(f"获取会议失败: {e}")
            return None
    
    async def get_meetings(
        self,
        status: Optional[str] = None,
        template_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        获取会议列表
        
        Args:
            status: 状态筛选
            template_id: 模板ID筛选
            start_date: 开始日期筛选
            end_date: 结束日期筛选
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            Dict[str, Any]: 会议列表
        """
        try:
            async with AsyncSessionLocal() as session:
                query = select(Meeting)
                
                # 添加筛选条件
                conditions = []
                if status:
                    conditions.append(Meeting.status == status)
                if template_id:
                    conditions.append(Meeting.template_id == template_id)
                if start_date:
                    conditions.append(Meeting.start_time >= start_date)
                if end_date:
                    conditions.append(Meeting.start_time <= end_date)
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                # 获取总数
                count_query = select(func.count(Meeting.id)).select_from(query.subquery())
                total_result = await session.execute(count_query)
                total = total_result.scalar() or 0
                
                # 分页查询
                query = query.order_by(desc(Meeting.start_time)).limit(limit).offset(offset)
                result = await session.execute(query)
                meetings = result.scalars().all()
                
                # 为每个会议添加统计信息
                meeting_list = []
                for meeting in meetings:
                    stats = await self._get_meeting_stats(session, meeting.id)
                    
                    # 获取模板信息
                    template_info = None
                    if meeting.template_id:
                        template = await session.get(Template, meeting.template_id)
                        if template:
                            template_info = {
                                "id": template.id,
                                "name": template.name,
                                "category": template.category
                            }
                    
                    meeting_list.append({
                        "id": meeting.id,
                        "title": meeting.title,
                        "description": meeting.description,
                        "start_time": meeting.start_time,
                        "end_time": meeting.end_time,
                        "status": meeting.status,
                        "template_id": meeting.template_id,
                        "template": template_info,
                        "stats": stats,
                        "created_at": meeting.created_at,
                        "updated_at": meeting.updated_at
                    })
                
                return {
                    "meetings": meeting_list,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(meetings) < total
                }
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"获取会议列表失败: {str(e)}"
            )
    
    async def update_meeting(
        self,
        meeting_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        status: Optional[str] = None,
        template_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        更新会议信息
        
        Args:
            meeting_id: 会议ID
            title: 新标题
            description: 新描述
            start_time: 新开始时间
            end_time: 新结束时间
            status: 新状态
            template_id: 新模板ID
            
        Returns:
            Dict[str, Any]: 更新后的会议信息
        """
        try:
            async with AsyncSessionLocal() as session:
                meeting = await session.get(Meeting, meeting_id)
                
                if not meeting:
                    return None
                
                # 验证模板是否存在
                if template_id:
                    template = await session.get(Template, template_id)
                    if not template:
                        raise HTTPException(status_code=404, detail="模板不存在")
                
                # 验证状态值
                if status and status not in ["active", "completed", "cancelled"]:
                    raise HTTPException(status_code=400, detail="无效的状态值")
                
                # 更新字段
                if title is not None:
                    meeting.title = title
                if description is not None:
                    meeting.description = description
                if start_time is not None:
                    meeting.start_time = start_time
                if end_time is not None:
                    meeting.end_time = end_time
                if status is not None:
                    meeting.status = status
                if template_id is not None:
                    meeting.template_id = template_id
                
                await session.commit()
                await session.refresh(meeting)
                
                # 获取完整信息
                return await self.get_meeting(meeting_id)
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"更新会议失败: {str(e)}"
            )
    
    async def delete_meeting(self, meeting_id: int) -> bool:
        """
        删除会议及其所有相关数据
        
        Args:
            meeting_id: 会议ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            async with AsyncSessionLocal() as session:
                meeting = await session.get(Meeting, meeting_id)
                
                if not meeting:
                    return False
                
                # 删除会议（级联删除相关数据）
                await session.delete(meeting)
                await session.commit()
                return True
                
        except Exception as e:
            print(f"删除会议失败: {e}")
            return False
    
    async def start_meeting(self, meeting_id: int) -> Optional[Dict[str, Any]]:
        """
        开始会议
        
        Args:
            meeting_id: 会议ID
            
        Returns:
            Dict[str, Any]: 更新后的会议信息
        """
        return await self.update_meeting(
            meeting_id=meeting_id,
            status="active",
            start_time=datetime.now()
        )
    
    async def end_meeting(self, meeting_id: int) -> Optional[Dict[str, Any]]:
        """
        结束会议
        
        Args:
            meeting_id: 会议ID
            
        Returns:
            Dict[str, Any]: 更新后的会议信息
        """
        return await self.update_meeting(
            meeting_id=meeting_id,
            status="completed",
            end_time=datetime.now()
        )
    
    async def get_meeting_summary(self, meeting_id: int) -> Optional[Dict[str, Any]]:
        """
        获取会议总结
        
        Args:
            meeting_id: 会议ID
            
        Returns:
            Dict[str, Any]: 会议总结信息
        """
        try:
            meeting_info = await self.get_meeting(meeting_id)
            if not meeting_info:
                return None
            
            async with AsyncSessionLocal() as session:
                # 获取详细统计信息
                stats = await self._get_detailed_meeting_stats(session, meeting_id)
                
                # 获取最近的笔记和对话
                recent_notes = await session.execute(
                    select(Note.content).where(Note.meeting_id == meeting_id)
                    .order_by(desc(Note.created_at)).limit(5)
                )
                notes_sample = [note.content[:100] + "..." if len(note.content) > 100 else note.content 
                               for note in recent_notes.scalars().all()]
                
                recent_conversations = await session.execute(
                    select(Conversation.question, Conversation.answer).where(Conversation.meeting_id == meeting_id)
                    .order_by(desc(Conversation.created_at)).limit(3)
                )
                conversations_sample = [
                    {"question": conv.question, "answer": conv.answer[:100] + "..." if len(conv.answer) > 100 else conv.answer}
                    for conv in recent_conversations.fetchall()
                ]
                
                return {
                    **meeting_info,
                    "detailed_stats": stats,
                    "recent_notes_sample": notes_sample,
                    "recent_conversations_sample": conversations_sample
                }
                
        except Exception as e:
            print(f"获取会议总结失败: {e}")
            return None
    
    async def search_meetings(
        self,
        keyword: str = "",
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        搜索会议
        
        Args:
            keyword: 搜索关键词
            status: 状态筛选
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            Dict[str, Any]: 搜索结果
        """
        try:
            async with AsyncSessionLocal() as session:
                query = select(Meeting)
                
                # 添加搜索条件
                conditions = []
                if keyword:
                    conditions.append(
                        or_(
                            Meeting.title.contains(keyword),
                            Meeting.description.contains(keyword)
                        )
                    )
                if status:
                    conditions.append(Meeting.status == status)
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                # 获取总数
                count_query = select(func.count(Meeting.id)).select_from(query.subquery())
                total_result = await session.execute(count_query)
                total = total_result.scalar() or 0
                
                # 分页查询
                query = query.order_by(desc(Meeting.start_time)).limit(limit).offset(offset)
                result = await session.execute(query)
                meetings = result.scalars().all()
                
                meeting_list = []
                for meeting in meetings:
                    stats = await self._get_meeting_stats(session, meeting.id)
                    meeting_list.append({
                        "id": meeting.id,
                        "title": meeting.title,
                        "description": meeting.description,
                        "start_time": meeting.start_time,
                        "end_time": meeting.end_time,
                        "status": meeting.status,
                        "stats": stats,
                        "created_at": meeting.created_at
                    })
                
                return {
                    "meetings": meeting_list,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(meetings) < total
                }
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"搜索会议失败: {str(e)}"
            )
    
    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """
        获取仪表板统计信息
        
        Returns:
            Dict[str, Any]: 仪表板统计数据
        """
        try:
            async with AsyncSessionLocal() as session:
                # 总会议数
                total_meetings = await session.scalar(select(func.count(Meeting.id)))
                
                # 状态统计
                status_stats = await session.execute(
                    select(Meeting.status, func.count(Meeting.id))
                    .group_by(Meeting.status)
                )
                status_counts = {row[0]: row[1] for row in status_stats.fetchall()}
                
                # 最近7天的会议数
                seven_days_ago = datetime.now() - timedelta(days=7)
                recent_meetings = await session.scalar(
                    select(func.count(Meeting.id))
                    .where(Meeting.created_at >= seven_days_ago)
                )
                
                # 今天的会议数
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                today_meetings = await session.scalar(
                    select(func.count(Meeting.id))
                    .where(Meeting.start_time >= today_start)
                )
                
                # 总转录时长（从音频文件统计）
                total_duration = await session.scalar(
                    select(func.sum(AudioFile.duration))
                ) or 0
                
                # 总笔记数
                total_notes = await session.scalar(select(func.count(Note.id)))
                
                # AI增强笔记数
                ai_enhanced_notes = await session.scalar(
                    select(func.count(Note.id)).where(Note.is_ai_enhanced == True)
                )
                
                # 总对话数
                total_conversations = await session.scalar(select(func.count(Conversation.id)))
                
                return {
                    "total_meetings": total_meetings or 0,
                    "status_breakdown": {
                        "active": status_counts.get("active", 0),
                        "completed": status_counts.get("completed", 0),
                        "cancelled": status_counts.get("cancelled", 0)
                    },
                    "recent_activity": {
                        "meetings_last_7_days": recent_meetings or 0,
                        "meetings_today": today_meetings or 0
                    },
                    "content_stats": {
                        "total_audio_duration_minutes": round((total_duration or 0) / 60, 2),
                        "total_notes": total_notes or 0,
                        "ai_enhanced_notes": ai_enhanced_notes or 0,
                        "total_conversations": total_conversations or 0
                    }
                }
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"获取仪表板统计失败: {str(e)}"
            )
    
    async def _get_meeting_stats(self, session, meeting_id: int) -> Dict[str, Any]:
        """获取会议基础统计信息"""
        # 音频文件数
        audio_count = await session.scalar(
            select(func.count(AudioFile.id)).where(AudioFile.meeting_id == meeting_id)
        )
        
        # 转录段数
        transcription_count = await session.scalar(
            select(func.count(Transcription.id)).where(Transcription.meeting_id == meeting_id)
        )
        
        # 笔记数
        note_count = await session.scalar(
            select(func.count(Note.id)).where(Note.meeting_id == meeting_id)
        )
        
        # 对话数
        conversation_count = await session.scalar(
            select(func.count(Conversation.id)).where(Conversation.meeting_id == meeting_id)
        )
        
        return {
            "audio_files": audio_count or 0,
            "transcriptions": transcription_count or 0,
            "notes": note_count or 0,
            "conversations": conversation_count or 0
        }
    
    async def _get_detailed_meeting_stats(self, session, meeting_id: int) -> Dict[str, Any]:
        """获取会议详细统计信息"""
        # 基础统计
        basic_stats = await self._get_meeting_stats(session, meeting_id)
        
        # 音频总时长
        total_duration = await session.scalar(
            select(func.sum(AudioFile.duration)).where(AudioFile.meeting_id == meeting_id)
        ) or 0
        
        # AI增强笔记数
        ai_enhanced_notes = await session.scalar(
            select(func.count(Note.id)).where(
                and_(Note.meeting_id == meeting_id, Note.is_ai_enhanced == True)
            )
        ) or 0
        
        # 转录置信度统计
        confidence_stats = await session.execute(
            select(func.avg(Transcription.confidence), func.min(Transcription.confidence), func.max(Transcription.confidence))
            .where(Transcription.meeting_id == meeting_id)
        )
        confidence_row = confidence_stats.fetchone()
        
        return {
            **basic_stats,
            "audio_duration_minutes": round(total_duration / 60, 2) if total_duration else 0,
            "ai_enhanced_notes": ai_enhanced_notes,
            "note_enhancement_rate": round((ai_enhanced_notes / basic_stats["notes"]) * 100, 2) if basic_stats["notes"] > 0 else 0,
            "transcription_confidence": {
                "average": round(confidence_row[0], 3) if confidence_row[0] else None,
                "min": round(confidence_row[1], 3) if confidence_row[1] else None,
                "max": round(confidence_row[2], 3) if confidence_row[2] else None
            }
        }


# 全局服务实例
meeting_service: Optional[MeetingService] = None


def get_meeting_service() -> MeetingService:
    """获取会议服务实例"""
    global meeting_service
    if meeting_service is None:
        meeting_service = MeetingService()
    return meeting_service