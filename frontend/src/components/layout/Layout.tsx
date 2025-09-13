'use client';

import { useEffect } from 'react';
import { SidebarProvider } from '@/components/ui/sidebar';
import { AppSidebar } from './AppSidebar';
import { Header } from './Header';
import { useAppStore } from '@/lib/store';
import { settingsService } from '@/lib/settings-service';
import { storageManager } from '@/lib/storage';
import { pwaService } from '@/lib/pwa-service';
import { performanceService } from '@/lib/performance-service';
import { OfflineIndicator } from '@/components/offline/OfflineIndicator';
import { InstallPrompt } from '@/components/pwa/InstallPrompt';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { theme, sidebarOpen, setTheme } = useAppStore();

  // 初始化存储和设置
  useEffect(() => {
    const initApp = async () => {
      // 只在客户端初始化存储
      if (typeof window !== 'undefined') {
        try {
          await storageManager.initializeDefaultTemplates();
          
          // 初始化用户设置
          const settings = settingsService.getSettings();
          
          // 初始化PWA服务
          await pwaService.initialize();
          
          // 初始化性能监控
          await performanceService.initialize();
          
          // 启用懒加载和预加载
          performanceService.enableLazyLoading();
          performanceService.preloadCriticalResources();
          
          console.log('应用初始化完成, 设置:', settings);
        } catch (error) {
          console.error('应用初始化失败:', error);
        }
      }
    };

    initApp();
  }, []);

  // 应用主题
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const root = document.documentElement;
      if (theme === 'dark') {
        root.classList.add('dark');
      } else {
        root.classList.remove('dark');
      }
    }
  }, [theme]);

  return (
    <SidebarProvider defaultOpen={sidebarOpen}>
      <div className="flex min-h-screen w-full bg-background">
        <AppSidebar />
        
        <div className="flex flex-1 flex-col">
          <Header />
          
          <main className="flex-1 overflow-auto">
            <div className="container mx-auto p-6">
              {children}
            </div>
          </main>
        </div>
      </div>
      
      {/* 离线状态指示器 */}
      <OfflineIndicator />
      
      {/* PWA安装提示 */}
      <InstallPrompt />
    </SidebarProvider>
  );
}