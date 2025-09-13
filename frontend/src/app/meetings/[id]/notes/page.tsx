'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
  ArrowLeft, 
  Plus, 
  Edit, 
  Trash2, 
  Clock,
  FileText,
  Search,
  Filter,
  MoreHorizontal,
  Eye,
  EyeOff
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { RichTextEditor } from '@/components/editor/RichTextEditor';
import { AIEnhancementPanel } from '@/components/ai/AIEnhancementPanel';
import { useAppStore } from '@/lib/store';
import { storageManager } from '@/lib/storage';
import { Meeting, Note } from '@/types';
import Link from 'next/link';

export default function MeetingNotesPage() {
  const params = useParams();
  const router = useRouter();
  const { notes, setNotes, addNote, updateNote, deleteNote } = useAppStore();
  
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [meetingNotes, setMeetingNotes] = useState<Note[]>([]);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // 编辑器内容
  const [editorContent, setEditorContent] = useState('');
  const [showAIPanel, setShowAIPanel] = useState(false);
  
  const meetingId = parseInt(params.id as string);

  // 加载会议和笔记数据
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);

        // 加载会议信息
        const meetingData = await storageManager.getMeeting(meetingId);
        if (!meetingData) {
          setError('会议不存在');
          return;
        }
        setMeeting(meetingData);

        // 加载会议笔记
        const notesData = await storageManager.getNotesByMeeting(meetingId);
        setMeetingNotes(notesData);
        setNotes(notesData);

      } catch (error) {
        console.error('加载数据失败:', error);
        setError('加载数据失败');
      } finally {
        setLoading(false);
      }
    };

    if (meetingId) {
      loadData();
    }
  }, [meetingId, setNotes]);

  // 过滤和排序笔记
  const filteredAndSortedNotes = meetingNotes
    .filter(note => 
      !searchTerm || 
      note.content.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      switch (sortBy) {
        case 'created_at':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        case 'updated_at':
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
        case 'timestamp':
          return (a.timestamp || 0) - (b.timestamp || 0);
        default:
          return 0;
      }
    });

  // 创建新笔记
  const handleCreateNote = async () => {
    if (!meeting) return;

    try {
      setIsCreating(true);
      
      const newNote = await storageManager.createNote({
        meeting_id: meeting.id,
        content: '新建笔记',
        timestamp: Date.now() / 1000,
      });

      addNote(newNote);
      setMeetingNotes(prev => [...prev, newNote]);
      setSelectedNote(newNote);
      setEditorContent(newNote.content);
      
    } catch (error) {
      console.error('创建笔记失败:', error);
      setError('创建笔记失败');
    } finally {
      setIsCreating(false);
    }
  };

  // 选择笔记
  const handleSelectNote = (note: Note) => {
    setSelectedNote(note);
    setEditorContent(note.content);
  };

  // 保存笔记
  const handleSaveNote = async () => {
    if (!selectedNote || !editorContent.trim()) return;

    try {
      setSaving(true);
      
      const updatedNote = await storageManager.updateNote(selectedNote.id, {
        content: editorContent.trim(),
      });

      if (updatedNote) {
        updateNote(selectedNote.id, updatedNote);
        setMeetingNotes(prev => prev.map(note => 
          note.id === selectedNote.id ? updatedNote : note
        ));
        setSelectedNote(updatedNote);
      }
      
    } catch (error) {
      console.error('保存笔记失败:', error);
      setError('保存笔记失败');
    } finally {
      setSaving(false);
    }
  };

  // 处理AI增强后的内容应用
  const handleEnhancementApply = (enhancedContent: string) => {
    setEditorContent(enhancedContent);
    setShowAIPanel(false);
    
    // 自动保存增强后的内容
    if (selectedNote) {
      setTimeout(() => {
        handleSaveNote();
      }, 500);
    }
  };

  // 显示AI增强面板
  const handleShowAIPanel = () => {
    setShowAIPanel(true);
  };

  // 关闭AI增强面板
  const handleCloseAIPanel = () => {
    setShowAIPanel(false);
  };

  // 删除笔记
  const handleDeleteNote = async (noteId: number) => {
    const confirmed = confirm('确定要删除这条笔记吗？此操作不可撤销。');
    if (!confirmed) return;

    try {
      await storageManager.deleteNote(noteId);
      
      deleteNote(noteId);
      setMeetingNotes(prev => prev.filter(note => note.id !== noteId));
      
      // 如果删除的是当前选中的笔记，清空编辑器
      if (selectedNote?.id === noteId) {
        setSelectedNote(null);
        setEditorContent('');
      }
      
    } catch (error) {
      console.error('删除笔记失败:', error);
      setError('删除笔记失败');
    }
  };

  // 格式化时间
  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // 获取笔记预览文本
  const getPreviewText = (content: string) => {
    return content.replace(/<[^>]*>/g, '').trim().slice(0, 100) + '...';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p>加载笔记数据中...</p>
        </div>
      </div>
    );
  }

  if (error || !meeting) {
    return (
      <div className="text-center py-12">
        <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
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
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" size="sm" asChild>
            <Link href={`/meetings/${meeting.id}`}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              返回会议详情
            </Link>
          </Button>
          
          <div>
            <h1 className="text-3xl font-bold tracking-tight">会议笔记</h1>
            <p className="text-muted-foreground">{meeting.title}</p>
          </div>
        </div>

        <Button 
          onClick={handleCreateNote} 
          disabled={isCreating}
        >
          <Plus className="h-4 w-4 mr-2" />
          新建笔记
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* 左侧：笔记列表 */}
        <div className="lg:col-span-1 space-y-4">
          {/* 搜索和过滤 */}
          <Card>
            <CardContent className="p-4 space-y-3">
              {/* 搜索 */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                <Input
                  placeholder="搜索笔记内容..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>

              {/* 排序 */}
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger>
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue placeholder="排序方式" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="created_at">创建时间</SelectItem>
                  <SelectItem value="updated_at">更新时间</SelectItem>
                  <SelectItem value="timestamp">会议时间点</SelectItem>
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          {/* 笔记列表 */}
          <div className="space-y-2">
            {filteredAndSortedNotes.length > 0 ? (
              filteredAndSortedNotes.map((note) => (
                <Card 
                  key={note.id} 
                  className={`cursor-pointer transition-all hover:shadow-md ${
                    selectedNote?.id === note.id ? 'ring-2 ring-primary' : ''
                  }`}
                  onClick={() => handleSelectNote(note)}
                >
                  <CardContent className="p-4">
                    <div className="space-y-2">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="text-sm font-medium line-clamp-2">
                            {getPreviewText(note.content)}
                          </p>
                        </div>
                        
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              onClick={(e) => e.stopPropagation()}
                            >
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem 
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSelectNote(note);
                              }}
                            >
                              <Edit className="h-4 w-4 mr-2" />
                              编辑
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem 
                              className="text-red-600"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteNote(note.id);
                              }}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              删除
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                      
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <div className="flex items-center space-x-2">
                          <Clock className="h-3 w-3" />
                          <span>{formatTime(note.created_at)}</span>
                        </div>
                        
                        {note.timestamp && (
                          <Badge variant="outline" className="text-xs">
                            {Math.floor(note.timestamp / 60)}:{String(Math.floor(note.timestamp % 60)).padStart(2, '0')}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            ) : (
              <Card>
                <CardContent className="p-8 text-center">
                  <FileText className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-muted-foreground">
                    {searchTerm ? '没有找到匹配的笔记' : '还没有笔记'}
                  </p>
                  {!searchTerm && (
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="mt-2"
                      onClick={handleCreateNote}
                    >
                      创建第一条笔记
                    </Button>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>

        {/* 右侧：编辑器和AI增强 */}
        <div className="lg:col-span-2 space-y-6">
          {selectedNote ? (
            <>
              {/* 笔记编辑器 */}
              <RichTextEditor
                content={editorContent}
                onChange={setEditorContent}
                onSave={handleSaveNote}
                placeholder="开始编辑笔记内容..."
                autoSave={true}
                autoSaveInterval={3000}
                showAIButton={true}
                onAIEnhance={handleShowAIPanel}
              />
              
              {/* AI增强面板 */}
              {showAIPanel && editorContent.trim() && (
                <AIEnhancementPanel
                  content={editorContent}
                  onEnhancementApply={handleEnhancementApply}
                  onClose={handleCloseAIPanel}
                  disabled={saving}
                />
              )}
            </>
          ) : (
            <Card className="h-[600px] flex items-center justify-center">
              <div className="text-center space-y-4">
                <div className="flex items-center justify-center space-x-2 text-muted-foreground">
                  <EyeOff className="h-8 w-8" />
                </div>
                <div>
                  <h3 className="text-lg font-medium">选择一条笔记开始编辑</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    从左侧列表中选择笔记，或创建新的笔记
                  </p>
                </div>
                <Button onClick={handleCreateNote}>
                  <Plus className="h-4 w-4 mr-2" />
                  创建新笔记
                </Button>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}