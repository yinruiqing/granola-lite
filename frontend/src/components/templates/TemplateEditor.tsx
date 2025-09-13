'use client';

import { useState, useEffect } from 'react';
import { 
  Plus,
  Trash2,
  GripVertical,
  Save,
  X,
  Eye,
  EyeOff
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Template, TemplateSection, TemplateStructure } from '@/types';

interface TemplateEditorProps {
  template?: Template;
  isOpen: boolean;
  onClose: () => void;
  onSave: (template: Omit<Template, 'id' | 'created_at' | 'updated_at'>) => void;
}

export function TemplateEditor({ template, isOpen, onClose, onSave }: TemplateEditorProps) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    category: 'meeting' as Template['category'],
    is_active: true,
    is_default: false,
  });
  
  const [structure, setStructure] = useState<TemplateStructure>({
    title: '',
    sections: [],
    variables: {},
  });
  
  const [showPreview, setShowPreview] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // 初始化表单数据
  useEffect(() => {
    if (template) {
      setFormData({
        name: template.name,
        description: template.description || '',
        category: template.category,
        is_active: template.is_active,
        is_default: template.is_default || false,
      });
      setStructure(template.structure);
    } else {
      // 重置为默认值
      setFormData({
        name: '',
        description: '',
        category: 'meeting',
        is_active: true,
        is_default: false,
      });
      setStructure({
        title: '',
        sections: [],
        variables: {},
      });
    }
    setErrors({});
  }, [template, isOpen]);

  // 添加新段落
  const addSection = () => {
    const newSection: TemplateSection = {
      id: `section_${Date.now()}`,
      title: '新段落',
      type: 'text',
      placeholder: '请输入内容...',
      required: false,
      order: structure.sections.length,
    };

    setStructure(prev => ({
      ...prev,
      sections: [...prev.sections, newSection]
    }));
  };

  // 删除段落
  const removeSection = (sectionId: string) => {
    setStructure(prev => ({
      ...prev,
      sections: prev.sections
        .filter(s => s.id !== sectionId)
        .map((s, index) => ({ ...s, order: index }))
    }));
  };

  // 更新段落
  const updateSection = (sectionId: string, updates: Partial<TemplateSection>) => {
    setStructure(prev => ({
      ...prev,
      sections: prev.sections.map(s =>
        s.id === sectionId ? { ...s, ...updates } : s
      )
    }));
  };

  // 移动段落位置
  const moveSection = (sectionId: string, direction: 'up' | 'down') => {
    const sections = [...structure.sections];
    const index = sections.findIndex(s => s.id === sectionId);
    
    if (index === -1) return;
    
    const newIndex = direction === 'up' ? index - 1 : index + 1;
    
    if (newIndex < 0 || newIndex >= sections.length) return;
    
    // 交换位置
    [sections[index], sections[newIndex]] = [sections[newIndex], sections[index]];
    
    // 更新 order
    sections.forEach((section, i) => {
      section.order = i;
    });
    
    setStructure(prev => ({
      ...prev,
      sections
    }));
  };

  // 表单验证
  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = '模板名称不能为空';
    }

    if (!structure.title.trim()) {
      newErrors.title = '模板标题不能为空';
    }

    if (structure.sections.length === 0) {
      newErrors.sections = '至少需要添加一个段落';
    }

    // 检查段落标题
    structure.sections.forEach((section, index) => {
      if (!section.title.trim()) {
        newErrors[`section_${index}_title`] = '段落标题不能为空';
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // 保存模板
  const handleSave = () => {
    if (!validateForm()) return;

    const templateData: Omit<Template, 'id' | 'created_at' | 'updated_at'> = {
      ...formData,
      structure,
    };

    onSave(templateData);
  };

  // 预览模板
  const renderPreview = () => {
    if (!structure.title || structure.sections.length === 0) {
      return (
        <div className="text-center text-muted-foreground p-8">
          <p>完善模板信息后可以预览效果</p>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        <h2 className="text-xl font-bold">{structure.title}</h2>
        {structure.sections
          .sort((a, b) => a.order - b.order)
          .map((section) => (
            <div key={section.id} className="border-l-2 border-blue-200 pl-4 py-2">
              <div className="flex items-center space-x-2 mb-2">
                <h3 className="font-semibold">{section.title}</h3>
                {section.required && (
                  <Badge variant="destructive" className="text-xs">必填</Badge>
                )}
                <Badge variant="outline" className="text-xs">{section.type}</Badge>
              </div>
              
              {section.type === 'text' && (
                <Textarea 
                  placeholder={section.placeholder}
                  className="min-h-[80px]"
                  disabled
                />
              )}
              
              {section.type === 'list' && (
                <div className="space-y-2">
                  <Input placeholder={section.placeholder} disabled />
                  <Input placeholder="添加列表项..." disabled />
                </div>
              )}
              
              {section.type === 'table' && (
                <div className="border rounded p-4 bg-gray-50">
                  <p className="text-sm text-muted-foreground">
                    表格区域 - {section.placeholder}
                  </p>
                </div>
              )}
              
              {section.type === 'markdown' && (
                <Textarea 
                  placeholder={`${section.placeholder} (支持 Markdown 格式)`}
                  className="min-h-[120px] font-mono text-sm"
                  disabled
                />
              )}
            </div>
          ))}
      </div>
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>
            {template ? '编辑模板' : '新建模板'}
          </DialogTitle>
          <DialogDescription>
            {template ? '修改模板的基本信息和结构' : '创建一个新的会议模板'}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-hidden">
          <div className="grid grid-cols-2 gap-6 h-full">
            {/* 左侧：编辑器 */}
            <div className="space-y-6 overflow-y-auto pr-2">
              {/* 基本信息 */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">基本信息</h3>
                
                <div className="space-y-2">
                  <Label htmlFor="name">模板名称 *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="输入模板名称"
                    className={errors.name ? 'border-red-500' : ''}
                  />
                  {errors.name && (
                    <p className="text-sm text-red-600">{errors.name}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="description">模板描述</Label>
                  <Textarea
                    id="description"
                    value={formData.description}
                    onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="描述模板的用途和场景"
                    rows={2}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="category">模板分类</Label>
                    <Select 
                      value={formData.category} 
                      onValueChange={(value: Template['category']) => 
                        setFormData(prev => ({ ...prev, category: value }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="meeting">会议模板</SelectItem>
                        <SelectItem value="notes">笔记模板</SelectItem>
                        <SelectItem value="summary">总结模板</SelectItem>
                        <SelectItem value="action_items">行动项模板</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>选项</Label>
                    <div className="space-y-2">
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="is_active"
                          checked={formData.is_active}
                          onCheckedChange={(checked) => 
                            setFormData(prev => ({ ...prev, is_active: !!checked }))
                          }
                        />
                        <Label htmlFor="is_active">启用模板</Label>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="is_default"
                          checked={formData.is_default}
                          onCheckedChange={(checked) => 
                            setFormData(prev => ({ ...prev, is_default: !!checked }))
                          }
                        />
                        <Label htmlFor="is_default">设为默认模板</Label>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* 模板结构 */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">模板结构</h3>
                
                <div className="space-y-2">
                  <Label htmlFor="title">模板标题 *</Label>
                  <Input
                    id="title"
                    value={structure.title}
                    onChange={(e) => setStructure(prev => ({ ...prev, title: e.target.value }))}
                    placeholder="模板生成文档的标题"
                    className={errors.title ? 'border-red-500' : ''}
                  />
                  {errors.title && (
                    <p className="text-sm text-red-600">{errors.title}</p>
                  )}
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label>段落设置</Label>
                    <Button onClick={addSection} size="sm">
                      <Plus className="h-4 w-4 mr-1" />
                      添加段落
                    </Button>
                  </div>

                  {errors.sections && (
                    <p className="text-sm text-red-600">{errors.sections}</p>
                  )}

                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {structure.sections
                      .sort((a, b) => a.order - b.order)
                      .map((section, index) => (
                        <Card key={section.id} className="p-4">
                          <div className="space-y-3">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-2">
                                <GripVertical className="h-4 w-4 text-gray-400" />
                                <span className="text-sm font-medium">段落 {index + 1}</span>
                              </div>
                              
                              <div className="flex items-center space-x-1">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => moveSection(section.id, 'up')}
                                  disabled={index === 0}
                                >
                                  ↑
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => moveSection(section.id, 'down')}
                                  disabled={index === structure.sections.length - 1}
                                >
                                  ↓
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => removeSection(section.id)}
                                >
                                  <Trash2 className="h-3 w-3" />
                                </Button>
                              </div>
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                              <div>
                                <Input
                                  value={section.title}
                                  onChange={(e) => updateSection(section.id, { title: e.target.value })}
                                  placeholder="段落标题"
                                  className={errors[`section_${index}_title`] ? 'border-red-500' : ''}
                                />
                                {errors[`section_${index}_title`] && (
                                  <p className="text-xs text-red-600 mt-1">
                                    {errors[`section_${index}_title`]}
                                  </p>
                                )}
                              </div>
                              
                              <Select 
                                value={section.type} 
                                onValueChange={(value: TemplateSection['type']) => 
                                  updateSection(section.id, { type: value })
                                }
                              >
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="text">文本</SelectItem>
                                  <SelectItem value="list">列表</SelectItem>
                                  <SelectItem value="table">表格</SelectItem>
                                  <SelectItem value="markdown">Markdown</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>

                            <Input
                              value={section.placeholder || ''}
                              onChange={(e) => updateSection(section.id, { placeholder: e.target.value })}
                              placeholder="占位符文本"
                            />

                            <div className="flex items-center space-x-2">
                              <Checkbox
                                id={`required_${section.id}`}
                                checked={section.required}
                                onCheckedChange={(checked) => 
                                  updateSection(section.id, { required: !!checked })
                                }
                              />
                              <Label htmlFor={`required_${section.id}`} className="text-sm">
                                必填项
                              </Label>
                            </div>
                          </div>
                        </Card>
                      ))}
                  </div>
                </div>
              </div>
            </div>

            {/* 右侧：预览 */}
            <div className="border-l pl-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">预览</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowPreview(!showPreview)}
                >
                  {showPreview ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>

              <div className="border rounded-lg p-4 bg-gray-50 min-h-[400px] overflow-y-auto">
                {renderPreview()}
              </div>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            <X className="h-4 w-4 mr-2" />
            取消
          </Button>
          <Button onClick={handleSave}>
            <Save className="h-4 w-4 mr-2" />
            保存模板
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}