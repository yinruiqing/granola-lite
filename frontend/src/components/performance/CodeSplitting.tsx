'use client'

import React, { lazy, Suspense, ComponentType } from 'react'
import { Loader2 } from 'lucide-react'

// 加载中组件
export function LoadingSpinner({ message = "正在加载..." }: { message?: string }) {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="flex items-center space-x-2">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm text-muted-foreground">{message}</span>
      </div>
    </div>
  );
}

// 错误边界组件
interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

export class LazyLoadErrorBoundary extends React.Component<
  React.PropsWithChildren<{ fallback?: React.ComponentType<{ error: Error }> }>,
  ErrorBoundaryState
> {
  constructor(props: React.PropsWithChildren<{ fallback?: React.ComponentType<{ error: Error }> }>) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('LazyLoad Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      const FallbackComponent = this.props.fallback;
      if (FallbackComponent && this.state.error) {
        return <FallbackComponent error={this.state.error} />;
      }
      return (
        <div className="flex items-center justify-center p-8">
          <div className="text-center">
            <p className="text-sm text-red-600 mb-2">组件加载失败</p>
            <button
              onClick={() => this.setState({ hasError: false })}
              className="px-3 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200"
            >
              重试
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// 懒加载组件包装器
export function withLazyLoading<P extends {}>(
  importFunc: () => Promise<{ default: ComponentType<P> }>,
  fallback?: React.ComponentType,
  errorFallback?: React.ComponentType<{ error: Error }>
) {
  const LazyComponent = lazy(importFunc);

  return function LazyWrapper(props: P) {
    const FallbackComponent = fallback || (() => <LoadingSpinner />);

    return (
      <LazyLoadErrorBoundary fallback={errorFallback}>
        <Suspense fallback={<FallbackComponent />}>
          <LazyComponent {...props} />
        </Suspense>
      </LazyLoadErrorBoundary>
    );
  };
}

// 预加载功能
export class ComponentPreloader {
  private static preloadedComponents = new Set<string>();

  static preload<T>(
    componentName: string,
    importFunc: () => Promise<{ default: ComponentType<T> }>
  ): void {
    if (this.preloadedComponents.has(componentName)) return;

    // 延迟预加载，避免阻塞主线程
    requestIdleCallback(() => {
      importFunc()
        .then(() => {
          this.preloadedComponents.add(componentName);
          console.log(`预加载完成: ${componentName}`);
        })
        .catch((error) => {
          console.warn(`预加载失败: ${componentName}`, error);
        });
    });
  }

  static preloadOnHover<T>(
    element: HTMLElement,
    componentName: string,
    importFunc: () => Promise<{ default: ComponentType<T> }>
  ): () => void {
    const handleMouseEnter = () => {
      this.preload(componentName, importFunc);
    };

    element.addEventListener('mouseenter', handleMouseEnter, { once: true });

    // 返回清理函数
    return () => {
      element.removeEventListener('mouseenter', handleMouseEnter);
    };
  }
}

// 路由级代码分割的懒加载组件
export const LazyDashboard = withLazyLoading(
  () => import('@/app/(main)/page'),
  () => <LoadingSpinner message="正在加载仪表板..." />
);

export const LazyMeetings = withLazyLoading(
  () => import('@/app/meetings/page'),
  () => <LoadingSpinner message="正在加载会议列表..." />
);

export const LazyNotes = withLazyLoading(
  () => import('@/app/notes/page'),
  () => <LoadingSpinner message="正在加载笔记..." />
);

export const LazySettings = withLazyLoading(
  () => import('@/app/settings/page'),
  () => <LoadingSpinner message="正在加载设置..." />
);

export const LazySearch = withLazyLoading(
  () => import('@/app/search/page'),
  () => <LoadingSpinner message="正在加载搜索..." />
);

export const LazyExport = withLazyLoading(
  () => import('@/app/export/page'),
  () => <LoadingSpinner message="正在加载导出功能..." />
);

export const LazyTemplates = withLazyLoading(
  () => import('@/app/templates/page'),
  () => <LoadingSpinner message="正在加载模板..." />
);

// 组件级代码分割
export const LazyRichTextEditor = withLazyLoading(
  () => import('@/components/editor/RichTextEditor'),
  () => <LoadingSpinner message="正在加载编辑器..." />
);

export const LazyChatInterface = withLazyLoading(
  () => import('@/components/chat/ChatInterface'),
  () => <LoadingSpinner message="正在加载聊天界面..." />
);

export const LazyAIEnhancementPanel = withLazyLoading(
  () => import('@/components/ai/AIEnhancementPanel'),
  () => <LoadingSpinner message="正在加载AI增强功能..." />
);

export const LazyPerformanceMonitor = withLazyLoading(
  () => import('@/components/performance/PerformanceMonitor'),
  () => <LoadingSpinner message="正在加载性能监控..." />
);

// Hook: 用于组件预加载
export function useComponentPreloader() {
  const preloadComponent = <T,>(
    componentName: string,
    importFunc: () => Promise<{ default: ComponentType<T> }>
  ) => {
    ComponentPreloader.preload(componentName, importFunc);
  };

  const preloadOnHover = <T,>(
    element: HTMLElement | null,
    componentName: string,
    importFunc: () => Promise<{ default: ComponentType<T> }>
  ) => {
    if (!element) return () => {};
    return ComponentPreloader.preloadOnHover(element, componentName, importFunc);
  };

  return { preloadComponent, preloadOnHover };
}