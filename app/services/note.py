"""
笔记服务
"""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy import select, update, delete, and_

from app.models.note import Note
from app.models.meeting import Meeting
from app.db.session import AsyncSessionLocal


class NoteService:
    """笔记服务"""
    
    async def create_note(
        self,
        meeting_id: int,
        content: str,
        position: int = 0,
        timestamp: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        创建笔记
        
        Args:
            meeting_id: 会议ID
            content: 笔记内容
            position: 笔记位置
            timestamp: 时间戳
            
        Returns:
            Dict[str, Any]: 创建的笔记信息
        """
        try:
            async with AsyncSessionLocal() as session:
                # 验证会议是否存在
                meeting = await session.get(Meeting, meeting_id)
                if not meeting:
                    raise HTTPException(status_code=404, detail="会议不存在")
                
                # 如果没有指定位置，设为最后一个位置
                if position == 0:
                    result = await session.execute(
                        select(Note.position).where(
                            Note.meeting_id == meeting_id
                        ).order_by(Note.position.desc()).limit(1)
                    )
                    max_position = result.scalar()
                    position = (max_position or 0) + 1
                
                # 创建笔记
                note = Note(
                    meeting_id=meeting_id,
                    content=content,
                    original_content=content,  # 保存原始内容
                    position=position,
                    timestamp=timestamp,
                    is_ai_enhanced=False
                )
                
                session.add(note)
                await session.commit()
                await session.refresh(note)
                
                return {
                    "id": note.id,
                    "meeting_id": note.meeting_id,
                    "content": note.content,
                    "original_content": note.original_content,
                    "position": note.position,
                    "timestamp": note.timestamp,
                    "is_ai_enhanced": note.is_ai_enhanced,
                    "created_at": note.created_at,
                    "updated_at": note.updated_at
                }
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"创建笔记失败: {str(e)}"
            )
    
    async def get_note(self, note_id: int) -> Optional[Dict[str, Any]]:
        """获取单个笔记"""
        try:
            async with AsyncSessionLocal() as session:
                note = await session.get(Note, note_id)
                
                if not note:
                    return None
                
                return {
                    "id": note.id,
                    "meeting_id": note.meeting_id,
                    "content": note.content,
                    "original_content": note.original_content,
                    "position": note.position,
                    "timestamp": note.timestamp,
                    "is_ai_enhanced": note.is_ai_enhanced,
                    "created_at": note.created_at,
                    "updated_at": note.updated_at
                }
                
        except Exception as e:
            print(f"获取笔记失败: {e}")
            return None
    
    async def get_meeting_notes(
        self,
        meeting_id: int,
        include_ai_enhanced: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取会议的所有笔记
        
        Args:
            meeting_id: 会议ID
            include_ai_enhanced: 是否包含AI增强的笔记
            
        Returns:
            List[Dict[str, Any]]: 笔记列表
        """
        try:
            async with AsyncSessionLocal() as session:
                query = select(Note).where(Note.meeting_id == meeting_id)
                
                if not include_ai_enhanced:
                    query = query.where(Note.is_ai_enhanced == False)
                
                query = query.order_by(Note.position, Note.created_at)
                
                result = await session.execute(query)
                notes = result.scalars().all()
                
                return [
                    {
                        "id": note.id,
                        "meeting_id": note.meeting_id,
                        "content": note.content,
                        "original_content": note.original_content,
                        "position": note.position,
                        "timestamp": note.timestamp,
                        "is_ai_enhanced": note.is_ai_enhanced,
                        "created_at": note.created_at,
                        "updated_at": note.updated_at
                    }
                    for note in notes
                ]
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"获取会议笔记失败: {str(e)}"
            )
    
    async def update_note(
        self,
        note_id: int,
        content: Optional[str] = None,
        position: Optional[int] = None,
        timestamp: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        更新笔记
        
        Args:
            note_id: 笔记ID
            content: 新的内容
            position: 新的位置
            timestamp: 新的时间戳
            
        Returns:
            Dict[str, Any]: 更新后的笔记信息
        """
        try:
            async with AsyncSessionLocal() as session:
                note = await session.get(Note, note_id)
                
                if not note:
                    return None
                
                # 更新字段
                if content is not None:
                    # 如果是用户手动编辑，保留原始内容，重置AI增强状态
                    if not note.is_ai_enhanced or content != note.content:
                        if note.original_content == note.content:
                            note.original_content = note.content  # 保存当前内容为原始内容
                        note.is_ai_enhanced = False
                    note.content = content
                
                if position is not None:
                    note.position = position
                
                if timestamp is not None:
                    note.timestamp = timestamp
                
                await session.commit()
                await session.refresh(note)
                
                return {
                    "id": note.id,
                    "meeting_id": note.meeting_id,
                    "content": note.content,
                    "original_content": note.original_content,
                    "position": note.position,
                    "timestamp": note.timestamp,
                    "is_ai_enhanced": note.is_ai_enhanced,
                    "created_at": note.created_at,
                    "updated_at": note.updated_at
                }
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"更新笔记失败: {str(e)}"
            )
    
    async def delete_note(self, note_id: int) -> bool:
        """删除笔记"""
        try:
            async with AsyncSessionLocal() as session:
                note = await session.get(Note, note_id)
                
                if not note:
                    return False
                
                await session.delete(note)
                await session.commit()
                return True
                
        except Exception as e:
            print(f"删除笔记失败: {e}")
            return False
    
    async def reorder_notes(
        self, 
        meeting_id: int, 
        note_orders: List[Dict[str, int]]
    ) -> List[Dict[str, Any]]:
        """
        重新排序笔记
        
        Args:
            meeting_id: 会议ID
            note_orders: 笔记顺序列表 [{"note_id": 1, "position": 1}, ...]
            
        Returns:
            List[Dict[str, Any]]: 重新排序后的笔记列表
        """
        try:
            async with AsyncSessionLocal() as session:
                # 验证所有笔记都属于该会议
                note_ids = [item["note_id"] for item in note_orders]
                
                result = await session.execute(
                    select(Note).where(
                        and_(
                            Note.id.in_(note_ids),
                            Note.meeting_id == meeting_id
                        )
                    )
                )
                notes = result.scalars().all()
                
                if len(notes) != len(note_ids):
                    raise HTTPException(
                        status_code=400, 
                        detail="部分笔记不存在或不属于该会议"
                    )
                
                # 批量更新位置
                for item in note_orders:
                    await session.execute(
                        update(Note).where(
                            Note.id == item["note_id"]
                        ).values(position=item["position"])
                    )
                
                await session.commit()
                
                # 返回更新后的笔记列表
                return await self.get_meeting_notes(meeting_id)
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"重新排序失败: {str(e)}"
            )
    
    async def duplicate_note(self, note_id: int) -> Optional[Dict[str, Any]]:
        """
        复制笔记
        
        Args:
            note_id: 源笔记ID
            
        Returns:
            Dict[str, Any]: 新创建的笔记信息
        """
        try:
            async with AsyncSessionLocal() as session:
                original_note = await session.get(Note, note_id)
                
                if not original_note:
                    return None
                
                # 获取最大位置
                result = await session.execute(
                    select(Note.position).where(
                        Note.meeting_id == original_note.meeting_id
                    ).order_by(Note.position.desc()).limit(1)
                )
                max_position = result.scalar()
                new_position = (max_position or 0) + 1
                
                # 创建新笔记
                new_note = Note(
                    meeting_id=original_note.meeting_id,
                    content=f"{original_note.content} (副本)",
                    original_content=original_note.original_content,
                    position=new_position,
                    timestamp=original_note.timestamp,
                    is_ai_enhanced=original_note.is_ai_enhanced
                )
                
                session.add(new_note)
                await session.commit()
                await session.refresh(new_note)
                
                return {
                    "id": new_note.id,
                    "meeting_id": new_note.meeting_id,
                    "content": new_note.content,
                    "original_content": new_note.original_content,
                    "position": new_note.position,
                    "timestamp": new_note.timestamp,
                    "is_ai_enhanced": new_note.is_ai_enhanced,
                    "created_at": new_note.created_at,
                    "updated_at": new_note.updated_at
                }
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"复制笔记失败: {str(e)}"
            )
    
    async def search_notes(
        self,
        meeting_id: Optional[int] = None,
        keyword: str = "",
        is_ai_enhanced: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        搜索笔记
        
        Args:
            meeting_id: 会议ID筛选
            keyword: 关键词
            is_ai_enhanced: AI增强状态筛选
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            Dict[str, Any]: 搜索结果
        """
        try:
            async with AsyncSessionLocal() as session:
                query = select(Note)
                
                # 添加筛选条件
                if meeting_id is not None:
                    query = query.where(Note.meeting_id == meeting_id)
                
                if keyword:
                    query = query.where(Note.content.contains(keyword))
                
                if is_ai_enhanced is not None:
                    query = query.where(Note.is_ai_enhanced == is_ai_enhanced)
                
                # 分页
                total_query = select(Note.id).select_from(query.subquery())
                total_result = await session.execute(total_query)
                total = len(total_result.fetchall())
                
                query = query.order_by(Note.created_at.desc()).limit(limit).offset(offset)
                result = await session.execute(query)
                notes = result.scalars().all()
                
                return {
                    "notes": [
                        {
                            "id": note.id,
                            "meeting_id": note.meeting_id,
                            "content": note.content,
                            "original_content": note.original_content,
                            "position": note.position,
                            "timestamp": note.timestamp,
                            "is_ai_enhanced": note.is_ai_enhanced,
                            "created_at": note.created_at,
                            "updated_at": note.updated_at
                        }
                        for note in notes
                    ],
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(notes) < total
                }
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"搜索笔记失败: {str(e)}"
            )


# 全局服务实例
note_service: Optional[NoteService] = None


def get_note_service() -> NoteService:
    """获取笔记服务实例"""
    global note_service
    if note_service is None:
        note_service = NoteService()
    return note_service