'use client'

import { useState, useEffect, useCallback } from 'react'
import { performanceService, PerformanceMetrics, PerformanceRecommendation } from '@/lib/performance-service'

interface UsePerformanceOptions {
  enableAutoRefresh?: boolean
  refreshInterval?: number
}

export function usePerformance(options: UsePerformanceOptions = {}) {
  const { enableAutoRefresh = false, refreshInterval = 5000 } = options

  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null)
  const [recommendations, setRecommendations] = useState<PerformanceRecommendation[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const updateMetrics = useCallback(() => {
    try {
      const currentMetrics = performanceService.getMetrics()
      const currentRecommendations = performanceService.getRecommendations()
      
      setMetrics(currentMetrics)
      setRecommendations(currentRecommendations)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取性能数据失败')
      console.error('性能数据更新失败:', err)
    }
  }, [])

  const initialize = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      await performanceService.initialize()
      
      // 延迟获取指标，确保有足够数据
      setTimeout(() => {
        updateMetrics()
        setIsLoading(false)
      }, 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : '性能监控初始化失败')
      setIsLoading(false)
      console.error('性能监控初始化失败:', err)
    }
  }, [updateMetrics])

  // 初始化
  useEffect(() => {
    initialize()
  }, [initialize])

  // 自动刷新
  useEffect(() => {
    if (!enableAutoRefresh || isLoading) return

    const interval = setInterval(updateMetrics, refreshInterval)
    return () => clearInterval(interval)
  }, [enableAutoRefresh, refreshInterval, updateMetrics, isLoading])

  // 清理
  useEffect(() => {
    return () => {
      performanceService.cleanup()
    }
  }, [])

  return {
    metrics,
    recommendations,
    isLoading,
    error,
    refresh: updateMetrics,
    initialize,
  }
}

// 用于监控组件性能的Hook
export function useComponentPerformance(componentName: string) {
  const [renderTime, setRenderTime] = useState<number | null>(null)
  const [mountTime, setMountTime] = useState<number | null>(null)

  useEffect(() => {
    const mountStartTime = performance.now()

    return () => {
      const mountEndTime = performance.now()
      const totalMountTime = mountEndTime - mountStartTime
      setMountTime(totalMountTime)

      // 记录长时间挂载的组件
      if (totalMountTime > 100) {
        console.warn(`组件 ${componentName} 挂载时间较长: ${totalMountTime.toFixed(2)}ms`)
      }
    }
  }, [componentName])

  const measureRender = useCallback(() => {
    const renderStartTime = performance.now()

    // 在下一帧测量渲染时间
    requestAnimationFrame(() => {
      const renderEndTime = performance.now()
      const totalRenderTime = renderEndTime - renderStartTime
      setRenderTime(totalRenderTime)

      // 记录长时间渲染的组件
      if (totalRenderTime > 16) { // 大于一帧的时间
        console.warn(`组件 ${componentName} 渲染时间较长: ${totalRenderTime.toFixed(2)}ms`)
      }
    })
  }, [componentName])

  return {
    renderTime,
    mountTime,
    measureRender,
  }
}

// 用于监控网络请求性能的Hook
export function useNetworkPerformance() {
  const [networkMetrics, setNetworkMetrics] = useState<{
    slowRequests: Array<{
      url: string
      duration: number
      timestamp: number
    }>
  }>({ slowRequests: [] })

  const recordRequest = useCallback((url: string, startTime: number, endTime: number) => {
    const duration = endTime - startTime

    // 记录慢请求（超过1秒）
    if (duration > 1000) {
      setNetworkMetrics(prev => ({
        slowRequests: [
          ...prev.slowRequests.slice(-9), // 只保留最近10个
          {
            url,
            duration,
            timestamp: Date.now(),
          }
        ]
      }))
    }
  }, [])

  return {
    networkMetrics,
    recordRequest,
  }
}

// 用于内存使用监控的Hook
export function useMemoryMonitor() {
  const [memoryInfo, setMemoryInfo] = useState<{
    used: number
    total: number
    percentage: number
  } | null>(null)

  useEffect(() => {
    const updateMemoryInfo = () => {
      if (typeof window === 'undefined') return

      const memory = (performance as any).memory
      if (memory) {
        const used = memory.usedJSHeapSize / 1024 / 1024 // MB
        const total = memory.totalJSHeapSize / 1024 / 1024 // MB
        const percentage = (used / total) * 100

        setMemoryInfo({ used, total, percentage })

        // 内存使用过高警告
        if (percentage > 80) {
          console.warn(`内存使用过高: ${percentage.toFixed(1)}% (${used.toFixed(1)}MB / ${total.toFixed(1)}MB)`)
        }
      }
    }

    updateMemoryInfo()
    const interval = setInterval(updateMemoryInfo, 5000)

    return () => clearInterval(interval)
  }, [])

  return memoryInfo
}