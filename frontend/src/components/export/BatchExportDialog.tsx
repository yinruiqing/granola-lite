'use client';

import { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Calendar, Download, Search, Filter, Package, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { ExportFormat, exportService } from '@/lib/export-service';
import { Meeting } from '@/types';

interface BatchExportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  meetings: Meeting[];
}

type FilterStatus = 'all' | 'scheduled' | 'in_progress' | 'completed' | 'cancelled';

interface ExportProgress {
  total: number;
  completed: number;
  failed: number;
  current?: string;
}

const statusLabels: Record<string, string> = {
  scheduled: '已安排',
  in_progress: '进行中', 
  completed: '已完成',
  cancelled: '已取消'
};

export function BatchExportDialog({ open, onOpenChange, meetings }: BatchExportDialogProps) {
  const [selectedMeetings, setSelectedMeetings] = useState<Set<number>>(new Set());
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('markdown');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all');
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState<ExportProgress | null>(null);
  const [exportResults, setExportResults] = useState<string[]>([]);

  // 筛选会议
  const filteredMeetings = useMemo(() => {
    return meetings.filter(meeting => {
      const matchesSearch = !searchQuery || 
        meeting.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        meeting.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        meeting.participants?.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesStatus = statusFilter === 'all' || meeting.status === statusFilter;
      
      return matchesSearch && matchesStatus;
    });
  }, [meetings, searchQuery, statusFilter]);

  // 处理选择所有会议
  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedMeetings(new Set(filteredMeetings.map(m => m.id)));
    } else {
      setSelectedMeetings(new Set());
    }
  };

  // 处理单个会议选择
  const handleSelectMeeting = (meetingId: number, checked: boolean) => {
    const newSelected = new Set(selectedMeetings);
    if (checked) {
      newSelected.add(meetingId);
    } else {
      newSelected.delete(meetingId);
    }
    setSelectedMeetings(newSelected);
  };

  // 获取选中的会议
  const selectedMeetingsList = useMemo(() => {
    return meetings.filter(m => selectedMeetings.has(m.id));
  }, [meetings, selectedMeetings]);

  // 批量导出
  const handleBatchExport = async () => {
    if (selectedMeetingsList.length === 0) {
      return;
    }

    setIsExporting(true);
    setExportProgress({
      total: selectedMeetingsList.length,
      completed: 0,
      failed: 0
    });
    setExportResults([]);

    const results: string[] = [];

    for (let i = 0; i < selectedMeetingsList.length; i++) {
      const meeting = selectedMeetingsList[i];
      
      setExportProgress(prev => prev ? {
        ...prev,
        current: meeting.title
      } : null);

      try {
        const result = await exportService.exportMeeting(meeting, {
          format: selectedFormat,
          includeMetadata: true,
          includeTranscription: true,
          includeNotes: true,
          includeAIEnhancements: true,
        });

        if (result.success) {
          results.push(`✅ ${meeting.title} - 导出成功`);
          setExportProgress(prev => prev ? {
            ...prev,
            completed: prev.completed + 1
          } : null);
        } else {
          results.push(`❌ ${meeting.title} - ${result.error}`);
          setExportProgress(prev => prev ? {
            ...prev,
            failed: prev.failed + 1
          } : null);
        }
      } catch (error) {
        results.push(`❌ ${meeting.title} - 导出失败: ${error instanceof Error ? error.message : '未知错误'}`);
        setExportProgress(prev => prev ? {
          ...prev,
          failed: prev.failed + 1
        } : null);
      }

      // 短暂延迟，避免过快操作
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    setExportResults(results);
    setIsExporting(false);
    
    // 3秒后自动关闭对话框
    setTimeout(() => {
      onOpenChange(false);
      setExportProgress(null);
      setExportResults([]);
      setSelectedMeetings(new Set());
    }, 3000);
  };

  const isAllSelected = filteredMeetings.length > 0 && 
    filteredMeetings.every(meeting => selectedMeetings.has(meeting.id));
  const isIndeterminate = selectedMeetings.size > 0 && 
    !filteredMeetings.every(meeting => selectedMeetings.has(meeting.id));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            批量导出会议
          </DialogTitle>
          <DialogDescription>
            选择要导出的会议，支持多种格式和批量处理。
          </DialogDescription>
        </DialogHeader>

        {!isExporting ? (
          <div className="flex-1 space-y-4 overflow-hidden">
            {/* 搜索和筛选 */}
            <div className="flex gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                  <Input
                    placeholder="搜索会议标题、描述或参与者..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
              <Select value={statusFilter} onValueChange={(value: FilterStatus) => setStatusFilter(value)}>
                <SelectTrigger className="w-[180px]">
                  <div className="flex items-center gap-2">
                    <Filter className="h-4 w-4" />
                    <SelectValue />
                  </div>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  <SelectItem value="scheduled">已安排</SelectItem>
                  <SelectItem value="in_progress">进行中</SelectItem>
                  <SelectItem value="completed">已完成</SelectItem>
                  <SelectItem value="cancelled">已取消</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* 格式选择 */}
            <div className="space-y-2">
              <Label className="text-base font-medium">导出格式</Label>
              <Select value={selectedFormat} onValueChange={(value: ExportFormat) => setSelectedFormat(value)}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="json">JSON</SelectItem>
                  <SelectItem value="markdown">Markdown</SelectItem>
                  <SelectItem value="txt">纯文本</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* 会议选择 */}
            <div className="space-y-3 flex-1 overflow-hidden">
              <div className="flex items-center justify-between">
                <Label className="text-base font-medium">选择会议</Label>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span>已选择 {selectedMeetings.size} / {filteredMeetings.length} 个会议</span>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="select-all"
                      checked={isAllSelected}
                      ref={(ref) => {
                        if (ref) ref.indeterminate = isIndeterminate;
                      }}
                      onCheckedChange={handleSelectAll}
                    />
                    <Label htmlFor="select-all">全选</Label>
                  </div>
                </div>
              </div>

              <ScrollArea className="flex-1 border rounded-md">
                <div className="p-4 space-y-3">
                  {filteredMeetings.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <Calendar className="mx-auto h-12 w-12 mb-4 opacity-50" />
                      <p>没有找到匹配的会议</p>
                    </div>
                  ) : (
                    filteredMeetings.map((meeting) => (
                      <div
                        key={meeting.id}
                        className={cn(
                          "flex items-start space-x-3 p-3 rounded-lg border",
                          selectedMeetings.has(meeting.id) ? "border-primary bg-primary/5" : "border-border hover:bg-accent"
                        )}
                      >
                        <Checkbox
                          id={`meeting-${meeting.id}`}
                          checked={selectedMeetings.has(meeting.id)}
                          onCheckedChange={(checked) => handleSelectMeeting(meeting.id, checked as boolean)}
                        />
                        <div className="flex-1 space-y-1">
                          <div className="flex items-center gap-2">
                            <Label
                              htmlFor={`meeting-${meeting.id}`}
                              className="font-medium cursor-pointer"
                            >
                              {meeting.title}
                            </Label>
                            <Badge variant={meeting.status === 'completed' ? 'default' : 'secondary'}>
                              {statusLabels[meeting.status] || meeting.status}
                            </Badge>
                          </div>
                          {meeting.description && (
                            <p className="text-sm text-muted-foreground line-clamp-2">
                              {meeting.description}
                            </p>
                          )}
                          <div className="flex items-center gap-4 text-xs text-muted-foreground">
                            <span>创建时间: {format(new Date(meeting.created_at), "yyyy-MM-dd HH:mm", { locale: zhCN })}</span>
                            {meeting.participants && (
                              <span>参与者: {meeting.participants}</span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </ScrollArea>
            </div>

            {/* 操作按钮 */}
            <div className="flex justify-end space-x-2">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                取消
              </Button>
              <Button 
                onClick={handleBatchExport} 
                disabled={selectedMeetings.size === 0}
              >
                <Download className="mr-2 h-4 w-4" />
                导出 {selectedMeetings.size} 个会议
              </Button>
            </div>
          </div>
        ) : (
          /* 导出进度 */
          <div className="flex-1 space-y-6">
            <div className="text-center space-y-4">
              <div className="mx-auto w-16 h-16 relative">
                <div className="absolute inset-0 rounded-full border-4 border-primary/20"></div>
                <div className="absolute inset-0 rounded-full border-4 border-primary border-t-transparent animate-spin"></div>
                <Package className="absolute inset-0 w-8 h-8 m-auto text-primary" />
              </div>
              
              {exportProgress && (
                <div className="space-y-2">
                  <div className="text-lg font-medium">正在导出会议...</div>
                  <div className="text-sm text-muted-foreground">
                    {exportProgress.current && `当前: ${exportProgress.current}`}
                  </div>
                  <div className="flex justify-center items-center gap-4 text-sm">
                    <div className="flex items-center gap-1 text-green-600">
                      <CheckCircle2 className="h-4 w-4" />
                      {exportProgress.completed} 成功
                    </div>
                    <div className="flex items-center gap-1 text-red-600">
                      <AlertCircle className="h-4 w-4" />
                      {exportProgress.failed} 失败
                    </div>
                    <div className="text-muted-foreground">
                      总计: {exportProgress.total}
                    </div>
                  </div>
                  <div className="w-full bg-secondary rounded-full h-2">
                    <div 
                      className="bg-primary h-2 rounded-full transition-all duration-300"
                      style={{ 
                        width: `${((exportProgress.completed + exportProgress.failed) / exportProgress.total) * 100}%` 
                      }}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* 导出结果 */}
            {exportResults.length > 0 && (
              <ScrollArea className="h-[200px] border rounded-md p-4">
                <div className="space-y-2">
                  {exportResults.map((result, index) => (
                    <div
                      key={index}
                      className={cn(
                        "text-sm p-2 rounded",
                        result.startsWith('✅') ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
                      )}
                    >
                      {result}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}

            {!exportProgress && exportResults.length > 0 && (
              <div className="text-center">
                <Button variant="outline" onClick={() => onOpenChange(false)}>
                  关闭
                </Button>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}