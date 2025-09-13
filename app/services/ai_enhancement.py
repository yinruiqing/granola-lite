"""
AI笔记增强服务
结合用户笔记和转录内容，使用AI生成增强版笔记
"""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException

from app.services.ai.ai_service import get_ai_service
from app.services.note import get_note_service
from app.services.transcription import get_transcription_service
from app.models.note import Note
from app.models.template import Template
from app.db.session import AsyncSessionLocal
from sqlalchemy import select


class AIEnhancementService:
    """AI笔记增强服务"""
    
    def __init__(self):
        self.ai_service = get_ai_service()
        self.note_service = get_note_service()
        self.transcription_service = get_transcription_service()
    
    async def enhance_note(
        self,
        note_id: int,
        use_template: bool = True,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        增强单个笔记
        
        Args:
            note_id: 笔记ID
            use_template: 是否使用会议模板
            custom_prompt: 自定义提示词
            
        Returns:
            Dict[str, Any]: 增强结果
        """
        try:
            # 获取笔记信息
            note_info = await self.note_service.get_note(note_id)
            if not note_info:
                raise HTTPException(status_code=404, detail="笔记不存在")
            
            meeting_id = note_info["meeting_id"]
            
            # 获取会议转录内容
            full_transcript = await self.transcription_service.get_full_meeting_transcript(meeting_id)
            if not full_transcript:
                raise HTTPException(status_code=400, detail="没有找到会议转录内容")
            
            # 获取模板提示（如果需要）
            template_prompt = None
            if use_template:
                template_prompt = await self._get_meeting_template_prompt(meeting_id)
            
            # 使用自定义提示或模板提示
            prompt_to_use = custom_prompt or template_prompt
            
            # 调用AI增强服务
            enhanced_content = await self.ai_service.enhance_notes(
                original_notes=note_info["content"],
                transcription=full_transcript,
                template_prompt=prompt_to_use
            )
            
            # 更新笔记
            async with AsyncSessionLocal() as session:
                note = await session.get(Note, note_id)
                if not note:
                    raise HTTPException(status_code=404, detail="笔记不存在")
                
                # 保存原始内容（如果还没保存过）
                if not note.original_content or note.original_content == note.content:
                    note.original_content = note.content
                
                # 更新内容和标记
                note.content = enhanced_content
                note.is_ai_enhanced = True
                
                await session.commit()
                await session.refresh(note)
                
                return {
                    "id": note.id,
                    "meeting_id": note.meeting_id,
                    "original_content": note.original_content,
                    "enhanced_content": note.content,
                    "is_ai_enhanced": note.is_ai_enhanced,
                    "enhancement_method": "template" if use_template else "custom",
                    "template_used": template_prompt is not None,
                    "updated_at": note.updated_at
                }
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"笔记增强失败: {str(e)}"
            )
    
    async def enhance_meeting_notes(
        self,
        meeting_id: int,
        only_unenhanced: bool = True,
        use_template: bool = True,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        增强会议的所有笔记
        
        Args:
            meeting_id: 会议ID
            only_unenhanced: 是否只增强未增强过的笔记
            use_template: 是否使用会议模板
            custom_prompt: 自定义提示词
            
        Returns:
            Dict[str, Any]: 批量增强结果
        """
        try:
            # 获取会议笔记
            notes = await self.note_service.get_meeting_notes(
                meeting_id=meeting_id,
                include_ai_enhanced=not only_unenhanced
            )
            
            if not notes:
                return {
                    "meeting_id": meeting_id,
                    "total_notes": 0,
                    "enhanced_count": 0,
                    "skipped_count": 0,
                    "failed_count": 0,
                    "results": []
                }
            
            # 筛选需要增强的笔记
            notes_to_enhance = []
            if only_unenhanced:
                notes_to_enhance = [n for n in notes if not n["is_ai_enhanced"]]
            else:
                notes_to_enhance = notes
            
            if not notes_to_enhance:
                return {
                    "meeting_id": meeting_id,
                    "total_notes": len(notes),
                    "enhanced_count": 0,
                    "skipped_count": len(notes),
                    "failed_count": 0,
                    "results": [],
                    "message": "所有笔记都已增强"
                }
            
            # 获取会议转录内容（一次性获取，避免重复查询）
            full_transcript = await self.transcription_service.get_full_meeting_transcript(meeting_id)
            if not full_transcript:
                raise HTTPException(status_code=400, detail="没有找到会议转录内容")
            
            # 获取模板提示
            template_prompt = None
            if use_template:
                template_prompt = await self._get_meeting_template_prompt(meeting_id)
            
            prompt_to_use = custom_prompt or template_prompt
            
            # 批量增强笔记
            results = []
            enhanced_count = 0
            failed_count = 0
            
            for note_info in notes_to_enhance:
                try:
                    # 调用AI增强
                    enhanced_content = await self.ai_service.enhance_notes(
                        original_notes=note_info["content"],
                        transcription=full_transcript,
                        template_prompt=prompt_to_use
                    )
                    
                    # 更新笔记
                    updated_note = await self._update_note_with_enhancement(
                        note_info["id"],
                        enhanced_content
                    )
                    
                    if updated_note:
                        results.append({
                            "note_id": note_info["id"],
                            "status": "success",
                            "original_length": len(note_info["content"]),
                            "enhanced_length": len(enhanced_content)
                        })
                        enhanced_count += 1
                    else:
                        results.append({
                            "note_id": note_info["id"],
                            "status": "failed",
                            "error": "更新笔记失败"
                        })
                        failed_count += 1
                        
                except Exception as e:
                    results.append({
                        "note_id": note_info["id"],
                        "status": "failed",
                        "error": str(e)
                    })
                    failed_count += 1
            
            return {
                "meeting_id": meeting_id,
                "total_notes": len(notes),
                "enhanced_count": enhanced_count,
                "skipped_count": len(notes) - len(notes_to_enhance),
                "failed_count": failed_count,
                "results": results,
                "enhancement_method": "template" if use_template else "custom",
                "template_used": template_prompt is not None
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"批量笔记增强失败: {str(e)}"
            )
    
    async def revert_note_enhancement(self, note_id: int) -> Optional[Dict[str, Any]]:
        """
        还原笔记增强，恢复到原始内容
        
        Args:
            note_id: 笔记ID
            
        Returns:
            Dict[str, Any]: 还原结果
        """
        try:
            async with AsyncSessionLocal() as session:
                note = await session.get(Note, note_id)
                if not note:
                    return None
                
                if not note.is_ai_enhanced or not note.original_content:
                    raise HTTPException(
                        status_code=400, 
                        detail="笔记未被AI增强或没有原始内容"
                    )
                
                # 恢复原始内容
                note.content = note.original_content
                note.is_ai_enhanced = False
                
                await session.commit()
                await session.refresh(note)
                
                return {
                    "id": note.id,
                    "meeting_id": note.meeting_id,
                    "content": note.content,
                    "original_content": note.original_content,
                    "is_ai_enhanced": note.is_ai_enhanced,
                    "reverted_at": note.updated_at
                }
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"还原笔记失败: {str(e)}"
            )
    
    async def compare_enhancement(self, note_id: int) -> Optional[Dict[str, Any]]:
        """
        比较笔记增强前后的内容
        
        Args:
            note_id: 笔记ID
            
        Returns:
            Dict[str, Any]: 比较结果
        """
        try:
            note_info = await self.note_service.get_note(note_id)
            if not note_info:
                return None
            
            if not note_info["is_ai_enhanced"] or not note_info["original_content"]:
                raise HTTPException(
                    status_code=400,
                    detail="笔记未被AI增强或没有原始内容可比较"
                )
            
            original = note_info["original_content"]
            enhanced = note_info["content"]
            
            return {
                "note_id": note_id,
                "original_content": original,
                "enhanced_content": enhanced,
                "original_length": len(original),
                "enhanced_length": len(enhanced),
                "length_increase": len(enhanced) - len(original),
                "length_increase_percentage": round(
                    ((len(enhanced) - len(original)) / len(original)) * 100, 2
                ) if len(original) > 0 else 0,
                "is_ai_enhanced": note_info["is_ai_enhanced"]
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"比较笔记失败: {str(e)}"
            )
    
    async def _get_meeting_template_prompt(self, meeting_id: int) -> Optional[str]:
        """获取会议模板的AI提示"""
        try:
            async with AsyncSessionLocal() as session:
                # 通过会议获取模板
                from sqlalchemy import select
                from app.models.meeting import Meeting
                
                result = await session.execute(
                    select(Meeting).where(Meeting.id == meeting_id)
                )
                meeting = result.scalar_one_or_none()
                
                if not meeting or not meeting.template_id:
                    return None
                
                template = await session.get(Template, meeting.template_id)
                if not template:
                    return None
                
                return template.prompt_template
                
        except Exception as e:
            print(f"获取模板提示失败: {e}")
            return None
    
    async def _update_note_with_enhancement(
        self, 
        note_id: int, 
        enhanced_content: str
    ) -> Optional[Dict[str, Any]]:
        """更新笔记的增强内容"""
        try:
            async with AsyncSessionLocal() as session:
                note = await session.get(Note, note_id)
                if not note:
                    return None
                
                # 保存原始内容
                if not note.original_content or note.original_content == note.content:
                    note.original_content = note.content
                
                # 更新内容
                note.content = enhanced_content
                note.is_ai_enhanced = True
                
                await session.commit()
                await session.refresh(note)
                
                return {
                    "id": note.id,
                    "content": note.content,
                    "original_content": note.original_content,
                    "is_ai_enhanced": note.is_ai_enhanced
                }
                
        except Exception as e:
            print(f"更新笔记增强内容失败: {e}")
            return None


# 全局服务实例
ai_enhancement_service: Optional[AIEnhancementService] = None


def get_ai_enhancement_service() -> AIEnhancementService:
    """获取AI增强服务实例"""
    global ai_enhancement_service
    if ai_enhancement_service is None:
        ai_enhancement_service = AIEnhancementService()
    return ai_enhancement_service