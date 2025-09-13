'use client';

import { Menu, Search, Bell, Settings, Moon, Sun } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { 
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { SidebarTrigger } from '@/components/ui/sidebar';
import { useAppStore } from '@/lib/store';
import { usePathname } from 'next/navigation';
import { GlobalSearch } from '@/components/search/GlobalSearch';

// 路径映射
const pathMap: Record<string, { title: string; parent?: string }> = {
  '/': { title: 'Dashboard' },
  '/meetings': { title: '会议列表' },
  '/meetings/new': { title: '创建会议', parent: '/meetings' },
  '/live': { title: '实时会议' },
  '/notes': { title: '笔记管理' },
  '/chat': { title: 'AI 问答' },
  '/templates': { title: '模板管理' },
  '/search': { title: '搜索' },
  '/export': { title: '数据导出' },
  '/settings': { title: '设置' },
};

export function Header() {
  const pathname = usePathname();
  const { theme, setTheme } = useAppStore();

  // 生成面包屑导航
  const generateBreadcrumbs = () => {
    const segments = pathname.split('/').filter(Boolean);
    const breadcrumbs = [{ title: 'Granola', href: '/' }];

    let currentPath = '';
    segments.forEach((segment, index) => {
      currentPath += `/${segment}`;
      const pathInfo = pathMap[currentPath];
      
      if (pathInfo) {
        breadcrumbs.push({
          title: pathInfo.title,
          href: currentPath,
        });
      } else if (index === segments.length - 1) {
        // 动态路由的处理
        breadcrumbs.push({
          title: `详情 #${segment}`,
          href: currentPath,
        });
      }
    });

    return breadcrumbs;
  };

  const breadcrumbs = generateBreadcrumbs();

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };

  return (
    <header className="flex h-16 items-center justify-between border-b bg-background px-4">
      <div className="flex items-center space-x-4">
        <SidebarTrigger />
        
        {/* 面包屑导航 */}
        <Breadcrumb>
          <BreadcrumbList>
            {breadcrumbs.map((crumb, index) => (
              <div key={crumb.href} className="flex items-center">
                {index > 0 && <BreadcrumbSeparator />}
                <BreadcrumbItem>
                  {index === breadcrumbs.length - 1 ? (
                    <BreadcrumbPage>{crumb.title}</BreadcrumbPage>
                  ) : (
                    <BreadcrumbLink href={crumb.href}>
                      {crumb.title}
                    </BreadcrumbLink>
                  )}
                </BreadcrumbItem>
              </div>
            ))}
          </BreadcrumbList>
        </Breadcrumb>
      </div>

      {/* 中间搜索区 */}
      <div className="hidden md:block flex-1 max-w-md mx-6">
        <GlobalSearch />
      </div>

      {/* 右侧操作区 */}
      <div className="flex items-center space-x-2">
        <TooltipProvider>
          {/* 移动端搜索按钮 */}
          <div className="md:hidden">
            <GlobalSearch />
          </div>

          {/* 通知按钮 */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon">
                <Bell className="h-5 w-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>通知</p>
            </TooltipContent>
          </Tooltip>

          {/* 主题切换 */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" onClick={toggleTheme}>
                {theme === 'light' ? (
                  <Moon className="h-5 w-5" />
                ) : (
                  <Sun className="h-5 w-5" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>切换主题</p>
            </TooltipContent>
          </Tooltip>

          {/* 设置按钮 */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" asChild>
                <a href="/settings">
                  <Settings className="h-5 w-5" />
                </a>
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>设置</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </header>
  );
}