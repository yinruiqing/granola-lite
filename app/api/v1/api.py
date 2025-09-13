"""
API v1路由汇总
"""

from fastapi import APIRouter

from app.api.v1.endpoints import audio, transcriptions, notes, ai_enhancement, templates, conversations, meetings, websocket, auth, files, ai_service, cache, tasks, monitoring, data_management, performance, security

api_router = APIRouter()

# 包含所有端点路由
api_router.include_router(audio.router, prefix="/audio", tags=["audio"])
api_router.include_router(transcriptions.router, prefix="/transcriptions", tags=["transcriptions"])
api_router.include_router(notes.router, prefix="/notes", tags=["notes"])
api_router.include_router(ai_enhancement.router, prefix="/ai", tags=["ai-enhancement"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(meetings.router, prefix="/meetings", tags=["meetings"])
api_router.include_router(websocket.router, prefix="/realtime", tags=["websocket"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(files.router, prefix="/files", tags=["file-storage"])
api_router.include_router(ai_service.router, prefix="/ai-service", tags=["ai-service"])
api_router.include_router(cache.router, prefix="/cache", tags=["cache"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["task-queue"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(data_management.router, prefix="/data", tags=["data-management"])
api_router.include_router(performance.router, prefix="/performance", tags=["performance"])
api_router.include_router(security.router, prefix="/security", tags=["security"])