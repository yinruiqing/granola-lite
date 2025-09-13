"""
安全加固系统
"""

from typing import Dict, Any, List, Optional, Union, Callable
import re
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from ipaddress import ip_address, ip_network
from email_validator import validate_email, EmailNotValidError
import sqlparse
from sqlparse import sql, tokens
from loguru import logger

from app.core.cache import cache_manager
from app.core.monitoring import metrics_collector


class InputValidator:
    """输入验证器"""
    
    def __init__(self):
        self.max_string_length = 10000
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        
        # 常见的恶意模式
        self.malicious_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS
            r'javascript:',  # JavaScript协议
            r'vbscript:',  # VBScript协议
            r'on\w+\s*=',  # 事件处理器
            r'eval\s*\(',  # eval函数
            r'expression\s*\(',  # CSS表达式
            r'<iframe[^>]*>',  # iframe标签
            r'<object[^>]*>',  # object标签
            r'<embed[^>]*>',  # embed标签
            r'<form[^>]*>',  # form标签
        ]
        
        # SQL注入模式
        self.sql_injection_patterns = [
            r'(\bUNION\b.*\bSELECT\b)',
            r'(\bOR\b.*=.*)',
            r'(\bAND\b.*=.*)',
            r'(\bINSERT\b.*\bINTO\b)',
            r'(\bUPDATE\b.*\bSET\b)',
            r'(\bDELETE\b.*\bFROM\b)',
            r'(\bDROP\b.*\bTABLE\b)',
            r'(\bCREATE\b.*\bTABLE\b)',
            r'(\bALTER\b.*\bTABLE\b)',
            r'(\bEXEC\b.*\()',
            r'(\bEXECUTE\b.*\()',
            r'(--.*)',
            r'(/\*.*\*/)',
            r'(\bxp_cmdshell\b)',
            r'(\bsp_executesql\b)',
        ]
    
    def validate_string(
        self, 
        value: str, 
        field_name: str = "input",
        max_length: Optional[int] = None,
        allow_html: bool = False,
        required: bool = True
    ) -> Dict[str, Any]:
        """验证字符串输入"""
        errors = []
        
        # 检查是否为空
        if not value and required:
            errors.append(f"{field_name} 不能为空")
            return {"valid": False, "errors": errors}
        
        if not value:
            return {"valid": True, "sanitized_value": ""}
        
        # 检查长度
        max_len = max_length or self.max_string_length
        if len(value) > max_len:
            errors.append(f"{field_name} 长度不能超过 {max_len} 个字符")
        
        # 检查恶意模式
        sanitized_value = value
        
        if not allow_html:
            # HTML转义
            sanitized_value = self._escape_html(sanitized_value)
            
            # 检查XSS模式
            for pattern in self.malicious_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    errors.append(f"{field_name} 包含潜在的恶意代码")
                    break
        
        # 检查SQL注入
        if self._detect_sql_injection(value):
            errors.append(f"{field_name} 包含潜在的SQL注入代码")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "sanitized_value": sanitized_value
        }
    
    def validate_email(self, email: str) -> Dict[str, Any]:
        """验证邮箱地址"""
        try:
            # 使用email-validator库进行验证
            validated_email = validate_email(email)
            return {
                "valid": True,
                "normalized_email": validated_email.email
            }
        except EmailNotValidError as e:
            return {
                "valid": False,
                "errors": [f"邮箱格式无效: {str(e)}"]
            }
    
    def validate_password(self, password: str) -> Dict[str, Any]:
        """验证密码强度"""
        errors = []
        score = 0
        
        if len(password) < 8:
            errors.append("密码长度至少8位")
        else:
            score += 1
        
        if len(password) >= 12:
            score += 1
        
        if re.search(r'[a-z]', password):
            score += 1
        else:
            errors.append("密码必须包含小写字母")
        
        if re.search(r'[A-Z]', password):
            score += 1
        else:
            errors.append("密码必须包含大写字母")
        
        if re.search(r'\d', password):
            score += 1
        else:
            errors.append("密码必须包含数字")
        
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 1
        else:
            errors.append("密码必须包含特殊字符")
        
        # 检查常见弱密码
        weak_passwords = [
            "password", "123456", "123456789", "qwerty", 
            "abc123", "password123", "admin", "root"
        ]
        
        if password.lower() in weak_passwords:
            errors.append("密码过于简单，请使用更复杂的密码")
            score = 0
        
        strength_level = "weak"
        if score >= 5:
            strength_level = "strong"
        elif score >= 3:
            strength_level = "medium"
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "strength": strength_level,
            "score": score
        }
    
    def validate_file_upload(
        self, 
        filename: str, 
        file_size: int,
        allowed_extensions: List[str] = None,
        max_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """验证文件上传"""
        errors = []
        
        # 检查文件名
        if not filename:
            errors.append("文件名不能为空")
            return {"valid": False, "errors": errors}
        
        # 检查文件扩展名
        if allowed_extensions:
            file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
            if file_ext not in allowed_extensions:
                errors.append(f"不支持的文件类型: .{file_ext}")
        
        # 检查文件大小
        max_file_size = max_size or self.max_file_size
        if file_size > max_file_size:
            errors.append(f"文件大小超过限制: {file_size / 1024 / 1024:.2f}MB > {max_file_size / 1024 / 1024:.2f}MB")
        
        # 检查文件名中的恶意字符
        dangerous_chars = ['..', '/', '\\', '<', '>', ':', '|', '?', '*']
        for char in dangerous_chars:
            if char in filename:
                errors.append("文件名包含非法字符")
                break
        
        # 生成安全的文件名
        safe_filename = self._sanitize_filename(filename)
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "safe_filename": safe_filename
        }
    
    def validate_ip_address(self, ip: str) -> Dict[str, Any]:
        """验证IP地址"""
        try:
            ip_obj = ip_address(ip)
            return {
                "valid": True,
                "ip_version": ip_obj.version,
                "is_private": ip_obj.is_private,
                "is_loopback": ip_obj.is_loopback
            }
        except ValueError as e:
            return {
                "valid": False,
                "errors": [f"无效的IP地址: {str(e)}"]
            }
    
    def validate_url(self, url: str) -> Dict[str, Any]:
        """验证URL"""
        # 简单的URL验证
        url_pattern = re.compile(
            r'^https?://'  # http:// 或 https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # 端口
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            return {
                "valid": False,
                "errors": ["URL格式无效"]
            }
        
        # 检查恶意URL模式
        malicious_url_patterns = [
            r'javascript:',
            r'data:',
            r'vbscript:',
            r'file://',
        ]
        
        for pattern in malicious_url_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return {
                    "valid": False,
                    "errors": ["URL包含潜在恶意协议"]
                }
        
        return {"valid": True}
    
    def _escape_html(self, text: str) -> str:
        """HTML转义"""
        escape_dict = {
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '&': '&amp;'
        }
        
        for char, escaped in escape_dict.items():
            text = text.replace(char, escaped)
        
        return text
    
    def _detect_sql_injection(self, value: str) -> bool:
        """检测SQL注入"""
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        return False
    
    def _sanitize_filename(self, filename: str) -> str:
        """生成安全的文件名"""
        # 移除路径分隔符
        filename = filename.replace('/', '_').replace('\\', '_')
        
        # 移除危险字符
        filename = re.sub(r'[<>:"|?*]', '', filename)
        
        # 限制长度
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            max_name_len = 255 - len(ext) - 1
            filename = name[:max_name_len] + '.' + ext if ext else name[:255]
        
        return filename


class SQLInjectionProtector:
    """SQL注入防护"""
    
    def __init__(self):
        self.dangerous_keywords = [
            'UNION', 'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP',
            'CREATE', 'ALTER', 'EXEC', 'EXECUTE', 'SCRIPT', 'DECLARE'
        ]
    
    def analyze_sql_query(self, query: str) -> Dict[str, Any]:
        """分析SQL查询的安全性"""
        try:
            # 解析SQL
            parsed = sqlparse.parse(query)[0]
            
            analysis = {
                "is_safe": True,
                "warnings": [],
                "dangerous_tokens": [],
                "query_type": None
            }
            
            # 分析tokens
            for token in parsed.flatten():
                token_value = str(token).upper().strip()
                
                # 识别查询类型
                if token.ttype is tokens.Keyword.DML:
                    analysis["query_type"] = token_value
                
                # 检查危险关键词
                if token_value in self.dangerous_keywords:
                    analysis["dangerous_tokens"].append(token_value)
                
                # 检查SQL注释
                if token.ttype in (tokens.Comment.Single, tokens.Comment.Multiline):
                    analysis["warnings"].append("查询包含注释")
                
                # 检查字符串拼接
                if '--' in token_value or '/*' in token_value:
                    analysis["is_safe"] = False
                    analysis["warnings"].append("检测到可能的SQL注入攻击")
            
            # 检查多语句
            if ';' in query and query.count(';') > 1:
                analysis["warnings"].append("检测到多条SQL语句")
            
            return analysis
            
        except Exception as e:
            logger.warning(f"SQL分析失败: {e}")
            return {
                "is_safe": False,
                "warnings": [f"SQL解析错误: {str(e)}"],
                "dangerous_tokens": [],
                "query_type": "unknown"
            }
    
    def sanitize_query_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """清理查询参数"""
        sanitized = {}
        validator = InputValidator()
        
        for key, value in params.items():
            if isinstance(value, str):
                validation_result = validator.validate_string(value, allow_html=False)
                sanitized[key] = validation_result["sanitized_value"]
            else:
                sanitized[key] = value
        
        return sanitized


class RateLimiter:
    """速率限制器"""
    
    def __init__(self):
        self.default_rate_limit = 100  # 每分钟请求数
        self.default_window = 60  # 时间窗口（秒）
        self.burst_limit = 10  # 突发请求限制
    
    async def is_rate_limited(
        self,
        key: str,
        limit: Optional[int] = None,
        window: Optional[int] = None
    ) -> Dict[str, Any]:
        """检查是否触发速率限制"""
        rate_limit = limit or self.default_rate_limit
        time_window = window or self.default_window
        
        current_time = int(time.time())
        window_start = current_time - time_window
        
        # Redis键
        redis_key = f"rate_limit:{key}"
        
        try:
            # 获取当前计数
            current_requests = await cache_manager.redis_client.zcount(
                redis_key, window_start, current_time
            )
            
            if current_requests >= rate_limit:
                # 记录限制指标
                metrics_collector.record_metric("rate_limit_exceeded", 1.0)
                
                # 获取重置时间
                oldest_request = await cache_manager.redis_client.zrange(
                    redis_key, 0, 0, withscores=True
                )
                
                reset_time = int(oldest_request[0][1]) + time_window if oldest_request else current_time + time_window
                
                return {
                    "limited": True,
                    "current_requests": current_requests,
                    "limit": rate_limit,
                    "reset_time": reset_time,
                    "retry_after": reset_time - current_time
                }
            
            # 记录此次请求
            await cache_manager.redis_client.zadd(redis_key, {str(current_time): current_time})
            
            # 清理过期记录
            await cache_manager.redis_client.zremrangebyscore(redis_key, 0, window_start)
            
            # 设置过期时间
            await cache_manager.redis_client.expire(redis_key, time_window)
            
            return {
                "limited": False,
                "current_requests": current_requests + 1,
                "limit": rate_limit,
                "remaining": rate_limit - current_requests - 1
            }
            
        except Exception as e:
            logger.error(f"速率限制检查失败: {e}")
            # 出错时不限制
            return {
                "limited": False,
                "error": str(e)
            }
    
    async def check_burst_limit(self, key: str, limit: Optional[int] = None) -> bool:
        """检查突发请求限制"""
        burst_limit = limit or self.burst_limit
        current_time = int(time.time())
        
        # 1秒内的请求计数
        redis_key = f"burst_limit:{key}"
        
        try:
            current_burst = await cache_manager.redis_client.incr(redis_key)
            
            if current_burst == 1:
                # 设置1秒过期
                await cache_manager.redis_client.expire(redis_key, 1)
            
            return current_burst > burst_limit
            
        except Exception as e:
            logger.error(f"突发限制检查失败: {e}")
            return False


class IPWhitelistManager:
    """IP白名单管理器"""
    
    def __init__(self):
        self.whitelist: List[str] = []
        self.blacklist: List[str] = []
    
    async def load_whitelist(self):
        """加载IP白名单"""
        try:
            whitelist_data = await cache_manager.get("ip_whitelist")
            if whitelist_data:
                self.whitelist = whitelist_data
        except Exception as e:
            logger.warning(f"加载IP白名单失败: {e}")
    
    async def save_whitelist(self):
        """保存IP白名单"""
        try:
            await cache_manager.set("ip_whitelist", self.whitelist, ttl=86400)
        except Exception as e:
            logger.error(f"保存IP白名单失败: {e}")
    
    def is_ip_allowed(self, ip: str) -> bool:
        """检查IP是否被允许"""
        try:
            ip_obj = ip_address(ip)
            
            # 检查黑名单
            for blocked_ip in self.blacklist:
                if '/' in blocked_ip:
                    # CIDR网络
                    if ip_obj in ip_network(blocked_ip, strict=False):
                        return False
                else:
                    # 单个IP
                    if str(ip_obj) == blocked_ip:
                        return False
            
            # 如果有白名单，检查白名单
            if self.whitelist:
                for allowed_ip in self.whitelist:
                    if '/' in allowed_ip:
                        # CIDR网络
                        if ip_obj in ip_network(allowed_ip, strict=False):
                            return True
                    else:
                        # 单个IP
                        if str(ip_obj) == allowed_ip:
                            return True
                return False
            
            # 没有白名单时，只要不在黑名单中就允许
            return True
            
        except Exception as e:
            logger.warning(f"IP检查失败: {e}")
            return True  # 出错时允许访问
    
    async def add_to_whitelist(self, ip: str) -> bool:
        """添加IP到白名单"""
        try:
            # 验证IP格式
            ip_address(ip.split('/')[0])  # 验证IP部分
            
            if ip not in self.whitelist:
                self.whitelist.append(ip)
                await self.save_whitelist()
            
            return True
        except Exception as e:
            logger.error(f"添加IP到白名单失败: {e}")
            return False
    
    async def remove_from_whitelist(self, ip: str) -> bool:
        """从白名单移除IP"""
        try:
            if ip in self.whitelist:
                self.whitelist.remove(ip)
                await self.save_whitelist()
            
            return True
        except Exception as e:
            logger.error(f"从白名单移除IP失败: {e}")
            return False
    
    async def add_to_blacklist(self, ip: str) -> bool:
        """添加IP到黑名单"""
        try:
            # 验证IP格式
            ip_address(ip.split('/')[0])  # 验证IP部分
            
            if ip not in self.blacklist:
                self.blacklist.append(ip)
                await cache_manager.set("ip_blacklist", self.blacklist, ttl=86400)
            
            return True
        except Exception as e:
            logger.error(f"添加IP到黑名单失败: {e}")
            return False


class SecurityAuditor:
    """安全审计器"""
    
    def __init__(self):
        self.audit_log_key = "security_audit_log"
    
    async def log_security_event(
        self,
        event_type: str,
        description: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        severity: str = "medium"
    ):
        """记录安全事件"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "description": description,
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "severity": severity
        }
        
        try:
            # 记录到Redis
            await cache_manager.redis_client.lpush(
                self.audit_log_key,
                str(event)
            )
            
            # 保持最近1000条记录
            await cache_manager.redis_client.ltrim(self.audit_log_key, 0, 999)
            
            # 记录指标
            metrics_collector.record_metric(f"security_event_{event_type}", 1.0)
            
            # 严重事件记录到日志
            if severity in ["high", "critical"]:
                logger.warning(f"安全事件: {event_type} - {description}")
            
        except Exception as e:
            logger.error(f"记录安全事件失败: {e}")
    
    async def get_security_events(
        self,
        limit: int = 100,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取安全事件"""
        try:
            events = await cache_manager.redis_client.lrange(
                self.audit_log_key, 0, limit - 1
            )
            
            parsed_events = []
            for event_str in events:
                try:
                    event = eval(event_str)  # 注意：生产环境应使用json.loads
                    if not event_type or event.get("event_type") == event_type:
                        parsed_events.append(event)
                except Exception:
                    continue
            
            return parsed_events
            
        except Exception as e:
            logger.error(f"获取安全事件失败: {e}")
            return []
    
    async def analyze_security_patterns(self) -> Dict[str, Any]:
        """分析安全模式"""
        try:
            events = await self.get_security_events(limit=1000)
            
            analysis = {
                "total_events": len(events),
                "event_types": {},
                "top_ips": {},
                "severity_distribution": {},
                "recent_events": events[:10] if events else []
            }
            
            for event in events:
                # 统计事件类型
                event_type = event.get("event_type", "unknown")
                analysis["event_types"][event_type] = analysis["event_types"].get(event_type, 0) + 1
                
                # 统计IP
                ip = event.get("ip_address")
                if ip:
                    analysis["top_ips"][ip] = analysis["top_ips"].get(ip, 0) + 1
                
                # 统计严重程度
                severity = event.get("severity", "medium")
                analysis["severity_distribution"][severity] = analysis["severity_distribution"].get(severity, 0) + 1
            
            # 排序top IPs
            analysis["top_ips"] = dict(sorted(
                analysis["top_ips"].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10])
            
            return analysis
            
        except Exception as e:
            logger.error(f"安全模式分析失败: {e}")
            return {}


# 全局实例
input_validator = InputValidator()
sql_protector = SQLInjectionProtector()
rate_limiter = RateLimiter()
ip_whitelist_manager = IPWhitelistManager()
security_auditor = SecurityAuditor()


__all__ = [
    'InputValidator',
    'SQLInjectionProtector',
    'RateLimiter',
    'IPWhitelistManager',
    'SecurityAuditor',
    'input_validator',
    'sql_protector',
    'rate_limiter',
    'ip_whitelist_manager',
    'security_auditor'
]