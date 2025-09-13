'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Download,
  Package,
  History,
  Settings,
  BarChart3,
  Calendar,
  FileText,
  Users,
  Clock,
  TrendingUp,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { useAppStore } from '@/lib/store';
import { storageManager } from '@/lib/storage';
import { Meeting, Note } from '@/types';
import { ExportUtils } from '@/components/export/ExportUtils';
import { ExportDialog } from '@/components/export/ExportDialog';
import { BatchExportDialog } from '@/components/export/BatchExportDialog';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';

export default function ExportPage() {
  const { meetings } = useAppStore();
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [exportDialog, setExportDialog] = useState<{ 
    open: boolean; 
    type?: 'meeting' | 'meetings' | 'note'; 
    data?: any 
  }>({ open: false });
  const [batchExportDialog, setBatchExportDialog] = useState(false);

  // 加载笔记数据
  useEffect(() => {
    const loadNotes = async () => {
      try {
        const allNotes: Note[] = [];
        for (const meeting of meetings) {
          const meetingNotes = await storageManager.getNotesByMeeting(meeting.id);
          allNotes.push(...meetingNotes);
        }
        setNotes(allNotes);
      } catch (error) {
        console.error('加载笔记失败:', error);
      } finally {
        setLoading(false);
      }
    };

    if (meetings.length > 0) {
      loadNotes();
    } else {
      setLoading(false);
    }
  }, [meetings]);

  // 统计数据
  const stats = {
    totalMeetings: meetings.length,
    totalNotes: notes.length,
    completedMeetings: meetings.filter(m => m.status === 'completed').length,
    recentMeetings: meetings.filter(m => {
      const meetingDate = new Date(m.created_at);
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
      return meetingDate >= thirtyDaysAgo;
    }).length,
    totalParticipants: new Set(
      meetings.flatMap(m => m.participants ? m.participants.split(',').map(p => p.trim()) : [])
    ).size,
    averageMeetingDuration: meetings.reduce((acc, m) => acc + (m.duration || 0), 0) / (meetings.length || 1)
  };

  // 最近的导出活动（模拟数据）
  const recentExports = [
    {
      id: '1',
      name: '月度会议报告',
      type: 'meetings',
      format: 'markdown',
      date: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
      status: 'completed',
      size: '2.4 MB'
    },
    {
      id: '2',
      name: '项目笔记备份',
      type: 'notes',
      format: 'json',
      date: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000),
      status: 'completed',
      size: '1.8 MB'
    },
    {
      id: '3',
      name: '全量数据导出',
      type: 'all',
      format: 'json',
      date: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
      status: 'failed',
      size: '-'
    }
  ];

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'meetings': return '会议';
      case 'notes': return '笔记';
      case 'templates': return '模板';
      case 'all': return '全部';
      default: return type;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <Badge variant="default" className="bg-green-100 text-green-800">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            已完成
          </Badge>
        );
      case 'failed':
        return (
          <Badge variant="destructive">
            <AlertCircle className="h-3 w-3 mr-1" />
            失败
          </Badge>
        );
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p>加载数据中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">数据导出</h1>
          <p className="text-muted-foreground">
            导出您的会议记录、笔记和模板，支持多种格式
          </p>
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
          <Button onClick={() => setExportDialog({ 
            open: true, 
            type: 'meetings', 
            data: meetings 
          })}>
            <Download className="h-4 w-4 mr-2" />
            快速导出
          </Button>
        </div>
      </div>

      {/* 数据统计概览 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总会议数</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalMeetings}</div>
            <p className="text-xs text-muted-foreground">
              其中 {stats.completedMeetings} 个已完成
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">笔记总数</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalNotes}</div>
            <p className="text-xs text-muted-foreground">
              平均每个会议 {Math.round(stats.totalNotes / (stats.totalMeetings || 1))} 条笔记
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">参与者</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalParticipants}</div>
            <p className="text-xs text-muted-foreground">
              不同的参与者人数
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">平均时长</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {Math.round(stats.averageMeetingDuration / 60)}min
            </div>
            <p className="text-xs text-muted-foreground">
              每个会议的平均持续时间
            </p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="tools" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="tools">导出工具</TabsTrigger>
          <TabsTrigger value="history">导出历史</TabsTrigger>
          <TabsTrigger value="analytics">数据分析</TabsTrigger>
        </TabsList>
        
        <TabsContent value="tools">
          <ExportUtils />
        </TabsContent>
        
        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <History className="h-5 w-5" />
                最近的导出记录
              </CardTitle>
            </CardHeader>
            <CardContent>
              {recentExports.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <History className="mx-auto h-12 w-12 mb-4 opacity-50" />
                  <p>还没有导出记录</p>
                  <p className="text-sm">开始您的第一次导出吧</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {recentExports.map((exportRecord) => (
                    <div key={exportRecord.id} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <h4 className="font-medium">{exportRecord.name}</h4>
                            {getStatusBadge(exportRecord.status)}
                          </div>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <span>类型: {getTypeLabel(exportRecord.type)}</span>
                            <span>格式: {exportRecord.format.toUpperCase()}</span>
                            <span>大小: {exportRecord.size}</span>
                          </div>
                          <div className="text-xs text-muted-foreground">
                            导出时间: {format(exportRecord.date, "yyyy-MM-dd HH:mm", { locale: zhCN })}
                          </div>
                        </div>
                        {exportRecord.status === 'completed' && (
                          <Button variant="outline" size="sm">
                            <Download className="h-3 w-3 mr-1" />
                            重新下载
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
        
        <TabsContent value="analytics" className="space-y-4">
          {/* 数据使用分析 */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  内容分布
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">会议记录</span>
                    <div className="flex items-center gap-2">
                      <div className="w-32 bg-secondary rounded-full h-2">
                        <div className="bg-blue-600 h-2 rounded-full w-3/4"></div>
                      </div>
                      <span className="text-sm font-medium">{stats.totalMeetings}</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">会议笔记</span>
                    <div className="flex items-center gap-2">
                      <div className="w-32 bg-secondary rounded-full h-2">
                        <div className="bg-green-600 h-2 rounded-full w-5/6"></div>
                      </div>
                      <span className="text-sm font-medium">{stats.totalNotes}</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">活跃参与者</span>
                    <div className="flex items-center gap-2">
                      <div className="w-32 bg-secondary rounded-full h-2">
                        <div className="bg-orange-600 h-2 rounded-full w-1/2"></div>
                      </div>
                      <span className="text-sm font-medium">{stats.totalParticipants}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  活跃度趋势
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">最近30天</span>
                    <Badge variant="outline">{stats.recentMeetings} 个会议</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">会议完成率</span>
                    <Badge variant="default">
                      {Math.round((stats.completedMeetings / (stats.totalMeetings || 1)) * 100)}%
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">平均会议时长</span>
                    <Badge variant="secondary">
                      {Math.round(stats.averageMeetingDuration / 60)} 分钟
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 导出建议 */}
          <Card>
            <CardHeader>
              <CardTitle>智能导出建议</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="border-l-4 border-blue-500 pl-4">
                  <h4 className="font-medium">建议导出最近会议</h4>
                  <p className="text-sm text-muted-foreground">
                    您有 {stats.recentMeetings} 个最近的会议记录，建议导出为 Markdown 格式便于查阅
                  </p>
                </div>
                <div className="border-l-4 border-green-500 pl-4">
                  <h4 className="font-medium">数据备份建议</h4>
                  <p className="text-sm text-muted-foreground">
                    建议定期将所有数据导出为 JSON 格式作为备份，确保数据安全
                  </p>
                </div>
                <div className="border-l-4 border-orange-500 pl-4">
                  <h4 className="font-medium">分享格式优化</h4>
                  <p className="text-sm text-muted-foreground">
                    如需与他人分享会议记录，推荐使用 PDF 或 Markdown 格式，便于阅读和打印
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* 导出对话框 */}
      {exportDialog.data && (
        <ExportDialog
          open={exportDialog.open}
          onOpenChange={(open) => setExportDialog({ open, type: open ? exportDialog.type : undefined, data: open ? exportDialog.data : undefined })}
          type={exportDialog.type!}
          data={exportDialog.data}
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