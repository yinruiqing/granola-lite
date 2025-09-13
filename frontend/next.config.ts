import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 实验性功能
  experimental: {
    // 启用优化的包导入
    optimizePackageImports: ['lucide-react', '@radix-ui/react-icons'],
  },
  
  // Turbopack配置（替代experimental.turbo）
  turbopack: {
    rules: {
      '*.svg': {
        loaders: ['@svgr/webpack'],
        as: '*.js',
      },
    },
  },
  
  // 图片优化
  images: {
    formats: ['image/webp', 'image/avif'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    minimumCacheTTL: 31536000, // 1 year
    dangerouslyAllowSVG: true,
    contentDispositionType: 'attachment',
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
  },
  
  webpack: (config, { isServer, dev }) => {
    // 忽略 Node.js 模块在客户端的使用
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        path: false,
        crypto: false,
      };
    }
    
    // 添加对 sql.js WASM 文件的支持
    config.module.rules.push({
      test: /\.wasm$/,
      type: 'asset/resource',
    });

    // 生产环境优化
    if (!dev && !isServer) {
      // 代码分割优化
      config.optimization.splitChunks = {
        chunks: 'all',
        cacheGroups: {
          default: false,
          vendors: false,
          // 第三方库分包
          vendor: {
            name: 'vendor',
            chunks: 'all',
            test: /node_modules/,
            priority: 20,
          },
          // UI组件库单独分包
          ui: {
            name: 'ui',
            chunks: 'all',
            test: /[\\/]components[\\/]ui[\\/]/,
            priority: 30,
          },
          // 大型库单独分包
          lucide: {
            name: 'lucide',
            chunks: 'all',
            test: /[\\/]node_modules[\\/]lucide-react[\\/]/,
            priority: 40,
          },
          // 共用模块
          common: {
            name: 'common',
            chunks: 'all',
            minChunks: 2,
            priority: 10,
            reuseExistingChunk: true,
          },
        },
      };

      // 模块联邦和预加载
      config.optimization.usedExports = true;
      config.optimization.sideEffects = false;
    }

    return config;
  },
  
  // 静态资源缓存
  async headers() {
    return [
      {
        source: '/sw.js',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=0, must-revalidate',
          },
        ],
      },
      {
        source: '/manifest.json',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
        ],
      },
    ];
  },
};

export default nextConfig;
