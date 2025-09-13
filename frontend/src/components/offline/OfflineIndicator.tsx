'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Wifi,
  WifiOff,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Clock,
  X
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { pwaService } from '@/lib/pwa-service';

interface OfflineIndicatorProps {
  className?: string;
}

export function OfflineIndicator({ className }: OfflineIndicatorProps) {
  const [isOnline, setIsOnline] = useState(true);
  const [showIndicator, setShowIndicator] = useState(false);
  const [pendingSync, setPendingSync] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(null);
  const [syncQueue, setSyncQueue] = useState<string[]>([]);

  useEffect(() => {
    // 初始状态
    setIsOnline(navigator.onLine);
    
    // 监听网络状态变化
    const handleOnline = () => {
      setIsOnline(true);
      setShowIndicator(true);
      setPendingSync(true);
      
      // 3秒后隐藏指示器
      setTimeout(() => {
        setShowIndicator(false);
        setPendingSync(false);
        setLastSyncTime(new Date());
      }, 3000);
    };

    const handleOffline = () => {
      setIsOnline(false);
      setShowIndicator(true);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // 监听PWA服务事件
    const handlePWAOnline = () => {
      console.log('PWA: Back online');
      setPendingSync(true);
    };

    const handlePWAOffline = () => {
      console.log('PWA: Gone offline');
    };

    const handleSyncComplete = (event: CustomEvent) => {
      console.log('PWA: Sync completed', event.detail);
      setPendingSync(false);
      setLastSyncTime(new Date());
      setSyncQueue([]);
    };

    pwaService.addEventListener('network-online', handlePWAOnline);
    pwaService.addEventListener('network-offline', handlePWAOffline);
    pwaService.addEventListener('sync-complete', handleSyncComplete);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      pwaService.removeEventListener('network-online', handlePWAOnline);
      pwaService.removeEventListener('network-offline', handlePWAOffline);
      pwaService.removeEventListener('sync-complete', handleSyncComplete);
    };
  }, []);

  // 手动重新连接
  const handleRetry = () => {
    if (navigator.onLine) {
      setIsOnline(true);
      setPendingSync(true);
      // 触发同步
      setTimeout(() => {
        setPendingSync(false);
        setLastSyncTime(new Date());
      }, 2000);
    }
  };

  // 关闭指示器
  const handleClose = () => {
    setShowIndicator(false);
  };

  // 添加到同步队列（模拟）
  const addToSyncQueue = (item: string) => {
    setSyncQueue(prev => [...prev, item]);
  };

  if (!showIndicator && isOnline) {
    return null;
  }

  return (
    <div className={cn("fixed top-4 right-4 z-50 max-w-sm", className)}>
      <Card className={cn(
        "shadow-lg border-l-4 transition-all duration-300",
        isOnline ? "border-l-green-500 bg-green-50 dark:bg-green-950" : "border-l-red-500 bg-red-50 dark:bg-red-950"
      )}>
        <CardContent className="p-4">
          <div className="flex items-start justify-between space-x-3">
            <div className="flex items-center space-x-3">
              <div className={cn(
                "flex-shrink-0 rounded-full p-2",
                isOnline ? "bg-green-100 dark:bg-green-900" : "bg-red-100 dark:bg-red-900"
              )}>
                {pendingSync ? (
                  <RefreshCw className="h-4 w-4 text-blue-600 animate-spin" />
                ) : isOnline ? (
                  <Wifi className="h-4 w-4 text-green-600" />
                ) : (
                  <WifiOff className="h-4 w-4 text-red-600" />
                )}
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center space-x-2">
                  <p className={cn(
                    "text-sm font-medium",
                    isOnline ? "text-green-900 dark:text-green-100" : "text-red-900 dark:text-red-100"
                  )}>
                    {pendingSync ? '正在同步...' : isOnline ? '已连接' : '离线模式'}
                  </p>
                  
                  {syncQueue.length > 0 && (
                    <Badge variant="secondary" className="text-xs">
                      {syncQueue.length}个待同步
                    </Badge>
                  )}
                </div>
                
                <p className={cn(
                  "text-xs mt-1",
                  isOnline ? "text-green-700 dark:text-green-300" : "text-red-700 dark:text-red-300"
                )}>
                  {pendingSync 
                    ? '正在同步离线数据...'
                    : isOnline 
                      ? '网络连接正常，数据已同步'
                      : '当前离线，数据将在恢复连接时同步'
                  }
                </p>
                
                {lastSyncTime && (
                  <div className="flex items-center space-x-1 mt-1">
                    <Clock className="h-3 w-3 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">
                      上次同步: {lastSyncTime.toLocaleTimeString()}
                    </span>
                  </div>
                )}
              </div>
            </div>
            
            <div className="flex items-center space-x-1">
              {!isOnline && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleRetry}
                  className="h-6 w-6 p-0"
                >
                  <RefreshCw className="h-3 w-3" />
                </Button>
              )}
              
              <Button
                variant="ghost"
                size="sm"
                onClick={handleClose}
                className="h-6 w-6 p-0"
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          </div>
          
          {/* 同步队列详情 */}
          {syncQueue.length > 0 && (
            <div className="mt-3 pt-3 border-t">
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">
                  待同步项目:
                </p>
                <div className="space-y-1">
                  {syncQueue.slice(0, 3).map((item, index) => (
                    <div key={index} className="flex items-center space-x-2">
                      <div className="w-2 h-2 rounded-full bg-yellow-400"></div>
                      <span className="text-xs text-muted-foreground">{item}</span>
                    </div>
                  ))}
                  {syncQueue.length > 3 && (
                    <div className="text-xs text-muted-foreground">
                      还有 {syncQueue.length - 3} 个项目...
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// 网络状态钩子
export function useNetworkStatus() {
  const [isOnline, setIsOnline] = useState(true);
  const [connectionType, setConnectionType] = useState<string>('unknown');

  useEffect(() => {
    setIsOnline(navigator.onLine);

    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // 获取连接类型（如果支持）
    if ('connection' in navigator) {
      const connection = (navigator as any).connection;
      setConnectionType(connection.effectiveType || connection.type || 'unknown');
      
      const handleConnectionChange = () => {
        setConnectionType(connection.effectiveType || connection.type || 'unknown');
      };
      
      connection.addEventListener('change', handleConnectionChange);
      
      return () => {
        window.removeEventListener('online', handleOnline);
        window.removeEventListener('offline', handleOffline);
        connection.removeEventListener('change', handleConnectionChange);
      };
    }

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return {
    isOnline,
    connectionType,
    isSlowConnection: connectionType === 'slow-2g' || connectionType === '2g'
  };
}