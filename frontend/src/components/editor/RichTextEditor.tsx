'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { 
  Bold, 
  Italic, 
  Underline, 
  List, 
  ListOrdered, 
  Quote,
  Link,
  Save,
  Undo,
  Redo,
  Type,
  AlignLeft,
  AlignCenter,
  AlignRight,
  Sparkles
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface RichTextEditorProps {
  content: string;
  onChange: (content: string) => void;
  onSave?: () => void;
  placeholder?: string;
  autoSave?: boolean;
  autoSaveInterval?: number;
  readOnly?: boolean;
  showToolbar?: boolean;
  showAIButton?: boolean;
  onAIEnhance?: () => void;
}

export function RichTextEditor({
  content,
  onChange,
  onSave,
  placeholder = '开始输入笔记...',
  autoSave = true,
  autoSaveInterval = 3000,
  readOnly = false,
  showToolbar = true,
  showAIButton = false,
  onAIEnhance,
}: RichTextEditorProps) {
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [wordCount, setWordCount] = useState(0);
  const [isEditorFocused, setIsEditorFocused] = useState(false);
  
  const editorRef = useRef<HTMLDivElement>(null);
  const autoSaveTimer = useRef<NodeJS.Timeout | null>(null);

  // 更新内容
  const updateContent = useCallback((newContent: string) => {
    onChange(newContent);
    
    // 更新字数统计
    const textContent = newContent.replace(/<[^>]*>/g, '').trim();
    setWordCount(textContent.length);
    
    // 设置自动保存
    if (autoSave && onSave) {
      if (autoSaveTimer.current) {
        clearTimeout(autoSaveTimer.current);
      }
      
      autoSaveTimer.current = setTimeout(() => {
        handleSave();
      }, autoSaveInterval);
    }
  }, [onChange, autoSave, onSave, autoSaveInterval]);

  // 处理保存
  const handleSave = useCallback(async () => {
    if (!onSave) return;
    
    try {
      setIsSaving(true);
      await onSave();
      setLastSaved(new Date());
    } catch (error) {
      console.error('保存失败:', error);
    } finally {
      setIsSaving(false);
    }
  }, [onSave]);

  // 手动插入列表
  const insertList = (ordered: boolean) => {
    if (!editorRef.current) return;
    
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;
    
    const range = selection.getRangeAt(0);
    const listTag = ordered ? 'ol' : 'ul';
    
    // 创建列表元素
    const listElement = document.createElement(listTag);
    const listItem = document.createElement('li');
    listItem.textContent = '列表项';
    listElement.appendChild(listItem);
    
    try {
      // 插入列表
      range.deleteContents();
      range.insertNode(listElement);
      
      // 将光标移到列表项内
      range.selectNodeContents(listItem);
      selection.removeAllRanges();
      selection.addRange(range);
      
      // 更新内容
      const newContent = editorRef.current.innerHTML;
      updateContent(newContent);
    } catch (error) {
      console.warn('手动插入列表失败:', error);
    }
  };

  // 执行格式化命令
  const execCommand = (command: string, value?: string) => {
    if (readOnly || !editorRef.current) return;
    
    // 确保编辑器有焦点
    editorRef.current.focus();
    
    try {
      // 对于列表命令，优先使用 execCommand，如果失败则使用手动插入
      if (command === 'insertUnorderedList') {
        const success = document.execCommand('insertUnorderedList', false);
        if (!success) {
          insertList(false);
          return;
        }
      } else if (command === 'insertOrderedList') {
        const success = document.execCommand('insertOrderedList', false);
        if (!success) {
          insertList(true);
          return;
        }
      } else if (command === 'formatBlock' && value === 'blockquote') {
        document.execCommand('formatBlock', false, 'blockquote');
      } else {
        document.execCommand(command, false, value);
      }
      
      // 小延迟后获取更新的内容，确保DOM已更新
      setTimeout(() => {
        if (editorRef.current) {
          const newContent = editorRef.current.innerHTML;
          updateContent(newContent);
        }
      }, 10);
      
    } catch (error) {
      console.warn('执行命令失败:', command, error);
      
      // 如果是列表命令失败，尝试手动插入
      if (command === 'insertUnorderedList') {
        insertList(false);
      } else if (command === 'insertOrderedList') {
        insertList(true);
      }
    }
  };

  // 处理编辑器输入
  const handleInput = () => {
    if (readOnly || !editorRef.current) return;
    
    const newContent = editorRef.current.innerHTML;
    updateContent(newContent);
  };

  // 处理键盘快捷键
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (readOnly) return;

    // Ctrl/Cmd + 快捷键
    if (e.ctrlKey || e.metaKey) {
      switch (e.key) {
        case 'b':
          e.preventDefault();
          execCommand('bold');
          break;
        case 'i':
          e.preventDefault();
          execCommand('italic');
          break;
        case 'u':
          e.preventDefault();
          execCommand('underline');
          break;
        case 's':
          e.preventDefault();
          handleSave();
          break;
        case 'z':
          if (e.shiftKey) {
            e.preventDefault();
            execCommand('redo');
          } else {
            e.preventDefault();
            execCommand('undo');
          }
          break;
        case 'y':
          e.preventDefault();
          execCommand('redo');
          break;
        default:
          break;
      }
    }
  };

  // 工具栏按钮配置
  const toolbarButtons = [
    {
      group: 'format',
      buttons: [
        { icon: Bold, command: 'bold', tooltip: '粗体 (Ctrl+B)' },
        { icon: Italic, command: 'italic', tooltip: '斜体 (Ctrl+I)' },
        { icon: Underline, command: 'underline', tooltip: '下划线 (Ctrl+U)' },
      ]
    },
    {
      group: 'list',
      buttons: [
        { icon: List, command: 'insertUnorderedList', tooltip: '无序列表' },
        { icon: ListOrdered, command: 'insertOrderedList', tooltip: '有序列表' },
        { icon: Quote, command: 'formatBlock', value: 'blockquote', tooltip: '引用' },
      ]
    },
    {
      group: 'align',
      buttons: [
        { icon: AlignLeft, command: 'justifyLeft', tooltip: '左对齐' },
        { icon: AlignCenter, command: 'justifyCenter', tooltip: '居中对齐' },
        { icon: AlignRight, command: 'justifyRight', tooltip: '右对齐' },
      ]
    },
    {
      group: 'history',
      buttons: [
        { icon: Undo, command: 'undo', tooltip: '撤销 (Ctrl+Z)' },
        { icon: Redo, command: 'redo', tooltip: '重做 (Ctrl+Y)' },
      ]
    },
  ];

  // 初始化编辑器内容
  useEffect(() => {
    if (editorRef.current && content !== editorRef.current.innerHTML) {
      editorRef.current.innerHTML = content;
      
      // 更新字数统计
      const textContent = content.replace(/<[^>]*>/g, '').trim();
      setWordCount(textContent.length);
    }
  }, [content]);

  // 清理定时器
  useEffect(() => {
    return () => {
      if (autoSaveTimer.current) {
        clearTimeout(autoSaveTimer.current);
      }
    };
  }, []);

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-2">
            <Type className="h-5 w-5" />
            <span>笔记编辑器</span>
          </CardTitle>
          
          <div className="flex items-center space-x-2">
            {isSaving && <Badge variant="secondary">保存中...</Badge>}
            {lastSaved && (
              <Badge variant="outline">
                {lastSaved.toLocaleTimeString('zh-CN', {
                  hour: '2-digit',
                  minute: '2-digit',
                })} 已保存
              </Badge>
            )}
            {showAIButton && onAIEnhance && content.trim() && (
              <Button 
                onClick={onAIEnhance} 
                size="sm" 
                disabled={readOnly}
                variant="outline"
                className="border-purple-200 text-purple-700 hover:bg-purple-50"
              >
                <Sparkles className="h-3 w-3 mr-1" />
                AI增强
              </Button>
            )}
            {onSave && (
              <Button 
                onClick={handleSave} 
                size="sm" 
                disabled={isSaving || readOnly}
                variant="outline"
              >
                <Save className="h-3 w-3 mr-1" />
                保存
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        {/* 工具栏 */}
        {showToolbar && !readOnly && (
          <div className="border-b p-3">
            <TooltipProvider>
              <div className="flex items-center space-x-1">
                {toolbarButtons.map((group, groupIndex) => (
                  <div key={group.group} className="flex items-center">
                    {group.buttons.map((button) => (
                      <Tooltip key={button.command}>
                        <TooltipTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => execCommand(button.command, button.value)}
                            className="h-8 w-8 p-0"
                          >
                            <button.icon className="h-4 w-4" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>{button.tooltip}</p>
                        </TooltipContent>
                      </Tooltip>
                    ))}
                    {groupIndex < toolbarButtons.length - 1 && (
                      <Separator orientation="vertical" className="mx-2 h-6" />
                    )}
                  </div>
                ))}
              </div>
            </TooltipProvider>
          </div>
        )}

        {/* 编辑器区域 */}
        <div className="relative">
          <div
            ref={editorRef}
            contentEditable={!readOnly}
            onInput={handleInput}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsEditorFocused(true)}
            onBlur={() => setIsEditorFocused(false)}
            className={`
              rich-text-editor min-h-[400px] p-4 outline-none resize-none
              ${readOnly ? 'cursor-default' : 'cursor-text'}
              ${isEditorFocused ? 'ring-2 ring-ring ring-offset-2' : ''}
            `}
            style={{
              wordBreak: 'break-word',
              lineHeight: '1.6',
            }}
            data-placeholder={placeholder}
          />
          
          {/* 占位符 */}
          {!content && !readOnly && (
            <div 
              className="absolute top-4 left-4 text-muted-foreground pointer-events-none select-none"
              style={{ lineHeight: '1.6' }}
            >
              {placeholder}
            </div>
          )}
        </div>

        {/* 状态栏 */}
        <div className="flex items-center justify-between p-3 bg-muted/30 border-t text-xs text-muted-foreground">
          <div className="flex items-center space-x-4">
            <span>字数: {wordCount}</span>
            {autoSave && onSave && (
              <span>自动保存: {autoSaveInterval / 1000}s</span>
            )}
          </div>
          
          {!readOnly && (
            <div className="flex items-center space-x-2 text-xs">
              <kbd className="px-1 py-0.5 bg-muted rounded text-xs">Ctrl+B</kbd>
              <span>粗体</span>
              <kbd className="px-1 py-0.5 bg-muted rounded text-xs">Ctrl+S</kbd>
              <span>保存</span>
            </div>
          )}
        </div>
      </CardContent>
      
      <style jsx global>{`
        .rich-text-editor:empty:before {
          content: attr(data-placeholder);
          color: #9ca3af;
          pointer-events: none;
        }
        
        .rich-text-editor blockquote {
          border-left: 4px solid #e5e7eb;
          padding-left: 1rem;
          margin: 1rem 0;
          color: #6b7280;
        }
        
        .rich-text-editor ul, .rich-text-editor ol {
          padding-left: 2rem;
          margin: 1rem 0;
          list-style-position: outside;
        }
        
        .rich-text-editor ul {
          list-style-type: disc !important;
        }
        
        .rich-text-editor ol {
          list-style-type: decimal !important;
        }
        
        .rich-text-editor li {
          margin: 0.25rem 0;
          display: list-item !important;
          list-style: inherit !important;
        }
        
        .rich-text-editor h1, .rich-text-editor h2, .rich-text-editor h3 {
          font-weight: bold;
          margin: 1rem 0 0.5rem 0;
        }
        
        .rich-text-editor h1 { font-size: 1.5rem; }
        .rich-text-editor h2 { font-size: 1.25rem; }
        .rich-text-editor h3 { font-size: 1.125rem; }
        
        .rich-text-editor p {
          margin: 0.5rem 0;
        }
        
        .rich-text-editor:focus {
          outline: none;
        }
        
        .rich-text-editor strong {
          font-weight: bold;
        }
        
        .rich-text-editor em {
          font-style: italic;
        }
        
        .rich-text-editor u {
          text-decoration: underline;
        }
      `}</style>
    </Card>
  );
}