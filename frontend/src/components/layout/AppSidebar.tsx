'use client';

import { 
  Home, 
  Mic, 
  FileText, 
  Settings, 
  Search, 
  Calendar,
  MessageSquare,
  Layout,
  Plus,
  Download,
  Activity
} from 'lucide-react';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '@/components/ui/sidebar';
import { Button } from '@/components/ui/button';
import { useAppStore } from '@/lib/store';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

// 导航菜单项
const menuItems = [
  {
    title: 'Dashboard',
    url: '/',
    icon: Home,
  },
  {
    title: '会议列表',
    url: '/meetings',
    icon: Calendar,
  },
  {
    title: '实时会议',
    url: '/live',
    icon: Mic,
  },
  {
    title: '笔记管理',
    url: '/notes',
    icon: FileText,
  },
  {
    title: 'AI 问答',
    url: '/chat',
    icon: MessageSquare,
  },
  {
    title: '模板管理',
    url: '/templates',
    icon: Layout,
  },
  {
    title: '数据导出',
    url: '/export',
    icon: Download,
  },
  {
    title: '搜索',
    url: '/search',
    icon: Search,
  },
  {
    title: '性能监控',
    url: '/performance',
    icon: Activity,
  },
  {
    title: '设置',
    url: '/settings',
    icon: Settings,
  },
];

export function AppSidebar() {
  const pathname = usePathname();
  const { meetings } = useAppStore();

  // 获取最近的会议
  const recentMeetings = meetings.slice(0, 5);

  return (
    <Sidebar collapsible="icon">
      <SidebarContent>
        {/* 主导航 */}
        <SidebarGroup>
          <SidebarGroupLabel>主导航</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {menuItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton 
                    asChild 
                    isActive={pathname === item.url}
                  >
                    <Link href={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* 最近会议 */}
        <SidebarGroup>
          <SidebarGroupLabel>最近会议</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {recentMeetings.length > 0 ? (
                recentMeetings.map((meeting) => (
                  <SidebarMenuItem key={meeting.id}>
                    <SidebarMenuButton asChild>
                      <Link href={`/meetings/${meeting.id}`}>
                        <Calendar className="w-4 h-4" />
                        <span className="truncate">{meeting.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))
              ) : (
                <SidebarMenuItem>
                  <SidebarMenuButton disabled>
                    <Calendar className="w-4 h-4" />
                    <span className="text-muted-foreground">暂无会议</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <div className="p-4 space-y-2">
          <Button size="sm" className="w-full justify-start" asChild>
            <Link href="/meetings/new">
              <Plus className="w-4 h-4 mr-2" />
              创建会议
            </Link>
          </Button>
          <Button 
            size="sm" 
            variant="outline" 
            className="w-full justify-start" 
            asChild
          >
            <Link href="/live">
              <Mic className="w-4 h-4 mr-2" />
              开始录音
            </Link>
          </Button>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}