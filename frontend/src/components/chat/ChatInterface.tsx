'use client';

import { useState, useRef, useEffect } from 'react';
import { 
  MessageCircle, 
  Send, 
  Bot, 
  User, 
  Clock,
  Lightbulb,
  RotateCcw,
  Loader2,
  Copy,
  Check,
  Trash2,
  Settings
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { chatService, ChatMessage, ChatContext } from '@/lib/chat-service';

interface ChatInterfaceProps {
  context: ChatContext;
  className?: string;
}

export function ChatInterface({ context, className = '' }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // 初始化聊天
  useEffect(() => {
    const initChat = () => {
      // 加载历史消息
      const history = chatService.getChatHistory(context.meetingId);
      setMessages(history);
      
      // 如果没有历史消息，显示欢迎消息和建议问题
      if (history.length === 0) {
        const welcomeMessage: ChatMessage = {
          id: 'welcome',
          role: 'assistant',
          content: `👋 您好！我是您的AI助手。\n\n我可以帮您分析会议"${context.meetingTitle}"的内容，回答相关问题，并提供智能建议。\n\n**我能做什么：**\n• 总结会议要点和决策\n• 提取行动项和任务\n• 分析风险和机会\n• 回答具体问题\n\n请选择下面的建议问题开始，或者直接输入您想了解的内容。`,
          timestamp: Date.now(),
          type: 'suggestion',
          meetingId: context.meetingId,
        };
        
        setMessages([welcomeMessage]);
        setSuggestions(chatService.getStarterQuestions(context));
      }
    };

    initChat();
  }, [context]);

  // 自动滚动到底部
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollElement = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollElement) {
        scrollElement.scrollTop = scrollElement.scrollHeight;
      }
    }
  }, [messages, isTyping]);

  // 发送消息
  const handleSendMessage = async (message: string = inputMessage) => {
    if (!message.trim() || isTyping) return;

    const userMessage: ChatMessage = {
      id: `user_${Date.now()}`,
      role: 'user',
      content: message.trim(),
      timestamp: Date.now(),
      meetingId: context.meetingId,
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsTyping(true);
    setSuggestions([]);

    try {
      const response = await chatService.sendMessage(message.trim(), context);
      
      setMessages(prev => [...prev, response.message]);
      if (response.suggestions) {
        setSuggestions(response.suggestions);
      }
    } catch (error) {
      console.error('发送消息失败:', error);
      
      const errorMessage: ChatMessage = {
        id: `error_${Date.now()}`,
        role: 'assistant',
        content: '抱歉，我现在无法回复您的消息。请稍后再试。',
        timestamp: Date.now(),
        meetingId: context.meetingId,
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // 复制消息
  const handleCopyMessage = async (messageId: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (error) {
      console.error('复制失败:', error);
    }
  };

  // 清空聊天记录
  const handleClearChat = () => {
    const confirmed = confirm('确定要清空所有聊天记录吗？此操作不可撤销。');
    if (confirmed) {
      chatService.clearHistory(context.meetingId);
      setMessages([]);
      setSuggestions(chatService.getStarterQuestions(context));
    }
  };

  // 格式化时间
  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 渲染消息内容
  const renderMessageContent = (content: string) => {
    return content.split('\n').map((line, index) => {
      // 处理粗体文本
      if (line.startsWith('**') && line.endsWith('**') && line.length > 4) {
        return (
          <div key={index} className="font-semibold text-sm mb-2 text-gray-900 break-words">
            {line.slice(2, -2)}
          </div>
        );
      }
      
      // 处理列表项
      if (line.startsWith('• ') || line.startsWith('- ')) {
        return (
          <div key={index} className="flex text-sm mb-1 ml-2 text-gray-700">
            <span className="text-blue-500 mr-2 flex-shrink-0">•</span>
            <span className="break-words flex-1">{line.slice(2)}</span>
          </div>
        );
      }
      
      // 处理空行
      if (!line.trim()) {
        return <div key={index} className="h-2" />;
      }
      
      // 普通文本
      return (
        <div key={index} className="text-sm text-gray-700 mb-1 break-words">
          {line}
        </div>
      );
    });
  };

  return (
    <Card className={`h-full flex flex-col ${className}`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-2">
            <MessageCircle className="h-5 w-5 text-blue-500" />
            <span>AI 智能问答</span>
          </CardTitle>
          
          <div className="flex items-center space-x-2">
            <Badge variant="outline" className="text-xs">
              {context.meetingTitle}
            </Badge>
            
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleClearChat}
                    className="h-6 w-6 p-0"
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>清空聊天记录</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col p-0">
        {/* 消息列表 */}
        <ScrollArea ref={scrollAreaRef} className="flex-1 px-6 overflow-hidden">
          <div className="space-y-4 pb-4 min-h-0">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex items-start space-x-3 w-full ${
                  message.role === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                {message.role === 'assistant' && (
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <Bot className="h-4 w-4 text-blue-600" />
                    </div>
                  </div>
                )}
                
                <div
                  className={`max-w-[75%] min-w-0 rounded-lg px-4 py-3 word-wrap ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-50 text-gray-900'
                  }`}
                  style={{ wordWrap: 'break-word', overflowWrap: 'break-word' }}
                >
                  <div className="space-y-1">
                    {message.role === 'user' ? (
                      <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
                    ) : (
                      <div className="break-words overflow-hidden">{renderMessageContent(message.content)}</div>
                    )}
                    
                    <div className="flex items-center justify-between mt-2">
                      <div className="flex items-center space-x-1 text-xs opacity-70">
                        <Clock className="h-3 w-3" />
                        <span>{formatTime(message.timestamp)}</span>
                      </div>
                      
                      {message.role === 'assistant' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleCopyMessage(message.id, message.content)}
                          className="h-6 w-6 p-0 opacity-70 hover:opacity-100"
                        >
                          {copiedMessageId === message.id ? (
                            <Check className="h-3 w-3 text-green-600" />
                          ) : (
                            <Copy className="h-3 w-3" />
                          )}
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
                
                {message.role === 'user' && (
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                      <User className="h-4 w-4 text-white" />
                    </div>
                  </div>
                )}
              </div>
            ))}
            
            {/* 正在输入指示器 */}
            {isTyping && (
              <div className="flex items-start space-x-3 w-full">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                    <Bot className="h-4 w-4 text-blue-600" />
                  </div>
                </div>
                <div className="bg-gray-50 rounded-lg px-4 py-3 max-w-[75%]">
                  <div className="flex items-center space-x-2">
                    <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                    <span className="text-sm text-gray-600">正在思考中...</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        <Separator />

        {/* 建议问题 */}
        {suggestions.length > 0 && (
          <div className="p-4 border-t bg-gray-50/50">
            <div className="flex items-center space-x-2 mb-3">
              <Lightbulb className="h-4 w-4 text-yellow-500" />
              <span className="text-sm font-medium text-gray-700">建议问题</span>
            </div>
            <div className="grid gap-2">
              {suggestions.map((suggestion, index) => (
                <Button
                  key={index}
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSendMessage(suggestion)}
                  disabled={isTyping}
                  className="justify-start text-left text-sm h-auto p-2 whitespace-normal break-words min-h-[2rem]"
                >
                  <span className="break-words">{suggestion}</span>
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* 输入区域 */}
        <div className="p-4">
          <div className="flex items-end space-x-2">
            <div className="flex-1">
              <Input
                ref={inputRef}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入您的问题或直接选择上方的建议问题..."
                disabled={isTyping}
                className="resize-none"
              />
            </div>
            <Button
              onClick={() => handleSendMessage()}
              disabled={!inputMessage.trim() || isTyping}
              size="sm"
            >
              {isTyping ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
          
          <div className="text-xs text-gray-500 mt-2">
            按 Enter 发送消息，Shift+Enter 换行
          </div>
        </div>
      </CardContent>
    </Card>
  );
}