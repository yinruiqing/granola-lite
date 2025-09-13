'use client'

import { useState, useRef, useEffect } from 'react'
import { cn } from '@/lib/utils'

interface LazyImageProps {
  src: string;
  alt: string;
  className?: string;
  width?: number;
  height?: number;
  placeholder?: string;
  threshold?: number;
  onLoad?: () => void;
  onError?: () => void;
}

export function LazyImage({
  src,
  alt,
  className,
  width,
  height,
  placeholder = '/placeholder-image.svg',
  threshold = 0.1,
  onLoad,
  onError,
}: LazyImageProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const [hasError, setHasError] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    if (typeof window === 'undefined' || !imgRef.current) return;

    // 使用 Intersection Observer 实现懒加载
    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) {
            setIsInView(true);
            observer.disconnect();
          }
        },
        { threshold }
      );

      observer.observe(imgRef.current);

      return () => observer.disconnect();
    } else {
      // 降级处理：直接加载
      setIsInView(true);
    }
  }, [threshold]);

  const handleLoad = () => {
    setIsLoaded(true);
    onLoad?.();
  };

  const handleError = () => {
    setHasError(true);
    onError?.();
  };

  return (
    <div 
      ref={imgRef}
      className={cn(
        "relative overflow-hidden bg-gray-100",
        className
      )}
      style={{ width, height }}
    >
      {/* 占位符 */}
      {!isLoaded && !hasError && (
        <div 
          className="absolute inset-0 flex items-center justify-center bg-gray-100 animate-pulse"
          style={{ width, height }}
        >
          {placeholder && (
            <img
              src={placeholder}
              alt=""
              className="w-1/3 h-1/3 opacity-30"
            />
          )}
        </div>
      )}

      {/* 实际图片 */}
      {isInView && !hasError && (
        <img
          src={src}
          alt={alt}
          className={cn(
            "transition-opacity duration-300",
            isLoaded ? "opacity-100" : "opacity-0",
            className
          )}
          style={{ width, height }}
          onLoad={handleLoad}
          onError={handleError}
          loading="lazy"
        />
      )}

      {/* 错误状态 */}
      {hasError && (
        <div 
          className="absolute inset-0 flex items-center justify-center bg-gray-100 text-gray-400"
          style={{ width, height }}
        >
          <div className="text-center">
            <svg 
              className="w-8 h-8 mx-auto mb-2" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
            <span className="text-xs">加载失败</span>
          </div>
        </div>
      )}

      {/* 加载进度指示器 */}
      {isInView && !isLoaded && !hasError && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-6 h-6 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
        </div>
      )}
    </div>
  );
}