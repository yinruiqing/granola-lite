'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { 
  Search as SearchIcon,
  Filter,
  SortAsc,
  LayoutGrid,
  List,
  Calendar,
  FileText,
  Layout,
  TrendingUp,
  Clock,
  Users,
  BarChart3,
  Zap,
  Settings
} from 'lucide-react';
import { useAppStore } from '@/lib/store';
import { storageManager } from '@/lib/storage';
import { Meeting, Note, Template } from '@/types';
import { SearchInput } from '@/components/search/SearchInput';
import { SearchResults } from '@/components/search/SearchResults';
import { SearchFilters } from '@/components/search/SearchFilters';
import { SearchAnalytics } from '@/components/search/SearchAnalytics';
import { searchService, SearchFilter, SearchResult, SearchOptions } from '@/lib/search-service';
import { cn } from '@/lib/utils';
import { useDebounce } from '@/hooks/useDebounce';

interface SearchStats {
  totalResults: number;
  byType: {
    meetings: number;
    notes: number;
    templates: number;
  };
  searchTime: number;
  avgRelevance: number;
}

export default function SearchPage() {
  const { meetings } = useAppStore();
  const [notes, setNotes] = useState<Note[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<SearchFilter>({});
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const [sortBy, setSortBy] = useState<'relevance' | 'date' | 'title' | 'type'>('relevance');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [searchStats, setSearchStats] = useState<SearchStats | null>(null);

  // 使用防抖优化搜索性能
  const debouncedQuery = useDebounce(query, 300);

  // 加载数据
  useEffect(() => {
    const loadData = async () => {
      try {
        // 加载笔记
        const allNotes: Note[] = [];
        for (const meeting of meetings) {
          const meetingNotes = await storageManager.getNotesByMeeting(meeting.id);
          allNotes.push(...meetingNotes);
        }
        setNotes(allNotes);

        // 加载模板
        const allTemplates = await storageManager.getAllTemplates();
        setTemplates(allTemplates);

        // 加载搜索历史
        const history = searchService.getSearchHistory();
        setSearchHistory(history);
      } catch (error) {
        console.error('加载数据失败:', error);
      }
    };

    loadData();
  }, [meetings]);

  // 执行搜索
  const performSearch = useCallback(async (searchQuery: string, searchFilters: SearchFilter) => {
    if (!searchQuery.trim() && Object.keys(searchFilters).length === 0) {
      setResults([]);
      setSearchStats(null);
      return;
    }

    setLoading(true);
    const startTime = Date.now();

    try {
      const searchOptions: SearchOptions = {
        query: searchQuery,
        filters: searchFilters,
        sortBy,
        sortOrder,
        fuzzy: true,
        limit: 50
      };

      const searchResults = await searchService.search(
        {
          meetings,
          notes,
          templates
        },
        searchOptions
      );

      const endTime = Date.now();
      const searchTime = endTime - startTime;

      setResults(searchResults);

      // 计算搜索统计
      const stats: SearchStats = {
        totalResults: searchResults.length,
        byType: {
          meetings: searchResults.filter(r => r.type === 'meeting').length,
          notes: searchResults.filter(r => r.type === 'note').length,
          templates: searchResults.filter(r => r.type === 'template').length
        },
        searchTime,
        avgRelevance: searchResults.reduce((acc, r) => acc + r.score, 0) / (searchResults.length || 1)
      };
      setSearchStats(stats);

      // 保存搜索历史
      if (searchQuery.trim()) {
        searchService.saveSearchHistory(searchQuery.trim());
        const newHistory = searchService.getSearchHistory();
        setSearchHistory(newHistory);
      }
    } catch (error) {
      console.error('搜索失败:', error);
      setResults([]);
      setSearchStats(null);
    } finally {
      setLoading(false);
    }
  }, [meetings, notes, templates, sortBy, sortOrder]);

  // 获取搜索建议
  const getSuggestions = useCallback(async (searchQuery: string) => {
    if (searchQuery.length < 2) {
      setSuggestions([]);
      return;
    }

    try {
      const searchSuggestions = await searchService.getSearchSuggestions(
        searchQuery,
        { meetings, notes, templates }
      );
      setSuggestions(searchSuggestions);
    } catch (error) {
      console.error('获取建议失败:', error);
      setSuggestions([]);
    }
  }, [meetings, notes, templates]);

  // 监听查询变化
  useEffect(() => {
    getSuggestions(debouncedQuery);
  }, [debouncedQuery, getSuggestions]);

  // 监听查询和过滤器变化执行搜索
  useEffect(() => {
    performSearch(debouncedQuery, filters);
  }, [debouncedQuery, filters, performSearch]);

  // 处理搜索
  const handleSearch = (searchQuery: string) => {
    setQuery(searchQuery);
  };

  // 处理结果点击
  const handleResultClick = (result: SearchResult) => {
    // 这里可以添加结果点击的处理逻辑
    console.log('点击结果:', result);
  };

  // 可用的过滤器数据
  const availableFilterData = useMemo(() => {
    const participants = new Set<string>();
    const categories = new Set<string>();
    const types = new Set<string>();
    const statuses = new Set<string>();

    meetings.forEach(meeting => {
      if (meeting.participants) {
        meeting.participants.split(',').forEach(p => participants.add(p.trim()));
      }
      statuses.add(meeting.status);
    });

    templates.forEach(template => {
      categories.add(template.category);
      types.add(template.type);
    });

    return {
      participants: Array.from(participants),
      categories: Array.from(categories),
      types: Array.from(types),
      statuses: Array.from(statuses)
    };
  }, [meetings, templates]);

  // 按类型分组的结果
  const resultsByType = useMemo(() => {
    return {
      meetings: results.filter(r => r.type === 'meeting'),
      notes: results.filter(r => r.type === 'note'),
      templates: results.filter(r => r.type === 'template')
    };
  }, [results]);

  return (
    <div className="space-y-6">
      {/* 页面标题和搜索框 */}
      <div className="space-y-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">全局搜索</h1>
          <p className="text-muted-foreground">
            在会议、笔记和模板中快速查找内容
          </p>
        </div>

        {/* 主搜索框 */}
        <div className="max-w-2xl">
          <SearchInput
            value={query}
            onChange={setQuery}
            onSearch={handleSearch}
            suggestions={suggestions}
            searchHistory={searchHistory}
            loading={loading}
            placeholder="搜索会议、笔记、模板..."
          />
        </div>

        {/* 搜索工具栏 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button
              variant={showFilters ? "default" : "outline"}
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
            >
              <Filter className="h-4 w-4 mr-2" />
              过滤器
              {Object.keys(filters).length > 0 && (
                <Badge variant="secondary" className="ml-2">
                  {Object.keys(filters).length}
                </Badge>
              )}
            </Button>

            <Select value={sortBy} onValueChange={(value: any) => setSortBy(value)}>
              <SelectTrigger className="w-40">
                <SortAsc className="h-4 w-4 mr-2" />
                <SelectValue placeholder="排序" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="relevance">相关性</SelectItem>
                <SelectItem value="date">日期</SelectItem>
                <SelectItem value="title">标题</SelectItem>
                <SelectItem value="type">类型</SelectItem>
              </SelectContent>
            </Select>

            <div className="flex items-center border rounded-md">
              <Button
                variant={viewMode === 'list' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('list')}
              >
                <List className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === 'grid' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setViewMode('grid')}
              >
                <LayoutGrid className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* 搜索统计 */}
          {searchStats && (
            <div className="flex items-center space-x-4 text-sm text-muted-foreground">
              <span>找到 {searchStats.totalResults} 个结果</span>
              <span>用时 {searchStats.searchTime}ms</span>
            </div>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-4">
        {/* 过滤器侧边栏 */}
        {showFilters && (
          <div className="lg:col-span-1">
            <SearchFilters
              filters={filters}
              onFiltersChange={setFilters}
              availableData={availableFilterData}
            />
          </div>
        )}

        {/* 主内容区 */}
        <div className={cn("space-y-6", showFilters ? "lg:col-span-3" : "lg:col-span-4")}>
          {/* 搜索结果统计卡片 */}
          {searchStats && (
            <div className="grid gap-4 md:grid-cols-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">总结果</CardTitle>
                  <SearchIcon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{searchStats.totalResults}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">会议</CardTitle>
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{searchStats.byType.meetings}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">笔记</CardTitle>
                  <FileText className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{searchStats.byType.notes}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">模板</CardTitle>
                  <Layout className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{searchStats.byType.templates}</div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* 搜索结果 */}
          <div>
            {query || Object.keys(filters).length > 0 ? (
              <Tabs defaultValue="all" className="space-y-4">
                <TabsList>
                  <TabsTrigger value="all">
                    全部 ({results.length})
                  </TabsTrigger>
                  <TabsTrigger value="meetings">
                    会议 ({resultsByType.meetings.length})
                  </TabsTrigger>
                  <TabsTrigger value="notes">
                    笔记 ({resultsByType.notes.length})
                  </TabsTrigger>
                  <TabsTrigger value="templates">
                    模板 ({resultsByType.templates.length})
                  </TabsTrigger>
                  <TabsTrigger value="analytics">
                    分析 <BarChart3 className="ml-1 h-3 w-3" />
                  </TabsTrigger>
                </TabsList>

                <TabsContent value="all">
                  <SearchResults
                    results={results}
                    loading={loading}
                    query={query}
                    onResultClick={handleResultClick}
                  />
                </TabsContent>

                <TabsContent value="meetings">
                  <SearchResults
                    results={resultsByType.meetings}
                    loading={loading}
                    query={query}
                    onResultClick={handleResultClick}
                  />
                </TabsContent>

                <TabsContent value="notes">
                  <SearchResults
                    results={resultsByType.notes}
                    loading={loading}
                    query={query}
                    onResultClick={handleResultClick}
                  />
                </TabsContent>

                <TabsContent value="templates">
                  <SearchResults
                    results={resultsByType.templates}
                    loading={loading}
                    query={query}
                    onResultClick={handleResultClick}
                  />
                </TabsContent>

                <TabsContent value="analytics">
                  <SearchAnalytics
                    results={results}
                    searchHistory={searchHistory}
                  />
                </TabsContent>
              </Tabs>
            ) : (
              /* 空状态 - 搜索建议 */
              <div className="space-y-8">
                {/* 快速开始 */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Zap className="h-5 w-5" />
                      <span>快速开始</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 md:grid-cols-2">
                      <Button
                        variant="outline"
                        className="justify-start h-auto p-4"
                        onClick={() => handleSearch('今天的会议')}
                      >
                        <div className="text-left">
                          <div className="font-medium">今天的会议</div>
                          <div className="text-sm text-muted-foreground">查看今日的所有会议</div>
                        </div>
                      </Button>

                      <Button
                        variant="outline"
                        className="justify-start h-auto p-4"
                        onClick={() => handleSearch('重要笔记')}
                      >
                        <div className="text-left">
                          <div className="font-medium">重要笔记</div>
                          <div className="text-sm text-muted-foreground">查找标记为重要的笔记</div>
                        </div>
                      </Button>

                      <Button
                        variant="outline"
                        className="justify-start h-auto p-4"
                        onClick={() => handleSearch('项目模板')}
                      >
                        <div className="text-left">
                          <div className="font-medium">项目模板</div>
                          <div className="text-sm text-muted-foreground">查找项目相关模板</div>
                        </div>
                      </Button>

                      <Button
                        variant="outline"
                        className="justify-start h-auto p-4"
                        onClick={() => setFilters({ hasAIEnhancement: true })}
                      >
                        <div className="text-left">
                          <div className="font-medium">AI增强内容</div>
                          <div className="text-sm text-muted-foreground">查看AI优化的内容</div>
                        </div>
                      </Button>
                    </div>
                  </CardContent>
                </Card>

                {/* 搜索提示 */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <BarChart3 className="h-5 w-5" />
                      <span>搜索技巧</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4 text-sm">
                      <div className="grid gap-4 md:grid-cols-2">
                        <div>
                          <h4 className="font-medium mb-2">基础搜索</h4>
                          <ul className="space-y-1 text-muted-foreground">
                            <li>• 输入关键词进行搜索</li>
                            <li>• 支持中英文混合搜索</li>
                            <li>• 自动匹配相关内容</li>
                          </ul>
                        </div>
                        <div>
                          <h4 className="font-medium mb-2">高级技巧</h4>
                          <ul className="space-y-1 text-muted-foreground">
                            <li>• 使用过滤器精确筛选</li>
                            <li>• 按类型、日期、参与者过滤</li>
                            <li>• 支持模糊匹配和智能建议</li>
                          </ul>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* 最近搜索历史 */}
                {searchHistory.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2">
                        <Clock className="h-5 w-5" />
                        <span>最近搜索</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-wrap gap-2">
                        {searchHistory.slice(0, 10).map((search, index) => (
                          <Badge
                            key={index}
                            variant="secondary"
                            className="cursor-pointer hover:bg-primary hover:text-primary-foreground transition-colors"
                            onClick={() => handleSearch(search)}
                          >
                            {search}
                          </Badge>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}