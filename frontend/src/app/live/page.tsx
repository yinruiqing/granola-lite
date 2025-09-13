'use client';

import { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { 
  Play, 
  Square, 
  FileText, 
  Settings, 
  Save,
  ArrowLeft,
  AlertCircle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { AudioRecorder } from '@/components/audio/AudioRecorder';
import { RealTimeTranscription } from '@/components/transcription/RealTimeTranscription';
import { useAppStore } from '@/lib/store';
import { storageManager } from '@/lib/storage';
import { Meeting } from '@/types';
import Link from 'next/link';

type SessionState = 'idle' | 'active' | 'paused';

export default function LiveMeetingPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { currentMeeting, setCurrentMeeting, addNote } = useAppStore();
  
  const [sessionState, setSessionState] = useState<SessionState>('idle');
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [notes, setNotes] = useState('');
  const [autoSave, setAutoSave] = useState(true);
  const [autoTranscribe, setAutoTranscribe] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const meetingIdParam = searchParams.get('meeting');
  const meetingId = meetingIdParam ? parseInt(meetingIdParam) : null;

  // 加载会议信息
  useEffect(() => {
    const loadMeeting = async () => {
      if (meetingId) {
        try {
          const meetingData = await storageManager.getMeeting(meetingId);
          if (meetingData) {
            setMeeting(meetingData);
            setCurrentMeeting(meetingData);
          } else {
            setError('会议不存在');
          }
        } catch (error) {
          console.error('加载会议失败:', error);
          setError('加载会议失败');
        }
      }
    };

    loadMeeting();
  }, [meetingId, setCurrentMeeting]);

  // 开始会议
  const startSession = async () => {
    try {
      setError(null);
      
      let activeMeeting = meeting;
      
      // 如果没有指定会议，创建一个新的
      if (!activeMeeting) {
        const newMeeting = await storageManager.createMeeting({
          title: `实时会议 - ${new Date().toLocaleString('zh-CN')}`,
          description: '实时录制的会议',
          status: 'in_progress',
        });
        
        activeMeeting = newMeeting;
        setMeeting(newMeeting);
        setCurrentMeeting(newMeeting);
        
        // 更新URL
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.set('meeting', newMeeting.id.toString());
        window.history.replaceState({}, '', newUrl.toString());
      } else {
        // 更新会议状态为进行中
        const updatedMeeting = await storageManager.updateMeeting(activeMeeting.id, {
          status: 'in_progress'
        });
        if (updatedMeeting) {
          setMeeting(updatedMeeting);
          setCurrentMeeting(updatedMeeting);
        }
      }
      
      setSessionState('active');
    } catch (error) {
      console.error('开始会议失败:', error);
      setError('开始会议失败，请重试');
    }
  };

  // 结束会议
  const endSession = async () => {
    try {
      setSessionState('idle');
      
      if (meeting) {
        // 保存笔记
        if (notes.trim()) {
          await saveNotes();
        }
        
        // 更新会议状态为已完成
        const updatedMeeting = await storageManager.updateMeeting(meeting.id, {
          status: 'completed'
        });
        
        if (updatedMeeting) {
          setMeeting(updatedMeeting);
          setCurrentMeeting(updatedMeeting);
        }
      }
      
      setError(null);
    } catch (error) {
      console.error('结束会议失败:', error);
      setError('结束会议失败');
    }
  };

  // 保存笔记
  const saveNotes = async () => {
    if (!meeting || !notes.trim()) return;

    try {
      setLoading(true);
      
      const note = await storageManager.createNote({
        meeting_id: meeting.id,
        content: notes.trim(),
        timestamp: Date.now() / 1000,
      });
      
      addNote(note);
      setNotes(''); // 清空已保存的笔记
      
    } catch (error) {
      console.error('保存笔记失败:', error);
      setError('保存笔记失败');
    } finally {
      setLoading(false);
    }
  };

  // 自动保存笔记
  useEffect(() => {
    if (!autoSave || !meeting || !notes.trim()) return;

    const autoSaveTimer = setTimeout(() => {
      if (sessionState === 'active') {
        saveNotes();
      }
    }, 30000); // 30秒自动保存

    return () => clearTimeout(autoSaveTimer);
  }, [notes, autoSave, meeting, sessionState]);

  // 处理录音数据
  const handleAudioData = async (audioBlob: Blob) => {
    if (!meeting) return;

    try {
      // 这里可以上传音频文件到服务器
      console.log('录音完成:', audioBlob.size, '字节');
      
      // 暂时只在控制台显示，后续可以实现上传到后端
    } catch (error) {
      console.error('处理录音失败:', error);
      setError('处理录音失败');
    }
  };

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" size="sm" asChild>
            <Link href={meeting ? `/meetings/${meeting.id}` : '/meetings'}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              {meeting ? '返回会议详情' : '返回会议列表'}
            </Link>
          </Button>
          
          <div>
            <h1 className="text-3xl font-bold tracking-tight">实时会议</h1>
            <div className="flex items-center space-x-3 mt-1">
              <p className="text-muted-foreground">
                {meeting ? meeting.title : '未选择会议'}
              </p>
              {sessionState !== 'idle' && (
                <Badge variant={sessionState === 'active' ? 'default' : 'secondary'}>
                  {sessionState === 'active' ? '进行中' : '已暂停'}
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* 主控制按钮 */}
        <div className="flex items-center space-x-2">
          {sessionState === 'idle' && (
            <Button onClick={startSession} size="lg" className="bg-green-600 hover:bg-green-700">
              <Play className="h-4 w-4 mr-2" />
              开始会议
            </Button>
          )}
          
          {sessionState === 'active' && (
            <Button onClick={endSession} size="lg" variant="destructive">
              <Square className="h-4 w-4 mr-2" />
              结束会议
            </Button>
          )}
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* 左侧：录音和转录 */}
        <div className="lg:col-span-2 space-y-6">
          {/* 录音控制 */}
          <div>
            <h2 className="text-lg font-semibold mb-4">音频录制</h2>
            <AudioRecorder
              onAudioData={handleAudioData}
              meetingId={meeting?.id}
              autoTranscribe={autoTranscribe}
            />
          </div>

          {/* 实时转录 */}
          {autoTranscribe && meeting && (
            <div>
              <h2 className="text-lg font-semibold mb-4">实时转录</h2>
              <RealTimeTranscription
                meetingId={meeting.id}
                isActive={sessionState === 'active'}
              />
            </div>
          )}
        </div>

        {/* 右侧：笔记和设置 */}
        <div className="space-y-6">
          {/* 会议笔记 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <FileText className="h-5 w-5" />
                  <span>会议笔记</span>
                </div>
                {notes.trim() && (
                  <Button 
                    onClick={saveNotes} 
                    size="sm" 
                    disabled={loading}
                    variant="outline"
                  >
                    <Save className="h-3 w-3 mr-1" />
                    保存
                  </Button>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="notes">实时笔记</Label>
                <Textarea
                  id="notes"
                  placeholder="在这里记录会议要点..."
                  rows={8}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="resize-none"
                />
              </div>
              
              <div className="text-xs text-muted-foreground">
                {autoSave ? '笔记将每30秒自动保存' : '请手动保存笔记'}
              </div>
            </CardContent>
          </Card>

          {/* 会议设置 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Settings className="h-5 w-5" />
                <span>会议设置</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>自动转录</Label>
                  <p className="text-xs text-muted-foreground">
                    实时将语音转换为文字
                  </p>
                </div>
                <Switch
                  checked={autoTranscribe}
                  onCheckedChange={setAutoTranscribe}
                  disabled={sessionState === 'active'}
                />
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>自动保存笔记</Label>
                  <p className="text-xs text-muted-foreground">
                    每30秒自动保存一次笔记
                  </p>
                </div>
                <Switch
                  checked={autoSave}
                  onCheckedChange={setAutoSave}
                />
              </div>
            </CardContent>
          </Card>

          {/* 会议信息 */}
          {meeting && (
            <Card>
              <CardHeader>
                <CardTitle>会议信息</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div>
                  <Label className="text-xs text-muted-foreground">标题</Label>
                  <p className="text-sm font-medium">{meeting.title}</p>
                </div>
                {meeting.description && (
                  <div>
                    <Label className="text-xs text-muted-foreground">描述</Label>
                    <p className="text-sm">{meeting.description}</p>
                  </div>
                )}
                <div>
                  <Label className="text-xs text-muted-foreground">创建时间</Label>
                  <p className="text-sm">
                    {new Date(meeting.created_at).toLocaleString('zh-CN')}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}