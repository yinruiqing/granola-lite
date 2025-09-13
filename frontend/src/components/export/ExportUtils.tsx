'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { 
  Download, 
  FileText, 
  Settings, 
  History, 
  Filter,
  Calendar,
  Clock,
  Package,
  CheckCircle2,
  AlertCircle,
  Info,
  Zap,
  Target
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface ExportTaskStatus {
  id: string;
  name: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  startTime: Date;
  endTime?: Date;
  error?: string;
  result?: {
    filename: string;
    size: number;
    downloadUrl?: string;
  };
}

interface ExportUtilsProps {
  className?: string;
}

export function ExportUtils({ className }: ExportUtilsProps) {
  const [exportTasks, setExportTasks] = useState<ExportTaskStatus[]>([]);
  const [exportPresets, setExportPresets] = useState([
    {
      id: '1',
      name: '标准导出',
      description: '包含所有基本信息的Markdown格式',
      format: 'markdown',
      options: {
        includeMetadata: true,
        includeTranscription: true,
        includeNotes: true
      }
    },
    {
      id: '2', 
      name: '数据备份',
      description: '完整的JSON格式数据备份',
      format: 'json',
      options: {
        includeMetadata: true,
        includeTranscription: true,
        includeNotes: true,
        includeAIEnhancements: true
      }
    }
  ]);

  const [selectedPreset, setSelectedPreset] = useState<string>('');
  const [customExportSettings, setCustomExportSettings] = useState({
    name: '',
    description: '',
    format: 'markdown',
    schedule: {
      enabled: false,
      frequency: 'weekly', // daily, weekly, monthly
      time: '09:00'
    },
    filters: {
      dateRange: {
        enabled: false,
        start: '',
        end: ''
      },
      status: {
        enabled: false,
        values: []
      }
    }
  });

  // 模拟导出任务执行
  const simulateExportTask = (taskName: string) => {
    const taskId = Date.now().toString();
    const newTask: ExportTaskStatus = {
      id: taskId,
      name: taskName,
      status: 'pending',
      progress: 0,
      startTime: new Date()
    };

    setExportTasks(prev => [newTask, ...prev]);

    // 模拟任务进度
    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 20;
      if (progress >= 100) {
        progress = 100;
        clearInterval(interval);
        
        setExportTasks(prev => prev.map(task => 
          task.id === taskId ? {
            ...task,
            status: Math.random() > 0.1 ? 'completed' : 'failed',
            progress: 100,
            endTime: new Date(),
            error: Math.random() > 0.1 ? undefined : '导出过程中发生错误',
            result: Math.random() > 0.1 ? {
              filename: `export-${taskName}-${Date.now()}.zip`,
              size: Math.floor(Math.random() * 10000) + 1000,
              downloadUrl: '#'
            } : undefined
          } : task
        ));
      } else {
        setExportTasks(prev => prev.map(task => 
          task.id === taskId ? {
            ...task,
            status: 'processing',
            progress: Math.floor(progress)
          } : task
        ));
      }
    }, 500);
  };

  const getStatusIcon = (status: ExportTaskStatus['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-4 w-4 text-green-600" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-600" />;
      case 'processing':
        return <div className="h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />;
      default:
        return <Clock className="h-4 w-4 text-gray-600" />;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getTaskDuration = (task: ExportTaskStatus) => {
    const end = task.endTime || new Date();
    const duration = end.getTime() - task.startTime.getTime();
    return `${Math.floor(duration / 1000)}s`;
  };

  return (
    <div className={cn("space-y-6", className)}>
      {/* 导出预设 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            快速导出
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2">
            {exportPresets.map((preset) => (
              <Card 
                key={preset.id}
                className={cn(
                  "cursor-pointer transition-colors border-2",
                  selectedPreset === preset.id ? "border-primary" : "border-border hover:border-primary/50"
                )}
                onClick={() => setSelectedPreset(preset.id)}
              >
                <CardContent className="p-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium">{preset.name}</h4>
                      <Badge variant="outline">{preset.format}</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{preset.description}</p>
                    <Button 
                      size="sm" 
                      className="w-full"
                      onClick={(e) => {
                        e.stopPropagation();
                        simulateExportTask(preset.name);
                      }}
                    >
                      <Download className="h-3 w-3 mr-1" />
                      立即导出
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 批量导出工具 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            批量导出工具
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <Button 
              variant="outline" 
              className="h-auto p-4 flex-col space-y-2"
              onClick={() => simulateExportTask('全部会议')}
            >
              <Calendar className="h-6 w-6" />
              <div className="text-center">
                <div className="font-medium">全部会议</div>
                <div className="text-xs text-muted-foreground">导出所有会议记录</div>
              </div>
            </Button>

            <Button 
              variant="outline" 
              className="h-auto p-4 flex-col space-y-2"
              onClick={() => simulateExportTask('最近笔记')}
            >
              <FileText className="h-6 w-6" />
              <div className="text-center">
                <div className="font-medium">最近笔记</div>
                <div className="text-xs text-muted-foreground">过去30天的笔记</div>
              </div>
            </Button>

            <Button 
              variant="outline" 
              className="h-auto p-4 flex-col space-y-2"
              onClick={() => simulateExportTask('完整数据')}
            >
              <Package className="h-6 w-6" />
              <div className="text-center">
                <div className="font-medium">完整备份</div>
                <div className="text-xs text-muted-foreground">包含所有数据</div>
              </div>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 导出历史和任务状态 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            导出历史
          </CardTitle>
        </CardHeader>
        <CardContent>
          {exportTasks.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <History className="mx-auto h-12 w-12 mb-4 opacity-50" />
              <p>还没有导出任务</p>
              <p className="text-sm">开始您的第一次导出吧</p>
            </div>
          ) : (
            <ScrollArea className="h-[300px]">
              <div className="space-y-3">
                {exportTasks.map((task) => (
                  <div key={task.id} className="border rounded-lg p-4">
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(task.status)}
                          <span className="font-medium">{task.name}</span>
                          <Badge variant={
                            task.status === 'completed' ? 'default' :
                            task.status === 'failed' ? 'destructive' :
                            task.status === 'processing' ? 'secondary' : 'outline'
                          }>
                            {task.status === 'completed' ? '已完成' :
                             task.status === 'failed' ? '失败' :
                             task.status === 'processing' ? '进行中' : '等待中'}
                          </Badge>
                        </div>
                        
                        <div className="text-sm text-muted-foreground space-y-1">
                          <div>开始时间: {format(task.startTime, "yyyy-MM-dd HH:mm:ss", { locale: zhCN })}</div>
                          {task.endTime && (
                            <div>耗时: {getTaskDuration(task)}</div>
                          )}
                          {task.error && (
                            <div className="text-red-600">错误: {task.error}</div>
                          )}
                          {task.result && (
                            <div className="flex items-center gap-4">
                              <span>文件: {task.result.filename}</span>
                              <span>大小: {formatFileSize(task.result.size)}</span>
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="text-right space-y-2">
                        {task.status === 'processing' && (
                          <div className="text-sm">{task.progress}%</div>
                        )}
                        {task.result && task.status === 'completed' && (
                          <Button size="sm" variant="outline">
                            <Download className="h-3 w-3 mr-1" />
                            下载
                          </Button>
                        )}
                      </div>
                    </div>

                    {task.status === 'processing' && (
                      <div className="mt-3">
                        <div className="w-full bg-secondary rounded-full h-2">
                          <div 
                            className="bg-primary h-2 rounded-full transition-all duration-300"
                            style={{ width: `${task.progress}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      {/* 高级导出设置 */}
      <Dialog>
        <DialogTrigger asChild>
          <Button variant="outline" className="w-full">
            <Settings className="h-4 w-4 mr-2" />
            高级导出设置
          </Button>
        </DialogTrigger>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle>高级导出配置</DialogTitle>
            <DialogDescription>
              创建自定义导出配置和定时任务
            </DialogDescription>
          </DialogHeader>
          
          <Tabs defaultValue="custom" className="flex-1 overflow-hidden">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="custom">自定义导出</TabsTrigger>
              <TabsTrigger value="schedule">定时任务</TabsTrigger>
            </TabsList>
            
            <TabsContent value="custom" className="space-y-4 overflow-y-auto">
              <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label>配置名称</Label>
                    <Input placeholder="我的导出配置" />
                  </div>
                  <div className="space-y-2">
                    <Label>导出格式</Label>
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="选择格式" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="json">JSON</SelectItem>
                        <SelectItem value="markdown">Markdown</SelectItem>
                        <SelectItem value="txt">纯文本</SelectItem>
                        <SelectItem value="pdf">PDF (实验性)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>描述</Label>
                  <Textarea placeholder="描述这个导出配置的用途..." />
                </div>

                <Separator />

                <div className="space-y-4">
                  <Label className="text-base font-medium">导出选项</Label>
                  <div className="grid gap-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">包含元数据</div>
                        <div className="text-sm text-muted-foreground">会议时间、参与者等信息</div>
                      </div>
                      <Switch />
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">包含转录内容</div>
                        <div className="text-sm text-muted-foreground">语音转文字记录</div>
                      </div>
                      <Switch />
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">包含AI增强</div>
                        <div className="text-sm text-muted-foreground">AI优化的摘要和总结</div>
                      </div>
                      <Switch />
                    </div>
                  </div>
                </div>

                <div className="flex justify-end space-x-2">
                  <Button variant="outline">取消</Button>
                  <Button>保存配置</Button>
                </div>
              </div>
            </TabsContent>
            
            <TabsContent value="schedule" className="space-y-4 overflow-y-auto">
              <div className="space-y-4">
                <div className="p-4 border rounded-lg bg-blue-50 dark:bg-blue-950/20">
                  <div className="flex items-start space-x-3">
                    <Info className="h-5 w-5 text-blue-600 mt-0.5" />
                    <div>
                      <div className="font-medium text-blue-900 dark:text-blue-100">定时导出功能</div>
                      <div className="text-sm text-blue-700 dark:text-blue-300">
                        设置定时任务，自动导出您的会议数据。支持每日、每周、每月的导出频率。
                      </div>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">启用定时导出</div>
                      <div className="text-sm text-muted-foreground">按计划自动导出数据</div>
                    </div>
                    <Switch />
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label>导出频率</Label>
                      <Select>
                        <SelectTrigger>
                          <SelectValue placeholder="选择频率" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="daily">每日</SelectItem>
                          <SelectItem value="weekly">每周</SelectItem>
                          <SelectItem value="monthly">每月</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>执行时间</Label>
                      <Input type="time" defaultValue="09:00" />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>导出配置</Label>
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder="选择导出配置" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="standard">标准导出</SelectItem>
                        <SelectItem value="backup">数据备份</SelectItem>
                        <SelectItem value="custom">自定义配置</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="flex justify-end space-x-2">
                  <Button variant="outline">取消</Button>
                  <Button>
                    <Zap className="h-4 w-4 mr-2" />
                    设置定时任务
                  </Button>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>
    </div>
  );
}