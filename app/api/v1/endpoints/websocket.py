"""
WebSocket端点
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional
import asyncio

from app.core.websocket import connection_manager
from app.core.events import event_emitter, Events
from loguru import logger

router = APIRouter()


async def handle_transcription_message(connection_id: str, data: dict):
    """处理转录相关消息"""
    message_type = data.get('action')
    meeting_id = data.get('meeting_id')
    
    if not meeting_id:
        await connection_manager.send_personal_message(connection_id, {
            'type': 'error',
            'message': 'meeting_id is required'
        })
        return
    
    if message_type == 'start_recording':
        # 开始录音
        await connection_manager.broadcast_to_room(f"meeting_{meeting_id}", {
            'type': 'recording_started',
            'meeting_id': meeting_id,
            'started_by': connection_manager.get_connection_info(connection_id)
        })
        
    elif message_type == 'stop_recording':
        # 停止录音
        await connection_manager.broadcast_to_room(f"meeting_{meeting_id}", {
            'type': 'recording_stopped',
            'meeting_id': meeting_id,
            'stopped_by': connection_manager.get_connection_info(connection_id)
        })
        
    elif message_type == 'audio_chunk':
        # 实时音频数据（这里可以集成实时转录）
        audio_data = data.get('audio_data')
        if audio_data:
            # 广播音频数据到房间内其他用户（如果需要）
            await connection_manager.broadcast_to_room(f"meeting_{meeting_id}", {
                'type': 'audio_chunk_received',
                'meeting_id': meeting_id,
                'from_connection': connection_id
            }, exclude=[connection_id])


async def handle_chat_message(connection_id: str, data: dict):
    """处理聊天消息"""
    meeting_id = data.get('meeting_id')
    message = data.get('message')
    
    if not meeting_id or not message:
        await connection_manager.send_personal_message(connection_id, {
            'type': 'error',
            'message': 'meeting_id and message are required'
        })
        return
    
    # 广播聊天消息
    user_info = connection_manager.get_connection_info(connection_id)
    await connection_manager.broadcast_to_room(f"meeting_{meeting_id}", {
        'type': 'chat_message',
        'meeting_id': meeting_id,
        'message': message,
        'from_user': user_info.get('user_id'),
        'from_connection': connection_id,
        'timestamp': data.get('timestamp')
    })


async def handle_cursor_position(connection_id: str, data: dict):
    """处理光标位置同步"""
    meeting_id = data.get('meeting_id')
    position = data.get('position')
    
    if not meeting_id or position is None:
        return
    
    # 广播光标位置到其他用户
    user_info = connection_manager.get_connection_info(connection_id)
    await connection_manager.broadcast_to_room(f"meeting_{meeting_id}", {
        'type': 'cursor_position',
        'meeting_id': meeting_id,
        'position': position,
        'from_user': user_info.get('user_id'),
        'from_connection': connection_id
    }, exclude=[connection_id])


async def handle_note_sync(connection_id: str, data: dict):
    """处理笔记同步"""
    meeting_id = data.get('meeting_id')
    note_data = data.get('note_data')
    action = data.get('action')  # create, update, delete
    
    if not meeting_id or not note_data:
        return
    
    user_info = connection_manager.get_connection_info(connection_id)
    
    # 广播笔记变更到其他用户
    await connection_manager.broadcast_to_room(f"meeting_{meeting_id}", {
        'type': 'note_sync',
        'meeting_id': meeting_id,
        'action': action,
        'note_data': note_data,
        'from_user': user_info.get('user_id'),
        'from_connection': connection_id
    }, exclude=[connection_id])


# 注册消息处理器
connection_manager.register_handler('transcription', handle_transcription_message)
connection_manager.register_handler('chat', handle_chat_message)
connection_manager.register_handler('cursor', handle_cursor_position)
connection_manager.register_handler('note_sync', handle_note_sync)


@router.websocket("/ws/{meeting_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    meeting_id: int,
    user_id: Optional[int] = Query(None)
):
    """
    WebSocket连接端点
    
    - **meeting_id**: 会议ID
    - **user_id**: 用户ID（可选）
    """
    connection_id = None
    
    try:
        # 建立连接
        connection_id = await connection_manager.connect(
            websocket, user_id=user_id, meeting_id=meeting_id
        )
        
        # 发射连接事件
        await event_emitter.emit(Events.USER_LOGIN, {
            'user_id': user_id,
            'meeting_id': meeting_id,
            'connection_id': connection_id
        })
        
        # 持续监听消息
        while True:
            try:
                # 接收消息
                message = await websocket.receive_text()
                
                # 处理消息
                await connection_manager.handle_message(connection_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket正常断开: {connection_id}")
                break
            except Exception as e:
                logger.error(f"处理WebSocket消息时出错: {e}")
                await connection_manager.send_personal_message(connection_id, {
                    'type': 'error',
                    'message': str(e)
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket连接出错: {e}")
    finally:
        # 清理连接
        if connection_id:
            await connection_manager.disconnect(connection_id)
            
            # 发射断开连接事件
            await event_emitter.emit(Events.USER_LOGOUT, {
                'user_id': user_id,
                'meeting_id': meeting_id,
                'connection_id': connection_id
            })


@router.get("/ws/stats")
async def websocket_stats():
    """获取WebSocket统计信息"""
    return {
        'active_connections': connection_manager.get_connection_count(),
        'active_rooms': connection_manager.get_room_count(),
        'rooms': {
            room_id: len(connections) 
            for room_id, connections in connection_manager.rooms.items()
        }
    }


@router.post("/ws/broadcast/{meeting_id}")
async def broadcast_to_meeting(meeting_id: int, message: dict):
    """向指定会议广播消息（用于服务端推送）"""
    room_id = f"meeting_{meeting_id}"
    sent_count = await connection_manager.broadcast_to_room(room_id, {
        'type': 'server_broadcast',
        'meeting_id': meeting_id,
        'data': message
    })
    
    return {
        'success': True,
        'sent_count': sent_count,
        'room_id': room_id
    }


@router.post("/ws/notify/{connection_id}")
async def notify_connection(connection_id: str, message: dict):
    """向指定连接发送通知"""
    success = await connection_manager.send_personal_message(connection_id, {
        'type': 'notification',
        'data': message
    })
    
    return {
        'success': success,
        'connection_id': connection_id
    }