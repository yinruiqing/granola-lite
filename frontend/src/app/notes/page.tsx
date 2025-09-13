'use client';

import { useState, useEffect } from 'react';
import { 
  FileText, 
  Search, 
  Filter, 
  Calendar,
  Clock,
  Plus,
  Edit,
  Trash2,
  MoreHorizontal,
  Eye,
  Download
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
import { useAppStore } from '@/lib/store';
import { storageManager } from '@/lib/storage';
import { Note, Meeting } from '@/types';
import Link from 'next/link';
import { ExportDialog } from '@/components/export/ExportDialog';

export default function NotesPage() {
  const { meetings } = useAppStore();
  
  const [notes, setNotes] = useState<Note[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [meetingFilter, setMeetingFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('updated_at');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exportDialog, setExportDialog] = useState<{ open: boolean; note?: Note }>({ open: false });

  // 加载所有笔记
  useEffect(() => {
    const loadAllNotes = async () => {
      try {
        setLoading(true);
        setError(null);

        // 获取所有会议的笔记
        const allNotes: Note[] = [];
        
        for (const meeting of meetings) {
          const meetingNotes = await storageManager.getNotesByMeeting(meeting.id);
          allNotes.push(...meetingNotes);
        }
        
        setNotes(allNotes);
      } catch (error) {
        console.error('加载笔记失败:', error);
        setError('加载笔记失败');
      } finally {
        setLoading(false);
      }
    };

    if (meetings.length > 0) {
      loadAllNotes();
    } else {
      setLoading(false);
    }
  }, [meetings]);

  // 过滤和排序笔记
  const filteredAndSortedNotes = notes
    .filter(note => {
      // 搜索过滤
      if (searchTerm && !note.content.toLowerCase().includes(searchTerm.toLowerCase())) {
        return false;
      }
      
      // 会议过滤
      if (meetingFilter !== 'all' && note.meeting_id !== parseInt(meetingFilter)) {
        return false;
      }
      
      return true;
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'created_at':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        case 'updated_at':
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
        case 'meeting_id':
          return a.meeting_id - b.meeting_id;
        default:
          return 0;
      }
    });

  // 删除笔记
  const handleDeleteNote = async (noteId: number) => {
    const confirmed = confirm('确定要删除这条笔记吗？此操作不可撤销。');
    if (!confirmed) return;

    try {
      await storageManager.deleteNote(noteId);
      setNotes(prev => prev.filter(note => note.id !== noteId));
    } catch (error) {
      console.error('删除笔记失败:', error);
      setError('删除笔记失败');
    }
  };

  // 获取会议信息
  const getMeetingInfo = (meetingId: number) => {
    return meetings.find(m => m.id === meetingId);
  };

  // 获取笔记预览文本
  const getPreviewText = (content: string) => {
    return content.replace(/<[^>]*>/g, '').trim().slice(0, 150);
  };

  // 格式化时间
  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN');
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

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">所有笔记</h1>
          <p className="text-muted-foreground">
            管理您的所有会议笔记 ({notes.length} 条笔记)
          </p>
        </div>
        
        <Button asChild>
          <Link href="/meetings/new">
            <Plus className="h-4 w-4 mr-2" />
            创建会议
          </Link>
        </Button>
      </div>

      {/* 搜索和过滤 */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* 搜索框 */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
              <Input
                placeholder="搜索笔记内容..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* 会议过滤 */}
            <Select value={meetingFilter} onValueChange={setMeetingFilter}>
              <SelectTrigger className="w-full sm:w-48">
                <Calendar className="h-4 w-4 mr-2" />
                <SelectValue placeholder="按会议过滤" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部会议</SelectItem>
                {meetings.map((meeting) => (
                  <SelectItem key={meeting.id} value={meeting.id.toString()}>
                    {meeting.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* 排序 */}
            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="w-full sm:w-48">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="排序方式" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="updated_at">更新时间</SelectItem>
                <SelectItem value="created_at">创建时间</SelectItem>
                <SelectItem value="meeting_id">按会议分组</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* 统计信息 */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总笔记数</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{notes.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">涉及会议</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {new Set(notes.map(note => note.meeting_id)).size}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">今日新增</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {notes.filter(note => {
                const today = new Date().toDateString();
                const noteDate = new Date(note.created_at).toDateString();
                return today === noteDate;
              }).length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 笔记列表 */}
      <div className="space-y-4">
        {error && (
          <Card>
            <CardContent className="p-6">
              <div className="text-red-600">{error}</div>
            </CardContent>
          </Card>
        )}

        {filteredAndSortedNotes.length > 0 ? (
          filteredAndSortedNotes.map((note) => {
            const meeting = getMeetingInfo(note.meeting_id);
            return (
              <Card key={note.id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 space-y-3">
                      {/* 会议信息 */}
                      <div className="flex items-center space-x-2">
                        <Badge variant="outline">
                          {meeting ? meeting.title : `会议 #${note.meeting_id}`}
                        </Badge>
                        {note.timestamp && (
                          <Badge variant="secondary" className="text-xs">
                            {Math.floor(note.timestamp / 60)}:{String(Math.floor(note.timestamp % 60)).padStart(2, '0')}
                          </Badge>
                        )}
                      </div>

                      {/* 笔记内容预览 */}
                      <div>
                        <p className="text-sm leading-relaxed line-clamp-3">
                          {getPreviewText(note.content)}
                        </p>
                      </div>

                      {/* 时间信息 */}
                      <div className="flex items-center space-x-4 text-xs text-muted-foreground">
                        <span className="flex items-center">
                          <Clock className="h-3 w-3 mr-1" />
                          创建于 {formatTime(note.created_at)}
                        </span>
                        {note.updated_at !== note.created_at && (
                          <span className="flex items-center">
                            <Edit className="h-3 w-3 mr-1" />
                            更新于 {formatTime(note.updated_at)}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* 操作按钮 */}
                    <div className="flex items-center space-x-2">
                      <Button variant="outline" size="sm" asChild>
                        <Link href={`/meetings/${note.meeting_id}/notes`}>
                          <Eye className="h-3 w-3 mr-1" />
                          查看
                        </Link>
                      </Button>

                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>笔记操作</DropdownMenuLabel>
                          <DropdownMenuItem asChild>
                            <Link href={`/meetings/${note.meeting_id}/notes`}>
                              <Edit className="h-4 w-4 mr-2" />
                              编辑笔记
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem asChild>
                            <Link href={`/meetings/${note.meeting_id}`}>
                              <Eye className="h-4 w-4 mr-2" />
                              查看会议
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setExportDialog({ open: true, note })}>
                            <Download className="h-4 w-4 mr-2" />
                            导出笔记
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem 
                            className="text-red-600"
                            onClick={() => handleDeleteNote(note.id)}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            删除笔记
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })
        ) : (
          <Card>
            <CardContent className="p-12">
              <div className="text-center space-y-4">
                <FileText className="h-12 w-12 text-muted-foreground mx-auto" />
                <div>
                  <h3 className="text-lg font-medium">
                    {searchTerm || meetingFilter !== 'all' ? '没有找到匹配的笔记' : '还没有笔记记录'}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {searchTerm || meetingFilter !== 'all' 
                      ? '尝试修改搜索条件或过滤器' 
                      : '开始一个会议并记录笔记吧'
                    }
                  </p>
                </div>
                {!searchTerm && meetingFilter === 'all' && (
                  <Button asChild>
                    <Link href="/meetings/new">创建新会议</Link>
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* 导出对话框 */}
      {exportDialog.note && (
        <ExportDialog
          open={exportDialog.open}
          onOpenChange={(open) => setExportDialog({ open, note: open ? exportDialog.note : undefined })}
          type="note"
          data={exportDialog.note}
        />
      )}
    </div>
  );
}