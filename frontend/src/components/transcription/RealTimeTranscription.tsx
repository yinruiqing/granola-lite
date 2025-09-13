'use client';

import { useState, useEffect, useRef } from 'react';
import { Wifi, WifiOff, Volume2, User, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { wsManager, WebSocketStatus, TranscriptionResult } from '@/lib/websocket';
import { useAppStore } from '@/lib/store';
import { storageManager } from '@/lib/storage';

interface RealTimeTranscriptionProps {
  meetingId: number;
  isActive: boolean;
}

interface TranscriptionMessage {
  id: string;
  text: string;
  speaker?: string;
  timestamp: number;
  isFinal: boolean;
  createdAt: Date;
}

export function RealTimeTranscription({ meetingId, isActive }: RealTimeTranscriptionProps) {
  const { addTranscription } = useAppStore();
  const [status, setStatus] = useState<WebSocketStatus>('disconnected');
  const [messages, setMessages] = useState<TranscriptionMessage[]>([]);
  const [currentMessage, setCurrentMessage] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // 滚动到底部
  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  };

  // 处理转录结果
  const handleTranscription = async (result: TranscriptionResult) => {
    const messageId = `${Date.now()}-${Math.random()}`;
    
    if (result.is_final) {
      // 最终结果，保存到数据库
      try {
        const transcription = await storageManager.createTranscription({
          meeting_id: meetingId,
          content: result.text,
          language: 'zh',
          speaker: result.speaker,
          timestamp: result.timestamp,
        });
        
        addTranscription(transcription);
        
        // 添加到消息列表
        const finalMessage: TranscriptionMessage = {
          id: messageId,
          text: result.text,
          speaker: result.speaker,
          timestamp: result.timestamp,
          isFinal: true,
          createdAt: new Date(),
        };
        
        setMessages(prev => [...prev, finalMessage]);
        setCurrentMessage('');
        
      } catch (error) {
        console.error('保存转录失败:', error);
        setError('保存转录失败');
      }
    } else {
      // 临时结果，显示在当前消息中
      setCurrentMessage(result.text);
    }
    
    setTimeout(scrollToBottom, 100);
  };

  // 处理WebSocket状态变化
  const handleStatusChange = (newStatus: WebSocketStatus) => {
    setStatus(newStatus);
    
    if (newStatus === 'connected') {
      setError(null);
      // 连接成功后初始化转录
      wsManager.initTranscription(16000, 'zh');
    } else if (newStatus === 'error') {
      setError('WebSocket连接错误');
    }
  };

  // 处理错误
  const handleError = (errorMessage: string) => {
    setError(errorMessage);
    console.error('转录错误:', errorMessage);
  };

  // 连接WebSocket
  const connectWebSocket = () => {
    if (isActive && meetingId) {
      wsManager.connect(meetingId, {
        onTranscription: handleTranscription,
        onStatusChange: handleStatusChange,
        onError: handleError,
      });
    }
  };

  // 断开WebSocket
  const disconnectWebSocket = () => {
    wsManager.disconnect();
    setStatus('disconnected');
    setCurrentMessage('');
  };

  // 重连逻辑
  const attemptReconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    reconnectTimeoutRef.current = setTimeout(() => {
      if (isActive && status === 'disconnected') {
        connectWebSocket();
      }
    }, 3000);
  };

  // 格式化时间
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  // 获取说话人头像
  const getSpeakerAvatar = (speaker?: string) => {
    if (!speaker) return '?';
    return speaker.charAt(0).toUpperCase();
  };

  // 获取状态样式
  const getStatusBadge = () => {
    switch (status) {
      case 'connected':
        return <Badge className="bg-green-100 text-green-800">演示模式</Badge>;
      case 'connecting':
        return <Badge variant="secondary">连接中...</Badge>;
      case 'disconnected':
        return <Badge variant="outline">未连接</Badge>;
      case 'error':
        return <Badge variant="destructive">连接错误</Badge>;
      default:
        return <Badge variant="secondary">未知状态</Badge>;
    }
  };

  // 监听isActive变化
  useEffect(() => {
    if (isActive) {
      connectWebSocket();
    } else {
      disconnectWebSocket();
    }

    return () => {
      disconnectWebSocket();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [isActive, meetingId]);

  // 监听状态变化，自动重连
  useEffect(() => {
    if (status === 'disconnected' && isActive) {
      attemptReconnect();
    }
  }, [status, isActive]);

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-2">
            {status === 'connected' ? (
              <Wifi className="h-5 w-5 text-green-500" />
            ) : (
              <WifiOff className="h-5 w-5 text-muted-foreground" />
            )}
            <span>实时转录</span>
          </CardTitle>
          {getStatusBadge()}
        </div>
        
        {error && (
          <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
            {error}
          </div>
        )}
        
        {status === 'connected' && (
          <div className="text-sm text-blue-600 bg-blue-50 p-2 rounded">
            🎭 演示模式：模拟转录数据用于展示功能
          </div>
        )}
      </CardHeader>

      <CardContent className="p-0 h-full">
        <ScrollArea ref={scrollAreaRef} className="h-[400px] px-4">
          <div className="space-y-4 pb-4">
            {messages.length === 0 && !currentMessage && (
              <div className="text-center text-muted-foreground py-8">
                <Volume2 className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p>等待语音输入...</p>
                <p className="text-xs mt-1">
                  {status === 'connected' ? '转录服务已就绪' : '正在连接转录服务...'}
                </p>
              </div>
            )}

            {/* 已完成的转录消息 */}
            {messages.map((message) => (
              <div key={message.id} className="flex space-x-3">
                <Avatar className="h-8 w-8 flex-shrink-0">
                  <AvatarFallback>
                    {getSpeakerAvatar(message.speaker)}
                  </AvatarFallback>
                </Avatar>
                
                <div className="flex-1 space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium">
                      {message.speaker || '说话人'}
                    </span>
                    <span className="text-xs text-muted-foreground flex items-center">
                      <Clock className="h-3 w-3 mr-1" />
                      {formatTime(message.timestamp)}
                    </span>
                  </div>
                  
                  <div className="bg-muted p-3 rounded-lg">
                    <p className="text-sm leading-relaxed">{message.text}</p>
                  </div>
                </div>
              </div>
            ))}

            {/* 当前正在转录的消息 */}
            {currentMessage && (
              <div className="flex space-x-3">
                <Avatar className="h-8 w-8 flex-shrink-0">
                  <AvatarFallback>?</AvatarFallback>
                </Avatar>
                
                <div className="flex-1 space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium">说话人</span>
                    <Badge variant="secondary" className="text-xs">转录中</Badge>
                  </div>
                  
                  <div className="bg-blue-50 border border-blue-200 p-3 rounded-lg">
                    <p className="text-sm leading-relaxed text-blue-900">
                      {currentMessage}
                      <span className="inline-block w-2 h-4 bg-blue-500 ml-1 animate-pulse" />
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}