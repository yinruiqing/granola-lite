'use client'

import { PerformanceMonitor } from '@/components/performance/PerformanceMonitor'

export default function PerformancePage() {
  return (
    <div className="container mx-auto py-8">
      <PerformanceMonitor />
    </div>
  )
}