const CACHE_NAME = 'granola-lite-v1';
const STATIC_CACHE_NAME = 'granola-static-v1';
const DYNAMIC_CACHE_NAME = 'granola-dynamic-v1';

// 需要缓存的静态资源
const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  '/meetings',
  '/notes',
  '/templates',
  '/search',
  '/settings',
  '/export',
  '/live',
  '/chat',
  // 添加关键的静态资源
  '/_next/static/css/',
  '/_next/static/js/',
];

// 需要缓存的API路由
const API_CACHE_PATTERNS = [
  /^\/api\/meetings/,
  /^\/api\/notes/,
  /^\/api\/templates/,
];

// 动态缓存的最大数量
const MAX_DYNAMIC_CACHE_SIZE = 50;

// Service Worker 安装事件
self.addEventListener('install', event => {
  console.log('[SW] Installing Service Worker');
  
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME)
      .then(cache => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .catch(err => {
        console.log('[SW] Cache installation failed:', err);
      })
  );
  
  // 强制激活新的 Service Worker
  self.skipWaiting();
});

// Service Worker 激活事件
self.addEventListener('activate', event => {
  console.log('[SW] Activating Service Worker');
  
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            // 删除旧版本的缓存
            if (cacheName !== STATIC_CACHE_NAME && 
                cacheName !== DYNAMIC_CACHE_NAME &&
                cacheName !== CACHE_NAME) {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
  );
  
  // 立即控制所有客户端
  self.clients.claim();
});

// 网络请求拦截
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  
  // 跳过非HTTP请求
  if (!request.url.startsWith('http')) {
    return;
  }
  
  // 处理不同类型的请求
  if (isStaticAsset(request)) {
    // 静态资源：缓存优先
    event.respondWith(cacheFirst(request));
  } else if (isAPIRequest(request)) {
    // API请求：网络优先，带缓存回退
    event.respondWith(networkFirstWithCache(request));
  } else if (isNavigationRequest(request)) {
    // 导航请求：网络优先，离线时返回缓存的页面
    event.respondWith(navigationHandler(request));
  } else {
    // 其他请求：网络优先
    event.respondWith(networkFirst(request));
  }
});

// 判断是否为静态资源
function isStaticAsset(request) {
  const url = new URL(request.url);
  return url.pathname.startsWith('/_next/') || 
         url.pathname.includes('.') ||
         url.pathname === '/manifest.json';
}

// 判断是否为API请求
function isAPIRequest(request) {
  const url = new URL(request.url);
  return url.pathname.startsWith('/api/') ||
         API_CACHE_PATTERNS.some(pattern => pattern.test(url.pathname));
}

// 判断是否为导航请求
function isNavigationRequest(request) {
  return request.mode === 'navigate' || 
         (request.method === 'GET' && request.headers.get('accept').includes('text/html'));
}

// 缓存优先策略
async function cacheFirst(request) {
  try {
    const cache = await caches.open(STATIC_CACHE_NAME);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      await cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('[SW] Cache first failed:', error);
    return new Response('Offline - Resource not available', {
      status: 503,
      statusText: 'Service Unavailable'
    });
  }
}

// 网络优先策略（带缓存）
async function networkFirstWithCache(request) {
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE_NAME);
      await cache.put(request, networkResponse.clone());
      
      // 限制动态缓存大小
      await limitCacheSize(DYNAMIC_CACHE_NAME, MAX_DYNAMIC_CACHE_SIZE);
    }
    
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', error);
    
    const cache = await caches.open(DYNAMIC_CACHE_NAME);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // 返回离线页面或错误响应
    return createOfflineResponse(request);
  }
}

// 导航处理器
async function navigationHandler(request) {
  try {
    const networkResponse = await fetch(request);
    return networkResponse;
  } catch (error) {
    console.log('[SW] Navigation failed, serving offline page');
    
    // 尝试从缓存获取请求的页面
    const cache = await caches.open(STATIC_CACHE_NAME);
    const cachedResponse = await cache.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // 返回主页作为离线回退
    const fallbackResponse = await cache.match('/');
    if (fallbackResponse) {
      return fallbackResponse;
    }
    
    // 创建离线页面
    return createOfflinePage();
  }
}

// 网络优先策略
async function networkFirst(request) {
  try {
    return await fetch(request);
  } catch (error) {
    console.log('[SW] Network request failed:', error);
    return new Response('Network Error', {
      status: 503,
      statusText: 'Service Unavailable'
    });
  }
}

// 创建离线响应
function createOfflineResponse(request) {
  if (request.headers.get('accept').includes('application/json')) {
    return new Response(
      JSON.stringify({ 
        error: 'Offline', 
        message: '当前离线，请检查网络连接' 
      }),
      {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
  
  return createOfflinePage();
}

// 创建离线页面
function createOfflinePage() {
  const offlineHTML = `
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>离线状态 - Granola Lite</title>
      <style>
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          min-height: 100vh;
          margin: 0;
          padding: 20px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          text-align: center;
        }
        .container {
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(10px);
          border-radius: 20px;
          padding: 40px;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.2);
        }
        h1 {
          font-size: 2.5rem;
          margin-bottom: 1rem;
          font-weight: 300;
        }
        p {
          font-size: 1.2rem;
          margin-bottom: 2rem;
          opacity: 0.9;
        }
        .icon {
          font-size: 4rem;
          margin-bottom: 2rem;
        }
        .retry-btn {
          background: rgba(255, 255, 255, 0.2);
          border: 2px solid rgba(255, 255, 255, 0.3);
          color: white;
          padding: 12px 24px;
          border-radius: 8px;
          font-size: 1rem;
          cursor: pointer;
          transition: all 0.3s ease;
        }
        .retry-btn:hover {
          background: rgba(255, 255, 255, 0.3);
          transform: translateY(-2px);
        }
        .features {
          margin-top: 2rem;
          text-align: left;
          opacity: 0.8;
        }
        .features li {
          margin: 0.5rem 0;
          list-style: none;
          position: relative;
          padding-left: 20px;
        }
        .features li:before {
          content: "✓";
          position: absolute;
          left: 0;
          color: #4ade80;
          font-weight: bold;
        }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="icon">📱</div>
        <h1>Granola Lite</h1>
        <p>当前处于离线状态，但您仍然可以：</p>
        <ul class="features">
          <li>查看已缓存的会议记录</li>
          <li>编辑离线笔记</li>
          <li>使用模板创建内容</li>
          <li>搜索本地数据</li>
        </ul>
        <button class="retry-btn" onclick="window.location.reload()">
          重新连接
        </button>
      </div>
      
      <script>
        // 监听网络状态变化
        window.addEventListener('online', () => {
          console.log('Back online');
          window.location.reload();
        });
        
        // 定期检查网络连接
        setInterval(() => {
          if (navigator.onLine) {
            window.location.reload();
          }
        }, 30000);
      </script>
    </body>
    </html>
  `;
  
  return new Response(offlineHTML, {
    status: 200,
    statusText: 'OK',
    headers: { 'Content-Type': 'text/html; charset=utf-8' }
  });
}

// 限制缓存大小
async function limitCacheSize(cacheName, maxSize) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  
  if (keys.length > maxSize) {
    // 删除最旧的缓存项
    const keysToDelete = keys.slice(0, keys.length - maxSize);
    await Promise.all(keysToDelete.map(key => cache.delete(key)));
  }
}

// 后台同步
self.addEventListener('sync', event => {
  if (event.tag === 'background-sync') {
    console.log('[SW] Background sync triggered');
    event.waitUntil(syncData());
  }
});

// 同步数据
async function syncData() {
  try {
    // 这里可以实现数据同步逻辑
    console.log('[SW] Syncing data...');
    
    // 通知客户端同步完成
    const clients = await self.clients.matchAll();
    clients.forEach(client => {
      client.postMessage({
        type: 'SYNC_COMPLETE',
        payload: { success: true }
      });
    });
  } catch (error) {
    console.error('[SW] Sync failed:', error);
  }
}

// 推送通知
self.addEventListener('push', event => {
  if (!event.data) return;
  
  const data = event.data.json();
  const options = {
    body: data.body,
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge.png',
    vibrate: [200, 100, 200],
    data: data.data,
    actions: data.actions || [],
    tag: data.tag || 'default'
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// 通知点击处理
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  const data = event.notification.data;
  const action = event.action;
  
  event.waitUntil(
    clients.matchAll().then(clientList => {
      // 如果有打开的窗口，则聚焦到该窗口
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          return client.focus();
        }
      }
      
      // 否则打开新窗口
      if (clients.openWindow) {
        const targetUrl = data?.url || '/';
        return clients.openWindow(targetUrl);
      }
    })
  );
});

// 消息处理
self.addEventListener('message', event => {
  const { type, payload } = event.data;
  
  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
      
    case 'CACHE_URLS':
      event.waitUntil(
        cacheUrls(payload.urls)
      );
      break;
      
    case 'CLEAR_CACHE':
      event.waitUntil(
        clearCache(payload.cacheName)
      );
      break;
  }
});

// 缓存指定URLs
async function cacheUrls(urls) {
  const cache = await caches.open(DYNAMIC_CACHE_NAME);
  return Promise.all(
    urls.map(url => 
      fetch(url)
        .then(response => {
          if (response.ok) {
            return cache.put(url, response);
          }
        })
        .catch(err => console.log('[SW] Failed to cache:', url, err))
    )
  );
}

// 清除缓存
async function clearCache(cacheName) {
  if (cacheName) {
    return caches.delete(cacheName);
  } else {
    const cacheNames = await caches.keys();
    return Promise.all(cacheNames.map(name => caches.delete(name)));
  }
}