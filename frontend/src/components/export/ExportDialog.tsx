'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { CalendarIcon, Download, FileText, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { ExportFormat, ExportOptions, exportService } from '@/lib/export-service';
import { Meeting, Note, Template } from '@/types';

interface ExportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  type: 'meeting' | 'meetings' | 'note' | 'template';
  data: Meeting | Meeting[] | Note | Template;
  title?: string;
}

const formatOptions: { value: ExportFormat; label: string; description: string }[] = [
  { value: 'json', label: 'JSON', description: '结构化数据格式，适合程序处理' },
  { value: 'markdown', label: 'Markdown', description: '文档格式，支持富文本显示' },
  { value: 'txt', label: '纯文本', description: '简单文本格式，通用性好' },
  { value: 'docx', label: 'Word文档', description: 'Microsoft Word格式（实验性）' },
  { value: 'pdf', label: 'PDF文档', description: 'PDF格式（实验性）' },
];

export function ExportDialog({ open, onOpenChange, type, data, title }: ExportDialogProps) {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('markdown');
  const [options, setOptions] = useState<ExportOptions>({
    format: 'markdown',
    includeMetadata: true,
    includeTranscription: true,
    includeNotes: true,
    includeAIEnhancements: true,
  });
  const [dateRange, setDateRange] = useState<{ start?: Date; end?: Date }>({});
  const [isExporting, setIsExporting] = useState(false);
  const [exportResult, setExportResult] = useState<string>('');

  // 获取可用的格式选项
  const getAvailableFormats = () => {
    if (type === 'meetings') {
      return formatOptions.filter(f => ['json', 'markdown', 'txt'].includes(f.value));
    }
    return formatOptions;
  };

  const handleFormatChange = (format: ExportFormat) => {
    setSelectedFormat(format);
    setOptions(prev => ({ ...prev, format }));
  };

  const handleExport = async () => {
    setIsExporting(true);
    setExportResult('');
    
    try {
      const exportOptions: ExportOptions = {
        ...options,
        format: selectedFormat,
        dateRange: dateRange.start && dateRange.end ? {
          start: dateRange.start,
          end: dateRange.end
        } : undefined,
      };

      let result;
      
      switch (type) {
        case 'meeting':
          result = await exportService.exportMeeting(data as Meeting, exportOptions);
          break;
        case 'meetings':
          result = await exportService.exportMeetings(data as Meeting[], exportOptions);
          break;
        case 'note':
          result = await exportService.exportNote(data as Note, selectedFormat);
          break;
        case 'template':
          result = await exportService.exportTemplate(data as Template, selectedFormat);
          break;
        default:
          throw new Error('不支持的导出类型');
      }

      if (result.success) {
        setExportResult(`导出成功！文件名: ${result.filename}`);
        setTimeout(() => {
          onOpenChange(false);
          setExportResult('');
        }, 2000);
      } else {
        setExportResult(`导出失败: ${result.error}`);
      }
    } catch (error) {
      setExportResult(`导出失败: ${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setIsExporting(false);
    }
  };

  const getDialogTitle = () => {
    switch (type) {
      case 'meeting':
        return `导出会议: ${(data as Meeting).title}`;
      case 'meetings':
        return `批量导出会议 (${(data as Meeting[]).length} 个)`;
      case 'note':
        return `导出笔记: ${(data as Note).title || '无标题'}`;
      case 'template':
        return `导出模板: ${(data as Template).name}`;
      default:
        return '导出';
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            {title || getDialogTitle()}
          </DialogTitle>
          <DialogDescription>
            选择导出格式和选项，然后下载文件到本地。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* 格式选择 */}
          <div className="space-y-3">
            <Label className="text-base font-medium">导出格式</Label>
            <div className="grid gap-3">
              {getAvailableFormats().map((format) => (
                <div
                  key={format.value}
                  className={cn(
                    "flex items-start space-x-3 rounded-lg border p-4 cursor-pointer transition-colors",
                    selectedFormat === format.value ? "border-primary bg-primary/5" : "border-border hover:bg-accent"
                  )}
                  onClick={() => handleFormatChange(format.value)}
                >
                  <input
                    type="radio"
                    name="format"
                    value={format.value}
                    checked={selectedFormat === format.value}
                    onChange={() => handleFormatChange(format.value)}
                    className="mt-1"
                  />
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      <span className="font-medium">{format.label}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">{format.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 导出选项 */}
          {(type === 'meeting' || type === 'meetings') && (
            <Tabs defaultValue="options" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="options">导出选项</TabsTrigger>
                <TabsTrigger value="filters">筛选条件</TabsTrigger>
              </TabsList>
              
              <TabsContent value="options" className="space-y-4">
                <div className="grid gap-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label className="text-base">包含元数据</Label>
                      <p className="text-sm text-muted-foreground">会议时间、参与者等基本信息</p>
                    </div>
                    <Switch
                      checked={options.includeMetadata}
                      onCheckedChange={(checked) => setOptions(prev => ({ ...prev, includeMetadata: checked }))}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label className="text-base">包含转录内容</Label>
                      <p className="text-sm text-muted-foreground">会议的语音转录记录</p>
                    </div>
                    <Switch
                      checked={options.includeTranscription}
                      onCheckedChange={(checked) => setOptions(prev => ({ ...prev, includeTranscription: checked }))}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label className="text-base">包含笔记内容</Label>
                      <p className="text-sm text-muted-foreground">手动编写的会议笔记</p>
                    </div>
                    <Switch
                      checked={options.includeNotes}
                      onCheckedChange={(checked) => setOptions(prev => ({ ...prev, includeNotes: checked }))}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label className="text-base">包含AI增强内容</Label>
                      <p className="text-sm text-muted-foreground">AI优化后的摘要和总结</p>
                    </div>
                    <Switch
                      checked={options.includeAIEnhancements}
                      onCheckedChange={(checked) => setOptions(prev => ({ ...prev, includeAIEnhancements: checked }))}
                    />
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="filters" className="space-y-4">
                {type === 'meetings' && (
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label className="text-base">日期范围</Label>
                      <p className="text-sm text-muted-foreground">只导出指定日期范围内的会议</p>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="space-y-2">
                        <Label>开始日期</Label>
                        <Popover>
                          <PopoverTrigger asChild>
                            <Button
                              variant="outline"
                              className={cn(
                                "w-full justify-start text-left font-normal",
                                !dateRange.start && "text-muted-foreground"
                              )}
                            >
                              <CalendarIcon className="mr-2 h-4 w-4" />
                              {dateRange.start ? (
                                format(dateRange.start, "PPP", { locale: zhCN })
                              ) : (
                                "选择开始日期"
                              )}
                            </Button>
                          </PopoverTrigger>
                          <PopoverContent className="w-auto p-0">
                            <Calendar
                              mode="single"
                              selected={dateRange.start}
                              onSelect={(date) => setDateRange(prev => ({ ...prev, start: date }))}
                              initialFocus
                            />
                          </PopoverContent>
                        </Popover>
                      </div>

                      <div className="space-y-2">
                        <Label>结束日期</Label>
                        <Popover>
                          <PopoverTrigger asChild>
                            <Button
                              variant="outline"
                              className={cn(
                                "w-full justify-start text-left font-normal",
                                !dateRange.end && "text-muted-foreground"
                              )}
                            >
                              <CalendarIcon className="mr-2 h-4 w-4" />
                              {dateRange.end ? (
                                format(dateRange.end, "PPP", { locale: zhCN })
                              ) : (
                                "选择结束日期"
                              )}
                            </Button>
                          </PopoverTrigger>
                          <PopoverContent className="w-auto p-0">
                            <Calendar
                              mode="single"
                              selected={dateRange.end}
                              onSelect={(date) => setDateRange(prev => ({ ...prev, end: date }))}
                              initialFocus
                            />
                          </PopoverContent>
                        </Popover>
                      </div>
                    </div>
                  </div>
                )}
              </TabsContent>
            </Tabs>
          )}

          {/* 导出结果 */}
          {exportResult && (
            <div className={cn(
              "rounded-lg p-3 text-sm",
              exportResult.includes('成功') ? "bg-green-50 text-green-700 border border-green-200" : "bg-red-50 text-red-700 border border-red-200"
            )}>
              {exportResult}
            </div>
          )}

          {/* 操作按钮 */}
          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isExporting}>
              取消
            </Button>
            <Button onClick={handleExport} disabled={isExporting}>
              {isExporting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  导出中...
                </>
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  开始导出
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}