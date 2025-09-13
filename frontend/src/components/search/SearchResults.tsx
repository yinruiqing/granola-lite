'use client';

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { 
  Calendar, 
  FileText, 
  Layout, 
  MessageSquare, 
  Clock, 
  Users, 
  Star,
  ExternalLink,
  Eye,
  Edit,
  Share2,
  Bookmark,
  MoreHorizontal
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import { SearchResult } from '@/lib/search-service';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import Link from 'next/link';

interface SearchResultsProps {
  results: SearchResult[];
  loading?: boolean;
  query: string;
  onResultClick?: (result: SearchResult) => void;
  className?: string;
}

export function SearchResults({ 
  results, 
  loading = false, 
  query, 
  onResultClick,
  className 
}: SearchResultsProps) {
  const [bookmarkedResults, setBookmarkedResults] = useState<Set<string>>(new Set());
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set());

  const getTypeIcon = (type: SearchResult['type']) => {
    switch (type) {
      case 'meeting':
        return <Calendar className="h-4 w-4" />;
      case 'note':
        return <FileText className="h-4 w-4" />;
      case 'template':
        return <Layout className="h-4 w-4" />;
      case 'conversation':
        return <MessageSquare className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  const getTypeLabel = (type: SearchResult['type']) => {
    switch (type) {
      case 'meeting':
        return '会议';
      case 'note':
        return '笔记';
      case 'template':
        return '模板';
      case 'conversation':
        return '对话';
      default:
        return type;
    }
  };

  const getTypeColor = (type: SearchResult['type']) => {
    switch (type) {
      case 'meeting':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'note':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'template':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      case 'conversation':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  const getResultUrl = (result: SearchResult) => {
    switch (result.type) {
      case 'meeting':
        return `/meetings/${result.originalData.id}`;
      case 'note':
        return `/meetings/${(result.originalData as any).meeting_id}/notes`;
      case 'template':
        return `/templates`;
      case 'conversation':
        return `/chat`;
      default:
        return '#';
    }
  };

  const handleBookmark = (resultId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setBookmarkedResults(prev => {
      const newBookmarks = new Set(prev);
      if (newBookmarks.has(resultId)) {
        newBookmarks.delete(resultId);
      } else {
        newBookmarks.add(resultId);
      }
      return newBookmarks;
    });
  };

  const handleExpand = (resultId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedResults(prev => {
      const newExpanded = new Set(prev);
      if (newExpanded.has(resultId)) {
        newExpanded.delete(resultId);
      } else {
        newExpanded.add(resultId);
      }
      return newExpanded;
    });
  };

  const highlightText = (text: string, query: string) => {
    if (!query) return text;
    
    const queryWords = query.toLowerCase().split(/\s+/);
    let highlightedText = text;
    
    queryWords.forEach(word => {
      if (word.length > 1) {
        const regex = new RegExp(`(${word})`, 'gi');
        highlightedText = highlightedText.replace(regex, '<mark class="bg-yellow-200 dark:bg-yellow-800 px-0.5 rounded">$1</mark>');
      }
    });
    
    return highlightedText;
  };

  const getRelevanceScore = (score: number) => {
    if (score >= 0.8) return { label: '高相关', color: 'bg-green-500' };
    if (score >= 0.5) return { label: '中相关', color: 'bg-yellow-500' };
    return { label: '低相关', color: 'bg-gray-400' };
  };

  if (loading) {
    return (
      <div className={cn("space-y-4", className)}>
        {[...Array(3)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardContent className="p-6">
              <div className="space-y-3">
                <div className="flex items-center space-x-3">
                  <div className="h-4 w-4 bg-gray-300 rounded"></div>
                  <div className="h-4 w-20 bg-gray-300 rounded"></div>
                  <div className="h-4 w-32 bg-gray-300 rounded"></div>
                </div>
                <div className="h-6 w-3/4 bg-gray-300 rounded"></div>
                <div className="h-4 w-full bg-gray-300 rounded"></div>
                <div className="h-4 w-2/3 bg-gray-300 rounded"></div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className={cn("text-center py-12", className)}>
        <div className="mx-auto w-24 h-24 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-4">
          <FileText className="h-8 w-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
          {query ? '未找到匹配结果' : '开始搜索'}
        </h3>
        <p className="text-gray-500 dark:text-gray-400">
          {query ? '尝试使用不同的关键词或调整筛选条件' : '输入关键词搜索会议、笔记和模板'}
        </p>
      </div>
    );
  }

  return (
    <ScrollArea className={cn("space-y-4", className)}>
      <div className="space-y-4">
        {/* 结果统计 */}
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>找到 {results.length} 个结果</span>
          <span>搜索用时 &lt; 100ms</span>
        </div>

        {results.map((result, index) => {
          const isExpanded = expandedResults.has(result.id);
          const isBookmarked = bookmarkedResults.has(result.id);
          const relevance = getRelevanceScore(result.score);

          return (
            <Card 
              key={result.id} 
              className="hover:shadow-md transition-all duration-200 cursor-pointer group"
              onClick={() => onResultClick?.(result)}
            >
              <CardContent className="p-6">
                <div className="space-y-4">
                  {/* 标题行 */}
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3 flex-1">
                      <div className="flex items-center space-x-2">
                        {getTypeIcon(result.type)}
                        <Badge variant="outline" className={getTypeColor(result.type)}>
                          {getTypeLabel(result.type)}
                        </Badge>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <div 
                          className={cn("w-2 h-2 rounded-full", relevance.color)}
                          title={relevance.label}
                        />
                        <span className="text-xs text-muted-foreground">
                          相关度: {Math.round(result.score * 100)}%
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => handleBookmark(result.id, e)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <Star 
                          className={cn(
                            "h-4 w-4",
                            isBookmarked ? "fill-yellow-400 text-yellow-400" : ""
                          )} 
                        />
                      </Button>

                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>操作</DropdownMenuLabel>
                          <DropdownMenuItem asChild>
                            <Link href={getResultUrl(result)}>
                              <Eye className="h-4 w-4 mr-2" />
                              查看详情
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Edit className="h-4 w-4 mr-2" />
                            编辑
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Share2 className="h-4 w-4 mr-2" />
                            分享
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem>
                            <Bookmark className="h-4 w-4 mr-2" />
                            {isBookmarked ? '取消收藏' : '添加收藏'}
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>

                  {/* 标题 */}
                  <h3 
                    className="text-lg font-semibold text-gray-900 dark:text-gray-100 leading-tight"
                    dangerouslySetInnerHTML={{ __html: highlightText(result.title, query) }}
                  />

                  {/* 摘要 */}
                  <div className="space-y-2">
                    <p 
                      className="text-gray-600 dark:text-gray-300 leading-relaxed"
                      dangerouslySetInnerHTML={{ 
                        __html: highlightText(
                          isExpanded ? result.content.slice(0, 500) : result.excerpt, 
                          query
                        ) 
                      }}
                    />
                    
                    {result.content.length > result.excerpt.length && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => handleExpand(result.id, e)}
                        className="text-primary hover:text-primary/80 p-0 h-auto font-normal"
                      >
                        {isExpanded ? '收起' : '展开更多'}
                      </Button>
                    )}
                  </div>

                  {/* 高亮片段 */}
                  {result.highlights.length > 0 && (
                    <div className="space-y-2">
                      <Separator />
                      <div>
                        <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          匹配片段:
                        </h4>
                        <div className="space-y-1">
                          {result.highlights.slice(0, isExpanded ? result.highlights.length : 2).map((highlight, i) => (
                            <p 
                              key={i}
                              className="text-sm text-gray-600 dark:text-gray-400 pl-4 border-l-2 border-primary/20"
                              dangerouslySetInnerHTML={{ __html: highlight }}
                            />
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 元数据 */}
                  <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t">
                    <div className="flex items-center space-x-4">
                      <span className="flex items-center">
                        <Clock className="h-3 w-3 mr-1" />
                        {format(new Date(result.metadata.created_at), "yyyy-MM-dd", { locale: zhCN })}
                      </span>
                      
                      {result.metadata.participants && (
                        <span className="flex items-center">
                          <Users className="h-3 w-3 mr-1" />
                          {result.metadata.participants}
                        </span>
                      )}

                      {result.metadata.status && (
                        <Badge variant="outline" className="text-xs">
                          {result.metadata.status}
                        </Badge>
                      )}
                    </div>

                    <Link 
                      href={getResultUrl(result)}
                      className="flex items-center hover:text-primary transition-colors"
                      onClick={(e) => e.stopPropagation()}
                    >
                      打开
                      <ExternalLink className="h-3 w-3 ml-1" />
                    </Link>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </ScrollArea>
  );
}