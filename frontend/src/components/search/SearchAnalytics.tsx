'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  BarChart3,
  TrendingUp,
  Search,
  Clock,
  Target,
  Users,
  Calendar,
  FileText,
  Layout,
  Zap,
  Star,
  Eye
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { SearchResult } from '@/lib/search-service';
import { format, startOfDay, subDays } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface SearchAnalyticsProps {
  results: SearchResult[];
  searchHistory: string[];
  className?: string;
}

interface SearchStats {
  totalSearches: number;
  totalResults: number;
  averageRelevance: number;
  popularTerms: { term: string; count: number }[];
  recentTrends: { date: string; searches: number }[];
  resultsByType: {
    meetings: number;
    notes: number;
    templates: number;
  };
  topResults: SearchResult[];
}

export function SearchAnalytics({ results, searchHistory, className }: SearchAnalyticsProps) {
  const [stats, setStats] = useState<SearchStats | null>(null);
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d');

  // 计算搜索统计
  useEffect(() => {
    const calculateStats = () => {
      // 计算热门搜索词
      const termCounts: Record<string, number> = {};
      searchHistory.forEach(term => {
        const words = term.toLowerCase().split(/\s+/);
        words.forEach(word => {
          if (word.length > 1) {
            termCounts[word] = (termCounts[word] || 0) + 1;
          }
        });
      });

      const popularTerms = Object.entries(termCounts)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 10)
        .map(([term, count]) => ({ term, count }));

      // 计算按类型分组的结果
      const resultsByType = {
        meetings: results.filter(r => r.type === 'meeting').length,
        notes: results.filter(r => r.type === 'note').length,
        templates: results.filter(r => r.type === 'template').length,
      };

      // 计算平均相关性
      const averageRelevance = results.length > 0 
        ? results.reduce((acc, r) => acc + r.score, 0) / results.length
        : 0;

      // 生成模拟的趋势数据（实际项目中应该从后端获取）
      const days = parseInt(timeRange.replace('d', ''));
      const recentTrends = Array.from({ length: days }, (_, i) => {
        const date = subDays(new Date(), days - i - 1);
        return {
          date: format(date, 'yyyy-MM-dd'),
          searches: Math.floor(Math.random() * 20) + 5 // 模拟数据
        };
      });

      // 获取高分结果
      const topResults = results
        .sort((a, b) => b.score - a.score)
        .slice(0, 5);

      setStats({
        totalSearches: searchHistory.length,
        totalResults: results.length,
        averageRelevance,
        popularTerms,
        recentTrends,
        resultsByType,
        topResults
      });
    };

    calculateStats();
  }, [results, searchHistory, timeRange]);

  if (!stats) {
    return (
      <div className={cn("space-y-6", className)}>
        <div className="animate-pulse space-y-4">
          <div className="h-32 bg-gray-200 rounded"></div>
          <div className="h-48 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("space-y-6", className)}>
      {/* 搜索概览统计 */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总搜索次数</CardTitle>
            <Search className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalSearches}</div>
            <p className="text-xs text-muted-foreground">
              过去{timeRange.replace('d', '天')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">搜索结果</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalResults}</div>
            <p className="text-xs text-muted-foreground">
              当前查询结果数
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">平均相关性</CardTitle>
            <Star className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {Math.round(stats.averageRelevance * 100)}%
            </div>
            <p className="text-xs text-muted-foreground">
              结果匹配度
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">搜索效率</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.totalResults > 0 ? Math.round(stats.totalResults / Math.max(stats.totalSearches, 1)) : 0}
            </div>
            <p className="text-xs text-muted-foreground">
              平均结果/次搜索
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* 结果类型分布 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5" />
              <span>结果类型分布</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Calendar className="h-4 w-4 text-blue-600" />
                  <span className="text-sm">会议</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-24 bg-secondary rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ 
                        width: `${stats.totalResults > 0 ? (stats.resultsByType.meetings / stats.totalResults) * 100 : 0}%` 
                      }}
                    />
                  </div>
                  <Badge variant="outline">{stats.resultsByType.meetings}</Badge>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <FileText className="h-4 w-4 text-green-600" />
                  <span className="text-sm">笔记</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-24 bg-secondary rounded-full h-2">
                    <div 
                      className="bg-green-600 h-2 rounded-full transition-all duration-300"
                      style={{ 
                        width: `${stats.totalResults > 0 ? (stats.resultsByType.notes / stats.totalResults) * 100 : 0}%` 
                      }}
                    />
                  </div>
                  <Badge variant="outline">{stats.resultsByType.notes}</Badge>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Layout className="h-4 w-4 text-purple-600" />
                  <span className="text-sm">模板</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-24 bg-secondary rounded-full h-2">
                    <div 
                      className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                      style={{ 
                        width: `${stats.totalResults > 0 ? (stats.resultsByType.templates / stats.totalResults) * 100 : 0}%` 
                      }}
                    />
                  </div>
                  <Badge variant="outline">{stats.resultsByType.templates}</Badge>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 热门搜索词 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5" />
              <span>热门搜索词</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-48">
              <div className="space-y-2">
                {stats.popularTerms.map((term, index) => (
                  <div key={term.term} className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <div className={cn(
                        "w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium",
                        index === 0 ? "bg-yellow-100 text-yellow-800" :
                        index === 1 ? "bg-gray-100 text-gray-800" :
                        index === 2 ? "bg-orange-100 text-orange-800" :
                        "bg-blue-100 text-blue-800"
                      )}>
                        {index + 1}
                      </div>
                      <span className="text-sm font-medium">{term.term}</span>
                    </div>
                    <Badge variant="secondary">{term.count}</Badge>
                  </div>
                ))}
                
                {stats.popularTerms.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <Search className="mx-auto h-8 w-8 mb-2 opacity-50" />
                    <p className="text-sm">暂无搜索数据</p>
                  </div>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* 搜索趋势 */}
        <Card className="md:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center space-x-2">
                <Clock className="h-5 w-5" />
                <span>搜索趋势</span>
              </CardTitle>
              <div className="flex space-x-1">
                {(['7d', '30d', '90d'] as const).map((range) => (
                  <Button
                    key={range}
                    variant={timeRange === range ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setTimeRange(range)}
                  >
                    {range.replace('d', '天')}
                  </Button>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {/* 简化的趋势图表 */}
              <div className="flex items-end space-x-1 h-32">
                {stats.recentTrends.map((trend, index) => (
                  <div
                    key={trend.date}
                    className="flex-1 flex flex-col items-center"
                  >
                    <div
                      className="bg-primary rounded-t w-full transition-all duration-300"
                      style={{
                        height: `${(trend.searches / 25) * 100}%`,
                        minHeight: '4px'
                      }}
                      title={`${trend.date}: ${trend.searches} 次搜索`}
                    />
                    {index % 5 === 0 && (
                      <span className="text-xs text-muted-foreground mt-1">
                        {format(new Date(trend.date), 'MM/dd')}
                      </span>
                    )}
                  </div>
                ))}
              </div>
              <p className="text-xs text-muted-foreground text-center">
                每日搜索次数变化趋势
              </p>
            </div>
          </CardContent>
        </Card>

        {/* 高质量结果 */}
        {stats.topResults.length > 0 && (
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Eye className="h-5 w-5" />
                <span>高相关性结果</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-48">
                <div className="space-y-3">
                  {stats.topResults.map((result, index) => (
                    <div key={result.id} className="flex items-start space-x-3 p-2 rounded-lg hover:bg-accent/50">
                      <div className="flex-shrink-0">
                        <div className={cn(
                          "w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium",
                          "bg-primary text-primary-foreground"
                        )}>
                          {index + 1}
                        </div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <h4 className="text-sm font-medium truncate">{result.title}</h4>
                          <Badge variant="outline" className="text-xs">
                            {result.type === 'meeting' ? '会议' : 
                             result.type === 'note' ? '笔记' : '模板'}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                          {result.excerpt}
                        </p>
                        <div className="flex items-center space-x-2 mt-2">
                          <div className="flex items-center space-x-1">
                            <Star className="h-3 w-3 text-yellow-500" />
                            <span className="text-xs font-medium">
                              {Math.round(result.score * 100)}%
                            </span>
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {format(new Date(result.metadata.created_at), "MM/dd", { locale: zhCN })}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}