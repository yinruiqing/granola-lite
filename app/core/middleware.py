"""
中间件配置
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from app.core.exceptions import GranolaException, granola_exception_to_http_exception
from app.core.logging import api_logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成请求ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        # 记录请求开始
        start_time = time.time()
        api_logger.info(
            f"Request started - {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else "unknown"
            }
        )
        
        # 处理请求
        try:
            response = await call_next(request)
        except Exception as e:
            # 记录异常
            process_time = time.time() - start_time
            api_logger.error(
                f"Request failed - {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": round(process_time, 4),
                    "error": str(e)
                }
            )
            raise
        
        # 记录请求完成
        process_time = time.time() - start_time
        api_logger.info(
            f"Request completed - {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": round(process_time, 4)
            }
        )
        
        # 添加响应头
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(round(process_time, 4))
        
        return response


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """异常处理中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except GranolaException as exc:
            # 处理自定义异常
            http_exc = granola_exception_to_http_exception(exc)
            api_logger.error(
                f"Granola exception: {exc.message}",
                extra={
                    "request_id": getattr(request.state, "request_id", "unknown"),
                    "error_code": exc.code,
                    "error_type": type(exc).__name__,
                    "path": request.url.path
                }
            )
            return JSONResponse(
                status_code=http_exc.status_code,
                content=http_exc.detail
            )
        except HTTPException as exc:
            # 处理HTTP异常
            api_logger.warning(
                f"HTTP exception: {exc.detail}",
                extra={
                    "request_id": getattr(request.state, "request_id", "unknown"),
                    "status_code": exc.status_code,
                    "path": request.url.path
                }
            )
            raise
        except Exception as exc:
            # 处理未预期的异常
            api_logger.error(
                f"Unhandled exception: {str(exc)}",
                extra={
                    "request_id": getattr(request.state, "request_id", "unknown"),
                    "error_type": type(exc).__name__,
                    "path": request.url.path
                },
                exc_info=True
            )
            
            return JSONResponse(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": True,
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "服务器内部错误",
                    "request_id": getattr(request.state, "request_id", "unknown")
                }
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件（简单实现）"""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        
        # 简单的滑动窗口实现
        current_time = time.time()
        
        if client_ip not in self.clients:
            self.clients[client_ip] = []
        
        # 清理过期的请求记录
        self.clients[client_ip] = [
            req_time for req_time in self.clients[client_ip]
            if current_time - req_time < self.period
        ]
        
        # 检查是否超过限制
        if len(self.clients[client_ip]) >= self.calls:
            api_logger.warning(
                f"Rate limit exceeded for client {client_ip}",
                extra={
                    "client_ip": client_ip,
                    "requests_count": len(self.clients[client_ip]),
                    "limit": self.calls,
                    "path": request.url.path
                }
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": True,
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "请求过于频繁，请稍后重试",
                    "retry_after": self.period
                }
            )
        
        # 记录本次请求
        self.clients[client_ip].append(current_time)
        
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全响应头中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # 添加安全头
        response.headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()"
        })
        
        return response