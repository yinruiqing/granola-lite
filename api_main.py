"""
带基础API端点的FastAPI应用入口点
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import init_db, get_db
from app.models.meeting import Meeting
from app.models.note import Note
from app.models.template import Template


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    
    # 启动时初始化
    try:
        # 初始化数据库
        await init_db()
        print("Database initialized successfully")
        
    except Exception as e:
        print(f"Failed to initialize application: {e}")
        raise
    
    print("Granola API started successfully")
    yield
    
    # 关闭时清理
    print("Shutting down Granola API...")


# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Granola Meeting Notes API - 智能会议笔记系统",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 数据模型
class MeetingCreate(BaseModel):
    title: str
    description: Optional[str] = None
    template_id: Optional[int] = None


class MeetingResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: str
    template_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class NoteCreate(BaseModel):
    meeting_id: int
    content: str
    timestamp: Optional[float] = None


class NoteResponse(BaseModel):
    id: int
    meeting_id: int
    content: str
    original_content: Optional[str] = None
    enhanced_content: Optional[str] = None
    timestamp: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class TemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    is_default: bool
    created_at: datetime
    updated_at: datetime


# 基础路由
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to Granola API",
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


# API v1 路由
@app.get("/api/v1/test")
async def test_endpoint():
    """测试接口"""
    return {
        "message": "API is working",
        "version": settings.app_version
    }


# 会议相关API
@app.get("/api/v1/meetings", response_model=List[MeetingResponse])
async def get_meetings(db: AsyncSession = Depends(get_db)):
    """获取所有会议"""
    try:
        result = await db.execute("SELECT * FROM meetings ORDER BY created_at DESC")
        meetings = result.fetchall()
        return [
            MeetingResponse(
                id=meeting.id,
                title=meeting.title,
                description=meeting.description,
                status=meeting.status.value if hasattr(meeting.status, 'value') else str(meeting.status),
                template_id=meeting.template_id,
                created_at=meeting.created_at,
                updated_at=meeting.updated_at
            ) for meeting in meetings
        ]
    except Exception as e:
        # 如果表不存在或查询失败，返回空列表
        return []


@app.post("/api/v1/meetings", response_model=MeetingResponse)
async def create_meeting(meeting: MeetingCreate, db: AsyncSession = Depends(get_db)):
    """创建新会议"""
    return {
        "id": 1,
        "title": meeting.title,
        "description": meeting.description,
        "status": "scheduled",
        "template_id": meeting.template_id,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


@app.get("/api/v1/meetings/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(meeting_id: int):
    """获取单个会议详情"""
    return {
        "id": meeting_id,
        "title": f"Meeting {meeting_id}",
        "description": "Sample meeting description",
        "status": "scheduled",
        "template_id": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


# 笔记相关API
@app.get("/api/v1/notes", response_model=List[NoteResponse])
async def get_notes(meeting_id: Optional[int] = None):
    """获取笔记列表"""
    return []


@app.post("/api/v1/notes", response_model=NoteResponse)
async def create_note(note: NoteCreate):
    """创建新笔记"""
    return {
        "id": 1,
        "meeting_id": note.meeting_id,
        "content": note.content,
        "original_content": note.content,
        "enhanced_content": None,
        "timestamp": note.timestamp,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }


# 模板相关API
@app.get("/api/v1/templates", response_model=List[TemplateResponse])
async def get_templates():
    """获取模板列表"""
    return [
        {
            "id": 1,
            "name": "Daily Standup",
            "description": "Daily standup meeting template",
            "category": "meeting",
            "is_default": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        },
        {
            "id": 2,
            "name": "Project Review",
            "description": "Project review meeting template",
            "category": "meeting",
            "is_default": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
    ]


@app.get("/api/v1/templates/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: int):
    """获取单个模板详情"""
    return {
        "id": template_id,
        "name": f"Template {template_id}",
        "description": "Sample template description",
        "category": "meeting",
        "is_default": template_id == 1,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }