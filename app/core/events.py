"""
应用事件系统
"""

from typing import Dict, Any, Callable, List
import asyncio
from datetime import datetime
from loguru import logger


class EventEmitter:
    """事件发射器"""
    
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
        self._middleware: List[Callable] = []
    
    def on(self, event: str, handler: Callable):
        """注册事件监听器"""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(handler)
    
    def off(self, event: str, handler: Callable):
        """移除事件监听器"""
        if event in self._listeners:
            try:
                self._listeners[event].remove(handler)
            except ValueError:
                pass
    
    def use(self, middleware: Callable):
        """添加中间件"""
        self._middleware.append(middleware)
    
    async def emit(self, event: str, data: Any = None, **kwargs):
        """发射事件"""
        event_data = {
            'event': event,
            'data': data,
            'timestamp': datetime.now(),
            **kwargs
        }
        
        # 执行中间件
        for middleware in self._middleware:
            try:
                if asyncio.iscoroutinefunction(middleware):
                    event_data = await middleware(event_data)
                else:
                    event_data = middleware(event_data)
                
                if event_data is None:
                    return  # 中间件阻止了事件
            except Exception as e:
                logger.error(f"Event middleware error: {e}")
                continue
        
        # 触发监听器
        if event in self._listeners:
            for handler in self._listeners[event]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event_data)
                    else:
                        handler(event_data)
                except Exception as e:
                    logger.error(f"Event handler error for '{event}': {e}")


# 全局事件发射器
event_emitter = EventEmitter()


# 事件类型常量
class Events:
    # 会议事件
    MEETING_CREATED = "meeting.created"
    MEETING_STARTED = "meeting.started"
    MEETING_ENDED = "meeting.ended"
    MEETING_DELETED = "meeting.deleted"
    
    # 音频事件
    AUDIO_UPLOADED = "audio.uploaded"
    AUDIO_TRANSCRIBED = "audio.transcribed"
    
    # 笔记事件
    NOTE_CREATED = "note.created"
    NOTE_UPDATED = "note.updated"
    NOTE_AI_ENHANCED = "note.ai_enhanced"
    
    # AI事件
    AI_CHAT_MESSAGE = "ai.chat_message"
    AI_ENHANCEMENT_REQUEST = "ai.enhancement_request"
    AI_REQUEST_SUCCESS = "ai.request_success"
    AI_REQUEST_FAILED = "ai.request_failed"
    
    # 任务事件
    TASK_SUCCESS = "task.success"
    TASK_FAILURE = "task.failure"
    TASK_RETRY = "task.retry"
    
    # 系统事件
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    SYSTEM_ERROR = "system.error"
    SYSTEM_ALERT = "system.alert"
    MEETING_REMINDER_SENT = "meeting.reminder_sent"


def log_middleware(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """日志中间件"""
    logger.info(f"Event: {event_data['event']}", extra={
        'event_type': event_data['event'],
        'timestamp': event_data['timestamp'],
        'data_keys': list(event_data.get('data', {}).keys()) if isinstance(event_data.get('data'), dict) else None
    })
    return event_data


# 添加默认中间件
event_emitter.use(log_middleware)