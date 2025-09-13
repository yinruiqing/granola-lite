"""
数据模型测试
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcription import Transcription
from app.models.note import Note
from app.core.auth import get_password_hash


class TestUserModel:
    """用户模型测试"""
    
    @pytest.mark.asyncio
    async def test_create_user(self, db_session: AsyncSession):
        """测试创建用户"""
        user = User(
            email="model@example.com",
            username="modeluser",
            full_name="Model User",
            hashed_password=get_password_hash("password123"),
            is_active=True
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "model@example.com"
        assert user.username == "modeluser"
        assert user.is_active is True
        assert user.is_admin is False
        assert user.created_at is not None
    
    @pytest.mark.asyncio
    async def test_user_relationships(self, db_session: AsyncSession, test_user: User):
        """测试用户关联关系"""
        # 创建会议
        meeting = Meeting(
            title="Test Meeting",
            user_id=test_user.id,
            status="active"
        )
        db_session.add(meeting)
        
        # 创建转录
        transcription = Transcription(
            meeting_id=meeting.id,
            user_id=test_user.id,
            text="Test transcription",
            language="en",
            status="completed"
        )
        db_session.add(transcription)
        
        # 创建笔记
        note = Note(
            title="Test Note",
            content="Test content",
            user_id=test_user.id,
            meeting_id=meeting.id
        )
        db_session.add(note)
        
        await db_session.commit()
        
        # 测试关联关系
        await db_session.refresh(test_user)
        assert len(test_user.meetings) == 1
        assert len(test_user.notes) == 1
        assert len(test_user.transcriptions) == 1
    
    @pytest.mark.asyncio
    async def test_user_string_representation(self, test_user: User):
        """测试用户字符串表示"""
        assert str(test_user) == f"<User {test_user.username}>"


class TestMeetingModel:
    """会议模型测试"""
    
    @pytest.mark.asyncio
    async def test_create_meeting(self, db_session: AsyncSession, test_user: User):
        """测试创建会议"""
        meeting = Meeting(
            title="Model Test Meeting",
            description="A meeting for model testing",
            user_id=test_user.id,
            status="active"
        )
        
        db_session.add(meeting)
        await db_session.commit()
        await db_session.refresh(meeting)
        
        assert meeting.id is not None
        assert meeting.title == "Model Test Meeting"
        assert meeting.user_id == test_user.id
        assert meeting.status == "active"
        assert meeting.created_at is not None
    
    @pytest.mark.asyncio
    async def test_meeting_user_relationship(self, test_meeting: Meeting, test_user: User):
        """测试会议用户关联"""
        assert test_meeting.user_id == test_user.id
        assert test_meeting.user.id == test_user.id
    
    @pytest.mark.asyncio
    async def test_meeting_transcription_relationship(
        self, 
        db_session: AsyncSession,
        test_meeting: Meeting,
        test_user: User
    ):
        """测试会议转录关联"""
        transcription = Transcription(
            meeting_id=test_meeting.id,
            user_id=test_user.id,
            text="Meeting transcription",
            language="en",
            status="completed"
        )
        
        db_session.add(transcription)
        await db_session.commit()
        
        await db_session.refresh(test_meeting)
        assert test_meeting.transcription is not None
        assert test_meeting.transcription.text == "Meeting transcription"
    
    @pytest.mark.asyncio
    async def test_meeting_notes_relationship(
        self,
        db_session: AsyncSession,
        test_meeting: Meeting,
        test_user: User
    ):
        """测试会议笔记关联"""
        note1 = Note(
            title="Note 1",
            content="Content 1",
            meeting_id=test_meeting.id,
            user_id=test_user.id
        )
        
        note2 = Note(
            title="Note 2", 
            content="Content 2",
            meeting_id=test_meeting.id,
            user_id=test_user.id
        )
        
        db_session.add_all([note1, note2])
        await db_session.commit()
        
        await db_session.refresh(test_meeting)
        assert len(test_meeting.notes) == 2


class TestTranscriptionModel:
    """转录模型测试"""
    
    @pytest.mark.asyncio
    async def test_create_transcription(
        self,
        db_session: AsyncSession,
        test_meeting: Meeting,
        test_user: User
    ):
        """测试创建转录"""
        transcription = Transcription(
            meeting_id=test_meeting.id,
            user_id=test_user.id,
            text="This is a test transcription",
            language="en",
            duration=300.5,
            confidence=0.95,
            status="completed"
        )
        
        db_session.add(transcription)
        await db_session.commit()
        await db_session.refresh(transcription)
        
        assert transcription.id is not None
        assert transcription.meeting_id == test_meeting.id
        assert transcription.user_id == test_user.id
        assert transcription.text == "This is a test transcription"
        assert transcription.language == "en"
        assert transcription.duration == 300.5
        assert transcription.confidence == 0.95
        assert transcription.status == "completed"
    
    @pytest.mark.asyncio
    async def test_transcription_relationships(self, test_transcription: Transcription):
        """测试转录关联关系"""
        assert test_transcription.meeting is not None
        assert test_transcription.user is not None
        assert test_transcription.meeting.title == "Test Meeting"
        assert test_transcription.user.email == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_transcription_segments(
        self,
        db_session: AsyncSession,
        test_meeting: Meeting,
        test_user: User
    ):
        """测试转录片段"""
        segments = [
            {"start_time": 0.0, "end_time": 5.0, "text": "Hello world"},
            {"start_time": 5.0, "end_time": 10.0, "text": "This is a test"}
        ]
        
        transcription = Transcription(
            meeting_id=test_meeting.id,
            user_id=test_user.id,
            text="Hello world This is a test",
            language="en",
            segments=segments,
            status="completed"
        )
        
        db_session.add(transcription)
        await db_session.commit()
        await db_session.refresh(transcription)
        
        assert transcription.segments == segments
        assert len(transcription.segments) == 2


class TestNoteModel:
    """笔记模型测试"""
    
    @pytest.mark.asyncio
    async def test_create_note(
        self,
        db_session: AsyncSession,
        test_meeting: Meeting,
        test_user: User
    ):
        """测试创建笔记"""
        note = Note(
            title="Model Test Note",
            content="This is a note content for model testing",
            meeting_id=test_meeting.id,
            user_id=test_user.id,
            category="test"
        )
        
        db_session.add(note)
        await db_session.commit()
        await db_session.refresh(note)
        
        assert note.id is not None
        assert note.title == "Model Test Note"
        assert note.content == "This is a note content for model testing"
        assert note.meeting_id == test_meeting.id
        assert note.user_id == test_user.id
        assert note.category == "test"
        assert note.created_at is not None
    
    @pytest.mark.asyncio
    async def test_note_relationships(self, test_note: Note):
        """测试笔记关联关系"""
        assert test_note.meeting is not None
        assert test_note.user is not None
        assert test_note.meeting.title == "Test Meeting"
        assert test_note.user.email == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_note_without_meeting(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """测试不关联会议的笔记"""
        note = Note(
            title="Standalone Note",
            content="A note without meeting",
            user_id=test_user.id,
            category="standalone"
        )
        
        db_session.add(note)
        await db_session.commit()
        await db_session.refresh(note)
        
        assert note.meeting_id is None
        assert note.meeting is None
        assert note.user is not None
    
    @pytest.mark.asyncio
    async def test_note_auto_timestamps(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """测试笔记自动时间戳"""
        note = Note(
            title="Timestamp Test",
            content="Testing timestamps",
            user_id=test_user.id
        )
        
        db_session.add(note)
        await db_session.commit()
        await db_session.refresh(note)
        
        original_created = note.created_at
        assert original_created is not None
        assert note.updated_at is None
        
        # 更新笔记
        note.content = "Updated content"
        await db_session.commit()
        await db_session.refresh(note)
        
        assert note.created_at == original_created
        assert note.updated_at is not None
        assert note.updated_at > original_created


class TestModelConstraints:
    """模型约束测试"""
    
    @pytest.mark.asyncio
    async def test_user_email_unique_constraint(self, db_session: AsyncSession, test_user: User):
        """测试用户邮箱唯一约束"""
        duplicate_user = User(
            email=test_user.email,  # 重复邮箱
            username="duplicate",
            full_name="Duplicate User",
            hashed_password=get_password_hash("password")
        )
        
        db_session.add(duplicate_user)
        
        with pytest.raises(Exception):  # 应该抛出完整性约束异常
            await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_meeting_requires_user(self, db_session: AsyncSession):
        """测试会议需要用户"""
        meeting = Meeting(
            title="Meeting without user",
            user_id=99999  # 不存在的用户ID
        )
        
        db_session.add(meeting)
        
        with pytest.raises(Exception):  # 应该抛出外键约束异常
            await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_note_requires_user(self, db_session: AsyncSession):
        """测试笔记需要用户"""
        note = Note(
            title="Note without user",
            content="Content",
            user_id=99999  # 不存在的用户ID
        )
        
        db_session.add(note)
        
        with pytest.raises(Exception):  # 应该抛出外键约束异常
            await db_session.commit()