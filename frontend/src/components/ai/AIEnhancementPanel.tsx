'use client';

import { useState } from 'react';
import { 
  Sparkles, 
  Loader2, 
  Eye, 
  EyeOff, 
  RotateCcw, 
  CheckCircle,
  AlertCircle,
  Lightbulb,
  ListTodo,
  Zap,
  FileText,
  Languages,
  Wand2,
  X
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Progress } from '@/components/ui/progress';
import { aiService, AIEnhancementOptions, AIEnhancementResult } from '@/lib/ai-service';

interface AIEnhancementPanelProps {
  content: string;
  onEnhancementApply: (enhancedContent: string) => void;
  onClose?: () => void;
  disabled?: boolean;
}

export function AIEnhancementPanel({ 
  content, 
  onEnhancementApply, 
  onClose,
  disabled = false 
}: AIEnhancementPanelProps) {
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [enhancementResult, setEnhancementResult] = useState<AIEnhancementResult | null>(null);
  const [showComparison, setShowComparison] = useState(false);
  const [enhancementType, setEnhancementType] = useState<AIEnhancementOptions['enhancementType']>('expand');
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  // 增强类型配置
  const enhancementTypes = [
    {
      value: 'expand' as const,
      label: '扩展内容',
      description: '补充详细信息和背景',
      icon: Zap,
    },
    {
      value: 'summarize' as const,
      label: '生成摘要',
      description: '提取关键要点',
      icon: FileText,
    },
    {
      value: 'format' as const,
      label: '格式优化',
      description: '改善结构和排版',
      icon: Wand2,
    },
    {
      value: 'action_items' as const,
      label: '提取行动项',
      description: '识别任务和待办事项',
      icon: ListTodo,
    },
  ];

  // 执行AI增强
  const handleEnhance = async () => {
    if (!content.trim() || disabled) return;

    try {
      setIsEnhancing(true);
      setError(null);
      setProgress(0);

      // 模拟进度更新
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      const options: AIEnhancementOptions = {
        enhancementType,
        style: 'professional',
        includeKeywords: true,
      };

      const result = await aiService.enhanceNote(content, options);
      
      clearInterval(progressInterval);
      setProgress(100);
      
      setEnhancementResult(result);
      setShowComparison(true);

    } catch (error) {
      console.error('AI增强失败:', error);
      setError(error instanceof Error ? error.message : 'AI增强失败，请重试');
    } finally {
      setIsEnhancing(false);
      setTimeout(() => setProgress(0), 1000);
    }
  };

  // 应用增强结果
  const handleApplyEnhancement = () => {
    if (enhancementResult) {
      onEnhancementApply(enhancementResult.enhancedContent);
      setEnhancementResult(null);
      setShowComparison(false);
    }
  };

  // 重置状态
  const handleReset = () => {
    setEnhancementResult(null);
    setShowComparison(false);
    setError(null);
  };

  // 关闭面板
  const handleClose = () => {
    if (onClose) {
      onClose();
    }
  };

  const selectedType = enhancementTypes.find(type => type.value === enhancementType);

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-2">
            <Sparkles className="h-5 w-5 text-purple-500" />
            <span>AI 内容增强</span>
            {isEnhancing && (
              <Badge variant="secondary" className="ml-2">
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                处理中
              </Badge>
            )}
          </CardTitle>
          {onClose && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClose}
              className="h-6 w-6 p-0"
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* 增强类型选择 */}
        <div className="space-y-2">
          <label className="text-sm font-medium">增强类型</label>
          <Select value={enhancementType} onValueChange={setEnhancementType} disabled={disabled}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {enhancementTypes.map((type) => (
                <SelectItem key={type.value} value={type.value}>
                  <div className="flex items-center space-x-2">
                    <type.icon className="h-4 w-4" />
                    <div>
                      <div className="font-medium">{type.label}</div>
                      <div className="text-xs text-muted-foreground">{type.description}</div>
                    </div>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* 进度条 */}
        {isEnhancing && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span>AI 正在分析内容...</span>
              <span>{progress}%</span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>
        )}

        {/* 错误信息 */}
        {error && (
          <div className="flex items-center space-x-2 p-3 bg-red-50 border border-red-200 rounded-md">
            <AlertCircle className="h-4 w-4 text-red-500" />
            <span className="text-sm text-red-700">{error}</span>
          </div>
        )}

        {/* 控制按钮 */}
        <div className="flex items-center space-x-2">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  onClick={handleEnhance}
                  disabled={!content.trim() || isEnhancing || disabled}
                  className="flex-1"
                >
                  {isEnhancing ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4 mr-2" />
                  )}
                  {isEnhancing ? '处理中...' : `${selectedType?.label || '开始增强'}`}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{selectedType?.description}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          {enhancementResult && (
            <Button
              variant="outline"
              size="icon"
              onClick={() => setShowComparison(!showComparison)}
            >
              {showComparison ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </Button>
          )}

          {enhancementResult && (
            <Button
              variant="outline"
              size="icon"
              onClick={handleReset}
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* 增强结果 */}
        {enhancementResult && (
          <div className="space-y-4">
            <Separator />
            
            {/* 结果统计 */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <span>置信度: {Math.round(enhancementResult.confidence * 100)}%</span>
              </div>
              <div className="flex items-center space-x-2">
                <Zap className="h-4 w-4 text-blue-500" />
                <span>处理时间: {Math.round(enhancementResult.processingTime)}ms</span>
              </div>
            </div>

            {/* AI建议 */}
            {enhancementResult.suggestions && enhancementResult.suggestions.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <Lightbulb className="h-4 w-4 text-yellow-500" />
                  <span className="text-sm font-medium">AI 建议</span>
                </div>
                <ul className="space-y-1 text-sm text-muted-foreground">
                  {enhancementResult.suggestions.map((suggestion, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <span className="text-yellow-500">•</span>
                      <span>{suggestion}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* 行动项 */}
            {enhancementResult.actionItems && enhancementResult.actionItems.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <ListTodo className="h-4 w-4 text-green-500" />
                  <span className="text-sm font-medium">识别的行动项</span>
                </div>
                <ul className="space-y-1 text-sm">
                  {enhancementResult.actionItems.map((item, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <span className="text-green-500">✓</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* 应用按钮 */}
            <div className="flex space-x-2">
              <Button onClick={handleApplyEnhancement} className="flex-1">
                <CheckCircle className="h-4 w-4 mr-2" />
                应用增强结果
              </Button>
              {showComparison && (
                <Button variant="outline" onClick={() => setShowComparison(false)}>
                  隐藏对比
                </Button>
              )}
            </div>
          </div>
        )}

        {/* 内容对比 */}
        {enhancementResult && showComparison && (
          <div className="space-y-4">
            <Separator />
            
            <div className="grid gap-4 md:grid-cols-2">
              {/* 原始内容 */}
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-gray-400 rounded-full"></div>
                  <span className="text-sm font-medium">原始内容</span>
                </div>
                <div className="p-3 bg-gray-50 border rounded-md text-sm max-h-60 overflow-y-auto">
                  <div 
                    dangerouslySetInnerHTML={{ 
                      __html: enhancementResult.originalContent.replace(/\n/g, '<br>') 
                    }} 
                  />
                </div>
              </div>

              {/* 增强内容 */}
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                  <span className="text-sm font-medium">增强内容</span>
                </div>
                <div className="p-3 bg-green-50 border border-green-200 rounded-md text-sm max-h-60 overflow-y-auto">
                  <div 
                    dangerouslySetInnerHTML={{ 
                      __html: enhancementResult.enhancedContent.replace(/\n/g, '<br>') 
                    }} 
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 使用提示 */}
        <div className="text-xs text-muted-foreground bg-muted/50 p-3 rounded-md">
          <div className="flex items-start space-x-2">
            <AlertCircle className="h-3 w-3 mt-0.5 text-muted-foreground" />
            <div>
              <p className="font-medium mb-1">AI 增强说明：</p>
              <ul className="space-y-1">
                <li>• 当前使用演示模式，实际部署时将连接真实的AI服务</li>
                <li>• 增强结果仅供参考，请根据实际情况进行调整</li>
                <li>• 可以多次使用不同类型的增强来优化内容</li>
              </ul>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}