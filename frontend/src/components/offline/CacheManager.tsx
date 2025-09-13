'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { 
  HardDrive,
  Trash2,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Clock,
  Database,
  Zap,
  TrendingUp,
  Settings
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { cacheService, CACHE_CONFIGS } from '@/lib/cache-service';
import { pwaService } from '@/lib/pwa-service';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface CacheManagerProps {
  className?: string;
}

export function CacheManager({ className }: CacheManagerProps) {
  const [cacheStats, setCacheStats] = useState<any[]>([]);
  const [totalSize, setTotalSize] = useState(0);
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState<string | null>(null);

  // 加载缓存统计
  const loadCacheStats = async () => {
    setLoading(true);
    try {
      // 获取应用缓存统计
      const appStats = cacheService.getAllStats();
      
      // 获取PWA缓存信息
      const pwaStats = await pwaService.getCacheInfo();
      
      // 合并统计信息
      const allStats = [
        ...appStats,
        ...pwaStats.caches.map(cache => ({
          name: cache.name,
          size: cache.size,
          hitRate: 0,
          items: [],
          type: 'pwa'
        }))
      ];
      
      setCacheStats(allStats);
      setTotalSize(pwaStats.totalSize);
    } catch (error) {
      console.error('加载缓存统计失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // 初始化缓存
    Object.values(CACHE_CONFIGS).forEach(config => {
      cacheService.initCache(config);
    });
    
    loadCacheStats();
  }, []);

  // 清理缓存
  const handleClearCache = async (cacheName: string, type?: string) => {
    setClearing(cacheName);
    try {
      if (type === 'pwa') {
        await pwaService.clearCache(cacheName);
      } else {
        cacheService.clear(cacheName);
      }
      await loadCacheStats();
    } catch (error) {
      console.error('清理缓存失败:', error);
    } finally {
      setClearing(null);
    }
  };

  // 清理过期项
  const handleCleanupExpired = async () => {
    setClearing('expired');
    try {
      const cleaned = cacheService.cleanupExpired();
      console.log(`清理了 ${cleaned} 个过期项`);
      await loadCacheStats();
    } catch (error) {
      console.error('清理过期项失败:', error);
    } finally {
      setClearing(null);
    }
  };

  // 全部清理
  const handleClearAll = async () => {
    const confirmed = confirm('确定要清除所有缓存吗？这将删除所有离线数据。');
    if (!confirmed) return;
    
    setClearing('all');
    try {
      // 清理应用缓存
      Object.keys(CACHE_CONFIGS).forEach(key => {
        cacheService.clear(CACHE_CONFIGS[key as keyof typeof CACHE_CONFIGS].name);
      });
      
      // 清理PWA缓存
      await pwaService.clearCache();
      
      await loadCacheStats();
    } catch (error) {
      console.error('清理所有缓存失败:', error);
    } finally {
      setClearing(null);
    }
  };

  // 格式化大小
  const formatSize = (size: number): string => {
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    if (size < 1024 * 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MB`;
    return `${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  };

  // 获取缓存类型信息
  const getCacheTypeInfo = (name: string) => {
    const config = Object.values(CACHE_CONFIGS).find(c => c.name === name);
    if (config) {
      return {
        label: name === 'meetings' ? '会议数据' : 
               name === 'notes' ? '笔记数据' :
               name === 'templates' ? '模板数据' :
               name === 'search' ? '搜索结果' :
               name === 'api' ? 'API响应' : name,
        color: name === 'meetings' ? 'bg-blue-100 text-blue-800' :
               name === 'notes' ? 'bg-green-100 text-green-800' :
               name === 'templates' ? 'bg-purple-100 text-purple-800' :
               name === 'search' ? 'bg-orange-100 text-orange-800' :
               'bg-gray-100 text-gray-800'
      };
    }
    return {
      label: name,
      color: 'bg-gray-100 text-gray-800'
    };
  };

  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="p-6">
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={cn("space-y-6", className)}>
      {/* 缓存总览 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <HardDrive className="h-5 w-5" />
            <span>缓存管理</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">总缓存大小</span>
                <span className="text-sm text-muted-foreground">
                  {formatSize(totalSize)}
                </span>
              </div>
              <Progress value={Math.min((totalSize / (10 * 1024 * 1024)) * 100, 100)} />
              <p className="text-xs text-muted-foreground">
                建议保持在10MB以下
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">缓存数量</span>
                <span className="text-sm text-muted-foreground">
                  {cacheStats.length} 个
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm text-green-600">运行正常</span>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">快速操作</span>
              </div>
              <div className="flex space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCleanupExpired}
                  disabled={clearing === 'expired'}
                >
                  {clearing === 'expired' ? (
                    <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                  ) : (
                    <Clock className="h-3 w-3 mr-1" />
                  )}
                  清理过期
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={loadCacheStats}
                  disabled={loading}
                >
                  <RefreshCw className={cn("h-3 w-3 mr-1", loading && "animate-spin")} />
                  刷新
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 缓存详情 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center space-x-2">
              <Database className="h-5 w-5" />
              <span>缓存详情</span>
            </CardTitle>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleClearAll}
              disabled={clearing === 'all'}
            >
              {clearing === 'all' ? (
                <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
              ) : (
                <Trash2 className="h-3 w-3 mr-1" />
              )}
              全部清理
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-80">
            <div className="space-y-4">
              {cacheStats.map((stat, index) => {
                const typeInfo = getCacheTypeInfo(stat.name);
                return (
                  <div key={index} className="border rounded-lg p-4">
                    <div className="flex items-start justify-between">
                      <div className="space-y-2">
                        <div className="flex items-center space-x-2">
                          <Badge variant="outline" className={typeInfo.color}>
                            {typeInfo.label}
                          </Badge>
                          {stat.type === 'pwa' && (
                            <Badge variant="secondary">PWA</Badge>
                          )}
                        </div>
                        
                        <div className="grid gap-2 md:grid-cols-3">
                          <div>
                            <span className="text-xs text-muted-foreground">项目数量</span>
                            <div className="font-medium">{stat.size}</div>
                          </div>
                          
                          {stat.hitRate !== undefined && (
                            <div>
                              <span className="text-xs text-muted-foreground">命中率</span>
                              <div className="font-medium">
                                {(stat.hitRate * 100).toFixed(1)}%
                              </div>
                            </div>
                          )}
                          
                          <div>
                            <span className="text-xs text-muted-foreground">状态</span>
                            <div className="flex items-center space-x-1">
                              <CheckCircle className="h-3 w-3 text-green-600" />
                              <span className="text-xs text-green-600">正常</span>
                            </div>
                          </div>
                        </div>
                      </div>

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleClearCache(stat.name, stat.type)}
                        disabled={clearing === stat.name}
                      >
                        {clearing === stat.name ? (
                          <RefreshCw className="h-3 w-3 animate-spin" />
                        ) : (
                          <Trash2 className="h-3 w-3" />
                        )}
                      </Button>
                    </div>

                    {/* 缓存项详情 */}
                    {stat.items && stat.items.length > 0 && (
                      <div className="mt-4 pt-4 border-t">
                        <div className="space-y-2">
                          <h5 className="text-xs font-medium text-muted-foreground">
                            最近缓存项 (显示前3个)
                          </h5>
                          {stat.items.slice(0, 3).map((item: any, itemIndex: number) => (
                            <div key={itemIndex} className="flex items-center justify-between text-xs">
                              <span className="truncate max-w-[200px]">{item.key}</span>
                              <div className="flex items-center space-x-2 text-muted-foreground">
                                <span>{formatSize(item.size || 0)}</span>
                                <span>{format(item.created, 'MM/dd HH:mm', { locale: zhCN })}</span>
                              </div>
                            </div>
                          ))}
                          {stat.items.length > 3 && (
                            <div className="text-xs text-muted-foreground">
                              还有 {stat.items.length - 3} 个项目...
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}

              {cacheStats.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <Database className="mx-auto h-12 w-12 mb-4 opacity-50" />
                  <p>暂无缓存数据</p>
                  <p className="text-sm">使用应用后将会显示缓存信息</p>
                </div>
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* 缓存建议 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <TrendingUp className="h-5 w-5" />
            <span>性能建议</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm">
            <div className="flex items-start space-x-3">
              <Zap className="h-4 w-4 text-blue-600 mt-0.5" />
              <div>
                <div className="font-medium">定期清理过期缓存</div>
                <div className="text-muted-foreground">建议每周清理一次过期项目以释放空间</div>
              </div>
            </div>
            
            <div className="flex items-start space-x-3">
              <Settings className="h-4 w-4 text-green-600 mt-0.5" />
              <div>
                <div className="font-medium">合理设置缓存大小</div>
                <div className="text-muted-foreground">保持总缓存大小在10MB以下可获得最佳性能</div>
              </div>
            </div>
            
            <div className="flex items-start space-x-3">
              <AlertCircle className="h-4 w-4 text-orange-600 mt-0.5" />
              <div>
                <div className="font-medium">注意存储空间</div>
                <div className="text-muted-foreground">设备存储空间不足时会自动清理最旧的缓存</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}