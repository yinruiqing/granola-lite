"""
AI对话服务
基于会议内容进行智能问答
"""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException

from app.services.ai.ai_service import get_ai_service
from app.services.transcription import get_transcription_service
from app.services.note import get_note_service
from app.models.conversation import Conversation
from app.models.meeting import Meeting
from app.db.session import AsyncSessionLocal
from sqlalchemy import select


class ConversationService:
    """AI对话服务"""
    
    def __init__(self):
        self.ai_service = get_ai_service()
        self.transcription_service = get_transcription_service()
        self.note_service = get_note_service()
    
    async def ask_question(
        self,
        meeting_id: int,
        question: str,
        include_notes: bool = True,
        include_transcripts: bool = True,
        context_limit: int = 8000
    ) -> Dict[str, Any]:
        """
        基于会议内容回答问题
        
        Args:
            meeting_id: 会议ID
            question: 用户问题
            include_notes: 是否包含笔记内容
            include_transcripts: 是否包含转录内容
            context_limit: 上下文长度限制
            
        Returns:
            Dict[str, Any]: 问答结果
        """
        try:
            # 验证会议是否存在
            async with AsyncSessionLocal() as session:
                meeting = await session.get(Meeting, meeting_id)
                if not meeting:
                    raise HTTPException(status_code=404, detail="会议不存在")
            
            # 构建上下文
            context_parts = []
            
            if include_transcripts:
                # 获取转录内容
                transcripts = await self.transcription_service.get_meeting_transcriptions(meeting_id)
                if transcripts:
                    transcript_text = "\n".join([
                        f"[{t.get('speaker', '发言人')}] {t['content']}" 
                        for t in transcripts
                    ])
                    context_parts.append(f"## 会议转录\n{transcript_text}")
            
            if include_notes:
                # 获取笔记内容
                notes = await self.note_service.get_meeting_notes(meeting_id)
                if notes:
                    notes_text = "\n".join([
                        f"• {note['content']}" 
                        for note in notes
                    ])
                    context_parts.append(f"## 会议笔记\n{notes_text}")
            
            # 合并上下文
            full_context = "\n\n".join(context_parts)
            
            if not full_context:
                raise HTTPException(
                    status_code=400,
                    detail="没有找到相关会议内容，无法回答问题"
                )
            
            # 限制上下文长度
            if len(full_context) > context_limit:
                full_context = full_context[:context_limit] + "...\n[内容已截断]"
            
            # 调用AI服务回答问题
            answer = await self.ai_service.answer_question(
                question=question,
                context=full_context
            )
            
            # 保存对话记录
            async with AsyncSessionLocal() as session:
                conversation = Conversation(
                    meeting_id=meeting_id,
                    question=question,
                    answer=answer,
                    context_used=full_context[:1000] + "..." if len(full_context) > 1000 else full_context,
                    model_used=self.ai_service.llm_provider.config.get("model", "unknown")
                )
                
                session.add(conversation)
                await session.commit()
                await session.refresh(conversation)
                
                return {
                    "conversation_id": conversation.id,
                    "meeting_id": meeting_id,
                    "question": question,
                    "answer": answer,
                    "context_summary": {
                        "included_notes": include_notes and bool(notes),
                        "included_transcripts": include_transcripts and bool(transcripts),
                        "context_length": len(full_context),
                        "context_truncated": len(full_context) >= context_limit
                    },
                    "model_used": conversation.model_used,
                    "created_at": conversation.created_at
                }
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"问答处理失败: {str(e)}"
            )
    
    async def get_conversation(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """获取单个对话记录"""
        try:
            async with AsyncSessionLocal() as session:
                conversation = await session.get(Conversation, conversation_id)
                
                if not conversation:
                    return None
                
                return {
                    "id": conversation.id,
                    "meeting_id": conversation.meeting_id,
                    "question": conversation.question,
                    "answer": conversation.answer,
                    "context_used": conversation.context_used,
                    "model_used": conversation.model_used,
                    "created_at": conversation.created_at
                }
                
        except Exception as e:
            print(f"获取对话记录失败: {e}")
            return None
    
    async def get_meeting_conversations(
        self,
        meeting_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        获取会议的对话历史
        
        Args:
            meeting_id: 会议ID
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            Dict[str, Any]: 对话列表
        """
        try:
            async with AsyncSessionLocal() as session:
                # 获取总数
                count_result = await session.execute(
                    select(Conversation.id).where(Conversation.meeting_id == meeting_id)
                )
                total = len(count_result.fetchall())
                
                # 分页查询
                query = select(Conversation).where(
                    Conversation.meeting_id == meeting_id
                ).order_by(
                    Conversation.created_at.desc()
                ).limit(limit).offset(offset)
                
                result = await session.execute(query)
                conversations = result.scalars().all()
                
                return {
                    "conversations": [
                        {
                            "id": c.id,
                            "question": c.question,
                            "answer": c.answer,
                            "model_used": c.model_used,
                            "created_at": c.created_at
                        }
                        for c in conversations
                    ],
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(conversations) < total
                }
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"获取对话历史失败: {str(e)}"
            )
    
    async def delete_conversation(self, conversation_id: int) -> bool:
        """删除对话记录"""
        try:
            async with AsyncSessionLocal() as session:
                conversation = await session.get(Conversation, conversation_id)
                
                if not conversation:
                    return False
                
                await session.delete(conversation)
                await session.commit()
                return True
                
        except Exception as e:
            print(f"删除对话记录失败: {e}")
            return False
    
    async def get_suggested_questions(
        self,
        meeting_id: int,
        question_count: int = 5
    ) -> List[str]:
        """
        基于会议内容生成建议问题
        
        Args:
            meeting_id: 会议ID
            question_count: 建议问题数量
            
        Returns:
            List[str]: 建议问题列表
        """
        try:
            # 获取会议内容摘要
            context_parts = []
            
            # 获取转录内容（取前1000字符作为摘要）
            transcripts = await self.transcription_service.get_meeting_transcriptions(meeting_id)
            if transcripts:
                transcript_summary = " ".join([
                    t['content'] for t in transcripts[:3]  # 取前3条转录
                ])[:1000]
                context_parts.append(f"转录摘要：{transcript_summary}")
            
            # 获取笔记内容
            notes = await self.note_service.get_meeting_notes(meeting_id)
            if notes:
                notes_summary = " ".join([
                    note['content'] for note in notes[:5]  # 取前5条笔记
                ])[:500]
                context_parts.append(f"笔记摘要：{notes_summary}")
            
            if not context_parts:
                return []
            
            context = "\n\n".join(context_parts)
            
            # 生成建议问题的提示
            suggestion_prompt = f"""
基于以下会议内容，请生成{question_count}个有价值的问题，这些问题应该：
1. 针对会议的核心内容
2. 能够帮助理解重要决策或讨论要点
3. 涵盖不同的方面（如决策、行动项、技术细节、时间安排等）

会议内容：
{context}

请直接返回{question_count}个问题，每个问题占一行，不需要编号。
"""
            
            messages = [
                {"role": "user", "content": suggestion_prompt}
            ]
            
            response = await self.ai_service.chat_completion(
                messages=messages,
                temperature=0.7
            )
            
            # 解析生成的问题
            questions = [
                q.strip() 
                for q in response.content.split('\n') 
                if q.strip() and not q.strip().startswith('#')
            ]
            
            return questions[:question_count]
            
        except Exception as e:
            print(f"生成建议问题失败: {e}")
            return []
    
    async def batch_ask_questions(
        self,
        meeting_id: int,
        questions: List[str],
        include_notes: bool = True,
        include_transcripts: bool = True
    ) -> Dict[str, Any]:
        """
        批量提问
        
        Args:
            meeting_id: 会议ID
            questions: 问题列表
            include_notes: 是否包含笔记
            include_transcripts: 是否包含转录
            
        Returns:
            Dict[str, Any]: 批量问答结果
        """
        results = []
        failed = []
        
        for question in questions:
            try:
                result = await self.ask_question(
                    meeting_id=meeting_id,
                    question=question,
                    include_notes=include_notes,
                    include_transcripts=include_transcripts
                )
                results.append(result)
            except Exception as e:
                failed.append({
                    "question": question,
                    "error": str(e)
                })
        
        return {
            "meeting_id": meeting_id,
            "total_questions": len(questions),
            "successful_count": len(results),
            "failed_count": len(failed),
            "results": results,
            "failed": failed
        }
    
    async def search_conversations(
        self,
        meeting_id: Optional[int] = None,
        keyword: str = "",
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        搜索对话记录
        
        Args:
            meeting_id: 会议ID筛选
            keyword: 搜索关键词
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            Dict[str, Any]: 搜索结果
        """
        try:
            async with AsyncSessionLocal() as session:
                query = select(Conversation)
                
                # 添加筛选条件
                conditions = []
                if meeting_id is not None:
                    conditions.append(Conversation.meeting_id == meeting_id)
                
                if keyword:
                    from sqlalchemy import or_
                    conditions.append(
                        or_(
                            Conversation.question.contains(keyword),
                            Conversation.answer.contains(keyword)
                        )
                    )
                
                if conditions:
                    query = query.where(*conditions)
                
                # 获取总数
                count_query = select(Conversation.id).select_from(query.subquery())
                total_result = await session.execute(count_query)
                total = len(total_result.fetchall())
                
                # 分页查询
                query = query.order_by(Conversation.created_at.desc()).limit(limit).offset(offset)
                result = await session.execute(query)
                conversations = result.scalars().all()
                
                return {
                    "conversations": [
                        {
                            "id": c.id,
                            "meeting_id": c.meeting_id,
                            "question": c.question,
                            "answer": c.answer,
                            "model_used": c.model_used,
                            "created_at": c.created_at
                        }
                        for c in conversations
                    ],
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(conversations) < total
                }
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"搜索对话记录失败: {str(e)}"
            )


# 全局服务实例
conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """获取对话服务实例"""
    global conversation_service
    if conversation_service is None:
        conversation_service = ConversationService()
    return conversation_service