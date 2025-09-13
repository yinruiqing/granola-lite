'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useAppStore } from '@/lib/store';
import { storageManager } from '@/lib/storage';
import { Template } from '@/types';
import Link from 'next/link';

export default function NewMeetingPage() {
  const router = useRouter();
  const { addMeeting } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [templates, setTemplates] = useState<Template[]>([]);

  // 表单状态
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    status: 'scheduled' as const,
    template_id: undefined as number | undefined,
  });

  // 加载模板
  useEffect(() => {
    const loadTemplates = async () => {
      try {
        const allTemplates = await storageManager.getAllTemplates();
        setTemplates(allTemplates);
      } catch (error) {
        console.error('加载模板失败:', error);
      }
    };

    loadTemplates();
  }, []);

  // 处理表单提交
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.title.trim()) {
      alert('请输入会议标题');
      return;
    }

    setLoading(true);
    try {
      const newMeeting = await storageManager.createMeeting({
        title: formData.title.trim(),
        description: formData.description.trim() || undefined,
        status: formData.status,
        template_id: formData.template_id,
      });

      addMeeting(newMeeting);
      router.push(`/meetings/${newMeeting.id}`);
    } catch (error) {
      console.error('创建会议失败:', error);
      alert('创建会议失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  // 处理输入变化
  const handleInputChange = (field: string, value: string | number) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div className="space-y-6">
      {/* 页面标题和导航 */}
      <div className="flex items-center space-x-4">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/meetings">
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回会议列表
          </Link>
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">创建新会议</h1>
          <p className="text-muted-foreground">填写会议基本信息</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid gap-6 lg:grid-cols-3">
          {/* 主要信息 */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle>基本信息</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* 会议标题 */}
                <div className="space-y-2">
                  <Label htmlFor="title">会议标题 *</Label>
                  <Input
                    id="title"
                    placeholder="输入会议标题"
                    value={formData.title}
                    onChange={(e) => handleInputChange('title', e.target.value)}
                    required
                  />
                </div>

                {/* 会议描述 */}
                <div className="space-y-2">
                  <Label htmlFor="description">会议描述</Label>
                  <Textarea
                    id="description"
                    placeholder="输入会议描述或议程"
                    rows={4}
                    value={formData.description}
                    onChange={(e) => handleInputChange('description', e.target.value)}
                  />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 设置选项 */}
          <div className="space-y-6">
            {/* 会议状态 */}
            <Card>
              <CardHeader>
                <CardTitle>会议状态</CardTitle>
              </CardHeader>
              <CardContent>
                <Select 
                  value={formData.status} 
                  onValueChange={(value: any) => handleInputChange('status', value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择会议状态" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="scheduled">已安排</SelectItem>
                    <SelectItem value="in_progress">进行中</SelectItem>
                    <SelectItem value="completed">已完成</SelectItem>
                  </SelectContent>
                </Select>
              </CardContent>
            </Card>

            {/* 会议模板 */}
            <Card>
              <CardHeader>
                <CardTitle>会议模板</CardTitle>
              </CardHeader>
              <CardContent>
                <Select 
                  value={formData.template_id?.toString() || "none"} 
                  onValueChange={(value) => handleInputChange('template_id', value === "none" ? undefined : parseInt(value))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择模板（可选）" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">不使用模板</SelectItem>
                    {templates.map((template) => (
                      <SelectItem key={template.id} value={template.id.toString()}>
                        {template.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                
                {templates.length === 0 && (
                  <p className="text-xs text-muted-foreground mt-2">
                    暂无可用模板，您可以在模板管理中创建
                  </p>
                )}
              </CardContent>
            </Card>

            {/* 操作按钮 */}
            <div className="flex flex-col gap-2">
              <Button type="submit" disabled={loading} className="w-full">
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    创建中...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    创建会议
                  </>
                )}
              </Button>
              
              <Button type="button" variant="outline" asChild className="w-full">
                <Link href="/meetings">取消</Link>
              </Button>
            </div>
          </div>
        </div>
      </form>

      {/* 模板预览 */}
      {formData.template_id && formData.template_id > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>模板预览</CardTitle>
          </CardHeader>
          <CardContent>
            {(() => {
              const selectedTemplate = templates.find(t => t.id === formData.template_id);
              if (!selectedTemplate) return <p className="text-muted-foreground">模板不存在</p>;
              
              return (
                <div className="space-y-3">
                  <div>
                    <h4 className="font-medium">{selectedTemplate.name}</h4>
                    {selectedTemplate.description && (
                      <p className="text-sm text-muted-foreground">{selectedTemplate.description}</p>
                    )}
                  </div>
                  
                  {selectedTemplate.structure?.sections && (
                    <div>
                      <h5 className="text-sm font-medium mb-2">建议的会议结构：</h5>
                      <ul className="text-sm text-muted-foreground space-y-1">
                        {selectedTemplate.structure.sections.map((section: string, index: number) => (
                          <li key={index} className="flex items-center">
                            <span className="w-2 h-2 bg-primary rounded-full mr-2 flex-shrink-0"></span>
                            {section}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })()}
          </CardContent>
        </Card>
      )}
    </div>
  );
}