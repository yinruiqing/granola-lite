'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
  ArrowLeft, 
  Edit, 
  Trash2, 
  Play, 
  FileText, 
  MessageSquare, 
  Calendar,
  Clock,
  User,
  MoreHorizontal,
  Bot
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAppStore } from '@/lib/store';
import { storageManager } from '@/lib/storage';
import { Meeting, Note, Transcription } from '@/types';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { ChatContext } from '@/lib/chat-service';
import Link from 'next/link';

export default function MeetingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { setCurrentMeeting } = useAppStore();
  
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [transcriptions, setTranscriptions] = useState<Transcription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showChat, setShowChat] = useState(false);

  const meetingId = parseInt(params.id as string);

  // 加载会议详情
  useEffect(() => {
    const loadMeetingDetail = async () => {
      try {
        setLoading(true);
        setError(null);

        const meetingData = await storageManager.getMeeting(meetingId);
        if (!meetingData) {
          setError('会议不存在');
          return;
        }

        setMeeting(meetingData);
        setCurrentMeeting(meetingData);

        // 加载相关的笔记和转录
        const [notesData, transcriptionsData] = await Promise.all([
          storageManager.getNotesByMeeting(meetingId),
          storageManager.getTranscriptionsByMeeting(meetingId)
        ]);

        setNotes(notesData);
        setTranscriptions(transcriptionsData);
      } catch (error) {
        console.error('加载会议详情失败:', error);
        setError('加载会议详情失败');
      } finally {
        setLoading(false);
      }
    };

    if (meetingId) {
      loadMeetingDetail();
    }
  }, [meetingId, setCurrentMeeting]);

  // 删除会议
  const handleDeleteMeeting = async () => {
    if (!meeting) return;
    
    const confirmed = confirm(`确定要删除会议"${meeting.title}"吗？此操作不可撤销。`);
    if (!confirmed) return;

    try {
      await storageManager.deleteMeeting(meeting.id);
      router.push('/meetings');
    } catch (error) {
      console.error('删除会议失败:', error);
      alert('删除会议失败，请重试');
    }
  };

  // 状态样式映射
  const getStatusBadge = (status: Meeting['status']) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-100 text-green-800">已完成</Badge>;
      case 'in_progress':
        return <Badge className="bg-orange-100 text-orange-800">进行中</Badge>;
      case 'scheduled':
        return <Badge className="bg-blue-100 text-blue-800">已安排</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p>加载会议详情中...</p>
        </div>
      </div>
    );
  }

  if (error || !meeting) {
    return (
      <div className="text-center py-12">
        <Calendar className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
        <h2 className="text-xl font-semibold mb-2">{error || '会议不存在'}</h2>
        <p className="text-muted-foreground mb-4">请检查会议ID是否正确</p>
        <Button asChild>
          <Link href="/meetings">返回会议列表</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题和操作 */}
      <div className="flex flex-col sm:flex-row justify-between items-start gap-4">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/meetings">
              <ArrowLeft className="h-4 w-4 mr-2" />
              返回列表
            </Link>
          </Button>
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-3xl font-bold tracking-tight">{meeting.title}</h1>
              {getStatusBadge(meeting.status)}
            </div>
            <p className="text-muted-foreground mt-1">
              创建于 {new Date(meeting.created_at).toLocaleString('zh-CN')}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Button 
            variant={showChat ? "default" : "outline"}
            onClick={() => setShowChat(!showChat)}
          >
            <Bot className="h-4 w-4 mr-2" />
            {showChat ? "隐藏AI助手" : "AI问答"}
          </Button>
          
          <Button variant="outline" asChild>
            <Link href={`/meetings/${meeting.id}/edit`}>
              <Edit className="h-4 w-4 mr-2" />
              编辑
            </Link>
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>会议操作</DropdownMenuLabel>
              <DropdownMenuItem asChild>
                <Link href={`/meetings/${meeting.id}/notes`}>
                  <FileText className="h-4 w-4 mr-2" />
                  查看笔记
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href={`/meetings/${meeting.id}/chat`}>
                  <MessageSquare className="h-4 w-4 mr-2" />
                  AI 问答
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem 
                className="text-red-600"
                onClick={handleDeleteMeeting}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                删除会议
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className={`grid gap-6 ${showChat ? 'lg:grid-cols-2' : 'lg:grid-cols-3'}`}>
        {/* 左侧主要内容 */}
        <div className={`space-y-6 ${showChat ? 'lg:col-span-1' : 'lg:col-span-2'}`}>
          {/* 会议信息 */}
          <Card>
            <CardHeader>
              <CardTitle>会议详情</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {meeting.description && (
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-2">会议描述</h4>
                  <p className="text-sm leading-relaxed">{meeting.description}</p>
                </div>
              )}
              
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="flex items-center space-x-3">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-xs text-muted-foreground">创建时间</p>
                    <p className="text-sm font-medium">
                      {new Date(meeting.created_at).toLocaleString('zh-CN')}
                    </p>
                  </div>
                </div>
                
                {meeting.updated_at !== meeting.created_at && (
                  <div className="flex items-center space-x-3">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-xs text-muted-foreground">更新时间</p>
                      <p className="text-sm font-medium">
                        {new Date(meeting.updated_at).toLocaleString('zh-CN')}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* 快速操作 */}
          <Card>
            <CardHeader>
              <CardTitle>快速操作</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2">
                <Button variant="outline" asChild className="justify-start h-12">
                  <Link href={`/live?meeting=${meeting.id}`}>
                    <Play className="h-4 w-4 mr-3" />
                    <div className="text-left">
                      <div className="font-medium">开始录音</div>
                      <div className="text-xs text-muted-foreground">实时转录会议内容</div>
                    </div>
                  </Link>
                </Button>

                <Button variant="outline" asChild className="justify-start h-12">
                  <Link href={`/meetings/${meeting.id}/notes`}>
                    <FileText className="h-4 w-4 mr-3" />
                    <div className="text-left">
                      <div className="font-medium">管理笔记</div>
                      <div className="text-xs text-muted-foreground">编辑会议笔记</div>
                    </div>
                  </Link>
                </Button>

                <Button variant="outline" asChild className="justify-start h-12">
                  <Link href={`/meetings/${meeting.id}/chat`}>
                    <MessageSquare className="h-4 w-4 mr-3" />
                    <div className="text-left">
                      <div className="font-medium">AI 问答</div>
                      <div className="text-xs text-muted-foreground">基于会议内容提问</div>
                    </div>
                  </Link>
                </Button>

                <Button variant="outline" asChild className="justify-start h-12">
                  <Link href={`/meetings/${meeting.id}/export`}>
                    <User className="h-4 w-4 mr-3" />
                    <div className="text-left">
                      <div className="font-medium">导出</div>
                      <div className="text-xs text-muted-foreground">导出会议纪要</div>
                    </div>
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 右侧：AI聊天或统计信息 */}
        {showChat ? (
          /* AI聊天界面 */
          <div className="lg:col-span-1">
            <ChatInterface 
              context={{
                meetingId: meeting.id,
                meetingTitle: meeting.title,
                transcription: transcriptions.map(t => t.content).join(' '),
                notes: notes.map(n => n.content),
                participants: [],
              }}
              className="h-[800px]"
            />
          </div>
        ) : (
          /* 统计信息 */
          <div className="space-y-6">
            {/* 统计概览 */}
            <Card>
              <CardHeader>
                <CardTitle>统计信息</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <FileText className="h-4 w-4 text-blue-500" />
                    <span className="text-sm">笔记数量</span>
                  </div>
                  <Badge variant="secondary">{notes.length}</Badge>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <MessageSquare className="h-4 w-4 text-green-500" />
                    <span className="text-sm">转录段数</span>
                  </div>
                  <Badge variant="secondary">{transcriptions.length}</Badge>
                </div>
                
                <Separator />
                
                <div className="text-xs text-muted-foreground">
                  最后活动: {new Date(meeting.updated_at).toLocaleDateString('zh-CN')}
                </div>
              </CardContent>
            </Card>

            {/* 最近笔记 */}
            {notes.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>最近笔记</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {notes.slice(0, 3).map((note) => (
                      <div key={note.id} className="p-3 border rounded-lg">
                        <p className="text-sm line-clamp-2">{note.content}</p>
                        <p className="text-xs text-muted-foreground mt-2">
                          {new Date(note.created_at).toLocaleString('zh-CN')}
                        </p>
                      </div>
                    ))}
                    {notes.length > 3 && (
                      <Button variant="ghost" size="sm" asChild className="w-full">
                        <Link href={`/meetings/${meeting.id}/notes`}>
                          查看全部 {notes.length} 条笔记
                        </Link>
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}