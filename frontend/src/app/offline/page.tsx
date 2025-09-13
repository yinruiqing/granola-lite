'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Wifi,
  WifiOff,
  Download,
  HardDrive,
  Smartphone,
  Bell,
  Shield,
  Zap,
  Cloud,
  Settings,
  CheckCircle,
  AlertCircle
} from 'lucide-react';
import { CacheManager } from '@/components/offline/CacheManager';
import { PWAFeatureCard, PWAStatusBadge } from '@/components/pwa/InstallPrompt';
import { useNetworkStatus } from '@/components/offline/OfflineIndicator';
import { pwaService } from '@/lib/pwa-service';

export default function OfflinePage() {
  const { isOnline, connectionType, isSlowConnection } = useNetworkStatus();
  const [pwaInstalled, setPwaInstalled] = useState(false);
  const [notificationEnabled, setNotificationEnabled] = useState(false);
  const [offlineMode, setOfflineMode] = useState(false);
  const [autoSync, setAutoSync] = useState(true);
  const [backgroundSync, setBackgroundSync] = useState(true);
  const [deviceInfo, setDeviceInfo] = useState<any>(null);

  useEffect(() => {
    // 获取PWA状态
    setPwaInstalled(pwaService.isInstalled());
    
    // 获取设备信息
    setDeviceInfo(pwaService.getDeviceInfo());
    
    // 检查通知权限
    if ('Notification' in window) {
      setNotificationEnabled(Notification.permission === 'granted');
    }

    // 从localStorage获取设置
    const settings = {
      offlineMode: localStorage.getItem('offline-mode') === 'true',
      autoSync: localStorage.getItem('auto-sync') !== 'false',
      backgroundSync: localStorage.getItem('background-sync') !== 'false',
    };
    
    setOfflineMode(settings.offlineMode);
    setAutoSync(settings.autoSync);
    setBackgroundSync(settings.backgroundSync);
  }, []);

  // 切换离线模式
  const handleOfflineModeToggle = (enabled: boolean) => {
    setOfflineMode(enabled);
    localStorage.setItem('offline-mode', enabled.toString());
    
    if (enabled) {
      // 预缓存重要资源
      pwaService.cacheResources([
        '/',
        '/meetings',
        '/notes',
        '/templates'
      ]);
    }
  };

  // 安装PWA
  const handleInstallPWA = async () => {
    const installed = await pwaService.showInstallPrompt();
    if (installed) {
      setPwaInstalled(true);
    }
  };

  // 请求通知权限
  const handleNotificationToggle = async (enabled: boolean) => {
    if (enabled) {
      const permission = await pwaService.requestNotificationPermission();
      setNotificationEnabled(permission === 'granted');
    } else {
      setNotificationEnabled(false);
    }
  };

  // 测试通知
  const handleTestNotification = async () => {
    await pwaService.sendNotification({
      title: '测试通知',
      body: 'Granola Lite 通知功能正常工作！',
      tag: 'test'
    });
  };

  // 分享应用
  const handleShare = async () => {
    const shared = await pwaService.share({
      title: 'Granola Lite - AI 会议纪要工具',
      text: '推荐一个很棒的会议记录工具',
      url: window.location.origin
    });
    
    if (!shared) {
      // 回退到复制链接
      alert('链接已复制到剪贴板');
    }
  };

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">离线支持</h1>
          <p className="text-muted-foreground">
            管理离线功能、缓存和PWA设置
          </p>
        </div>
        <PWAStatusBadge />
      </div>

      {/* 网络状态 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            {isOnline ? <Wifi className="h-5 w-5" /> : <WifiOff className="h-5 w-5" />}
            <span>网络状态</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <Label>连接状态</Label>
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className={isOnline ? 'text-green-600' : 'text-red-600'}>
                  {isOnline ? '在线' : '离线'}
                </span>
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>连接类型</Label>
              <Badge variant="outline">
                {connectionType === 'wifi' ? 'WiFi' : 
                 connectionType === '4g' ? '4G' :
                 connectionType === '3g' ? '3G' :
                 connectionType === '2g' ? '2G' :
                 connectionType === 'slow-2g' ? '慢速2G' : '未知'}
              </Badge>
            </div>
            
            <div className="space-y-2">
              <Label>网络质量</Label>
              <div className="flex items-center space-x-2">
                {isSlowConnection ? (
                  <>
                    <AlertCircle className="h-4 w-4 text-orange-500" />
                    <span className="text-orange-600">慢速连接</span>
                  </>
                ) : (
                  <>
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span className="text-green-600">连接良好</span>
                  </>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="settings" className="space-y-6">
        <TabsList>
          <TabsTrigger value="settings">离线设置</TabsTrigger>
          <TabsTrigger value="cache">缓存管理</TabsTrigger>
          <TabsTrigger value="pwa">PWA功能</TabsTrigger>
          <TabsTrigger value="device">设备信息</TabsTrigger>
        </TabsList>

        <TabsContent value="settings" className="space-y-6">
          {/* 离线设置 */}
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Cloud className="h-5 w-5" />
                  <span>同步设置</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>离线优先模式</Label>
                    <p className="text-sm text-muted-foreground">
                      优先使用本地数据，减少网络请求
                    </p>
                  </div>
                  <Switch
                    checked={offlineMode}
                    onCheckedChange={handleOfflineModeToggle}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>自动同步</Label>
                    <p className="text-sm text-muted-foreground">
                      网络连接时自动同步数据
                    </p>
                  </div>
                  <Switch
                    checked={autoSync}
                    onCheckedChange={(checked) => {
                      setAutoSync(checked);
                      localStorage.setItem('auto-sync', checked.toString());
                    }}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>后台同步</Label>
                    <p className="text-sm text-muted-foreground">
                      应用在后台时继续同步数据
                    </p>
                  </div>
                  <Switch
                    checked={backgroundSync}
                    onCheckedChange={(checked) => {
                      setBackgroundSync(checked);
                      localStorage.setItem('background-sync', checked.toString());
                    }}
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Bell className="h-5 w-5" />
                  <span>通知设置</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>推送通知</Label>
                    <p className="text-sm text-muted-foreground">
                      接收重要事件的通知提醒
                    </p>
                  </div>
                  <Switch
                    checked={notificationEnabled}
                    onCheckedChange={handleNotificationToggle}
                  />
                </div>

                {notificationEnabled && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleTestNotification}
                  >
                    <Bell className="h-3 w-3 mr-1" />
                    测试通知
                  </Button>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="cache">
          <CacheManager />
        </TabsContent>

        <TabsContent value="pwa" className="space-y-6">
          {/* PWA功能 */}
          <div className="grid gap-6 md:grid-cols-2">
            <PWAFeatureCard />
            
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Smartphone className="h-5 w-5" />
                  <span>PWA 操作</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {!pwaInstalled ? (
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                      安装PWA版本获得更好的体验
                    </p>
                    <Button onClick={handleInstallPWA}>
                      <Download className="h-4 w-4 mr-2" />
                      安装应用
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <CheckCircle className="h-4 w-4 text-green-600" />
                      <span className="text-green-600">PWA已安装</span>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      您正在使用PWA版本，享受最佳体验
                    </p>
                  </div>
                )}

                <Button
                  variant="outline"
                  onClick={handleShare}
                  className="w-full"
                >
                  <Settings className="h-4 w-4 mr-2" />
                  分享应用
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="device" className="space-y-6">
          {/* 设备信息 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Shield className="h-5 w-5" />
                <span>设备信息</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {deviceInfo && (
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-3">
                    <div>
                      <Label>平台</Label>
                      <p className="text-sm text-muted-foreground">{deviceInfo.platform}</p>
                    </div>
                    <div>
                      <Label>语言</Label>
                      <p className="text-sm text-muted-foreground">{deviceInfo.language}</p>
                    </div>
                    <div>
                      <Label>安装状态</Label>
                      <p className="text-sm text-muted-foreground">
                        {deviceInfo.isStandalone ? 'PWA模式' : '浏览器模式'}
                      </p>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <Label>存储支持</Label>
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <Badge variant={deviceInfo.storage.localStorage ? 'default' : 'secondary'}>
                            LocalStorage
                          </Badge>
                          <Badge variant={deviceInfo.storage.indexedDB ? 'default' : 'secondary'}>
                            IndexedDB
                          </Badge>
                        </div>
                      </div>
                    </div>
                    
                    <div>
                      <Label>功能支持</Label>
                      <div className="space-y-1">
                        <div className="flex flex-wrap gap-1">
                          <Badge variant={deviceInfo.features.serviceWorker ? 'default' : 'secondary'}>
                            Service Worker
                          </Badge>
                          <Badge variant={deviceInfo.features.notifications ? 'default' : 'secondary'}>
                            通知
                          </Badge>
                          <Badge variant={deviceInfo.features.share ? 'default' : 'secondary'}>
                            分享
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}