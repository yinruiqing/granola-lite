'use client';

import { Calendar, Mic, FileText, MessageSquare, TrendingUp, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAppStore } from '@/lib/store';
import Link from 'next/link';

export default function Dashboard() {
  const { meetings } = useAppStore();

  // 计算统计数据
  const stats = {
    totalMeetings: meetings.length,
    completedMeetings: meetings.filter(m => m.status === 'completed').length,
    inProgressMeetings: meetings.filter(m => m.status === 'in_progress').length,
    scheduledMeetings: meetings.filter(m => m.status === 'scheduled').length,
  };

  const recentMeetings = meetings.slice(0, 3);

  return (
    <div className="space-y-8">
      {/* 欢迎区域 */}
      <div className="flex flex-col space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">欢迎使用 Granola Lite</h1>
        <p className="text-muted-foreground">
          智能会议记录和转录工具，让您的会议更高效
        </p>
      </div>

      {/* 快速操作 */}
      <div className="flex flex-col sm:flex-row gap-4">
        <Button size="lg" asChild>
          <Link href="/meetings/new" className="flex items-center space-x-2">
            <Calendar className="h-5 w-5" />
            <span>创建新会议</span>
          </Link>
        </Button>
        
        <Button size="lg" variant="outline" asChild>
          <Link href="/live" className="flex items-center space-x-2">
            <Mic className="h-5 w-5" />
            <span>开始实时录音</span>
          </Link>
        </Button>
      </div>

      {/* 统计卡片 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-center space-x-2">
            <Calendar className="h-5 w-5 text-blue-500" />
            <div className="space-y-1">
              <p className="text-sm font-medium leading-none">总会议数</p>
              <p className="text-2xl font-bold">{stats.totalMeetings}</p>
            </div>
          </div>
        </div>

        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-center space-x-2">
            <TrendingUp className="h-5 w-5 text-green-500" />
            <div className="space-y-1">
              <p className="text-sm font-medium leading-none">已完成</p>
              <p className="text-2xl font-bold">{stats.completedMeetings}</p>
            </div>
          </div>
        </div>

        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-center space-x-2">
            <Clock className="h-5 w-5 text-orange-500" />
            <div className="space-y-1">
              <p className="text-sm font-medium leading-none">进行中</p>
              <p className="text-2xl font-bold">{stats.inProgressMeetings}</p>
            </div>
          </div>
        </div>

        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-center space-x-2">
            <Calendar className="h-5 w-5 text-purple-500" />
            <div className="space-y-1">
              <p className="text-sm font-medium leading-none">已安排</p>
              <p className="text-2xl font-bold">{stats.scheduledMeetings}</p>
            </div>
          </div>
        </div>
      </div>

      {/* 最近会议 */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold tracking-tight">最近会议</h2>
          <Button variant="outline" asChild>
            <Link href="/meetings">查看全部</Link>
          </Button>
        </div>

        <div className="space-y-3">
          {recentMeetings.length > 0 ? (
            recentMeetings.map((meeting) => (
              <div 
                key={meeting.id} 
                className="flex items-center justify-between rounded-lg border p-4"
              >
                <div className="space-y-1">
                  <h3 className="font-medium">{meeting.title}</h3>
                  <p className="text-sm text-muted-foreground">
                    {meeting.description || '暂无描述'}
                  </p>
                  <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                    <span>{new Date(meeting.created_at).toLocaleDateString()}</span>
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      meeting.status === 'completed' ? 'bg-green-100 text-green-800' :
                      meeting.status === 'in_progress' ? 'bg-orange-100 text-orange-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {meeting.status === 'completed' ? '已完成' :
                       meeting.status === 'in_progress' ? '进行中' : '已安排'}
                    </span>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <Button variant="outline" size="sm" asChild>
                    <Link href={`/meetings/${meeting.id}`}>查看详情</Link>
                  </Button>
                </div>
              </div>
            ))
          ) : (
            <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8">
              <Calendar className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-lg font-medium">还没有会议记录</p>
              <p className="text-sm text-muted-foreground mb-4">
                创建您的第一个会议开始使用吧
              </p>
              <Button asChild>
                <Link href="/meetings/new">创建新会议</Link>
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* 功能快捷方式 */}
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold tracking-tight">快速访问</h2>
        
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Link href="/notes" className="group">
            <div className="flex items-center space-x-3 rounded-lg border p-4 transition-colors hover:bg-accent">
              <FileText className="h-8 w-8 text-blue-500" />
              <div>
                <h3 className="font-medium group-hover:text-accent-foreground">笔记管理</h3>
                <p className="text-sm text-muted-foreground">查看和编辑您的会议笔记</p>
              </div>
            </div>
          </Link>

          <Link href="/chat" className="group">
            <div className="flex items-center space-x-3 rounded-lg border p-4 transition-colors hover:bg-accent">
              <MessageSquare className="h-8 w-8 text-green-500" />
              <div>
                <h3 className="font-medium group-hover:text-accent-foreground">AI 问答</h3>
                <p className="text-sm text-muted-foreground">基于会议内容进行智能问答</p>
              </div>
            </div>
          </Link>

          <Link href="/templates" className="group">
            <div className="flex items-center space-x-3 rounded-lg border p-4 transition-colors hover:bg-accent">
              <FileText className="h-8 w-8 text-purple-500" />
              <div>
                <h3 className="font-medium group-hover:text-accent-foreground">模板管理</h3>
                <p className="text-sm text-muted-foreground">管理您的会议模板</p>
              </div>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}
