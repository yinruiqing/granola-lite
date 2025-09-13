'use client';

import { useEffect, useState } from 'react';
import { Plus, Search, Filter, MoreHorizontal, Calendar, Clock, Users, Download, Package } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useAppStore } from '@/lib/store';
import { storageManager } from '@/lib/storage';
import { Meeting } from '@/types';
import Link from 'next/link';
import { ExportDialog } from '@/components/export/ExportDialog';
import { BatchExportDialog } from '@/components/export/BatchExportDialog';

export default function MeetingsPage() {
  const { meetings, setMeetings } = useAppStore();
  const [filteredMeetings, setFilteredMeetings] = useState<Meeting[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [exportDialog, setExportDialog] = useState<{ open: boolean; meeting?: Meeting }>({ open: false });
  const [batchExportDialog, setBatchExportDialog] = useState(false);

  // 加载会议数据
  useEffect(() => {
    const loadMeetings = async () => {
      try {
        const allMeetings = await storageManager.getAllMeetings();
        setMeetings(allMeetings);
        setLoading(false);
      } catch (error) {
        console.error('加载会议失败:', error);
        setLoading(false);
      }
    };

    loadMeetings();
  }, [setMeetings]);

  // 过滤和搜索
  useEffect(() => {
    let filtered = meetings;

    // 状态过滤
    if (statusFilter !== 'all') {
      filtered = filtered.filter(meeting => meeting.status === statusFilter);
    }

    // 搜索过滤
    if (searchTerm) {
      filtered = filtered.filter(meeting =>
        meeting.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (meeting.description && meeting.description.toLowerCase().includes(searchTerm.toLowerCase()))
      );
    }

    setFilteredMeetings(filtered);
  }, [meetings, statusFilter, searchTerm]);

  // 删除会议
  const handleDeleteMeeting = async (id: number) => {
    try {
      await storageManager.deleteMeeting(id);
      const updatedMeetings = await storageManager.getAllMeetings();
      setMeetings(updatedMeetings);
    } catch (error) {
      console.error('删除会议失败:', error);
    }
  };

  // 状态样式映射
  const getStatusBadge = (status: Meeting['status']) => {
    switch (status) {
      case 'completed':
        return <Badge variant="default" className="bg-green-100 text-green-800">已完成</Badge>;
      case 'in_progress':
        return <Badge variant="default" className="bg-orange-100 text-orange-800">进行中</Badge>;
      case 'scheduled':
        return <Badge variant="default" className="bg-blue-100 text-blue-800">已安排</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p>加载会议数据中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题和操作 */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">会议管理</h1>
          <p className="text-muted-foreground">管理您的所有会议记录</p>
        </div>
        
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setBatchExportDialog(true)}
            disabled={meetings.length === 0}
          >
            <Package className="h-4 w-4 mr-2" />
            批量导出
          </Button>
          <Button asChild>
            <Link href="/meetings/new">
              <Plus className="h-4 w-4 mr-2" />
              创建会议
            </Link>
          </Button>
        </div>
      </div>

      {/* 搜索和过滤 */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* 搜索框 */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
              <Input
                placeholder="搜索会议标题或描述..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* 状态过滤 */}
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-48">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="过滤状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="scheduled">已安排</SelectItem>
                <SelectItem value="in_progress">进行中</SelectItem>
                <SelectItem value="completed">已完成</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* 会议统计 */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总会议数</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{meetings.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">进行中</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {meetings.filter(m => m.status === 'in_progress').length}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">已完成</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {meetings.filter(m => m.status === 'completed').length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 会议列表 */}
      <div className="space-y-4">
        {filteredMeetings.length > 0 ? (
          filteredMeetings.map((meeting) => (
            <Card key={meeting.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center space-x-3">
                      <h3 className="text-lg font-semibold">{meeting.title}</h3>
                      {getStatusBadge(meeting.status)}
                    </div>
                    
                    {meeting.description && (
                      <p className="text-sm text-muted-foreground line-clamp-2">
                        {meeting.description}
                      </p>
                    )}
                    
                    <div className="flex items-center space-x-4 text-xs text-muted-foreground">
                      <span className="flex items-center">
                        <Calendar className="h-3 w-3 mr-1" />
                        创建于 {new Date(meeting.created_at).toLocaleDateString('zh-CN')}
                      </span>
                      {meeting.updated_at !== meeting.created_at && (
                        <span className="flex items-center">
                          <Clock className="h-3 w-3 mr-1" />
                          更新于 {new Date(meeting.updated_at).toLocaleDateString('zh-CN')}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Button variant="outline" size="sm" asChild>
                      <Link href={`/meetings/${meeting.id}`}>
                        查看详情
                      </Link>
                    </Button>

                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuLabel>操作</DropdownMenuLabel>
                        <DropdownMenuItem asChild>
                          <Link href={`/meetings/${meeting.id}/edit`}>
                            编辑会议
                          </Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem asChild>
                          <Link href={`/meetings/${meeting.id}/notes`}>
                            查看笔记
                          </Link>
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => setExportDialog({ open: true, meeting })}>
                          <Download className="h-4 w-4 mr-2" />
                          导出会议
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem 
                          className="text-red-600"
                          onClick={() => handleDeleteMeeting(meeting.id)}
                        >
                          删除会议
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        ) : (
          <Card>
            <CardContent className="p-12">
              <div className="text-center space-y-4">
                <Calendar className="h-12 w-12 text-muted-foreground mx-auto" />
                <div>
                  <h3 className="text-lg font-medium">
                    {searchTerm || statusFilter !== 'all' ? '没有找到匹配的会议' : '还没有会议记录'}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {searchTerm || statusFilter !== 'all' 
                      ? '尝试修改搜索条件或过滤器' 
                      : '创建您的第一个会议开始使用吧'
                    }
                  </p>
                </div>
                {!searchTerm && statusFilter === 'all' && (
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
      {exportDialog.meeting && (
        <ExportDialog
          open={exportDialog.open}
          onOpenChange={(open) => setExportDialog({ open, meeting: open ? exportDialog.meeting : undefined })}
          type="meeting"
          data={exportDialog.meeting}
        />
      )}

      <BatchExportDialog
        open={batchExportDialog}
        onOpenChange={setBatchExportDialog}
        meetings={meetings}
      />
    </div>
  );
}