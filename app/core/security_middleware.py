"""
安全中间件
"""

from typing import Dict, Any, Optional
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS, HTTP_403_FORBIDDEN
from loguru import logger

from app.core.security import (
    rate_limiter, 
    ip_whitelist_manager, 
    security_auditor,
    input_validator
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # 添加安全头
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value
        
        # 移除服务器信息
        if "server" in response.headers:
            del response.headers["server"]
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""
    
    def __init__(self, app, calls_per_minute: int = 100, burst_limit: int = 10):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.burst_limit = burst_limit
    
    async def dispatch(self, request: Request, call_next):
        # 获取客户端IP
        client_ip = self._get_client_ip(request)
        
        # 检查突发限制
        is_burst_limited = await rate_limiter.check_burst_limit(
            f"burst:{client_ip}", 
            self.burst_limit
        )
        
        if is_burst_limited:
            await security_auditor.log_security_event(
                event_type="burst_limit_exceeded",
                description=f"客户端 {client_ip} 触发突发请求限制",
                ip_address=client_ip,
                user_agent=request.headers.get("user-agent"),
                severity="medium"
            )
            
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "请求过于频繁，请稍后再试",
                    "detail": "触发突发请求限制"
                }
            )
        
        # 检查常规速率限制
        rate_limit_result = await rate_limiter.is_rate_limited(
            f"requests:{client_ip}",
            limit=self.calls_per_minute,
            window=60
        )
        
        if rate_limit_result["limited"]:
            await security_auditor.log_security_event(
                event_type="rate_limit_exceeded",
                description=f"客户端 {client_ip} 超过速率限制",
                ip_address=client_ip,
                user_agent=request.headers.get("user-agent"),
                severity="medium"
            )
            
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "请求次数超过限制",
                    "detail": f"每分钟最多 {self.calls_per_minute} 次请求",
                    "retry_after": rate_limit_result.get("retry_after", 60)
                },
                headers={
                    "Retry-After": str(rate_limit_result.get("retry_after", 60)),
                    "X-RateLimit-Limit": str(self.calls_per_minute),
                    "X-RateLimit-Remaining": str(rate_limit_result.get("remaining", 0)),
                    "X-RateLimit-Reset": str(rate_limit_result.get("reset_time", int(time.time()) + 60))
                }
            )
        
        # 添加速率限制头到响应
        response = await call_next(request)
        
        response.headers["X-RateLimit-Limit"] = str(self.calls_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_result.get("remaining", 0))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 检查代理头
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # 获取第一个IP（原始客户端IP）
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # 直接连接的IP
        return request.client.host if request.client else "unknown"


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """IP白名单中间件"""
    
    def __init__(self, app, whitelist_enabled: bool = False):
        super().__init__(app)
        self.whitelist_enabled = whitelist_enabled
    
    async def dispatch(self, request: Request, call_next):
        if not self.whitelist_enabled:
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        
        # 检查IP是否被允许
        if not ip_whitelist_manager.is_ip_allowed(client_ip):
            await security_auditor.log_security_event(
                event_type="ip_blocked",
                description=f"阻止来自 {client_ip} 的访问",
                ip_address=client_ip,
                user_agent=request.headers.get("user-agent"),
                severity="high"
            )
            
            return JSONResponse(
                status_code=HTTP_403_FORBIDDEN,
                content={
                    "error": "访问被拒绝",
                    "detail": "您的IP地址不在允许列表中"
                }
            )
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host if request.client else "unknown"


class InputValidationMiddleware(BaseHTTPMiddleware):
    """输入验证中间件"""
    
    def __init__(self, app, enable_validation: bool = True):
        super().__init__(app)
        self.enable_validation = enable_validation
        self.max_request_size = 10 * 1024 * 1024  # 10MB
    
    async def dispatch(self, request: Request, call_next):
        if not self.enable_validation:
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        
        # 检查请求大小
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            await security_auditor.log_security_event(
                event_type="request_too_large",
                description=f"请求体过大: {content_length} bytes",
                ip_address=client_ip,
                user_agent=request.headers.get("user-agent"),
                severity="medium"
            )
            
            return JSONResponse(
                status_code=413,
                content={
                    "error": "请求体过大",
                    "detail": f"请求大小不能超过 {self.max_request_size / 1024 / 1024:.1f}MB"
                }
            )
        
        # 验证URL路径
        path_validation = input_validator.validate_string(
            str(request.url.path),
            field_name="URL路径",
            max_length=1000,
            allow_html=False
        )
        
        if not path_validation["valid"]:
            await security_auditor.log_security_event(
                event_type="malicious_path",
                description=f"恶意URL路径: {request.url.path}",
                ip_address=client_ip,
                user_agent=request.headers.get("user-agent"),
                severity="high"
            )
            
            return JSONResponse(
                status_code=400,
                content={
                    "error": "无效的请求路径",
                    "detail": "路径包含非法字符"
                }
            )
        
        # 验证查询参数
        for param_name, param_value in request.query_params.items():
            param_validation = input_validator.validate_string(
                param_value,
                field_name=f"查询参数 {param_name}",
                max_length=1000,
                allow_html=False
            )
            
            if not param_validation["valid"]:
                await security_auditor.log_security_event(
                    event_type="malicious_query_param",
                    description=f"恶意查询参数: {param_name}={param_value}",
                    ip_address=client_ip,
                    user_agent=request.headers.get("user-agent"),
                    severity="high"
                )
                
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "无效的查询参数",
                        "detail": f"参数 {param_name} 包含非法内容"
                    }
                )
        
        # 验证User-Agent
        user_agent = request.headers.get("user-agent", "")
        if len(user_agent) > 500:
            await security_auditor.log_security_event(
                event_type="suspicious_user_agent",
                description=f"异常User-Agent长度: {len(user_agent)}",
                ip_address=client_ip,
                user_agent=user_agent[:100] + "...",
                severity="medium"
            )
        
        # 检查常见攻击模式
        suspicious_headers = [
            "x-forwarded-for",
            "x-real-ip", 
            "x-originating-ip",
            "x-remote-ip"
        ]
        
        for header in suspicious_headers:
            header_value = request.headers.get(header, "")
            if header_value and len(header_value) > 100:
                await security_auditor.log_security_event(
                    event_type="suspicious_header",
                    description=f"可疑头部 {header}: {header_value[:50]}...",
                    ip_address=client_ip,
                    user_agent=request.headers.get("user-agent"),
                    severity="medium"
                )
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host if request.client else "unknown"


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF保护中间件"""
    
    def __init__(self, app, enable_csrf: bool = True):
        super().__init__(app)
        self.enable_csrf = enable_csrf
        self.safe_methods = {"GET", "HEAD", "OPTIONS"}
        
    async def dispatch(self, request: Request, call_next):
        if not self.enable_csrf or request.method in self.safe_methods:
            return await call_next(request)
        
        # 检查CSRF token
        csrf_token = request.headers.get("x-csrf-token") or \
                    (await self._get_form_data(request)).get("csrf_token")
        
        if not csrf_token:
            client_ip = self._get_client_ip(request)
            await security_auditor.log_security_event(
                event_type="csrf_token_missing",
                description="CSRF token缺失",
                ip_address=client_ip,
                user_agent=request.headers.get("user-agent"),
                severity="medium"
            )
            
            return JSONResponse(
                status_code=HTTP_403_FORBIDDEN,
                content={
                    "error": "CSRF保护",
                    "detail": "缺少CSRF token"
                }
            )
        
        # 这里应该验证CSRF token的有效性
        # 简化实现，生产环境需要更严格的验证
        if not self._validate_csrf_token(csrf_token):
            client_ip = self._get_client_ip(request)
            await security_auditor.log_security_event(
                event_type="csrf_token_invalid",
                description=f"无效的CSRF token: {csrf_token[:10]}...",
                ip_address=client_ip,
                user_agent=request.headers.get("user-agent"),
                severity="high"
            )
            
            return JSONResponse(
                status_code=HTTP_403_FORBIDDEN,
                content={
                    "error": "CSRF保护",
                    "detail": "无效的CSRF token"
                }
            )
        
        return await call_next(request)
    
    async def _get_form_data(self, request: Request) -> Dict[str, Any]:
        """获取表单数据"""
        try:
            if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
                return dict(await request.form())
        except Exception:
            pass
        return {}
    
    def _validate_csrf_token(self, token: str) -> bool:
        """验证CSRF token"""
        # 简化实现，生产环境需要更复杂的验证逻辑
        return len(token) >= 32 and token.isalnum()
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        return request.client.host if request.client else "unknown"


__all__ = [
    'SecurityHeadersMiddleware',
    'RateLimitMiddleware',
    'IPWhitelistMiddleware',
    'InputValidationMiddleware',
    'CSRFProtectionMiddleware'
]