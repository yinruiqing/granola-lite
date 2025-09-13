'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Activity, 
  Zap, 
  Clock, 
  TrendingUp, 
  AlertTriangle, 
  Info,
  RefreshCw,
  BarChart3,
  Monitor
} from 'lucide-react'
import { performanceService, PerformanceMetrics, PerformanceRecommendation } from '@/lib/performance-service'

interface PerformanceMonitorProps {
  className?: string;
}

export function PerformanceMonitor({ className }: PerformanceMonitorProps) {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [recommendations, setRecommendations] = useState<PerformanceRecommendation[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    initializeMonitoring();

    return () => {
      performanceService.cleanup();
    };
  }, []);

  const initializeMonitoring = async () => {
    try {
      setIsLoading(true);
      await performanceService.initialize();
      
      // 延迟获取指标，确保有足够数据
      setTimeout(() => {
        updateMetrics();
        setIsLoading(false);
      }, 2000);

      // 定期更新指标
      const interval = setInterval(updateMetrics, 5000);
      return () => clearInterval(interval);
    } catch (error) {
      console.error('性能监控初始化失败:', error);
      setIsLoading(false);
    }
  };

  const updateMetrics = () => {
    const currentMetrics = performanceService.getMetrics();
    const currentRecommendations = performanceService.getRecommendations();
    
    setMetrics(currentMetrics);
    setRecommendations(currentRecommendations);
  };

  const handleRefresh = () => {
    updateMetrics();
  };

  const getMetricStatus = (value: number, thresholds: { good: number; poor: number }) => {
    if (value <= thresholds.good) return 'good';
    if (value <= thresholds.poor) return 'needs-improvement';
    return 'poor';
  };

  const getMetricColor = (status: string) => {
    switch (status) {
      case 'good': return 'text-green-600';
      case 'needs-improvement': return 'text-yellow-600';
      case 'poor': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  if (isLoading) {
    return (
      <div className={`flex items-center justify-center p-8 ${className}`}>
        <div className="flex items-center space-x-2">
          <RefreshCw className="h-4 w-4 animate-spin" />
          <span>正在初始化性能监控...</span>
        </div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center p-8">
          <div className="text-center">
            <Monitor className="h-8 w-8 text-gray-400 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">暂无性能数据</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-semibold">性能监控</h2>
          <p className="text-sm text-muted-foreground">实时监控应用性能指标</p>
        </div>
        <Button onClick={handleRefresh} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          刷新数据
        </Button>
      </div>

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList>
          <TabsTrigger value="overview">概览</TabsTrigger>
          <TabsTrigger value="vitals">Core Web Vitals</TabsTrigger>
          <TabsTrigger value="recommendations">优化建议</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* 页面加载时间 */}
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center space-x-2">
                  <Clock className="h-4 w-4 text-blue-600" />
                  <span className="text-sm font-medium">加载时间</span>
                </div>
                <div className="mt-2">
                  <div className="text-2xl font-bold">{formatDuration(metrics.loadTime)}</div>
                  <div className="text-xs text-muted-foreground">页面完全加载</div>
                </div>
              </CardContent>
            </Card>

            {/* DOM 就绪时间 */}
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center space-x-2">
                  <Zap className="h-4 w-4 text-green-600" />
                  <span className="text-sm font-medium">DOM 就绪</span>
                </div>
                <div className="mt-2">
                  <div className="text-2xl font-bold">{formatDuration(metrics.domContentLoaded)}</div>
                  <div className="text-xs text-muted-foreground">DOM 解析完成</div>
                </div>
              </CardContent>
            </Card>

            {/* 内存使用 */}
            {metrics.memoryUsage && (
              <Card>
                <CardContent className="p-4">
                  <div className="flex items-center space-x-2">
                    <BarChart3 className="h-4 w-4 text-purple-600" />
                    <span className="text-sm font-medium">内存使用</span>
                  </div>
                  <div className="mt-2">
                    <div className="text-2xl font-bold">{metrics.memoryUsage.used.toFixed(1)}MB</div>
                    <div className="text-xs text-muted-foreground">
                      / {metrics.memoryUsage.total.toFixed(1)}MB
                    </div>
                    <Progress 
                      value={(metrics.memoryUsage.used / metrics.memoryUsage.total) * 100} 
                      className="mt-2 h-1"
                    />
                  </div>
                </CardContent>
              </Card>
            )}

            {/* 优化状态 */}
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center space-x-2">
                  <TrendingUp className="h-4 w-4 text-orange-600" />
                  <span className="text-sm font-medium">优化建议</span>
                </div>
                <div className="mt-2">
                  <div className="text-2xl font-bold">{recommendations.length}</div>
                  <div className="text-xs text-muted-foreground">
                    {recommendations.filter(r => r.type === 'critical').length} 个关键项
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="vitals" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* LCP - Largest Contentful Paint */}
            {metrics.largestContentfulPaint && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">最大内容绘制 (LCP)</CardTitle>
                  <CardDescription>主要内容加载时间</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className={`text-2xl font-bold ${getMetricColor(getMetricStatus(metrics.largestContentfulPaint, { good: 2500, poor: 4000 }))}`}>
                    {formatDuration(metrics.largestContentfulPaint)}
                  </div>
                  <Badge 
                    variant={
                      getMetricStatus(metrics.largestContentfulPaint, { good: 2500, poor: 4000 }) === 'good' 
                        ? 'default' 
                        : 'destructive'
                    }
                    className="mt-2"
                  >
                    {getMetricStatus(metrics.largestContentfulPaint, { good: 2500, poor: 4000 }) === 'good' ? '良好' : '需优化'}
                  </Badge>
                </CardContent>
              </Card>
            )}

            {/* FID - First Input Delay */}
            {metrics.firstInputDelay && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">首次输入延迟 (FID)</CardTitle>
                  <CardDescription>用户交互响应时间</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className={`text-2xl font-bold ${getMetricColor(getMetricStatus(metrics.firstInputDelay, { good: 100, poor: 300 }))}`}>
                    {formatDuration(metrics.firstInputDelay)}
                  </div>
                  <Badge 
                    variant={
                      getMetricStatus(metrics.firstInputDelay, { good: 100, poor: 300 }) === 'good' 
                        ? 'default' 
                        : 'destructive'
                    }
                    className="mt-2"
                  >
                    {getMetricStatus(metrics.firstInputDelay, { good: 100, poor: 300 }) === 'good' ? '良好' : '需优化'}
                  </Badge>
                </CardContent>
              </Card>
            )}

            {/* CLS - Cumulative Layout Shift */}
            {metrics.cumulativeLayoutShift !== undefined && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">累积布局偏移 (CLS)</CardTitle>
                  <CardDescription>视觉稳定性指标</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className={`text-2xl font-bold ${getMetricColor(getMetricStatus(metrics.cumulativeLayoutShift, { good: 0.1, poor: 0.25 }))}`}>
                    {metrics.cumulativeLayoutShift.toFixed(3)}
                  </div>
                  <Badge 
                    variant={
                      getMetricStatus(metrics.cumulativeLayoutShift, { good: 0.1, poor: 0.25 }) === 'good' 
                        ? 'default' 
                        : 'destructive'
                    }
                    className="mt-2"
                  >
                    {getMetricStatus(metrics.cumulativeLayoutShift, { good: 0.1, poor: 0.25 }) === 'good' ? '良好' : '需优化'}
                  </Badge>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        <TabsContent value="recommendations" className="space-y-4">
          {recommendations.length === 0 ? (
            <Card>
              <CardContent className="flex items-center justify-center p-8">
                <div className="text-center">
                  <TrendingUp className="h-8 w-8 text-green-500 mx-auto mb-2" />
                  <p className="font-medium text-green-700">性能表现良好</p>
                  <p className="text-sm text-muted-foreground">暂无优化建议</p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {recommendations.map((recommendation, index) => (
                <Card key={index}>
                  <CardContent className="p-4">
                    <div className="flex items-start space-x-3">
                      {recommendation.type === 'critical' && (
                        <AlertTriangle className="h-5 w-5 text-red-500 mt-0.5" />
                      )}
                      {recommendation.type === 'warning' && (
                        <AlertTriangle className="h-5 w-5 text-yellow-500 mt-0.5" />
                      )}
                      {recommendation.type === 'info' && (
                        <Info className="h-5 w-5 text-blue-500 mt-0.5" />
                      )}
                      
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <h3 className="font-medium">{recommendation.title}</h3>
                          <Badge 
                            variant={
                              recommendation.impact === 'high' ? 'destructive' :
                              recommendation.impact === 'medium' ? 'default' : 'secondary'
                            }
                          >
                            {recommendation.impact === 'high' ? '高影响' :
                             recommendation.impact === 'medium' ? '中影响' : '低影响'}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          {recommendation.description}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}