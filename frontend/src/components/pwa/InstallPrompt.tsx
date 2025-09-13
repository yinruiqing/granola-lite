'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  Smartphone,
  Download,
  X,
  CheckCircle,
  Star,
  Zap,
  Shield,
  Wifi
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { pwaService } from '@/lib/pwa-service';

interface InstallPromptProps {
  className?: string;
}

export function InstallPrompt({ className }: InstallPromptProps) {
  const [showPrompt, setShowPrompt] = useState(false);
  const [isInstalling, setIsInstalling] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const [canInstall, setCanInstall] = useState(false);

  useEffect(() => {
    // 检查是否已安装
    setIsInstalled(pwaService.isInstalled());
    
    // 如果已安装，不显示提示
    if (pwaService.isInstalled()) {
      return;
    }

    // 监听安装事件
    const handleInstallAvailable = () => {
      setCanInstall(true);
      setShowPrompt(true);
    };

    const handleInstalled = () => {
      setIsInstalled(true);
      setShowPrompt(false);
      setCanInstall(false);
    };

    pwaService.addEventListener('install-available', handleInstallAvailable);
    pwaService.addEventListener('installed', handleInstalled);

    // 延迟显示提示（给用户一些时间体验应用）
    const timer = setTimeout(() => {
      if (pwaService.canInstall() && !pwaService.isInstalled()) {
        setCanInstall(true);
        setShowPrompt(true);
      }
    }, 30000); // 30秒后显示

    return () => {
      clearTimeout(timer);
      pwaService.removeEventListener('install-available', handleInstallAvailable);
      pwaService.removeEventListener('installed', handleInstalled);
    };
  }, []);

  const handleInstall = async () => {
    setIsInstalling(true);
    try {
      const installed = await pwaService.showInstallPrompt();
      if (installed) {
        setIsInstalled(true);
        setShowPrompt(false);
      }
    } catch (error) {
      console.error('安装失败:', error);
    } finally {
      setIsInstalling(false);
    }
  };

  const handleDismiss = () => {
    setShowPrompt(false);
    // 记录用户拒绝安装，一段时间内不再提示
    localStorage.setItem('pwa-install-dismissed', Date.now().toString());
  };

  // 检查是否最近被拒绝过
  useEffect(() => {
    const dismissed = localStorage.getItem('pwa-install-dismissed');
    if (dismissed) {
      const dismissedTime = parseInt(dismissed);
      const now = Date.now();
      const threeDays = 3 * 24 * 60 * 60 * 1000; // 3天
      
      if (now - dismissedTime < threeDays) {
        setShowPrompt(false);
        return;
      }
    }
  }, []);

  if (isInstalled || !canInstall || !showPrompt) {
    return null;
  }

  return (
    <div className={cn("fixed bottom-4 left-4 right-4 z-50 sm:left-auto sm:w-96", className)}>
      <Card className="shadow-lg border-primary/20 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/20 dark:to-indigo-950/20">
        <CardHeader className="pb-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-3">
              <div className="bg-primary/10 rounded-full p-2">
                <Smartphone className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle className="text-lg">安装 Granola Lite</CardTitle>
                <CardDescription>
                  获得更好的体验
                </CardDescription>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDismiss}
              className="h-6 w-6 p-0 text-muted-foreground"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* 功能亮点 */}
          <div className="grid gap-3">
            <div className="flex items-center space-x-3">
              <div className="bg-green-100 dark:bg-green-900/30 rounded-full p-1">
                <Wifi className="h-3 w-3 text-green-600" />
              </div>
              <span className="text-sm">离线访问，随时记录</span>
            </div>
            
            <div className="flex items-center space-x-3">
              <div className="bg-blue-100 dark:bg-blue-900/30 rounded-full p-1">
                <Zap className="h-3 w-3 text-blue-600" />
              </div>
              <span className="text-sm">启动更快，性能更佳</span>
            </div>
            
            <div className="flex items-center space-x-3">
              <div className="bg-purple-100 dark:bg-purple-900/30 rounded-full p-1">
                <Shield className="h-3 w-3 text-purple-600" />
              </div>
              <span className="text-sm">安全可靠，数据本地</span>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex space-x-3">
            <Button 
              onClick={handleInstall} 
              disabled={isInstalling}
              className="flex-1"
            >
              {isInstalling ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  安装中...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4 mr-2" />
                  立即安装
                </>
              )}
            </Button>
            
            <Button 
              variant="outline" 
              onClick={handleDismiss}
              className="px-4"
            >
              稍后
            </Button>
          </div>

          {/* 安装提示 */}
          <div className="text-xs text-muted-foreground text-center">
            <p>安装后可从主屏幕直接启动，无需浏览器</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// 已安装状态指示器
export function PWAStatusBadge() {
  const [isInstalled, setIsInstalled] = useState(false);

  useEffect(() => {
    setIsInstalled(pwaService.isInstalled());
    
    const handleInstalled = () => {
      setIsInstalled(true);
    };

    pwaService.addEventListener('installed', handleInstalled);
    
    return () => {
      pwaService.removeEventListener('installed', handleInstalled);
    };
  }, []);

  if (!isInstalled) {
    return null;
  }

  return (
    <Badge 
      variant="secondary" 
      className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100"
    >
      <Smartphone className="h-3 w-3 mr-1" />
      已安装
    </Badge>
  );
}

// PWA功能介绍卡片
export function PWAFeatureCard({ className }: { className?: string }) {
  const features = [
    {
      icon: Wifi,
      title: '离线访问',
      description: '无网络时也能查看和编辑内容',
      color: 'text-blue-600'
    },
    {
      icon: Zap,
      title: '极速启动',
      description: '比网页版快3倍的启动速度',
      color: 'text-yellow-600'
    },
    {
      icon: Shield,
      title: '数据安全',
      description: '所有数据本地存储，隐私保护',
      color: 'text-green-600'
    },
    {
      icon: Smartphone,
      title: '原生体验',
      description: '类似原生APP的流畅体验',
      color: 'text-purple-600'
    }
  ];

  return (
    <Card className={cn("bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/20 dark:to-indigo-950/20", className)}>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Star className="h-5 w-5 text-primary" />
          <span>PWA 应用优势</span>
        </CardTitle>
        <CardDescription>
          安装后享受更好的使用体验
        </CardDescription>
      </CardHeader>
      
      <CardContent>
        <div className="grid gap-4 md:grid-cols-2">
          {features.map((feature, index) => (
            <div key={index} className="flex items-start space-x-3">
              <div className="bg-white dark:bg-gray-800 rounded-full p-2 shadow-sm">
                <feature.icon className={cn("h-4 w-4", feature.color)} />
              </div>
              <div>
                <h4 className="font-medium text-sm">{feature.title}</h4>
                <p className="text-xs text-muted-foreground mt-1">
                  {feature.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}