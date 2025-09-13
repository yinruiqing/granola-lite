"""
WebSocket连接管理器
"""

import asyncio
import json
import uuid
from typing import Dict, List, Set, Optional, Any, Callable
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from app.core.events import event_emitter, Events


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 活跃连接：connection_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        
        # 房间管理：room_id -> Set[connection_id]
        self.rooms: Dict[str, Set[str]] = {}
        
        # 连接元数据：connection_id -> metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
        # 消息处理器
        self.message_handlers: Dict[str, Callable] = {}
        
        # 心跳检测
        self.heartbeat_interval = 30  # 30秒
        self.heartbeat_task: Optional[asyncio.Task] = None
        
    def register_handler(self, message_type: str, handler: Callable):
        """注册消息处理器"""
        self.message_handlers[message_type] = handler
        
    async def connect(self, websocket: WebSocket, user_id: Optional[int] = None, 
                     meeting_id: Optional[int] = None) -> str:
        """接受WebSocket连接"""
        await websocket.accept()
        
        # 生成连接ID
        connection_id = str(uuid.uuid4())
        
        # 存储连接
        self.active_connections[connection_id] = websocket
        
        # 存储连接元数据
        self.connection_metadata[connection_id] = {
            'user_id': user_id,
            'meeting_id': meeting_id,
            'connected_at': datetime.now(),
            'last_ping': datetime.now()
        }
        
        # 如果有会议ID，加入会议房间
        if meeting_id:
            await self.join_room(connection_id, f"meeting_{meeting_id}")
            
        # 启动心跳检测（如果还没启动）
        if not self.heartbeat_task:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
        logger.info(f"WebSocket连接已建立: {connection_id}, 用户: {user_id}, 会议: {meeting_id}")
        
        # 发送连接成功消息
        await self.send_personal_message(connection_id, {
            'type': 'connection_established',
            'connection_id': connection_id,
            'timestamp': datetime.now().isoformat()
        })
        
        return connection_id
        
    async def disconnect(self, connection_id: str):
        """断开WebSocket连接"""
        if connection_id in self.active_connections:
            # 从所有房间中移除
            for room_id in list(self.rooms.keys()):
                if connection_id in self.rooms[room_id]:
                    await self.leave_room(connection_id, room_id)
                    
            # 清理连接数据
            del self.active_connections[connection_id]
            
            if connection_id in self.connection_metadata:
                metadata = self.connection_metadata[connection_id]
                del self.connection_metadata[connection_id]
                
                logger.info(f"WebSocket连接已断开: {connection_id}, 用户: {metadata.get('user_id')}")
                
        # 如果没有活跃连接，停止心跳检测
        if not self.active_connections and self.heartbeat_task:
            self.heartbeat_task.cancel()
            self.heartbeat_task = None
            
    async def join_room(self, connection_id: str, room_id: str):
        """加入房间"""
        if connection_id not in self.active_connections:
            return False
            
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
            
        self.rooms[room_id].add(connection_id)
        
        # 通知房间内其他用户
        await self.broadcast_to_room(room_id, {
            'type': 'user_joined',
            'connection_id': connection_id,
            'user_id': self.connection_metadata.get(connection_id, {}).get('user_id'),
            'timestamp': datetime.now().isoformat()
        }, exclude=[connection_id])
        
        logger.info(f"连接 {connection_id} 加入房间 {room_id}")
        return True
        
    async def leave_room(self, connection_id: str, room_id: str):
        """离开房间"""
        if room_id in self.rooms and connection_id in self.rooms[room_id]:
            self.rooms[room_id].remove(connection_id)
            
            # 如果房间为空，删除房间
            if not self.rooms[room_id]:
                del self.rooms[room_id]
            else:
                # 通知房间内其他用户
                await self.broadcast_to_room(room_id, {
                    'type': 'user_left',
                    'connection_id': connection_id,
                    'user_id': self.connection_metadata.get(connection_id, {}).get('user_id'),
                    'timestamp': datetime.now().isoformat()
                })
                
            logger.info(f"连接 {connection_id} 离开房间 {room_id}")
            
    async def send_personal_message(self, connection_id: str, message: Dict[str, Any]):
        """发送个人消息"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message, default=str))
                return True
            except Exception as e:
                logger.error(f"发送个人消息失败 {connection_id}: {e}")
                await self.disconnect(connection_id)
                return False
        return False
        
    async def broadcast_to_room(self, room_id: str, message: Dict[str, Any], 
                              exclude: List[str] = None):
        """向房间广播消息"""
        if room_id not in self.rooms:
            return 0
            
        exclude = exclude or []
        sent_count = 0
        failed_connections = []
        
        for connection_id in self.rooms[room_id]:
            if connection_id not in exclude:
                success = await self.send_personal_message(connection_id, message)
                if success:
                    sent_count += 1
                else:
                    failed_connections.append(connection_id)
                    
        # 清理失败的连接
        for connection_id in failed_connections:
            await self.disconnect(connection_id)
            
        return sent_count
        
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """向所有连接广播消息"""
        sent_count = 0
        failed_connections = []
        
        for connection_id in list(self.active_connections.keys()):
            success = await self.send_personal_message(connection_id, message)
            if success:
                sent_count += 1
            else:
                failed_connections.append(connection_id)
                
        # 清理失败的连接
        for connection_id in failed_connections:
            await self.disconnect(connection_id)
            
        return sent_count
        
    async def handle_message(self, connection_id: str, message: str):
        """处理接收到的消息"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            # 更新最后活跃时间
            if connection_id in self.connection_metadata:
                self.connection_metadata[connection_id]['last_ping'] = datetime.now()
                
            # 处理ping消息
            if message_type == 'ping':
                await self.send_personal_message(connection_id, {
                    'type': 'pong',
                    'timestamp': datetime.now().isoformat()
                })
                return
                
            # 调用注册的处理器
            if message_type in self.message_handlers:
                handler = self.message_handlers[message_type]
                await handler(connection_id, data)
            else:
                logger.warning(f"未知消息类型: {message_type}")
                await self.send_personal_message(connection_id, {
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                })
                
        except json.JSONDecodeError:
            logger.error(f"无效的JSON消息: {message}")
            await self.send_personal_message(connection_id, {
                'type': 'error',
                'message': 'Invalid JSON format'
            })
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
            await self.send_personal_message(connection_id, {
                'type': 'error',
                'message': 'Internal server error'
            })
            
    async def _heartbeat_loop(self):
        """心跳检测循环"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                current_time = datetime.now()
                timeout_connections = []
                
                # 检查超时的连接
                for connection_id, metadata in self.connection_metadata.items():
                    last_ping = metadata['last_ping']
                    if (current_time - last_ping).seconds > self.heartbeat_interval * 2:
                        timeout_connections.append(connection_id)
                        
                # 断开超时连接
                for connection_id in timeout_connections:
                    logger.info(f"连接超时，断开连接: {connection_id}")
                    await self.disconnect(connection_id)
                    
                # 向活跃连接发送心跳
                for connection_id in list(self.active_connections.keys()):
                    await self.send_personal_message(connection_id, {
                        'type': 'heartbeat',
                        'timestamp': current_time.isoformat()
                    })
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳检测循环出错: {e}")
                
    def get_room_connections(self, room_id: str) -> List[str]:
        """获取房间内的连接列表"""
        return list(self.rooms.get(room_id, set()))
        
    def get_connection_count(self) -> int:
        """获取活跃连接数"""
        return len(self.active_connections)
        
    def get_room_count(self) -> int:
        """获取房间数"""
        return len(self.rooms)
        
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """获取连接信息"""
        return self.connection_metadata.get(connection_id)


# 全局连接管理器实例
connection_manager = ConnectionManager()


# 注册事件处理器
@event_emitter.on(Events.AUDIO_TRANSCRIBED)
async def on_audio_transcribed(event_data):
    """音频转录完成时的处理器"""
    meeting_id = event_data['data']['meeting_id']
    room_id = f"meeting_{meeting_id}"
    
    await connection_manager.broadcast_to_room(room_id, {
        'type': 'transcription_complete',
        'meeting_id': meeting_id,
        'transcription_id': event_data['data']['transcription_id'],
        'timestamp': datetime.now().isoformat()
    })


@event_emitter.on(Events.NOTE_CREATED)
async def on_note_created(event_data):
    """笔记创建时的处理器"""
    meeting_id = event_data['data'].get('meeting_id')
    if meeting_id:
        room_id = f"meeting_{meeting_id}"
        
        await connection_manager.broadcast_to_room(room_id, {
            'type': 'note_created',
            'meeting_id': meeting_id,
            'note_id': event_data['data']['note_id'],
            'timestamp': datetime.now().isoformat()
        })