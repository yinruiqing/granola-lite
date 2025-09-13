'use client';

import { useState, useEffect } from 'react';
import { 
  Plus,
  Search,
  Filter,
  Copy,
  Edit,
  Trash2,
  Eye,
  FileText,
  Settings,
  MoreHorizontal,
  CheckCircle,
  Calendar,
  Users,
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { storageManager } from '@/lib/storage';
import { Template } from '@/types';
import { TemplateEditor } from '@/components/templates/TemplateEditor';
import { ExportDialog } from '@/components/export/ExportDialog';

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [filteredTemplates, setFilteredTemplates] = useState<Template[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [showEditor, setShowEditor] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<Template | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exportDialog, setExportDialog] = useState<{ open: boolean; template?: Template }>({ open: false });

  // 加载模板
  useEffect(() => {
    const loadTemplates = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // 初始化默认模板
        await storageManager.initializeDefaultTemplates();
        
        const data = await storageManager.getAllTemplates();
        setTemplates(data);
        setFilteredTemplates(data);
      } catch (error) {
        console.error('加载模板失败:', error);
        setError('加载模板失败');
      } finally {
        setLoading(false);
      }
    };

    loadTemplates();
  }, []);

  // 筛选模板
  useEffect(() => {
    let filtered = templates;

    // 搜索过滤
    if (searchTerm) {
      filtered = filtered.filter(template =>
        template.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        template.description?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // 分类过滤
    if (categoryFilter !== 'all') {
      filtered = filtered.filter(template => template.category === categoryFilter);
    }

    // 状态过滤
    if (statusFilter !== 'all') {
      if (statusFilter === 'active') {
        filtered = filtered.filter(template => template.is_active);
      } else if (statusFilter === 'inactive') {
        filtered = filtered.filter(template => !template.is_active);
      } else if (statusFilter === 'default') {
        filtered = filtered.filter(template => template.is_default);
      }
    }

    setFilteredTemplates(filtered);
  }, [templates, searchTerm, categoryFilter, statusFilter]);

  // 删除模板
  const handleDeleteTemplate = async (id: number) => {
    const confirmed = confirm('确定要删除这个模板吗？此操作不可撤销。');
    if (!confirmed) return;

    try {
      const success = await storageManager.deleteTemplate(id);
      if (success) {
        setTemplates(prev => prev.filter(t => t.id !== id));
      }
    } catch (error) {
      console.error('删除模板失败:', error);
      setError('删除模板失败');
    }
  };

  // 复制模板
  const handleDuplicateTemplate = async (id: number) => {
    const original = templates.find(t => t.id === id);
    if (!original) return;

    const newName = prompt('请输入新模板名称:', `${original.name} - 副本`);
    if (!newName) return;

    try {
      const duplicated = await storageManager.duplicateTemplate(id, newName);
      if (duplicated) {
        setTemplates(prev => [duplicated, ...prev]);
      }
    } catch (error) {
      console.error('复制模板失败:', error);
      setError('复制模板失败');
    }
  };

  // 切换模板状态
  const handleToggleStatus = async (id: number) => {
    const template = templates.find(t => t.id === id);
    if (!template) return;

    try {
      const updated = await storageManager.updateTemplate(id, {
        is_active: !template.is_active
      });
      
      if (updated) {
        setTemplates(prev => prev.map(t => t.id === id ? updated : t));
      }
    } catch (error) {
      console.error('更新模板状态失败:', error);
      setError('更新模板状态失败');
    }
  };

  // 预览模板
  const handlePreviewTemplate = (template: Template) => {
    setSelectedTemplate(template);
    setShowPreview(true);
  };

  // 创建新模板
  const handleCreateTemplate = () => {
    setEditingTemplate(null);
    setShowEditor(true);
  };

  // 编辑模板
  const handleEditTemplate = (template: Template) => {
    setEditingTemplate(template);
    setShowEditor(true);
  };

  // 保存模板
  const handleSaveTemplate = async (templateData: Omit<Template, 'id' | 'created_at' | 'updated_at'>) => {
    try {
      if (editingTemplate) {
        // 更新现有模板
        const updated = await storageManager.updateTemplate(editingTemplate.id, templateData);
        if (updated) {
          setTemplates(prev => prev.map(t => t.id === editingTemplate.id ? updated : t));
        }
      } else {
        // 创建新模板
        const created = await storageManager.createTemplate(templateData);
        setTemplates(prev => [created, ...prev]);
      }
      
      setShowEditor(false);
      setEditingTemplate(null);
    } catch (error) {
      console.error('保存模板失败:', error);
      setError('保存模板失败');
    }
  };

  // 获取分类标签
  const getCategoryBadge = (category: string) => {
    const configs = {
      meeting: { label: '会议', color: 'bg-blue-100 text-blue-800' },
      notes: { label: '笔记', color: 'bg-green-100 text-green-800' },
      summary: { label: '总结', color: 'bg-purple-100 text-purple-800' },
      action_items: { label: '行动项', color: 'bg-orange-100 text-orange-800' },
    };
    
    const config = configs[category as keyof typeof configs] || { label: category, color: 'bg-gray-100 text-gray-800' };
    return (
      <Badge className={`${config.color} border-0`}>
        {config.label}
      </Badge>
    );
  };

  // 格式化时间
  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p>加载模板中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">模板管理</h1>
          <p className="text-muted-foreground">
            管理和自定义您的会议模板 ({templates.length} 个模板)
          </p>
        </div>

        <Button onClick={handleCreateTemplate}>
          <Plus className="h-4 w-4 mr-2" />
          新建模板
        </Button>
      </div>

      {/* 搜索和筛选 */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* 搜索框 */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
              <Input
                placeholder="搜索模板名称或描述..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* 分类筛选 */}
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-full sm:w-48">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="按分类筛选" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部分类</SelectItem>
                <SelectItem value="meeting">会议模板</SelectItem>
                <SelectItem value="notes">笔记模板</SelectItem>
                <SelectItem value="summary">总结模板</SelectItem>
                <SelectItem value="action_items">行动项模板</SelectItem>
              </SelectContent>
            </Select>

            {/* 状态筛选 */}
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-48">
                <Settings className="h-4 w-4 mr-2" />
                <SelectValue placeholder="按状态筛选" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="active">启用</SelectItem>
                <SelectItem value="inactive">禁用</SelectItem>
                <SelectItem value="default">默认模板</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* 统计信息 */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总模板数</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{templates.length}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">启用模板</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {templates.filter(t => t.is_active).length}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">默认模板</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {templates.filter(t => t.is_default).length}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">自定义模板</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {templates.filter(t => !t.is_default).length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 错误提示 */}
      {error && (
        <Card>
          <CardContent className="p-6">
            <div className="text-red-600">{error}</div>
          </CardContent>
        </Card>
      )}

      {/* 模板列表 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredTemplates.length > 0 ? (
          filteredTemplates.map((template) => (
            <Card key={template.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <CardTitle className="text-lg">{template.name}</CardTitle>
                      {template.is_default && (
                        <Badge variant="outline" className="text-xs">
                          默认
                        </Badge>
                      )}
                    </div>
                    {getCategoryBadge(template.category)}
                  </div>
                  
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="sm">
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuLabel>模板操作</DropdownMenuLabel>
                      <DropdownMenuItem onClick={() => handlePreviewTemplate(template)}>
                        <Eye className="h-4 w-4 mr-2" />
                        预览
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleEditTemplate(template)}>
                        <Edit className="h-4 w-4 mr-2" />
                        编辑
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleDuplicateTemplate(template.id)}>
                        <Copy className="h-4 w-4 mr-2" />
                        复制
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => setExportDialog({ open: true, template })}>
                        <Download className="h-4 w-4 mr-2" />
                        导出
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem 
                        onClick={() => handleToggleStatus(template.id)}
                      >
                        <CheckCircle className="h-4 w-4 mr-2" />
                        {template.is_active ? '禁用' : '启用'}
                      </DropdownMenuItem>
                      {!template.is_default && (
                        <DropdownMenuItem 
                          className="text-red-600"
                          onClick={() => handleDeleteTemplate(template.id)}
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          删除
                        </DropdownMenuItem>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </CardHeader>

              <CardContent>
                <div className="space-y-3">
                  {template.description && (
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {template.description}
                    </p>
                  )}

                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{template.structure.sections.length} 个部分</span>
                    <span>{formatTime(template.updated_at)}</span>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <div className={`w-2 h-2 rounded-full ${
                        template.is_active ? 'bg-green-500' : 'bg-gray-300'
                      }`} />
                      <span className="text-xs text-muted-foreground">
                        {template.is_active ? '启用' : '禁用'}
                      </span>
                    </div>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handlePreviewTemplate(template)}
                    >
                      <Eye className="h-3 w-3 mr-1" />
                      预览
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        ) : (
          <div className="col-span-full">
            <Card>
              <CardContent className="p-12">
                <div className="text-center space-y-4">
                  <FileText className="h-12 w-12 text-muted-foreground mx-auto" />
                  <div>
                    <h3 className="text-lg font-medium">
                      {searchTerm || categoryFilter !== 'all' || statusFilter !== 'all' 
                        ? '没有找到匹配的模板' 
                        : '还没有模板'
                      }
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      {searchTerm || categoryFilter !== 'all' || statusFilter !== 'all'
                        ? '尝试修改搜索条件或筛选器'
                        : '创建您的第一个自定义模板'
                      }
                    </p>
                  </div>
                  {!searchTerm && categoryFilter === 'all' && statusFilter === 'all' && (
                    <Button onClick={handleCreateTemplate}>
                      <Plus className="h-4 w-4 mr-2" />
                      新建模板
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>

      {/* 预览对话框 */}
      <Dialog open={showPreview} onOpenChange={setShowPreview}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedTemplate?.name}</DialogTitle>
            <DialogDescription>
              {selectedTemplate?.description}
            </DialogDescription>
          </DialogHeader>

          {selectedTemplate && (
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                {getCategoryBadge(selectedTemplate.category)}
                <Badge variant="outline">
                  {selectedTemplate.structure.sections.length} 个部分
                </Badge>
              </div>

              <div className="border rounded-lg p-4 bg-gray-50">
                <h3 className="font-semibold mb-3">{selectedTemplate.structure.title}</h3>
                
                <div className="space-y-3">
                  {selectedTemplate.structure.sections
                    .sort((a, b) => a.order - b.order)
                    .map((section) => (
                      <div key={section.id} className="border-l-2 border-blue-200 pl-3">
                        <div className="flex items-center space-x-2">
                          <h4 className="font-medium">{section.title}</h4>
                          {section.required && (
                            <Badge variant="destructive" className="text-xs">
                              必填
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          类型: {section.type} • {section.placeholder}
                        </p>
                      </div>
                    ))}
                </div>
              </div>

              <div className="text-xs text-muted-foreground">
                创建时间: {formatTime(selectedTemplate.created_at)} •
                更新时间: {formatTime(selectedTemplate.updated_at)}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* 模板编辑器 */}
      <TemplateEditor
        template={editingTemplate || undefined}
        isOpen={showEditor}
        onClose={() => {
          setShowEditor(false);
          setEditingTemplate(null);
        }}
        onSave={handleSaveTemplate}
      />

      {/* 导出对话框 */}
      {exportDialog.template && (
        <ExportDialog
          open={exportDialog.open}
          onOpenChange={(open) => setExportDialog({ open, template: open ? exportDialog.template : undefined })}
          type="template"
          data={exportDialog.template}
        />
      )}
    </div>
  );
}