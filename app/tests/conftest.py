"""
测试配置和fixtures
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.database import get_db, Base
from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcription import Transcription
from app.models.note import Note
from app.core.auth import get_password_hash, create_access_token
from app.core.cache import cache_manager


# 测试数据库URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# 创建测试数据库引擎
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)

# 测试数据库会话
TestingSessionLocal = sessionmaker(
    test_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_database():
    """设置测试数据库"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """提供数据库会话"""
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
async def override_get_db(db_session: AsyncSession):
    """覆盖数据库依赖"""
    async def _override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """提供测试客户端"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """创建测试用户"""
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """创建管理员用户"""
    admin = User(
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        hashed_password=get_password_hash("adminpassword"),
        is_active=True,
        is_admin=True
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
async def auth_headers(test_user: User) -> dict:
    """生成认证头"""
    access_token = create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def admin_auth_headers(admin_user: User) -> dict:
    """生成管理员认证头"""
    access_token = create_access_token(data={"sub": admin_user.email})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def test_meeting(db_session: AsyncSession, test_user: User) -> Meeting:
    """创建测试会议"""
    meeting = Meeting(
        title="Test Meeting",
        description="A test meeting for testing purposes",
        user_id=test_user.id,
        status="active"
    )
    db_session.add(meeting)
    await db_session.commit()
    await db_session.refresh(meeting)
    return meeting


@pytest.fixture
async def test_transcription(db_session: AsyncSession, test_meeting: Meeting, test_user: User) -> Transcription:
    """创建测试转录"""
    transcription = Transcription(
        meeting_id=test_meeting.id,
        user_id=test_user.id,
        text="This is a test transcription content",
        language="en",
        duration=120.5,
        confidence=0.95,
        status="completed"
    )
    db_session.add(transcription)
    await db_session.commit()
    await db_session.refresh(transcription)
    return transcription


@pytest.fixture
async def test_note(db_session: AsyncSession, test_meeting: Meeting, test_user: User) -> Note:
    """创建测试笔记"""
    note = Note(
        title="Test Note",
        content="This is a test note content",
        meeting_id=test_meeting.id,
        user_id=test_user.id,
        category="test"
    )
    db_session.add(note)
    await db_session.commit()
    await db_session.refresh(note)
    return note


@pytest.fixture(autouse=True)
async def setup_cache():
    """设置测试缓存"""
    # 使用内存缓存进行测试
    cache_manager.use_memory_cache = True
    yield
    # 清理缓存
    if hasattr(cache_manager, 'memory_cache'):
        cache_manager.memory_cache.clear()


# 测试数据工厂
class TestDataFactory:
    """测试数据工厂"""
    
    @staticmethod
    def user_data(**kwargs):
        """用户测试数据"""
        default_data = {
            "email": "factory@example.com",
            "username": "factoryuser",
            "full_name": "Factory User",
            "password": "factorypassword"
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def meeting_data(**kwargs):
        """会议测试数据"""
        default_data = {
            "title": "Factory Meeting",
            "description": "A meeting created by factory",
            "status": "active"
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def note_data(**kwargs):
        """笔记测试数据"""
        default_data = {
            "title": "Factory Note",
            "content": "A note created by factory",
            "category": "test"
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def transcription_data(**kwargs):
        """转录测试数据"""
        default_data = {
            "text": "Factory transcription content",
            "language": "en",
            "duration": 60.0,
            "confidence": 0.9,
            "status": "completed"
        }
        default_data.update(kwargs)
        return default_data


@pytest.fixture
def test_data_factory():
    """测试数据工厂fixture"""
    return TestDataFactory