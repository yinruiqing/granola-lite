'use client';

import { useState, useEffect, useCallback } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog';
import { 
  Search, 
  Calendar, 
  FileText, 
  Layout, 
  ArrowRight, 
  Loader2,
  Command
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAppStore } from '@/lib/store';
import { storageManager } from '@/lib/storage';
import { searchService, SearchResult } from '@/lib/search-service';
import { useDebounce } from '@/hooks/useDebounce';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

interface GlobalSearchProps {
  className?: string;
}

export function GlobalSearch({ className }: GlobalSearchProps) {
  const router = useRouter();
  const { meetings } = useAppStore();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [notes, setNotes] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);

  const debouncedQuery = useDebounce(query, 300);

  // 加载数据
  useEffect(() => {
    const loadData = async () => {
      try {
        // 加载笔记
        const allNotes: any[] = [];
        for (const meeting of meetings) {
          const meetingNotes = await storageManager.getNotesByMeeting(meeting.id);
          allNotes.push(...meetingNotes);
        }
        setNotes(allNotes);

        // 加载模板
        const allTemplates = await storageManager.getAllTemplates();
        setTemplates(allTemplates);
      } catch (error) {
        console.error('加载数据失败:', error);
      }
    };

    if (meetings.length > 0) {
      loadData();
    }
  }, [meetings]);

  // 执行搜索
  const performSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([]);
      return;
    }

    setLoading(true);
    try {
      const searchResults = await searchService.search(
        {
          meetings,
          notes,
          templates
        },
        {
          query: searchQuery,
          fuzzy: true,
          limit: 8 // 限制结果数量以适应弹窗
        }
      );

      setResults(searchResults);
    } catch (error) {
      console.error('搜索失败:', error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [meetings, notes, templates]);

  // 监听查询变化
  useEffect(() => {
    performSearch(debouncedQuery);
  }, [debouncedQuery, performSearch]);

  // 处理键盘事件
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setOpen(true);
      }
      if (e.key === 'Escape') {
        setOpen(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const getTypeIcon = (type: SearchResult['type']) => {
    switch (type) {
      case 'meeting':
        return <Calendar className="h-4 w-4" />;
      case 'note':
        return <FileText className="h-4 w-4" />;
      case 'template':
        return <Layout className="h-4 w-4" />;
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
      default:
        return type;
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
      default:
        return '#';
    }
  };

  const handleResultClick = (result: SearchResult) => {
    setOpen(false);
    setQuery('');
    
    // 保存搜索历史
    if (query.trim()) {
      searchService.saveSearchHistory(query.trim());
    }

    // 导航到结果页面
    const url = getResultUrl(result);
    if (url !== '#') {
      router.push(url);
    }
  };

  const handleViewAllResults = () => {
    setOpen(false);
    
    // 保存搜索历史并导航到搜索页面
    if (query.trim()) {
      searchService.saveSearchHistory(query.trim());
      router.push(`/search?q=${encodeURIComponent(query)}`);
    } else {
      router.push('/search');
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            "relative w-full justify-start text-sm font-normal sm:pr-12 md:w-40 lg:w-64",
            className
          )}
        >
          <Search className="mr-2 h-4 w-4" />
          <span className="hidden lg:inline-flex">搜索会议、笔记...</span>
          <span className="inline-flex lg:hidden">搜索...</span>
          <kbd className="pointer-events-none absolute right-1.5 top-2 hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
            <span className="text-xs">⌘</span>K
          </kbd>
        </Button>
      </DialogTrigger>
      
      <DialogContent className="overflow-hidden p-0 shadow-lg sm:max-w-[550px]">
        <div className="flex items-center border-b px-3">
          <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索会议、笔记、模板..."
            className="flex h-11 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50 border-0 focus-visible:ring-0"
            autoFocus
          />
          {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin shrink-0 opacity-50" />}
        </div>

        {query ? (
          <ScrollArea className="max-h-[300px] overflow-y-auto">
            {results.length > 0 ? (
              <div className="grid gap-1">
                {results.map((result) => (
                  <div
                    key={result.id}
                    onClick={() => handleResultClick(result)}
                    className="flex cursor-pointer select-none items-center rounded-sm px-3 py-2 text-sm outline-none hover:bg-accent hover:text-accent-foreground"
                  >
                    <div className="mr-2 flex h-6 w-6 items-center justify-center">
                      {getTypeIcon(result.type)}
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <div className="truncate font-medium">{result.title}</div>
                      <div className="text-xs text-muted-foreground truncate">
                        {result.excerpt}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant="secondary" className="text-xs">
                        {getTypeLabel(result.type)}
                      </Badge>
                      <ArrowRight className="h-3 w-3 opacity-50" />
                    </div>
                  </div>
                ))}
                
                {/* 查看更多结果 */}
                <div className="border-t">
                  <div
                    onClick={handleViewAllResults}
                    className="flex cursor-pointer select-none items-center rounded-sm px-3 py-2 text-sm outline-none hover:bg-accent hover:text-accent-foreground"
                  >
                    <Search className="mr-2 h-4 w-4" />
                    <span>查看所有 "{query}" 的搜索结果</span>
                    <ArrowRight className="ml-auto h-3 w-3 opacity-50" />
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-6 text-center text-sm text-muted-foreground">
                <Search className="mx-auto h-8 w-8 opacity-50" />
                <p className="mt-2">未找到相关结果</p>
                <p className="text-xs">尝试使用不同的关键词</p>
              </div>
            )}
          </ScrollArea>
        ) : (
          <div className="px-3 py-2">
            <div className="text-sm text-muted-foreground space-y-3">
              <div>
                <p className="font-medium mb-2">快速搜索</p>
                <div className="flex flex-wrap gap-1">
                  {['今天的会议', '重要笔记', '项目模板', '待办事项'].map((suggestion) => (
                    <Button
                      key={suggestion}
                      variant="ghost"
                      size="sm"
                      className="h-6 text-xs"
                      onClick={() => setQuery(suggestion)}
                    >
                      {suggestion}
                    </Button>
                  ))}
                </div>
              </div>
              
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center space-x-1">
                  <kbd className="pointer-events-none h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono font-medium opacity-100 inline-flex">
                    <span>⌘</span>K
                  </kbd>
                  <span>打开搜索</span>
                </div>
                <div className="flex items-center space-x-1">
                  <kbd className="pointer-events-none h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono font-medium opacity-100 inline-flex">
                    ESC
                  </kbd>
                  <span>关闭</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}